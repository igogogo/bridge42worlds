#!/usr/bin/env python3
"""Чинит учёных со слишком тонкими related_tags (0-1 тег) — растущий список (--gaps/--famous)
подбирает теги из СЛУЧАЙНОЙ выборки SAMPLE_TAGS, из-за чего не всегда попадает на реально
подходящие; для многих учёных (в т.ч. только что добавленных Эйнштейна/Ньютона/Кюри) связей
почти нет. Для каждого такого — отдельный точный подбор по ПОЛНОМУ списку активных тегов.

Запуск:
    python scientist_tags_repair.py            # только список
    python scientist_tags_repair.py --apply     # реально чинит (LLM-вызовы)
"""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from string import Template

from common import CONFIG, chat, load_prompt, parse_json_salvage

DEFAULT_LANG = CONFIG.get("default_lang", "ru")
LANGS = CONFIG.get("languages", ["ru", "en", "es"])
SCI_PATH = Path("lang/ru/data/scientists.json")
TAGS_PATH = Path("lang/ru/data/tags-list.json")
THIN_THRESHOLD = 1


def find_thin():
    sci = json.loads(SCI_PATH.read_text(encoding="utf-8"))
    return {k: v for k, v in sci.items() if len(v.get("related_tags") or []) <= THIN_THRESHOLD}


def repair_one(name, entry, active_tags):
    prompt = Template(load_prompt("scientist-tags-repair")).safe_substitute(
        name=name, fields=", ".join(entry.get("fields") or []), description=entry.get("description", ""),
        current_tags=", ".join(entry.get("related_tags") or []),
        tag_ids=", ".join(t["en"] for t in active_tags))
    try:
        r = chat("scientists", prompt)
        data = parse_json_salvage(r.choices[0].message.content) or {}
        return data.get("tags", [])
    except Exception as e:
        print(f"   ⚠️ {name}: ошибка {e}")
        return []


def main():
    ap = argparse.ArgumentParser(description="Чинит учёных с тонкими related_tags")
    ap.add_argument("--apply", action="store_true", help="реально чинить (LLM-вызовы), без флага — только список")
    args = ap.parse_args()

    thin = find_thin()
    if not thin:
        print("✅ Все учёные достаточно связаны с тегами.")
        return

    print(f"⚠️ {len(thin)} учёных со слабыми related_tags (≤{THIN_THRESHOLD}):")
    for name, entry in thin.items():
        print(f"   {name}: {entry.get('related_tags') or []}")

    if not args.apply:
        print(f"\nℹ️  Запусти с --apply, чтобы починить ({len(thin)} LLM-вызовов).")
        return

    active_tags = json.loads(TAGS_PATH.read_text(encoding="utf-8"))
    active_ids = {t["en"] for t in active_tags}
    sci = json.loads(SCI_PATH.read_text(encoding="utf-8"))

    def one(item):
        name, entry = item
        new_tags = [t for t in repair_one(name, entry, active_tags) if t in active_ids]
        if not new_tags:
            print(f"   ⚠️ {name}: LLM не нашла подходящих тегов, пропущено")
            return None
        merged = sorted(set(entry.get("related_tags") or []) | set(new_tags))
        print(f"   ✅ {name}: +{new_tags}")
        return (name, merged)

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(one, thin.items()))

    fixed = 0
    for r in results:
        if r:
            name, merged = r
            sci[name]["related_tags"] = merged
            fixed += 1
    SCI_PATH.write_text(json.dumps(sci, ensure_ascii=False, indent=2), encoding="utf-8")

    # lang/{lang}/data/scientists.json тоже кэширует related_tags — синхронизируем.
    for lang in LANGS:
        p = Path(f"lang/{lang}/data/scientists.json")
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        changed = False
        for r in results:
            if not r:
                continue
            name, merged = r
            if name in data and data[name].get("related_tags") != merged:
                data[name]["related_tags"] = merged
                changed = True
        if changed:
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n✅ Починено {fixed}/{len(thin)} учёных.")
    print("   Дальше: python run.py html")


if __name__ == "__main__":
    main()
