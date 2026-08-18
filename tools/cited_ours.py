#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""№41 «Цитатные связи»: какие из цитируемых работ мы уже разбирали → data/cited-ours.json.

Врезка «Из цитируемого мы разбирали» — самая честная дорога вглубь, какая у нас есть.
«Похожие» подбирает вектор, и это наша догадка о близости; здесь связь провёл САМ АВТОР
статьи, сославшись на работу, — а мы её разобрали. Читателю не нужно верить нашему
алгоритму: он идёт по ссылке из списка литературы.

Источник — data/citations.json, ветка internal (210 643 пары «кто кого цитирует», собраны
из PDF и через Semantic Scholar). Пересечение с нашим архивом даёт немного: 271 статья и
376 переходов на 5963 разобранных работы. Это ожидаемо и не повод расширять правило: мы
разбираем 5 тысяч работ из трёх миллионов, и совпадение цитирования с нашим выбором —
редкая удача. Зато каждая такая связь настоящая.

Формат выхода — как у data/related-vec.json, чтобы клиент читал его тем же приёмом:
    {"<id статьи>": ["<id разобранной цитируемой>", ...]}
Идентификаторы даются в том виде, в каком лежат в articles-index.json (иногда с версией),
иначе ссылка не соберётся.

    python tools/cited_ours.py --dry
    python tools/cited_ours.py
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MAIN = Path("C:/Users/nadez/PycharmProjects/bridge42worlds")
OUT = ROOT / "data" / "cited-ours.json"
MAX_PER_ARTICLE = 6      # больше шести ссылок во врезке читатель уже не пройдёт


def load(rel):
    p = ROOT / rel
    if not p.exists() and (MAIN / rel).exists():
        p = MAIN / rel
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def base(aid):
    """id без версии: в цитированиях версия то есть, то нет, а работа одна и та же."""
    return re.sub(r"v\d+$", "", str(aid or "").strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="посчитать и не писать")
    args = ap.parse_args()

    cit = load("data/citations.json")
    internal = cit.get("internal") or []
    if not internal:
        print("нет data/citations.json (ветка internal) — врезке не на чем стоять")
        return 1

    idx = load("lang/ru/articles-index.json")
    if not isinstance(idx, list) or not idx:
        print("нет lang/ru/articles-index.json")
        return 1
    # База → реальный id статьи. Индекс держит по записи на уровень чтения, поэтому
    # берём первый попавшийся: id у всех уровней один.
    real = {}
    for a in idx:
        b = base(a.get("id"))
        if b and b not in real:
            real[b] = a["id"]

    out, pairs = {}, 0
    for x in internal:
        f, t = base(x.get("from")), base(x.get("to"))
        if not f or not t or f == t:
            continue
        if f not in real or t not in real:
            continue
        lst = out.setdefault(real[f], [])
        if real[t] not in lst:
            lst.append(real[t])
            pairs += 1
    for k in out:
        out[k] = out[k][:MAX_PER_ARTICLE]

    sizes = sorted((len(v) for v in out.values()), reverse=True)
    print(f"статей со связью: {len(out)} из {len(real)} · переходов: {pairs}"
          f" · максимум у одной: {sizes[0] if sizes else 0}")
    if args.dry:
        for aid, lst in list(sorted(out.items(), key=lambda kv: -len(kv[1])))[:5]:
            print(f"    {aid} → {lst}")
        print("(сухо) ничего не записано")
        return 0

    from common import write_json_atomic
    write_json_atomic(OUT, out, indent=None)
    print(f"✅ {OUT} записан")
    return 0


if __name__ == "__main__":
    sys.exit(main())
