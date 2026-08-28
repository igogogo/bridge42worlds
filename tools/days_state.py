# -*- coding: utf-8 -*-
"""Отчёт простого прогона дней в журнал схемы конвейера.

Схема (/pipeline.html) читает журнал, который ведёт tools/full_run.py. Но самый
узкий прогон — «забрать дни и выложить» — идёт мимо оркестратора, и на схеме
выглядел зависшим: она показывала последнее, что ей сообщили, а сообщили ей час
назад. Владелец 28.08: «на странице пайплайна не видно прогресса, всё висит один
день».

Этот помощник дописывает состояние по факту: смотрит, какие дни уже лежат в
архиве, и отмечает их пройденными.

    python tools/days_state.py --days 2026-08-24,2026-08-25 --current day-2026-08-25
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "data" / "pipeline-runs.json"


def main():
    ap = argparse.ArgumentParser(description="Состояние простого прогона дней")
    ap.add_argument("--days", required=True)
    ap.add_argument("--current")
    ap.add_argument("--finish", action="store_true", help="прогон завершён")
    a = ap.parse_args()

    days = [d.strip() for d in a.days.split(",") if d.strip()]
    plan = [f"day-{d}" for d in days] + ["html", "publish"]
    done, secs = [], {}
    steps = {}
    for d in days:
        folder = ROOT / "lang" / "ru" / "archive" / d
        n = len([p for p in folder.glob("*") if p.is_dir()]) if folder.exists() else 0
        if n and f"day-{d}" != a.current:
            done.append(f"day-{d}")
            steps[f"day-{d}"] = {"ok": True, "out": [f"статей: {n}"]}
        elif n:
            steps[f"day-{d}"] = {"out": [f"статей пока: {n}"]}

    try:
        runs = json.loads(RUNS.read_text(encoding="utf-8")) if RUNS.exists() else []
    except Exception:
        runs = []
    rid = "прогон дней " + time.strftime("%Y-%m-%d")
    rec = next((r for r in runs if r.get("id") == rid), None)
    if rec is None:
        rec = {"id": rid, "started": time.strftime("%Y-%m-%d %H:%M"), "days": days}
        runs.append(rec)
    rec.update({"done": done, "failed": [], "plan": plan, "steps": steps,
                "secs": secs, "at": time.strftime("%Y-%m-%d %H:%M"),
                "current": None if a.finish else a.current})
    RUNS.write_text(json.dumps(runs[-30:], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"журнал обновлён: пройдено {len(done)} из {len(days)} дней"
          + (f" · идёт {a.current}" if a.current and not a.finish else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
