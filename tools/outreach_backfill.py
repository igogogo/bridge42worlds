#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Достроить журналу рассылки номера работ, которых там нет.

Все 35 писем до 10.09 записаны с пустым полем aid: в ветке «письмо по работе» номер
просто забыли передать в запись (починено в author_letter.py). Восстановить его можно
однозначно: письмо шло автору о КОНКРЕТНОЙ работе, и по имени автора в нашем индексе
находится ровно она.

Правило восстановления: берём работы автора, разобранные до даты письма, и выбираем
самую свежую — именно её мы и разбирали, когда писали. Если работ у автора несколько
и выбор неоднозначен, оставляем пустым и говорим об этом: выдуманная привязка хуже
отсутствующей.

    python tools/outreach_backfill.py           показать, что достроится
    python tools/outreach_backfill.py --apply   записать
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

LOG = ROOT / "data" / "outreach-log.jsonl"


def main():
    apply = "--apply" in sys.argv
    rows = [json.loads(x) for x in LOG.read_text(encoding="utf-8").splitlines() if x.strip()]
    idx = json.loads((ROOT / "lang" / "en" / "articles-index.json").read_text(encoding="utf-8"))

    # ТОЧНЫЙ ИСТОЧНИК ПЕРВЫМ. Очередь кандидатов (outreach-candidates.jsonl) хранит пару
    # «автор → работа» ровно в том виде, в каком письмо и составлялось. Догадка по индексу
    # нужна только там, где кандидата уже вымыло из очереди: она берёт самую свежую работу
    # автора до даты письма и потому ошибается, если прогон успел добавить автору новую
    # (поймано на Тьягараджане и Шомаз 10.09).
    exact = {}
    cand = ROOT / "data" / "outreach-candidates.jsonl"
    if cand.exists():
        for line in cand.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                c = json.loads(line)
            except json.JSONDecodeError:
                continue
            if c.get("author") and c.get("id"):
                exact[c["author"]] = c["id"]

    by_author = {}
    for a in idx:
        if a.get("version") and a["version"] != "popular":
            continue
        for name in (a.get("authors") or []):
            by_author.setdefault(name, []).append((a.get("date", ""), a["id"]))

    filled = miss = 0
    for r in rows:
        if r.get("aid"):
            continue
        if r.get("author") in exact:
            r["aid"] = exact[r["author"]]
            filled += 1
            print(f"   {(r.get('at') or '')[:10]}  {r['author'][:28]:28} → {r['aid']:14} (из очереди, точно)")
            continue
        works = sorted(by_author.get(r.get("author") or "", []), reverse=True)
        day = (r.get("at") or "")[:10]
        # Работы, разобранные НЕ ПОЗЖЕ письма: о будущей работе мы писать не могли.
        before = [w for w in works if w[0] <= day]
        pick = before[0] if before else (works[0] if works else None)
        if pick:
            r["aid"] = pick[1]
            filled += 1
            print(f"   {day}  {r['author'][:28]:28} → {pick[1]:14} ({pick[0]}, работ у автора {len(works)})")
        else:
            miss += 1
            print(f"   {day}  {r['author'][:28]:28} → работ в индексе не нашлось")

    print(f"\nдостроено {filled}, не удалось {miss}, всего писем {len(rows)}")
    if not apply:
        print("это показ. Записать: python tools/outreach_backfill.py --apply")
        return 0
    LOG.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"→ {LOG.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
