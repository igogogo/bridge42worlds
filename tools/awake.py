#!/usr/bin/env python3
"""Не давать машине заснуть, пока идёт прогон.

Владелец 31.08: «минут через 45 заснём, это affect it?». Да, влияет. Сон
приостанавливает генератор посреди работы: локальную сборку он переживёт и
продолжит после пробуждения, а вот шаг, который в этот момент говорит с
Cloudflare (заливка D1, векторы, выкладка), получит оборванное соединение — и
упадёт уже после того, как половина отправлена.

Ставим системный флаг «я занят» — тот же, которым пользуется проигрыватель
видео. Права администратора не нужны, настройки питания не трогаются: флаг
живёт ровно столько, сколько живёт этот процесс, и снимается сам при выходе.
Экран при этом гаснуть может — держим систему, а не дисплей.

    python tools/awake.py                     держать, пока идёт прогон
    python tools/awake.py --hours 6           держать шесть часов и отпустить
    python tools/awake.py --status            спит машина сейчас или нет
"""
import argparse
import ctypes
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "data" / "pipeline-runs.json"

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_AWAYMODE_REQUIRED = 0x00000040

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def hold():
    """Взять флаг. Возвращает False, если ОС отказала (не Windows и т.п.)."""
    try:
        r = ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED)
        return r != 0
    except Exception:
        return False


def release():
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    except Exception:
        pass


def running():
    """Идёт ли прогон: у последней записи журнала есть текущий шаг."""
    try:
        d = json.loads(RUNS.read_text(encoding="utf-8"))
    except Exception:
        return False
    if not d:
        return False
    last = d[-1] if isinstance(d, list) else d
    return bool(last.get("current"))


def main():
    ap = argparse.ArgumentParser(description="Держать машину бодрой, пока идёт прогон")
    ap.add_argument("--hours", type=float, default=0,
                    help="держать столько часов независимо от прогона")
    ap.add_argument("--status", action="store_true", help="только показать, что идёт")
    a = ap.parse_args()

    if a.status:
        print("прогон идёт" if running() else "прогонов нет")
        return 0

    if not hold():
        print("⚠ не удалось взять флаг бодрости (не Windows?) — машина может заснуть")
        return 1
    until = time.time() + a.hours * 3600 if a.hours else None
    what = f"{a.hours} ч" if a.hours else "пока идёт прогон"
    print(f"☕ держу машину бодрой: {what}. Прерывание (Ctrl+C) отпускает флаг.")
    try:
        idle = 0
        while True:
            time.sleep(30)
            if until:
                if time.time() >= until:
                    print("время вышло — отпускаю")
                    break
            else:
                # Прогон мог не успеть записать шаг: отпускаем не с первого пустого
                # чтения, а после пяти подряд (две с половиной минуты тишины).
                idle = idle + 1 if not running() else 0
                if idle >= 5:
                    print("прогон закончился — отпускаю")
                    break
    except KeyboardInterrupt:
        print("остановлено вручную")
    finally:
        release()
    return 0


if __name__ == "__main__":
    sys.exit(main())
