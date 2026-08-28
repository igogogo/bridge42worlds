# -*- coding: utf-8 -*-
"""Отметчик прогона дней: держит журнал схемы живым, пока идёт простой прогон.

Схема конвейера читает журнал, а самый узкий прогон («забрать дни и выложить»)
идёт мимо оркестратора и журнала не ведёт — 28.08 из-за этого страница час
показывала один день, хотя конвейер работал.

Первая попытка отметчика была на shell и сломалась о кавычки при опросе процессов
Windows: решил, что прогон кончился, и замолчал. Здесь то же самое на Python —
без экранирования и без внешних команд.

    python tools/days_ticker.py --days 2026-08-24,2026-08-25 --every 30
"""
import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def daily_state():
    """Идёт ли разбор дня и какой именно.

    День берём из командной строки самого процесса, а не «первый без статей»:
    статьи появляются по ходу, и день с восемью готовыми из двадцати всё ещё
    в работе — отметчик показывал бы следующий, которого никто не начинал.
    """
    # wmic из Windows 11 убран (проверено 28.08: FileNotFoundError), поэтому
    # спрашиваем PowerShell. Команда одной строкой, без вложенных кавычек — на
    # них сломалась первая версия отметчика.
    ps = ("Get-CimInstance Win32_Process | "
          "Where-Object { $_.CommandLine -like '*run.py daily*' } | "
          "Select-Object -ExpandProperty CommandLine")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=40,
                             encoding="utf-8", errors="replace").stdout or ""
    except Exception:
        return True, None    # не смогли спросить — считаем, что идёт: молчать хуже
    for line in out.splitlines():
        if "run.py daily" in line:
            m = re.search(r"(20\d\d-\d\d-\d\d)", line)
            return True, (m.group(1) if m else None)
    return False, None


def current_day(days):
    """Какой день сейчас: первый, у которого ещё нет статей."""
    for d in days:
        folder = ROOT / "lang" / "ru" / "archive" / d
        n = len([p for p in folder.glob("*") if p.is_dir()]) if folder.exists() else 0
        if not n:
            return d
    return days[-1] if days else None


def main():
    ap = argparse.ArgumentParser(description="Отметчик прогона дней")
    ap.add_argument("--days", required=True)
    ap.add_argument("--every", type=int, default=30)
    ap.add_argument("--max-minutes", type=int, default=180)
    a = ap.parse_args()
    days = [d.strip() for d in a.days.split(",") if d.strip()]
    deadline = time.time() + a.max_minutes * 60

    while time.time() < deadline:
        alive, day = daily_state()
        cmd = [sys.executable, "tools/days_state.py", "--days", a.days]
        if alive:
            cur = day or current_day(days)
            if cur:
                cmd += ["--current", f"day-{cur}"]
        else:
            cmd += ["--finish"]
        subprocess.run(cmd, cwd=ROOT, capture_output=True)
        if not alive:
            print("прогон закончился — отметчик остановлен", flush=True)
            return 0
        time.sleep(a.every)
    print("время отметчика вышло", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
