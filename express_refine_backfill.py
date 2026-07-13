#!/usr/bin/env python3
"""Бэкфилл рефайна Simple-версии для экспресс-статей, сгенерённых ДО того, как
refine_simple() стал обязательным шагом экспресс-пайплайна (см. build_article() в
generate.py). Юзер пожаловался, что Simple получилась слишком сложной — рефайн упрощает
текст (термины/метафора/тон), сохраняя main_tag/extra_tags/scientists/mini как есть
(article-refine-simple.txt их не трогает, refine_simple() дополнительно форсит).

Рефайн может задеть title/oneliner/description/fun_fact/scifi — поэтому после него
simple-версию нужно ПЕРЕВЕСТИ ЗАНОВО на остальные языки (иначе en/es останутся на
старом тексте). mini/threads не трогаем — refine_simple() их не меняет.

Запуск:
    python express_refine_backfill.py            # только список затронутых id
    python express_refine_backfill.py --apply     # реально рефайнит + перепереводит
"""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common import CONFIG
from gen_llm import refine_simple, translate_scipop

DEFAULT_LANG = CONFIG.get("default_lang", "ru")
LANGS = CONFIG.get("languages", ["ru", "en", "es"])
TARGET_LANGS = [l for l in LANGS if l != DEFAULT_LANG]
ARCHIVE = Path(f"lang/{DEFAULT_LANG}/archive")


def find_express():
    out = []
    for data_path in sorted(ARCHIVE.glob("*/*/data.json")):
        data = json.loads(data_path.read_text(encoding="utf-8"))
        if data.get("express"):
            out.append((data, data_path))
    return out


def main():
    ap = argparse.ArgumentParser(description="Бэкфилл рефайна Simple для экспресс-статей")
    ap.add_argument("--apply", action="store_true", help="реально рефайнить (LLM-вызовы), без флага — только список")
    args = ap.parse_args()

    items = find_express()
    if not items:
        print("✅ Экспресс-статей не найдено.")
        return

    print(f"⚠️ {len(items)} экспресс-статей без рефайна Simple:")
    for data, _ in items:
        print(f"   {data['id']} — {data.get('date', '')}")

    if not args.apply:
        print(f"\nℹ️  Запусти с --apply, чтобы причесать ({len(items)} × "
              f"(1 рефайн + {len(TARGET_LANGS)} перевода) LLM-вызовов).")
        return

    def one(item):
        data, data_path = item
        simple_ru = data.get("simple", {}).get(DEFAULT_LANG)
        if not simple_ru:
            print(f"   ⚠️ {data['id']}: нет simple.{DEFAULT_LANG}, пропущено")
            return False

        refined = refine_simple(simple_ru)
        data["simple"][DEFAULT_LANG] = refined

        for lang in TARGET_LANGS:
            try:
                data["simple"][lang] = translate_scipop(refined, lang) or refined
            except Exception as e:
                print(f"   ⚠️ {data['id']}/{lang}: перевод не удался ({e})")

        data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"   ✅ {data['id']}")
        return True

    with ThreadPoolExecutor(max_workers=min(8, len(items))) as ex:
        results = list(ex.map(one, items))

    print(f"\n✅ Причёсано {sum(results)}/{len(items)} экспресс-статей.")
    print("   Дальше: python run.py html")


if __name__ == "__main__":
    main()
