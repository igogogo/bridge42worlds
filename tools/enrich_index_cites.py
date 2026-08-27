# -*- coding: utf-8 -*-
"""Цитируемость Scholar → готовые индексы статей, точечно и без пересборки.

Полная пересборка HTML вписывает cites сама (generate.s2_cites при сборке
индекса), но S2-дособор заканчивается ПОЗЖЕ ночного rebuild — этим скриптом
финишер доносит цифры в уже собранные articles-index*.json всех языков и
уровней. Идемпотентно: перезаписывает поле, ничего больше не трогает.

    python tools/enrich_index_cites.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPERS = ROOT / "data" / "s2" / "papers.json"


def main():
    if not PAPERS.exists():
        print("нет data/s2/papers.json — нечего вписывать")
        return 1
    raw = json.loads(PAPERS.read_text(encoding="utf-8"))
    cites = {}
    for k, v in raw.items():
        if v and v.get("citationCount"):
            cites[k] = v["citationCount"]
            cites[k.split("v")[0]] = v["citationCount"]
    print(f"статей с цитированиями: {len(raw)} собрано, "
          f"{sum(1 for v in raw.values() if v and v.get('citationCount'))} ненулевых")
    touched = 0
    # ВСЕ индексы, включая latest-* — их читает лента на главной (проверено
    # глазами 27.08: цитируемость легла в index, а лента берёт latest и молчала)
    files = (list((ROOT / "lang").glob("*/articles-index*.json"))
             + list((ROOT / "lang").glob("*/articles-latest*.json")))
    for p in files:
        try:
            idx = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        changed = False
        for a in idx:
            c = cites.get(a.get("id", "")) or cites.get(a.get("id", "").split("v")[0])
            if c and a.get("cites") != c:
                a["cites"] = c
                changed = True
        if changed:
            p.write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")
            touched += 1
    print(f"✅ индексов обновлено: {touched}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
