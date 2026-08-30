#!/usr/bin/env python3
"""Дописать наборам идей адреса наших разборов — тем, что писались до этого поля.

Опора из нашего архива должна вести на страницу сайта, а не в поиск по номеру.
Адрес собирается по дате и номеру, но папка статьи зовётся то с версией
(2608.21711v1), то без неё — поэтому проверяем по диску, а не по шаблону.

Разовый инструмент: наборы, написанные позже, получают адрес сразу (tools/ideas.py).

    python tools/ideas_urls.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "ideas"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def url_of(date, aid):
    if not (date and aid):
        return ""
    base = ROOT / "lang" / "ru" / "archive" / str(date)
    for name in (aid, f"{aid}v1", f"{aid}v2"):
        if (base / name).is_dir():
            return f"/lang/{{lang}}/archive/{date}/{name}/"
    return ""


def main():
    touched = added = 0
    for p in sorted(SRC.glob("*.json")):
        if p.name == "index.json":
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        changed = False
        for s in d.get("sources") or []:
            if s.get("field") or s.get("url"):
                continue
            u = url_of(s.get("date"), s.get("id"))
            if u:
                s["url"] = u
                changed = True
                added += 1
        if changed:
            p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            touched += 1
    print(f"наборов поправлено: {touched} · адресов дописано: {added}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
