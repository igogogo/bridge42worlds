# -*- coding: utf-8 -*-
import socket
import struct
import os
import threading
import time
import yaml
from datetime import datetime

PORT = 8888
DATA_DIR = "./data"
BIN_DIR = os.path.join(DATA_DIR, "bin")
CSV_DIR = os.path.join(DATA_DIR, "csv")
HEADERS_FILE = os.path.join(DATA_DIR, "headers.csv")
SERVER_LOG = os.path.join(DATA_DIR, "server.log")
CONFIG_LOG = os.path.join(DATA_DIR, "config_history.log")
CONFIG_FILE = "config.yaml"

DEFAULT_CONFIG = {
    'session_duration': 5,
    'buffer_mode': 0,
    'fix_mode': 0,
    'send_enabled': True,
    'fix_order': 'TGD',
    'prime_order': 'TG',
    'sensor_hz': 1600,
    'agents': {i: {'delay_sec': i * 5} for i in range(1, 11)}
}

HEADER_FORMAT = '<I6sBBIIIIIBBBBHHII'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
RECORD_FORMAT = '<IfIH'
RECORD_SIZE = struct.calcsize(RECORD_FORMAT)

file_lock = threading.Lock()
agent_info = {}
last_config_hash = None


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                c = yaml.safe_load(f)
                for k in DEFAULT_CONFIG:
                    if k not in c: c[k] = DEFAULT_CONFIG[k]
                return c
        except:
            pass
    return DEFAULT_CONFIG.copy()


def config_to_line(config):
    """Одна строка с ключевыми параметрами конфига."""
    bm = config.get('buffer_mode', 0)
    fm = config.get('fix_mode', 0)
    sh = config.get('sensor_hz', 1600)
    fo = config.get('fix_order', 'TGD')
    po = config.get('prime_order', 'TG')
    dur = config.get('session_duration', 5)
    se = config.get('send_enabled', True)
    buf_names = {0: 'КОЛЬЦО', 1: 'ОСТАНОВКА', 2: 'ТИШИНА'}
    fix_names = {0: 'A', 1: 'B'}
    return (f"dur={dur}s | buf={buf_names.get(bm, '?')} | fix={fix_names.get(fm, '?')} | "
            f"order={fo}/{po} | hz={sh} | send={1 if se else 0}")


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"{ts} | {level:8} | {msg}"
    print(line)
    with file_lock:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SERVER_LOG, 'a', encoding='utf-8') as f:
            f.write(line + "\n")


def log_config_change(config):
    """Логировать изменение конфигурации."""
    global last_config_hash
    cfg_line = config_to_line(config)
    cfg_hash = hash(cfg_line)
    if cfg_hash != last_config_hash:
        last_config_hash = cfg_hash
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with file_lock:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(CONFIG_LOG, 'a', encoding='utf-8') as f:
                f.write(f"{ts} | {cfg_line}\n")
        log(f"КОНФИГ | {cfg_line}", "CONFIG")


def print_banner():
    print("""
+======================================================================+
|                                                                      |
|   ESP32-C6  DATA SERVER  v7.1                                        |
|                                                                      |
+======================================================================+
  Давным-давно, в далёкой-далёкой лаборатории...
  ...группа исследователей развернула кольцо из десяти ESP32-C6.
  И да пребудет с вами Сила.
======================================================================
""")


def print_config(config):
    buf_names = {0: 'КОЛЬЦЕВОЙ', 1: 'ОСТАНОВКА', 2: 'ТИШИНА'}
    fix_names = {0: 'A - после простого', 1: 'B - при генерации'}
    print("+----------------------------------------------------------------------+")
    print("|  ТЕКУЩАЯ КОНФИГУРАЦИЯ                                               |")
    print("+----------------------------------------------------------------------+")
    print(f"|  session_duration = {config.get('session_duration', 5):>3} сек      - длительность сессии         |")
    bm = config.get('buffer_mode', 0)
    print(f"|  buffer_mode      = {bm:>3}            - {buf_names.get(bm, '?')}                       |")
    fm = config.get('fix_mode', 0)
    print(f"|  fix_mode         = {fm:>3}            - {fix_names.get(fm, '?')}         |")
    print(f"|  send_enabled     = {str(config.get('send_enabled', True)):>5}       - отправка данных               |")
    print(f"|  sensor_hz        = {config.get('sensor_hz', 1600):>4}          - частота датчика                |")
    print(f"|  fix_order        = {config.get('fix_order', 'TGD'):>5}         - порядок в режиме B            |")
    print(f"|  prime_order      = {config.get('prime_order', 'TG'):>5}         - порядок в режиме A            |")
    print("+----------------------------------------------------------------------+")
    print("|  АГЕНТЫ:                                                            |")
    agents_cfg = config.get('agents', {})
    for aid in sorted(agents_cfg.keys()):
        cfg = agents_cfg[aid]
        delay = cfg.get('delay_sec', aid * 5)
        real_mac = '?'
        for m, info in agent_info.items():
            if info.get('agent_id') == aid: real_mac = m; break
        delta_str = ""
        if real_mac != '?' and real_mac in agent_info:
            delta = (datetime.now() - agent_info[real_mac]['last_seen']).total_seconds()
            if delta > 60:
                delta_str = f" ⚠ ОФЛАЙН ({delta:.0f}сек)"
            elif delta < 120:
                delta_str = f" ({delta:.0f}сек назад)"
        print(f"|    #{aid:>2}: задержка {delay:>2}сек | MAC: {real_mac}{delta_str}")
    print("+----------------------------------------------------------------------+\n")
    # Одна строка с ключевыми параметрами
    print(f"  ▶ {config_to_line(config)}\n")


def save_headers_csv(header, filename, mac):
    (_, mac_bytes, bm, aid, cnt, tc, tp, ss, dur, forced, fm, tsyn, sok, ow, se, tca, tpa) = header
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with file_lock:
        os.makedirs(DATA_DIR, exist_ok=True)
        fe = os.path.exists(HEADERS_FILE)
        with open(HEADERS_FILE, 'a', encoding='utf-8') as f:
            if not fe:
                f.write(
                    "datetime,mac,agent_id,buffer_mode,count,checked,primes,session_start,duration_sec,fix_mode,time_synced,sensor_ok,overwrites,forced,send_errors,filename\n")
            f.write(
                f"{ts},{mac},{aid},{bm},{cnt},{tc},{tp},{ss},{dur},{fm},{tsyn},{sok},{ow},{forced},{se},{filename}\n")


def save_session(mac, header, records):
    (_, mac_bytes, bm, aid, cnt, tc, tp, ss, dur, forced, fm, tsyn, sok, ow, se, tca, tpa) = header
    agent_info[mac] = {'agent_id': aid, 'last_seen': datetime.now(), 'errors': se}
    session_time = datetime.fromtimestamp(ss) if ss > 1000000 else datetime.now()
    date_dir = session_time.strftime("%Y%m%d")
    minute_dir = session_time.strftime("%H%M")
    mac_safe = mac.replace(':', '_')
    bin_subdir = os.path.join(BIN_DIR, date_dir, minute_dir)
    csv_subdir = os.path.join(CSV_DIR, date_dir, minute_dir)
    os.makedirs(bin_subdir, exist_ok=True)
    os.makedirs(csv_subdir, exist_ok=True)
    bin_file = os.path.join(bin_subdir, f"{mac_safe}.bin")
    csv_file = os.path.join(csv_subdir, f"{mac_safe}.csv")

    # Бинарный файл — пишем как есть
    with open(bin_file, 'wb') as f:
        f.write(struct.pack(HEADER_FORMAT, *header))
        for rec in records:
            f.write(struct.pack(RECORD_FORMAT, *rec))

    # CSV — нормализуем timestamp_us, вычитая минимум
    min_ts = min(r[2] for r in records) if records else 0

    with open(csv_file, 'w', encoding='utf-8') as f:
        f.write("agent_id,prime,g,timestamp_us,checked_since\n")
        for prime, g, ts_us, checked in records:
            f.write(f"{aid},{prime},{g:.6f},{ts_us - min_ts},{checked}\n")

    rel_path = f"bin/{date_dir}/{minute_dir}/{mac_safe}.bin"
    save_headers_csv(header, rel_path, mac)
    buf_s = ["КОЛЬЦО", "СТОП", "ТИШИНА"][bm] if bm < 3 else "?"

    # Логируем конфиг при каждом получении данных
    config = load_config()
    log_config_change(config)

    log(f"АГЕНТ #{aid} | {mac} | {cnt} зап | {buf_s} | {'A' if fm == 0 else 'B'} | {dur}с{' FORCED' if forced else ''} | время={'OK' if tsyn else 'N/A'} | датчик={'OK' if sok else 'ERR'} | {rel_path}",
        "DATA")

def check_offline_agents():
    now = datetime.now()
    for mac, info in list(agent_info.items()):
        delta = (now - info['last_seen']).total_seconds()
        if delta > 60:
            config = load_config()
            cfg_line = config_to_line(config)
            log(f"ОФЛАЙН | агент #{info['agent_id']} | {mac} | {delta:.0f}сек | конфиг: {cfg_line}", "WARN")


def offline_monitor():
    while True:
        time.sleep(30)
        check_offline_agents()


def handle_client(sock, addr):
    try:
        sock.settimeout(60)
        fb = sock.recv(1)
        if not fb: return

        if fb == b'C':
            rest = sock.recv(256).decode('utf-8', errors='ignore').strip()
            if rest.startswith("FG|"):
                parts = rest[3:].split('|')
                mac = parts[0]
                agent_id = 1
                for p in parts[1:]:
                    if p.startswith("agent="): agent_id = int(p.split('=')[1])
                agent_info[mac] = {'agent_id': agent_id, 'last_seen': datetime.now(), 'errors': 0}
                config = load_config()
                log_config_change(config)
                ac = config.get('agents', {}).get(agent_id, {'delay_sec': agent_id * 5})
                delay_sec = ac.get('delay_sec', agent_id * 5)
                resp = f"CFG|duration={config.get('session_duration', 5)}|buffer_mode={config.get('buffer_mode', 0)}|fix_mode={config.get('fix_mode', 0)}|send_enabled={1 if config.get('send_enabled', True) else 0}|delay_sec={delay_sec}|sensor_hz={config.get('sensor_hz', 1600)}|fix_order={config.get('fix_order', 'TGD')}|prime_order={config.get('prime_order', 'TG')}\n"
                sock.send(resp.encode())
            return

        if fb == b'E':
            rest = sock.recv(512).decode('utf-8', errors='ignore').strip()
            if rest.startswith("RROR|"):
                parts = rest[5:].split('|')
                mac = parts[0] if parts else "?"
                code = "unknown";
                agent_id = 0;
                sensor_resets = 0;
                sensor_errors = 0
                for p in parts[1:]:
                    if p.startswith("code="): code = p.split('=')[1]
                    if p.startswith("agent="): agent_id = int(p.split('=')[1])
                    if p.startswith("sensor_resets="): sensor_resets = int(p.split('=')[1])
                    if p.startswith("sensor_errors="): sensor_errors = int(p.split('=')[1])
                detail = ""
                if code == "sensor_error":
                    detail = f" | перезагрузок: {sensor_resets} | ошибок: {sensor_errors}"
                elif code == "time_not_synced":
                    detail = " | NTP недоступен"
                elif code == "send_failed_repeatedly":
                    detail = " | буфер очищен"
                config = load_config()
                log_config_change(config)
                log(f"ОШИБКА | агент #{agent_id} | {mac} | {code}{detail} | конфиг: {config_to_line(config)}", "ERROR")
            sock.send(b"OK\n")
            return

        if fb == b'W':
            rest = sock.recv(512).decode('utf-8', errors='ignore').strip()
            if rest.startswith("ARN|"):
                parts = rest[4:].split('|')
                mac = parts[0] if parts else "?"
                reason = "unknown";
                agent_id = 0
                for p in parts[1:]:
                    if p.startswith("reason="): reason = p.split('=')[1]
                    if p.startswith("agent="): agent_id = int(p.split('=')[1])
                config = load_config()
                log(f"WARN | агент #{agent_id} | {mac} | {reason} | конфиг: {config_to_line(config)}", "WARN")
            sock.send(b"OK\n")
            return

        hd = fb + sock.recv(HEADER_SIZE - 1)
        if len(hd) != HEADER_SIZE: sock.send(b"ERROR\n"); return
        header = struct.unpack(HEADER_FORMAT, hd)
        if header[0] != 0xDEADBEEF: sock.send(b"ERROR\n"); return
        mac = ':'.join(f'{b:02X}' for b in header[1])
        count = header[4]
        data_size = count * RECORD_SIZE
        data = b''
        while len(data) < data_size:
            chunk = sock.recv(min(8192, data_size - len(data)))
            if not chunk: break
            data += chunk
        if len(data) != data_size:
            log(f"НЕПОЛНЫЕ ДАННЫЕ | {mac} | {len(data)}/{data_size} байт", "ERROR")
            sock.send(b"ERROR\n");
            return
        records = []
        for i in range(count):
            off = i * RECORD_SIZE
            try:
                records.append(struct.unpack(RECORD_FORMAT, data[off:off + RECORD_SIZE]))
            except:
                break
        if len(records) != count: sock.send(b"ERROR\n"); return
        save_session(mac, header, records)
        sock.send(b"OK\n")
    except socket.timeout:
        log(f"ТАЙМАУТ | {addr[0]}", "TIMEOUT")
    except Exception as e:
        log(f"ОШИБКА | {addr[0]} | {e}", "ERROR")
    finally:
        try:
            sock.close()
        except:
            pass


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BIN_DIR, exist_ok=True)
    os.makedirs(CSV_DIR, exist_ok=True)

    print_banner()
    config = load_config()
    print_config(config)
    log_config_change(config)

    threading.Thread(target=offline_monitor, daemon=True).start()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', PORT))
    server.listen(10)

    log(f"СЕРВЕР ЗАПУЩЕН | порт {PORT} | запись {RECORD_SIZE} байт | лог конфига: {CONFIG_LOG}")
    print("  Ожидание подключений...\n")

    while True:
        try:
            client, addr = server.accept()
            threading.Thread(target=handle_client, args=(client, addr), daemon=True).start()
        except KeyboardInterrupt:
            log("СЕРВЕР ОСТАНОВЛЕН");
            break
        except Exception as e:
            log(f"ОШИБКА: {e}", "ERROR")


if __name__ == "__main__":
    main()