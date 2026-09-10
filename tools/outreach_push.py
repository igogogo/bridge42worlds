#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Список работ, авторам которых мы писали, — в облако, для доски посещений.

Владелец 10.09: «помечай поле, если авторам отправлялись письма». Доска посещений живёт
в воркере и читает D1, а журнал рассылки лежит только у нас на машине и на сайт не едет
(и правильно: в нём адреса живых людей).

Поэтому в облако уходит РОВНО ОДНО: номер работы и день отправки. Ни имени, ни адреса,
ни языка письма. Номер работы и так публичен — это адрес нашей же страницы; всё остальное
остаётся на машине.

    python tools/outreach_push.py            показать, что уйдёт
    python tools/outreach_push.py --apply    записать в D1
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

LOG = ROOT / "data" / "outreach-log.jsonl"


def main():
    apply = "--apply" in sys.argv
    rows = [json.loads(x) for x in LOG.read_text(encoding="utf-8").splitlines() if x.strip()]
    # По работе берём ПЕРВОЕ письмо: важно «когда мы к ним обратились», а не сколько раз.
    sent = {}
    for r in sorted(rows, key=lambda x: x.get("at") or ""):
        aid = (r.get("aid") or "").strip()
        if aid:
            sent.setdefault(aid.split("v")[0], (r.get("at") or "")[:10])
    print(f"работ с письмом: {len(sent)} (писем всего {len(rows)})")
    for aid, day in list(sent.items())[:6]:
        print(f"   {aid:14} {day}")
    if not apply:
        print("это показ. Записать: python tools/outreach_push.py --apply")
        return 0

    from comments_triage import sql
    if not (os.environ.get("CLOUDFLARE_ACCOUNT_ID") and os.environ.get("CLOUDFLARE_API_TOKEN")):
        # Ключи лежат в .env; без них шаг молча ничего не сделал бы, а это хуже ошибки.
        from embeddings_build import load_env
        load_env(ROOT)
    sql("""CREATE TABLE IF NOT EXISTS outreach_sent (
             id TEXT PRIMARY KEY,     -- номер работы без версии
             at TEXT NOT NULL         -- день первого письма автору этой работы
           )""")
    # Пачками: D1 не любит длинных списков подстановок, а строк здесь десятки.
    items = list(sent.items())
    for i in range(0, len(items), 40):
        part = items[i:i + 40]
        vals = ",".join("(?,?)" for _ in part)
        params = [x for pair in part for x in pair]
        sql(f"INSERT OR REPLACE INTO outreach_sent (id, at) VALUES {vals}", params)
    got = sql("SELECT COUNT(*) n FROM outreach_sent")
    print(f"✅ в облаке работ с письмом: {got[0]['n'] if got else '?'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
