#include <Wire.h>
#include <WiFi.h>
#include <time.h>
#include <esp_random.h>
#include <ArduinoJson.h>

// ========== НАСТРОЙКИ ==========
const char* ssid = "RT-WiFi-9388";
const char* password = "A78aha6ejh";
const char* computerIP = "192.168.0.14";
const int computerPort = 8888;

const int START_BUFFER_SIZE = 100;
const int MAX_BUFFER_SIZE = 1000;
const int SEND_TIMEOUT = 5000;
const int FORCE_CLEAR_AFTER = 3;
const int DEVICE_ID = 1;

// ========== ПИНЫ ==========
#define ANTENNA_POWER 3
#define ANTENNA_SELECT 14
#define LED_PIN 15

#define I2C_SDA 22
#define I2C_SCL 23
#define LIS3DSH_ADDR 0x19
#define CTRL_REG1 0x20
#define CTRL_REG4 0x23
#define CTRL_REG5 0x24
#define OUT_X_L   0x28

WiFiClient client;

// ========== СТРУКТУРА (ДО использования!) ==========
struct PrimeData {
    uint32_t primeNumber;
    float acceleration;
    uint32_t timestamp;
    uint32_t timePrimeCheck;
    uint32_t timeAccelRead;
};

// ========== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ==========
PrimeData* buffer = nullptr;
int bufferCapacity = START_BUFFER_SIZE;
int bufferIndex = 0;

unsigned long totalChecked = 0;
unsigned long primeCount = 0;
unsigned long startTime = 0;

int failedSendAttempts = 0;
int totalSends = 0;
int totalPrimesSent = 0;

unsigned long totalPrimeCheckTime = 0;
unsigned long totalAccelReadTime = 0;
unsigned long maxPrimeCheckTime = 0;
unsigned long minPrimeCheckTime = 0xFFFFFFFF;
unsigned long maxAccelReadTime = 0;
unsigned long minAccelReadTime = 0xFFFFFFFF;

// Дальше идут функции: modpow, millerTest, isPrime...

// ========== ТЕСТ МИЛЛЕРА-РАБИНА ==========
uint64_t modpow(uint64_t a, uint64_t b, uint64_t m) {
    uint64_t result = 1;
    a %= m;
    while (b) {
        if (b & 1) result = (result * a) % m;
        a = (a * a) % m;
        b >>= 1;
    }
    return result;
}

bool millerTest(uint32_t d, uint32_t n, uint32_t a) {
    uint64_t x = modpow(a, d, n);
    if (x == 1 || x == n - 1) return true;
    
    while (d != n - 1) {
        x = (x * x) % n;
        d <<= 1;
        if (x == 1) return false;
        if (x == n - 1) return true;
    }
    return false;
}

bool isPrimeDeterministic(uint32_t n) {
    if (n < 2) return false;
    if (n == 2 || n == 3) return true;
    if (n % 2 == 0) return false;
    
    uint32_t d = n - 1;
    while (d % 2 == 0) d /= 2;
    
    const uint32_t bases[] = {2, 7, 61};
    for (int i = 0; i < 3; i++) {
        if (bases[i] >= n) continue;
        if (!millerTest(d, n, bases[i])) return false;
    }
    return true;
}

bool isPrimeRandom(uint32_t n, int rounds = 3) {
    if (n < 2) return false;
    if (n == 2 || n == 3) return true;
    if (n % 2 == 0) return false;
    
    uint32_t d = n - 1;
    while (d % 2 == 0) d /= 2;
    
    for (int i = 0; i < rounds; i++) {
        uint32_t a = 2 + (esp_random() % (n - 3));
        if (!millerTest(d, n, a)) return false;
    }
    return true;
}

bool isPrime(uint32_t n) {
    if (n < 1000000) {
        return isPrimeDeterministic(n);
    }
    if (!isPrimeDeterministic(n)) return false;
    return isPrimeRandom(n, 3);
}

// ========== УПРАВЛЕНИЕ БУФЕРОМ ==========
bool resizeBuffer(int newSize) {
    if (newSize > MAX_BUFFER_SIZE) {
        Serial.printf("   ⚠️ Буфер не может быть больше %d\n", MAX_BUFFER_SIZE);
        return false;
    }
    
    PrimeData* newBuffer = (PrimeData*)realloc(buffer, newSize * sizeof(PrimeData));
    if (newBuffer == nullptr) {
        Serial.println("   ❌ Ошибка выделения памяти!");
        return false;
    }
    
    buffer = newBuffer;
    bufferCapacity = newSize;
    Serial.printf("   📦 Буфер изменён: %d -> %d\n", bufferCapacity, newSize);
    return true;
}

void expandBuffer() {
    int newSize = bufferCapacity * 2;
    if (newSize <= MAX_BUFFER_SIZE) {
        Serial.printf("   📈 Расширяем буфер до %d...\n", newSize);
        resizeBuffer(newSize);
    } else if (bufferCapacity < MAX_BUFFER_SIZE) {
        Serial.printf("   📈 Расширяем буфер до максимума %d...\n", MAX_BUFFER_SIZE);
        resizeBuffer(MAX_BUFFER_SIZE);
    } else {
        Serial.println("   ⚠️ Буфер уже максимального размера!");
    }
}

void shrinkBuffer() {
    if (bufferCapacity > START_BUFFER_SIZE) {
        int newSize = START_BUFFER_SIZE;
        Serial.printf("   📉 Сжимаем буфер до %d...\n", newSize);
        resizeBuffer(newSize);
    }
}

void addToBuffer(uint32_t prime, float accel, uint32_t timestamp, 
                 uint32_t primeCheckTime, uint32_t accelReadTime) {
    if (bufferIndex >= bufferCapacity) {
        // Буфер полон - расширяем
        Serial.printf("   ⚠️ Буфер полон (%d), расширяем...\n", bufferCapacity);
        expandBuffer();
        
        // Проверяем, хватило ли места
        if (bufferIndex >= bufferCapacity) {
            Serial.println("   ❌ Невозможно добавить число! Буфер переполнен");
            return;
        }
    }
    
    buffer[bufferIndex].primeNumber = prime;
    buffer[bufferIndex].acceleration = accel;
    buffer[bufferIndex].timestamp = timestamp;
    buffer[bufferIndex].timePrimeCheck = primeCheckTime;
    buffer[bufferIndex].timeAccelRead = accelReadTime;
    bufferIndex++;
    
    // Обновляем статистику
    totalPrimeCheckTime += primeCheckTime;
    totalAccelReadTime += accelReadTime;
    
    if (primeCheckTime > maxPrimeCheckTime) maxPrimeCheckTime = primeCheckTime;
    if (primeCheckTime < minPrimeCheckTime) minPrimeCheckTime = primeCheckTime;
    if (accelReadTime > maxAccelReadTime) maxAccelReadTime = accelReadTime;
    if (accelReadTime < minAccelReadTime) minAccelReadTime = accelReadTime;
    
    Serial.printf("   📝 Буфер: [%d/%d] | Простое: %u | G:%.3f | ⏱️ %d/%dus\n", 
                 bufferIndex, bufferCapacity, prime, accel, primeCheckTime, accelReadTime);
}

// ========== ОТПРАВКА ==========
bool sendBufferAsJSON() {
    if (bufferIndex == 0) return false;
    
    Serial.printf("\n📤 ОТПРАВКА %d чисел (буфер %d)...\n", bufferIndex, bufferCapacity);
    unsigned long sendStart = millis();
    
    // Подключение с повторением
    int attempts = 0;
    while (!client.connect(computerIP, computerPort) && attempts < 3) {
        Serial.printf("   Подключение %d/3...\n", attempts + 1);
        delay(500);
        attempts++;
    }
    
    if (!client.connected()) {
        Serial.println("   ❌ Нет подключения");
        failedSendAttempts++;
        return false;
    }
    
    // Сжатый JSON
    JsonDocument doc;
    doc["d"] = DEVICE_ID;
    doc["b"] = bufferIndex;
    doc["tc"] = totalChecked;
    doc["tp"] = primeCount;
    doc["cap"] = bufferCapacity;  // Текущий размер буфера
    
    JsonArray dataArray = doc["a"].to<JsonArray>();
    
    for (int i = 0; i < bufferIndex; i++) {
        JsonObject item = dataArray.add<JsonObject>();
        item["p"] = buffer[i].primeNumber;
        item["g"] = buffer[i].acceleration;
        item["t"] = buffer[i].timestamp;
        item["pu"] = buffer[i].timePrimeCheck;
        item["au"] = buffer[i].timeAccelRead;
    }
    
    String jsonString;
    serializeJson(doc, jsonString);
    
    Serial.printf("   📦 Размер: %d байт\n", jsonString.length());
    
    client.print(jsonString);
    client.print("\n");
    client.flush();
    
    // Ждем ответ
    unsigned long timeout = millis() + SEND_TIMEOUT;
    bool success = false;
    
    while (!client.available() && millis() < timeout) {
        delay(10);
    }
    
    if (client.available()) {
        String response = client.readString();
        if (response.indexOf("OK") >= 0) {
            unsigned long sendTime = millis() - sendStart;
            success = true;
            totalSends++;
            totalPrimesSent += bufferIndex;
            failedSendAttempts = 0;  // Сбрасываем счетчик ошибок
            
            Serial.printf("   ✅ ОТПРАВЛЕНО! %d чисел, %d байт, %lu мс\n", 
                         bufferIndex, jsonString.length(), sendTime);
            Serial.printf("   📊 Статистика: всего отправок %d, чисел %d\n", 
                         totalSends, totalPrimesSent);
            
            blinkLED();
            
            // Очищаем буфер
            bufferIndex = 0;
            
            // Если буфер был расширен, сжимаем обратно
            if (bufferCapacity > START_BUFFER_SIZE) {
                shrinkBuffer();
            }
        } else {
            Serial.printf("   ⚠️ Ошибка сервера: %s\n", response.c_str());
            failedSendAttempts++;
        }
    } else {
        Serial.println("   ⏰ Таймаут ответа");
        failedSendAttempts++;
    }
    
    client.stop();
    
    // Принудительная очистка при слишком многих ошибках
    if (failedSendAttempts >= FORCE_CLEAR_AFTER && bufferIndex > 0) {
        Serial.printf("\n⚠️ ПРИНУДИТЕЛЬНАЯ ОЧИСТКА! %d попыток отправки не удались\n", failedSendAttempts);
        Serial.printf("   Потеряно %d простых чисел\n", bufferIndex);
        bufferIndex = 0;
        failedSendAttempts = 0;
        
        // Сжимаем буфер, если был расширен
        if (bufferCapacity > START_BUFFER_SIZE) {
            shrinkBuffer();
        }
        
        blinkLED();
        blinkLED();  // Двойной сигнал об ошибке
    }
    
    return success;
}

// ========== ПОЛУЧЕНИЕ ВРЕМЕНИ ==========
uint32_t getUnixTimestamp() {
    struct tm timeinfo;
    if (!getLocalTime(&timeinfo)) {
        return 0;
    }
    time_t t = mktime(&timeinfo);
    return (uint32_t)t;
}

String getHumanTime() {
    struct tm timeinfo;
    if (!getLocalTime(&timeinfo)) {
        return "1970-01-01 00:00:00";
    }
    char buffer[30];
    strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", &timeinfo);
    return String(buffer);
}

// ========== ЧТЕНИЕ LIS3DSH ==========
float readTotalGWithTiming(uint32_t* elapsedMicros) {
    unsigned long start = micros();
    
    Wire.beginTransmission(LIS3DSH_ADDR);
    Wire.write(OUT_X_L | 0x80);
    Wire.endTransmission();
    Wire.requestFrom(LIS3DSH_ADDR, 6);
    
    int16_t rawX = Wire.read() | (Wire.read() << 8);
    int16_t rawY = Wire.read() | (Wire.read() << 8);
    int16_t rawZ = Wire.read() | (Wire.read() << 8);
    
    float ax = rawX * 0.000061f;
    float ay = rawY * 0.000061f;
    float az = rawZ * 0.000061f;
    
    float result = sqrt(ax*ax + ay*ay + az*az);
    
    *elapsedMicros = micros() - start;
    return result;
}

bool isPrimeWithTiming(uint32_t n, uint32_t* elapsedMicros) {
    unsigned long start = micros();
    bool result = isPrime(n);
    *elapsedMicros = micros() - start;
    return result;
}

// ========== LED ==========
void blinkLED() {
    digitalWrite(LED_PIN, HIGH);
    delay(50);
    digitalWrite(LED_PIN, LOW);
}

// ========== СТАТИСТИКА ==========
void printStats() {
    float ratio = (float)primeCount / totalChecked * 100;
    float elapsed = (millis() - startTime) / 1000.0;
    float speed = totalChecked / elapsed;
    
    Serial.println("\n============================================================");
    Serial.printf("📊 СТАТИСТИКА:\n");
    Serial.printf("   Простых: %lu | Проверено: %lu | Отношение: %.4f%%\n", primeCount, totalChecked, ratio);
    Serial.printf("   Буфер: %d/%d | Скорость: %.0f ч/сек\n", bufferIndex, bufferCapacity, speed);
    Serial.printf("\n⏱️  Тайминги (мкс): Prime сред:%4lu accel сред:%4lu\n", 
                 totalPrimeCheckTime / primeCount, totalAccelReadTime / primeCount);
    Serial.printf("📤 Отправки: успешных %d, чисел отправлено %d\n", totalSends, totalPrimesSent);
    if (failedSendAttempts > 0) {
        Serial.printf("⚠️ Неудачных попыток: %d\n", failedSendAttempts);
    }
    Serial.println("============================================================");
}

// ========== ИНИЦИАЛИЗАЦИЯ LIS3DSH ==========
void initLIS3DSH() {
    Wire.beginTransmission(LIS3DSH_ADDR);
    Wire.write(CTRL_REG1);
    Wire.write(0x67);
    Wire.endTransmission();
    
    Wire.beginTransmission(LIS3DSH_ADDR);
    Wire.write(CTRL_REG4);
    Wire.write(0x88);
    Wire.endTransmission();
    
    Wire.beginTransmission(LIS3DSH_ADDR);
    Wire.write(CTRL_REG5);
    Wire.write(0x03);
    Wire.endTransmission();
    
    delay(100);
}

// ========== SETUP ==========
void setup() {
    Serial.begin(115200);
    delay(1000);
    
    Serial.println("\n============================================================");
    Serial.println("   ESP32-C6 + LIS3DSH - АДАПТИВНЫЙ БУФЕР");
    Serial.printf("   Буфер: %d -> %d (макс %d)\n", START_BUFFER_SIZE, MAX_BUFFER_SIZE, MAX_BUFFER_SIZE);
    Serial.println("============================================================");
    
    // Выделяем память для буфера
    buffer = (PrimeData*)malloc(START_BUFFER_SIZE * sizeof(PrimeData));
    if (buffer == nullptr) {
        Serial.println("❌ Ошибка выделения памяти!");
        while(1) delay(1000);
    }
    bufferCapacity = START_BUFFER_SIZE;
    
    pinMode(LED_PIN, OUTPUT);
    pinMode(ANTENNA_POWER, OUTPUT);
    pinMode(ANTENNA_SELECT, OUTPUT);
    
    digitalWrite(ANTENNA_POWER, LOW);
    delay(100);
    digitalWrite(ANTENNA_SELECT, HIGH);
    
    Serial.print("\n📡 Wi-Fi: ");
    Serial.println(ssid);
    WiFi.begin(ssid, password);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("\n   ❌ Ошибка Wi-Fi!");
        while(1) delay(1000);
    }
    
    Serial.println("\n   ✅ Подключен!");
    Serial.printf("   IP: %s\n", WiFi.localIP().toString().c_str());
    
    Serial.println("\n🔄 LIS3DSH...");
    Wire.begin(I2C_SDA, I2C_SCL);
    initLIS3DSH();
    Serial.println("   ✅ Готов");
    
    Serial.println("\n🕒 Синхронизация времени...");
    configTime(3 * 3600, 0, "pool.ntp.org", "time.nist.gov");
    
    time_t now = time(nullptr);
    attempts = 0;
    while (now < 24 * 3600 && attempts < 30) {
        delay(500);
        Serial.print(".");
        attempts++;
        now = time(nullptr);
    }
    
    if (now >= 24 * 3600) {
        Serial.println(" ✅");
        Serial.printf("📅 %s\n", getHumanTime().c_str());
    } else {
        Serial.println(" ⚠️ Время не синхронизировано");
    }
    
    startTime = millis();
    
    Serial.println("\n🎯 СТАРТ!");
    Serial.println("============================================================\n");
}

// ========== LOOP ==========
void loop() {
    uint32_t num = esp_random();
    totalChecked++;
    
    uint32_t primeCheckTime;
    bool isPrimeResult = isPrimeWithTiming(num, &primeCheckTime);
    
    if (isPrimeResult) {
        primeCount++;
        
        uint32_t accelReadTime;
        float accel = readTotalGWithTiming(&accelReadTime);
        uint32_t timestamp = getUnixTimestamp();
        String humanTime = getHumanTime();
        
        Serial.printf("\n✨ #%lu: %u | G:%.3f | ⏱️ %d/%dus\n", 
                     primeCount, num, accel, primeCheckTime, accelReadTime);
        
        // Добавляем в буфер (автоматически расширит если нужно)
        addToBuffer(num, accel, timestamp, primeCheckTime, accelReadTime);
        
        // Пытаемся отправить если достигли целевого размера (START_BUFFER_SIZE)
        // Или если буфер больше целевого
        if (bufferIndex >= START_BUFFER_SIZE || 
            (bufferCapacity > START_BUFFER_SIZE && bufferIndex >= bufferCapacity)) {
            
            Serial.printf("\n🎯 ДОСТИГНУТ РАЗМЕР %d, отправка...\n", 
                         bufferIndex >= START_BUFFER_SIZE ? START_BUFFER_SIZE : bufferCapacity);
            printStats();
            
            sendBufferAsJSON();
        }
        
        // Статистика каждые 50 простых
        if (primeCount % 50 == 0) {
            printStats();
        }
    }
    
    delay(5);
}