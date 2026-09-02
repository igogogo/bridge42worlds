#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Зашёл ли автор после письма — и куда именно.

Владелец просил дважды (2026-09-01): «нужен контроль, зашёл ли человек за эту страницу
или нет». Долг закрыт здесь.

ПОЧЕМУ НЕ СЧЁТЧИК В ПИСЬМЕ. Обычно это делают меткой в ссылке или картинкой-пикселем.
У нас нельзя ни то, ни другое: ссылок в письме нет принципиально, а пиксель — ровно то
слежение, из-за которого письма и перестали открывать. Мы пишем человеку о его работе и
следить за ним не собираемся.

ЧЕМ МЕРЯЕМ ВМЕСТО ЭТОГО. Своей же статистикой посещений (таблица events в D1): у страницы
автора адрес известен, у страницы работы — тоже. Смотрим, открывали ли эти адреса ПОСЛЕ
дня письма. Засчитываем оба пути, потому что письмо предлагает оба: найти себя по имени
или по номеру работы.

ЧЕСТНАЯ ОГОВОРКА, БЕЗ КОТОРОЙ ЦИФРЕ ВЕРИТЬ НЕЛЬЗЯ. Мы видим, что страницу открыли, а не
КТО её открыл. На сайте с полусотней читателей в неделю заход на страницу конкретного
автора через день после письма — сигнал сильный, но это совпадение во времени, а не
доказательство. «Пришёл» здесь значит «страницу открывали после письма», и не больше.

    python tools/outreach_visits.py           кто зашёл после письма
    python tools/outreach_visits.py --all     показать и тех, кто не заходил
"""
import argparse
import json
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

LOG = ROOT / "data" / "outreach-log.jsonl"


def letters():
    """Кому и когда писали. Один автор — одно письмо, поэтому дубликатов не ждём,
    но если запись почему-то повторилась, берём ПЕРВУЮ: считать заходы надо от даты
    настоящего письма, а не от последней строки в журнале."""
    if not LOG.exists():
        return []
    out, seen = [], set()
    for line in LOG.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        who = r.get("author")
        if not who or who in seen:
            continue
        seen.add(who)
        out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="показать и тех, кто не заходил")
    args = ap.parse_args()

    rows = letters()
    if not rows:
        print("писем ещё не отправляли — считать нечего "
              "(журнал data/outreach-log.jsonl пуст)")
        return 0

    import generate as G
    from comments_triage import sql

    print(f"писем отправлено: {len(rows)}\n")
    came = 0
    lines = []
    for r in rows:
        who, day = r["author"], (r.get("at") or "")[:10]
        slug = G.author_slug(who)
        apath = f"/lang/en/authors/{slug}.html"
        aid = (r.get("aid") or "").strip()

        # Страница автора: адрес известен точно, сравниваем как есть.
        hits = sql("SELECT COUNT(*) n, COUNT(DISTINCT uid) u, MIN(day) first "
                   "FROM events WHERE dev=0 AND type='view' AND path=? AND day>=?",
                   [apath, day])
        h = (hits or [{}])[0]
        n_author, u_author, first_author = int(h.get("n") or 0), int(h.get("u") or 0), h.get("first")

        # Страница работы: у неё пять языков и три уровня, поэтому ищем по номеру
        # в адресе, а не точным совпадением.
        n_paper = u_paper = 0
        first_paper = None
        if aid:
            hp = (sql("SELECT COUNT(*) n, COUNT(DISTINCT uid) u, MIN(day) first "
                      "FROM events WHERE dev=0 AND type='view' AND path LIKE ? AND day>=?",
                      [f"%/{aid}/%", day]) or [{}])[0]
            n_paper, u_paper = int(hp.get("n") or 0), int(hp.get("u") or 0)
            first_paper = hp.get("first")

        was = n_author or n_paper
        came += 1 if was else 0
        if not was and not args.all:
            continue
        mark = "✅" if was else "· "
        where = []
        if n_author:
            where.append(f"страница автора {n_author} раз / {u_author} устр. с {first_author}")
        if n_paper:
            where.append(f"работа {n_paper} раз / {u_paper} устр. с {first_paper}")
        lines.append(f"{mark} {day}  {who[:30]:30} {'; '.join(where) or 'заходов нет'}")

    for ln in lines:
        print(ln)
    print(f"\nпришли после письма: {came} из {len(rows)}")
    print("Считается заход на страницу, а не человек: мы видим, что адрес открывали "
          "после письма,\nи не видим, кто именно. На нашем трафике это сильный сигнал, "
          "но не доказательство.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
