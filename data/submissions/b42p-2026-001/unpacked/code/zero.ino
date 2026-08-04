
//═══ ESP32-C6 АГЕНТ #0 v7.0 ═══
//Антенна: ВЫКЛ | Частота датчика: 1600Гц
//Буфер: 252000 байт | RAM: 124636
//...
//WiFi: 192.168.0.46 | MAC: 58:E6:C5:14:2C:0C
//[АГЕНТ #0] ✅ Время синхр.
//[АГЕНТ #0] 📊 СЕССИЯ #1 | прост=2286 пров=46388 | буфер=2286/18000 | g:0.670-1.256 ср=0.979
//[АГЕНТ #0] 📤 2286 зап | задержка 5с
//[АГЕНТ #0] ✅ отправлено 2286 зап (32004 байт)

#include <Wire.h>
#include <WiFi.h>
#include <time.h>
#include <esp_random.h>
#include <math.h>
#include <string.h>

// ========== НАСТРОЙКИ ==========ЗЕМЛЯ, ЗЕЛЕЕЁНАЯ ЗЕЛЕЕЕЕНАЯ
const char* myRlName = "zero(:) 18COM";
const char* ssid     = "RT-WiFi-9388";
const char* password = "A78aha6ejh";
const char* serverIP = "192.168.0.200";
const int   serverPort = 8888;
const int   AGENT_ID = 0;

// ========== АНТЕННА (опционально) ==========
#define ANTENNA_POWER 3
#define ANTENNA_SELECT 14
bool antennaEnabled = false;  // false = без антенны, true = с антенной

// ========== ПИНЫ ==========
#define I2C_SDA 22
#define I2C_SCL 23
#define LED_PIN 15

// ========== LIS3DSH ==========
#define LIS3DSH_ADDR 0x19
#define CTRL_REG1 0x20
#define CTRL_REG4 0x23
#define CTRL_REG5 0x24
#define OUT_X_L   0x28
const float SCALE_4G = 4.0f / 32768.0f;

// ========== ПАРАМЕТРЫ ==========
const int MAX_BUFFER_SIZE  = 18000;
int BUFFER_MODE            = 0;
bool SEND_ENABLED          = true;
int WORK_DURATION          = 5;
int FIX_MODE               = 0;
char FIX_ORDER[]           = "TGD";
char PRIME_ORDER[]         = "TG";
int SEND_DELAY_SEC         = 5;
int SENSOR_HZ              = 1600;  // частота датчика (обновляется с сервера)

// ========== СОСТОЯНИЕ ==========
unsigned long totalChecked    = 0;
unsigned long totalPrimes     = 0;
int           sessionCount    = 0;
unsigned long scanStartUs     = 0;
int           overwrites      = 0;
bool          stoppedByBuffer = false;
bool          timeSynced      = false;
int           sendErrors      = 0;
int           sensorErrors    = 0;
int           sensorResets    = 0;
bool          sensorOK        = true;

// ========== СТРУКТУРЫ ==========
#pragma pack(push, 1)
struct PrimeData {
    uint32_t prime;
    float    g;
    uint32_t timestamp_us;
    uint16_t checked_since;
};

struct BinaryHeader {
    uint32_t magic;
    uint8_t  mac[6];
    uint8_t  buffer_mode;
    uint8_t  agent_id;
    uint32_t count;
    uint32_t total_checked;
    uint32_t total_primes;
    uint32_t session_start;
    uint32_t duration_sec;
    uint8_t  forced;
    uint8_t  fix_mode;
    uint8_t  time_synced;
    uint8_t  sensor_ok;
    uint16_t overwrites;
    uint16_t send_errors;
    uint32_t total_checked_all;
    uint32_t total_primes_all;
};
#pragma pack(pop)

PrimeData* buffer      = nullptr;
int        writeIndex  = 0;
int        readIndex   = 0;
int        bufferItems = 0;
bool       bufferFull  = false;
WiFiClient client;

const uint16_t smallPrimes[] = {
    3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97,
    101,103,107,109,113,127,131,137,139,149,151,157,163,167,173,179,181,191,193,197,199,
    211,223,227,229,233,239,241,251,257,263,269,271,277,281,283,293,307,311,313,317,331,
    337,347,349,353,359,367,373,379,383,389,397,401,409,419,421,431,433,439,443,449,457,
    461,463,467,479,487,491,499,503,509,521,523,541,547,557,563,569,571,577,587,593,599,
    601,607,613,617,619,631,641,643,647,653,659,661,673,677,683,691,701,709,719,727,733,
    739,743,751,757,761,769,773,787,797,809,811,821,823,827,829,839,853,857,859,863,877,
    881,883,887,907,911,919,929,937,941,947,953,967,971,977,983,991,997
};
const int smallPrimesCount = sizeof(smallPrimes) / sizeof(smallPrimes[0]);

bool isPrimeFast(uint32_t n) {
    if (n < 2) return false;
    if (n == 2) return true;
    if (n % 2 == 0) return false;
    for (int i = 0; i < smallPrimesCount; i++) {
        uint32_t p = smallPrimes[i];
        if (p * p > n) return true;
        if (n % p == 0) return false;
    }
    uint32_t d = n - 1;
    while (d % 2 == 0) d /= 2;
    const uint32_t bases[] = {2, 7, 61};
    for (int i = 0; i < 3; i++) {
        uint32_t a = bases[i];
        if (a >= n) continue;
        uint64_t x = 1, base = a, exp = d;
        while (exp) {
            if (exp & 1) x = (x * base) % n;
            base = (base * base) % n;
            exp >>= 1;
        }
        if (x == 1 || x == n - 1) continue;
        bool composite = true;
        for (uint32_t r = d; r != n - 1; r <<= 1) {
            x = (x * x) % n;
            if (x == 1) return false;
            if (x == n - 1) { composite = false; break; }
        }
        if (composite) return false;
    }
    return true;
}

void blinkQuick() { digitalWrite(LED_PIN, HIGH); delayMicroseconds(50); digitalWrite(LED_PIN, LOW); }
void blinkLED(int times, int ms) { for(int i=0;i<times;i++){ digitalWrite(LED_PIN,HIGH); delay(ms); digitalWrite(LED_PIN,LOW); delay(ms); } }

void initLIS3DSH() {
    uint8_t reg1_val;
    switch (SENSOR_HZ) {
        case 100:  reg1_val = 0x67; break;
        case 400:  reg1_val = 0x7F; break;
        case 800:  reg1_val = 0x8F; break;
        case 1600: reg1_val = 0x9F; break;
        default:   reg1_val = 0x9F; break;
    }
    Wire.beginTransmission(LIS3DSH_ADDR); Wire.write(CTRL_REG1); Wire.write(reg1_val); Wire.endTransmission();
    Wire.beginTransmission(LIS3DSH_ADDR); Wire.write(CTRL_REG4); Wire.write(0x90); Wire.endTransmission();
    Wire.beginTransmission(LIS3DSH_ADDR); Wire.write(CTRL_REG5); Wire.write(0x03); Wire.endTransmission();
    delay(200);
}

float readAccel() {
    int16_t rawX = 0, rawY = 0, rawZ = 0;
    
    Wire.beginTransmission(LIS3DSH_ADDR);
    Wire.write(OUT_X_L | 0x80);
    if (Wire.endTransmission() != 0) {
        sensorErrors++;
        if (sensorErrors >= 6) {
            sensorOK = false;
            if (sensorErrors == 6) {
                Serial.printf("[АГЕНТ #%d] 🔄 ПЕРЕЗАГРУЗКА ДАТЧИКА (ошибок I2C: %d)\n", AGENT_ID, sensorErrors);
                initLIS3DSH();
                sensorResets++;
                sensorErrors = 0;
                sensorOK = true;
            }
        }
        return -1.0f;
    }
    
    Wire.requestFrom(LIS3DSH_ADDR, 6);
    if (Wire.available() < 6) {
        sensorErrors++;
        if (sensorErrors >= 6) {
            sensorOK = false;
            if (sensorErrors == 6) {
                Serial.printf("[АГЕНТ #%d] 🔄 ПЕРЕЗАГРУЗКА ДАТЧИКА (нет данных: %d байт)\n", AGENT_ID, Wire.available());
                initLIS3DSH();
                sensorResets++;
                sensorErrors = 0;
                sensorOK = true;
            }
        }
        return -1.0f;
    }
    
    rawX = Wire.read() | (Wire.read() << 8);
    rawY = Wire.read() | (Wire.read() << 8);
    rawZ = Wire.read() | (Wire.read() << 8);
    
    if (abs(rawX) > 32767 || abs(rawY) > 32767 || abs(rawZ) > 32767) {
        sensorErrors++;
        return -1.0f;
    }
    
    sensorErrors = 0;
    sensorOK = true;
    
    float ax = rawX * SCALE_4G;
    float ay = rawY * SCALE_4G;
    float az = rawZ * SCALE_4G;
    float g = sqrt(ax*ax + ay*ay + az*az);
    if (g > 100.0f || g < -10.0f) return -1.0f;
    return g;
}

bool syncTime() {
    configTime(3*3600, 0, "ntp1.vniiftri.ru", "ntp2.vniiftri.ru", "pool.ntp.org");
    time_t now = time(nullptr); int a = 0;
    while (now < 1000000 && a < 20) { delay(500); now = time(nullptr); a++; }
    timeSynced = (now > 1000000);
    Serial.println(timeSynced ? "[АГЕНТ #" + String(AGENT_ID) + "] ✅ Время синхр." : "[АГЕНТ #" + String(AGENT_ID) + "] ⚠️ NTP не ответил");
    return timeSynced;
}

bool syncTimeFast() {
    configTime(3*3600, 0, "pool.ntp.org", "time.nist.gov");
    for (int i=1; i<=3; i++) { if (time(nullptr)>1000000) { timeSynced=true; return true; } if (i<3) delay(2000); }
    timeSynced = false; return false;
}

void waitForNextMinute() {
    if (!timeSynced) { delay(10000); return; }
    struct tm ti; if (!getLocalTime(&ti, 2000)) { delay(10000); return; }
    int w = (60-ti.tm_sec)*1000; if (w<100) w+=60000;
    delay(w);
}

void addToBuffer(uint32_t prime, float g, uint32_t ts, uint16_t cs) {
    if (BUFFER_MODE==2) return;
    if (BUFFER_MODE==1 && bufferFull) return;
    PrimeData d; d.prime=prime; d.g=g; d.timestamp_us=ts; d.checked_since=cs;
    buffer[writeIndex]=d; writeIndex=(writeIndex+1)%MAX_BUFFER_SIZE;
    if (bufferItems<MAX_BUFFER_SIZE) bufferItems++;
    else { if (BUFFER_MODE==0) { readIndex=(readIndex+1)%MAX_BUFFER_SIZE; overwrites++; } else { bufferFull=true; writeIndex=(writeIndex-1+MAX_BUFFER_SIZE)%MAX_BUFFER_SIZE; } }
}

bool sendMessage(const String& msg) {
    for (int attempt=0; attempt<3; attempt++) {
        if (client.connect(serverIP, serverPort)) { client.print(msg+"\n"); client.flush(); delay(200); client.stop(); return true; }
        delay(1000);
    }
    return false;
}

void sendError(const String& code) {
    String msg = "ERROR|" + WiFi.macAddress() + "|code=" + code + "|agent=" + String(AGENT_ID);
    if (code == "sensor_error") {
        msg += "|sensor_resets=" + String(sensorResets) + "|sensor_errors=" + String(sensorErrors);
    }
    sendMessage(msg);
}

void sendWarning(const String& reason) {
    sendMessage("WARN|"+WiFi.macAddress()+"|reason="+reason+"|agent="+String(AGENT_ID));
}

bool sendBuffer() {
    if (bufferItems==0) return true;
    Serial.printf("[АГЕНТ #%d] 📤 %d зап | задержка %dс\n", AGENT_ID, bufferItems, SEND_DELAY_SEC);
    delay(SEND_DELAY_SEC*1000);

    if (WiFi.status()!=WL_CONNECTED) { WiFi.reconnect(); int a=0; while (WiFi.status()!=WL_CONNECTED && a<30) { delay(500); a++; } if (WiFi.status()!=WL_CONNECTED) { sendErrors++; return false; } }

    for (int attempt=0; attempt<3; attempt++) {
        client.setTimeout(10);
        if (!client.connect(serverIP, serverPort)) { delay(2000); continue; }

        BinaryHeader h; memset(&h, 0, sizeof(h));
        h.magic=0xDEADBEEF; WiFi.macAddress(h.mac);
        h.buffer_mode=BUFFER_MODE; h.agent_id=AGENT_ID; h.count=bufferItems;
        h.total_checked=totalChecked; h.total_primes=totalPrimes;
        h.session_start=timeSynced?time(nullptr)-WORK_DURATION:0; h.duration_sec=WORK_DURATION;
        h.forced=stoppedByBuffer?1:0; h.fix_mode=FIX_MODE; h.time_synced=timeSynced?1:0; h.sensor_ok=sensorOK?1:0;
        h.overwrites=overwrites; h.send_errors=sendErrors; h.total_checked_all=totalChecked; h.total_primes_all=totalPrimes;

        if (client.write((uint8_t*)&h, sizeof(h))!=sizeof(h)) { client.stop(); continue; }

        int start=readIndex; bool sendOK=true; size_t totalSent=0;
        for (int i=0; i<bufferItems; i++) {
            int idx=(start+i)%MAX_BUFFER_SIZE;
            if (client.write((uint8_t*)&buffer[idx], sizeof(PrimeData))!=sizeof(PrimeData)) { sendOK=false; break; }
            totalSent+=sizeof(PrimeData);
            if (i%50==49) { client.flush(); delay(10); }
            if (i%500==499) yield();
        }
        if (!sendOK) { client.stop(); continue; }
        client.flush(); delay(10);

        unsigned long to=millis()+15000; bool ok=false;
        while (!client.available() && millis()<to) yield();
        if (client.available()) { String r=client.readStringUntil('\n'); ok=r.startsWith("OK"); }
        client.stop();

        if (ok) {
            Serial.printf("[АГЕНТ #%d] ✅ отправлено %d зап (%d байт)\n", AGENT_ID, bufferItems, totalSent);
            readIndex=0; writeIndex=0; bufferItems=0; bufferFull=false; overwrites=0; stoppedByBuffer=false; sendErrors=0;
            return true;
        }
        Serial.printf("[АГЕНТ #%d] ⚠️ попытка %d не удалась\n", AGENT_ID, attempt+1);
        delay(1000);
    }
    sendErrors++;
    Serial.printf("[АГЕНТ #%d] ❌ отправка не удалась (%d ошибок)\n", AGENT_ID, sendErrors);
    return false;
}

bool fetchConfig() {
    for (int attempt=0; attempt<3; attempt++) {
        if (!client.connect(serverIP, serverPort)) { delay(1000); continue; }
        client.print("CFG|"+WiFi.macAddress()+"|agent="+String(AGENT_ID)+"\n"); client.flush();
        unsigned long t=millis()+5000; bool ok=false;
        while (!client.available() && millis()<t) yield();
        if (client.available()) { String r=client.readStringUntil('\n');
            if (r.startsWith("CFG|")) {
                int p;
                p=r.indexOf("duration="); if(p>0){ int v=r.substring(p+9).toInt(); WORK_DURATION=(v>0&&v<=30)?v:WORK_DURATION; }
                p=r.indexOf("buffer_mode="); if(p>0){ int v=r.substring(p+12).toInt(); BUFFER_MODE=(v>=0&&v<=2)?v:BUFFER_MODE; }
                p=r.indexOf("fix_mode="); if(p>0){ int v=r.substring(p+9).toInt(); FIX_MODE=(v>=0&&v<=1)?v:FIX_MODE; }
                p=r.indexOf("send_enabled="); if(p>0) SEND_ENABLED=(r.substring(p+13).toInt()==1);
                p=r.indexOf("delay_sec="); if(p>0) SEND_DELAY_SEC=r.substring(p+10).toInt();
                p=r.indexOf("sensor_hz="); if(p>0){ int v=r.substring(p+10).toInt(); if(v==100||v==400||v==800||v==1600){ SENSOR_HZ=v; initLIS3DSH(); } }
                p=r.indexOf("fix_order="); if(p>0){ String o=r.substring(p+10,p+13); if(o.length()==3) strncpy(FIX_ORDER,o.c_str(),3); }
                p=r.indexOf("prime_order="); if(p>0){ String o=r.substring(p+12,p+14); if(o.length()==2) strncpy(PRIME_ORDER,o.c_str(),2); }
                ok=true;
            }
        }
        client.stop();
        if (ok) return true;
    }
    return false;
}

void runSession() {
    unsigned long cs=0, sCh=0, sPr=0; float gMin=999, gMax=-999, gSum=0; int vG=0;
    stoppedByBuffer=false;
    uint32_t endTime=timeSynced?(time(nullptr)+WORK_DURATION):(millis()/1000+WORK_DURATION);
    unsigned long lastLog=millis();

    while (true) {
        uint32_t ct=timeSynced?time(nullptr):(millis()/1000);
        if (ct>=endTime) break;
        if (BUFFER_MODE==1 && bufferFull) { stoppedByBuffer=true; break; }

        uint32_t num, ts=0; float g=0; bool prime=false; cs++;

        if (FIX_MODE==0) { num=esp_random(); prime=isPrimeFast(num); if (prime) { for (int i=0;i<2;i++) { if (PRIME_ORDER[i]=='T') ts=micros()-scanStartUs; if (PRIME_ORDER[i]=='G') g=readAccel(); } } }
        else { for (int i=0;i<3;i++) { if (FIX_ORDER[i]=='T') ts=micros()-scanStartUs; if (FIX_ORDER[i]=='G') g=readAccel(); if (FIX_ORDER[i]=='D') num=esp_random(); } prime=isPrimeFast(num); }

        sCh++; totalChecked++;
        if (prime) { sPr++; totalPrimes++; if (g>=0) { if (g<gMin) gMin=g; if (g>gMax) gMax=g; gSum+=g; vG++; } addToBuffer(num,g,ts,(uint16_t)cs); cs=0; blinkQuick(); }

        if (millis()-lastLog>=10000) { lastLog=millis(); Serial.printf("[АГЕНТ #%d] 🔄 %luсек | пров=%lu | прост=%lu | буфер=%d/%d | RAM=%d | датчик=%s | %dГц\n", AGENT_ID, endTime-ct, sCh, sPr, bufferItems, MAX_BUFFER_SIZE, ESP.getFreeHeap(), sensorOK?"OK":"ERR", SENSOR_HZ); }
        if (sCh%1000==0) yield();
    }
    Serial.printf("[АГЕНТ #%d] 📊 СЕССИЯ #%d | прост=%lu пров=%lu | буфер=%d/%d", AGENT_ID, sessionCount, sPr, sCh, bufferItems, MAX_BUFFER_SIZE);
    if (vG>0) Serial.printf(" | g:%.3f-%.3f ср=%.3f", gMin, gMax, gSum/vG);
    if (sensorResets>0) Serial.printf(" | перезагрузок датчика: %d", sensorResets);
    if (antennaEnabled) Serial.printf(" | антенна: ВКЛ");
    Serial.println();
}

void runSessionSilent() {
    while (true) { if (isPrimeFast(esp_random())) { totalPrimes++; blinkQuick(); } totalChecked++; if (totalChecked%10000==0) yield(); }
}

void setup() {
    Serial.begin(115200); delay(1000);
    pinMode(LED_PIN, OUTPUT); digitalWrite(LED_PIN, LOW);
    
    // Антенна
    if (antennaEnabled) {
        pinMode(ANTENNA_POWER, OUTPUT);
        pinMode(ANTENNA_SELECT, OUTPUT);
        digitalWrite(ANTENNA_POWER, LOW);
        delay(100);
        digitalWrite(ANTENNA_SELECT, HIGH);
    }

    Serial.printf("\n═══ ESP32-C6 АГЕНТ #%d v7.0 ═══\n", AGENT_ID);
    Serial.printf("Антенна: %s | Частота датчика: %dГц\n", antennaEnabled?"ВКЛ":"ВЫКЛ", SENSOR_HZ);
    
    buffer=(PrimeData*)malloc(MAX_BUFFER_SIZE*sizeof(PrimeData));
    Serial.printf("Буфер: %d байт | RAM: %d\n", MAX_BUFFER_SIZE*(int)sizeof(PrimeData), ESP.getFreeHeap());
    
    WiFi.setAutoReconnect(true);
    WiFi.mode(WIFI_STA); WiFi.begin(ssid, password);
    while (WiFi.status()!=WL_CONNECTED) { delay(500); Serial.print("."); }
    Serial.printf("\nWiFi: %s | MAC: %s\n", WiFi.localIP().toString().c_str(), WiFi.macAddress().c_str());
    
    Wire.begin(I2C_SDA, I2C_SCL); Wire.setClock(400000); initLIS3DSH();
    syncTime(); scanStartUs=micros();
}

void loop() {
    if (WORK_DURATION==0) { delay(60000); return; }
    if (BUFFER_MODE==2) { runSessionSilent(); return; }

    if (!timeSynced && BUFFER_MODE!=2) { sendError("time_not_synced"); for (int i=0;i<3;i++) { if (syncTime()) break; delay(5000); } if (!timeSynced) { delay(30000); return; } }

    waitForNextMinute(); sessionCount++; runSession();
    if (!sensorOK) { sendError("sensor_error"); }
    if (stoppedByBuffer) sendWarning("buffer_full_before_time");

    if (SEND_ENABLED) { if (!sendBuffer() && sendErrors>=5) { sendError("send_failed_repeatedly"); readIndex=0; writeIndex=0; bufferItems=0; bufferFull=false; overwrites=0; sendErrors=0; } }

    syncTimeFast(); fetchConfig(); scanStartUs=micros(); blinkLED(5, 100);
}