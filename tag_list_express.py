#!/usr/bin/env python3
"""Разовый скрипт: выбирает подмножество АКТИВНЫХ тегов для экспресс-режима генерации статей
(меньше тегов в промте generate_express → короче и дешевле промт). Отбор — по article_count
из tags-graph.json (тег, который уже часто используется в реальных статьях, — разумный дефолт
«самых интересных»/самых нужных категорий). Результат можно смело отредактировать вручную —
это просто список {ru,en,type,domain}, тот же формат, что и tags-list.json.

Количество — config.json → express.tag_count. Путь сохранения — express.tags_file.
Запускать по мере надобности вручную перед экспресс-батчем (не часть обычного пайплайна).
"""

import json
from pathlib import Path

from common import CONFIG

EXPRESS_CFG = CONFIG.get("express", {})
TAG_COUNT = EXPRESS_CFG.get("tag_count", 25)
OUT_PATH = Path(EXPRESS_CFG.get("tags_file", "lang/ru/data/tags-list-express.json"))

ACTIVE_PATH = Path("lang/ru/data/tags-list.json")
GRAPH_PATH = Path("data/tags-graph.json")


def main():
    active = json.loads(ACTIVE_PATH.read_text(encoding="utf-8"))
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8")).get("graph", {}) if GRAPH_PATH.exists() else {}
    ranked = sorted(active, key=lambda t: graph.get(t["en"], {}).get("article_count", 0), reverse=True)
    picked = ranked[:TAG_COUNT]
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(picked, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ {OUT_PATH}: {len(picked)} тегов для экспресс-режима (по article_count из {len(active)} активных)")
    for t in picked:
        cnt = graph.get(t["en"], {}).get("article_count", 0)
        print(f"   {t['ru']} ({t['en']}) — {cnt} статей")


if __name__ == "__main__":
    main()
