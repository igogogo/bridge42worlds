#!/usr/bin/env python3
"""Переводит подписи к рисункам статей на остальные языки сайта.

captions извлекаются regex'ом из английского PDF (gen_arxiv.extract_captions) и раньше
хранились в data.json плоским английским списком — показывались на RU/ES страницах как есть,
без перевода. Новый формат — {"en": [...], "ru": [...], "es": [...]}; generate.py уже пишет
его для новых статей (см. captions_for_lang() + build_article()). Этот скрипт мигрирует
СУЩЕСТВУЮЩИЕ статьи со старым плоским форматом на новый, переводя реально.

Запуск:
    python caption_backfill.py            # только список затронутых id
    python caption_backfill.py --apply     # реально переводит (LLM-вызовы)
"""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common import CONFIG
from gen_llm import translate_captions

DEFAULT_LANG = CONFIG.get("default_lang", "ru")
LANGS = CONFIG.get("languages", ["ru", "en", "es"])
CAP_TARGETS = [l for l in LANGS if l != "en"]
ARCHIVE = Path(f"lang/{DEFAULT_LANG}/archive")


def find_legacy():
    out = []
    for data_path in sorted(ARCHIVE.glob("*/*/data.json")):
        data = json.loads(data_path.read_text(encoding="utf-8"))
        caps = data.get("captions")
        if isinstance(caps, list) and caps:
            out.append((data, data_path))
    return out


def main():
    ap = argparse.ArgumentParser(description="Переводит подписи к рисункам на ru/es (миграция старого плоского формата)")
    ap.add_argument("--apply", action="store_true", help="реально переводить (LLM-вызовы), без флага — только список")
    args = ap.parse_args()

    items = find_legacy()
    if not items:
        print("✅ Нет статей со старым (нелокализованным) форматом подписей.")
        return

    total_caps = sum(len(d.get("captions") or []) for d, _ in items)
    print(f"⚠️ {len(items)} статей с английскими подписями без перевода ({total_caps} подписей всего):")
    for data, _ in items:
        print(f"   {data['id']} — {len(data['captions'])} подписей")

    if not args.apply:
        print(f"\nℹ️  Запусти с --apply, чтобы перевести ({len(items)} × {len(CAP_TARGETS)} LLM-вызовов).")
        return

    def one(item):
        data, data_path = item
        captions_en = data["captions"]
        captions_by_lang = {"en": captions_en}
        for lang in CAP_TARGETS:
            try:
                captions_by_lang[lang] = translate_captions(captions_en, lang)
            except Exception as e:
                print(f"   ⚠️ {data['id']}/{lang}: перевод не удался ({e}), оставлен английский")
                captions_by_lang[lang] = captions_en
        data["captions"] = captions_by_lang
        data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"   ✅ {data['id']}")
        return True

    with ThreadPoolExecutor(max_workers=min(8, len(items))) as ex:
        results = list(ex.map(one, items))

    print(f"\n✅ Переведено {sum(results)}/{len(items)} статей.")
    print("   Дальше: python run.py html")


if __name__ == "__main__":
    main()
