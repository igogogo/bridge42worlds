"""Календарь совета: заседания по воскресеньям, уведомления за два дня.

Регламент владельца 2026-08-02: «заседания раз в неделю по воскресеньям, ставь
календарь, за два дня уведомления всем — почтой, если есть; если нет, зашли в кабинет,
увидели повестку». Отсюда две команды, обе идут в планировщик:

    python tools/council_schedule.py --notify    пятница: закрыть повестку и уведомить
    python tools/council_schedule.py --close     воскресенье вечером: подвести итоги
    python tools/council_schedule.py --plan      показать календарь на месяц вперёд

Почему отдельным инструментом, а не внутри рассылки: рассылка умеет отправлять письма,
календарь решает КОГДА. Смешаешь — и однажды письмо уйдёт в среду, потому что кто-то
запустил скрипт руками.
"""
import argparse
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
COUNCIL = ROOT / "data" / "council"
NOTIFY_DAYS_BEFORE = 2


def next_sunday(d=None):
    d = d or date.today()
    return d + timedelta(days=(6 - d.weekday()) % 7)


def plan(n=5):
    s = next_sunday()
    return [(s + timedelta(weeks=i), s + timedelta(weeks=i) - timedelta(days=NOTIFY_DAYS_BEFORE))
            for i in range(n)]


def upcoming():
    p = COUNCIL / "upcoming.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def ensure_meeting(day):
    """Файл заседания на дату. Если его нет — заводим пустой каркас: повестку наполнят
    предложения участников и вопросы ИИ-участников, но день должен существовать заранее,
    иначе «раз в неделю» превращается в «когда соберёмся»."""
    p = COUNCIL / f"{day}.json"
    if not p.exists():
        p.write_text(json.dumps({
            "date": str(day), "number": None, "status": "open",
            "opened": str(date.today()), "agenda": [], "sprint": [], "next": []
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  заведено заседание {day}")
    (COUNCIL / "upcoming.json").write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--notify", action="store_true")
    ap.add_argument("--close", action="store_true")
    args = ap.parse_args()

    if args.plan or not (args.notify or args.close):
        print("Заседания по воскресеньям, уведомления за два дня:")
        for meet, notify in plan():
            print(f"  {meet}  ←  уведомления {notify}")
        m = upcoming()
        print(f"\nближайшее в работе: {m.get('date','—')}, вопросов {len(m.get('agenda') or [])}")
        return 0

    if args.notify:
        day = next_sunday()
        ensure_meeting(day)
        m = upcoming()
        if not (m.get("agenda") or []):
            print("⚠️ повестка пуста — уведомлять не о чем. Сначала ИИ-участники вносят "
                  "3-4 вопроса развития, предложения читателей подтягиваются сами.")
            return 1
        print(f"повестка заседания {day}: вопросов {len(m['agenda'])} — рассылаю")
        return subprocess.run([sys.executable, str(ROOT / "tools" / "council_mail.py"), "--agenda"]).returncode

    if args.close:
        m = upcoming()
        day = m.get("date")
        if not day:
            print("нет заседания для закрытия")
            return 1
        p = COUNCIL / f"{day}.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        d["status"] = "closed"
        d["closed"] = str(date.today())
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"заседание {day} закрыто; следующее — {next_sunday(date.today() + timedelta(days=1))}")
        return subprocess.run([sys.executable, str(ROOT / "tools" / "council_mail.py"), "--results"]).returncode

    return 0


if __name__ == "__main__":
    sys.exit(main())
