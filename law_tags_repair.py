#!/usr/bin/env python3
"""Чинит законы, чьи теги ведут ТОЛЬКО в образовательный ярус.

Статьи тегируются только из АКТИВНОГО пула (generate.py читает только tags-list.json),
а law_list.py при генерации подбирает теги из active+educational вместе (load_tag_ids()).
Если законy случайно достались теги только образовательного яруса — он никогда не
пересечётся по тегам ни с одной статьёй, и секция «Похожие статьи» на его странице
навсегда пустая (see generate.py: related-articles фильтр — `set(a["tags"]) & set(law_tags)`).

Для каждого такого закона просит LLM подобрать 1-3 подходящих АКТИВНЫХ тега в ДОПОЛНЕНИЕ
к уже собранным (не убирая их) — восстанавливает связь закон↔реальный контент.

Запуск:
    python law_tags_repair.py            # только отчёт (dry-run)
    python law_tags_repair.py --apply     # реально правит (делает LLM-вызовы)
"""
import argparse
import json
from pathlib import Path
from string import Template

from common import CONFIG, chat, load_prompt, parse_json_salvage

LAWS_PATH = Path("lang/ru/data/laws-list.json")
ACTIVE_TAGS_PATH = Path("lang/ru/data/tags-list.json")
GRAPH_PATH = Path("data/laws-graph.json")
LANGS = CONFIG.get("languages", ["ru", "en", "es"])


def find_orphaned(laws, active_ids):
    return [l for l in laws if l.get("tags") and not (set(l["tags"]) & active_ids)]


def repair_law(law, active_tags):
    prompt = Template(load_prompt("law-tags-repair")).safe_substitute(
        law_ru=law["ru"],
        law_type=law.get("type", ""),
        current_tags=", ".join(law.get("tags", [])),
        tag_ids=", ".join(t["en"] for t in active_tags),
    )
    try:
        r = chat("laws_list", prompt)
        data = parse_json_salvage(r.choices[0].message.content) or {}
        return data.get("tags", [])
    except Exception as e:
        print(f"    ⚠️ {law['en']}: ошибка {e}")
        return []


def main():
    ap = argparse.ArgumentParser(description="Восстанавливает связь законов с активными тегами")
    ap.add_argument("--apply", action="store_true", help="реально править (LLM-вызовы), без флага — только отчёт")
    args = ap.parse_args()

    laws = json.loads(LAWS_PATH.read_text(encoding="utf-8"))
    active = json.loads(ACTIVE_TAGS_PATH.read_text(encoding="utf-8"))
    active_ids = {t["en"] for t in active}

    orphaned = find_orphaned(laws, active_ids)
    if not orphaned:
        print("✅ Все законы связаны хотя бы с одним активным тегом.")
        return

    print(f"⚠️ {len(orphaned)}/{len(laws)} законов без связи с активными тегами (только образовательные — "
          f"«Похожие статьи» у них всегда пусто):")
    for l in orphaned:
        print(f"   {l['en']} ({l['ru']}): {l['tags']}")

    if not args.apply:
        print(f"\nℹ️  Запусти с --apply, чтобы восстановить связи через LLM ({len(orphaned)} вызовов).")
        return

    graph_doc = json.loads(GRAPH_PATH.read_text(encoding="utf-8")) if GRAPH_PATH.exists() else {"graph": {}}
    graph = graph_doc.get("graph", {})

    fixed_ids = {}
    for law in orphaned:
        new_tags = [t for t in repair_law(law, active) if t in active_ids]
        if not new_tags:
            print(f"   ⚠️ {law['en']}: LLM не нашла подходящих активных тегов, пропущено")
            continue
        law["tags"] = sorted(set(law["tags"]) | set(new_tags))
        if law["en"] in graph:
            graph[law["en"]]["tags"] = law["tags"]
        fixed_ids[law["en"]] = law["tags"]
        print(f"   ✅ {law['en']}: +{new_tags}")

    LAWS_PATH.write_text(json.dumps(laws, ensure_ascii=False, indent=2), encoding="utf-8")
    graph_doc["graph"] = graph
    GRAPH_PATH.write_text(json.dumps(graph_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    # generate_law_page() рендерит теги закона из lang/{lang}/data/laws.json (снимок, сделанный
    # law_describe.py на момент описания), НЕ из laws-list.json/laws-graph.json — без этой
    # синхронизации починенные законы продолжали бы показывать старые теги на странице.
    for lang in LANGS:
        p = Path(f"lang/{lang}/data/laws.json")
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        changed = False
        for lid, new_tags in fixed_ids.items():
            if lid in data and data[lid].get("tags") != new_tags:
                data[lid]["tags"] = new_tags
                changed = True
        if changed:
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n✅ Починено {len(fixed_ids)}/{len(orphaned)} законов.")
    print("   Дальше: python run.py html")


if __name__ == "__main__":
    main()
