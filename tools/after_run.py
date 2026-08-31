#!/usr/bin/env python3
"""Дождаться конца идущего прогона и запустить следующий.

Владелец 31.08: «после недельного прогони ежедневный ещё раз, чтобы оба зелёные» и
«давай всё закончим, когда всё будет консистентно автоматом после прогонов». Два
конвейера подряд руками означает сидеть и смотреть; а запустить второй заранее
нельзя — два генератора на одном дереве это гонка записи, от которой мы и ставили
замки.

Ждём не по журналу, а по ЖИВОМУ ПРОЦЕССУ: журнал пишет шаг, а процесс может умереть
между шагами и оставить в нём «идёт». Ждём, пока указанный pid не исчезнет, потом
запускаем команду и отдаём её код наружу.

    python tools/after_run.py --pid 4444 -- python tools/full_run.py --catch-up
    python tools/after_run.py --pid 4444 --what "ежедневный" -- ...
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def alive(pid):
    """Жив ли процесс. На Windows os.kill(pid, 0) не годится — спрашиваем систему."""
    try:
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                             capture_output=True, text=True, timeout=30).stdout
        return str(pid) in out
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description="Дождаться конца прогона и запустить следующий")
    ap.add_argument("--pid", type=int, required=True, help="чей конец ждём")
    ap.add_argument("--what", default="следующий прогон")
    ap.add_argument("--every", type=int, default=60, help="как часто проверять, с")
    ap.add_argument("--max-hours", type=float, default=12, help="сколько ждать максимум")
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="-- команда")
    a = ap.parse_args()
    cmd = [x for x in a.cmd if x != "--"]
    if not cmd:
        print("нечего запускать: команда после --")
        return 2

    print(f"жду конца процесса {a.pid}, потом запускаю: {a.what}")
    until = time.time() + a.max_hours * 3600
    while alive(a.pid):
        if time.time() > until:
            print(f"⛔ прогон {a.pid} не кончился за {a.max_hours} ч — не запускаю ничего")
            return 1
        time.sleep(a.every)
    print(f"✅ процесс {a.pid} закончился · запускаю {a.what}")
    r = subprocess.run(cmd, cwd=str(ROOT), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    print(f"{a.what}: код {r.returncode}")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
