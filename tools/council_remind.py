#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Напоминание в канал: голосование совета открыто, кто ещё не голосовал.

Часть субботнего шага (tools/council_aivote.cmd). Заседание 23.08 закрылось с нулём
голосов людей — не потому что вопросы не интересовали, а потому что о дедлайне никто
не напомнил. Напоминание идёт ПОСЛЕ голосования ИИ: человек открывает страницу и видит
уже занятые позиции и комментарии, а не пустую повестку.
"""
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    p = ROOT / "data" / "council" / "upcoming.json"
    if not p.exists():
        print("повестки нет — молчу")
        return 0
    d = json.loads(p.read_text(encoding="utf-8"))
    agenda = d.get("agenda") or []
    when = d.get("date", "")
    if not agenda or when < date.today().isoformat():
        print("повестка пуста или в прошлом — молчу")
        return 0
    voted = sum(1 for q in agenda if q.get("votes"))
    text = (f"🗳 <b>Совет: голосование открыто</b>\n"
            f"Заседание {when}, вопросов {len(agenda)}, с голосами {voted}.\n"
            f"ИИ-участники проголосовали, комментарии на странице. "
            f"Закрытие — воскресенье 21:00.\n"
            f"https://bridge42worlds.academy/lang/ru/council.html")
    subprocess.run([sys.executable, str(ROOT / "tools" / "status_tg.py"), text],
                   cwd=str(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
