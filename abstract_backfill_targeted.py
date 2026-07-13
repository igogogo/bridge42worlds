#!/usr/bin/env python3
"""Точечная перегенерация «Аннотаций», обрезанных СТАРЫМ багом (_cap_text резал по
старому код-лимиту 350/550/900 с многоточием — см. TODO.md/HANDOFF.md, «Обрезка аннотаций
статей многоточием»). Новый лимит 500/750/1200 действует для ВСЕХ статей, сгенерённых
после фикса — таких трогать не нужно, blind `run.py abstracts --force` перегенерил бы
ВСЕ 240 статей (лишние ~180×3 звонка). Здесь — только реально пострадавшие.

Детект: RU-аннотация уровня X заканчивается «…» И её длина ≤ старого лимита этого уровня
(350/550/900) — то есть текст обрублен ровно на старой границе, а не на новой (500/750/1200)
или короче по естественным причинам.

Запуск:
    python abstract_backfill_targeted.py            # только отчёт (какие id и сколько)
    python abstract_backfill_targeted.py --apply     # реально перегенерирует (LLM-вызовы)
"""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common import CONFIG
from gen_llm import generate_abstract, translate_scipop

OLD_LIMITS = {"simple": 350, "popular": 550, "advanced": 900}
DEFAULT_LANG = CONFIG.get("default_lang", "ru")
LANGS = CONFIG.get("languages", ["ru", "en", "es"])
TARGET_LANGS = [l for l in LANGS if l != DEFAULT_LANG]
ARCHIVE = Path(f"lang/{DEFAULT_LANG}/archive")


def find_affected():
    affected = []
    for data_path in sorted(ARCHIVE.glob("*/*/data.json")):
        data = json.loads(data_path.read_text(encoding="utf-8"))
        ab = (data.get("abstract") or {}).get(DEFAULT_LANG) or {}
        hit = any(
            (ab.get(lvl, "") or "").endswith("…") and len(ab.get(lvl, "")) <= lim
            for lvl, lim in OLD_LIMITS.items()
        )
        if hit:
            affected.append((data, data_path.parent))
    return affected


def main():
    ap = argparse.ArgumentParser(description="Точечно перегенерирует старые обрезанные аннотации")
    ap.add_argument("--apply", action="store_true", help="реально перегенерировать (LLM-вызовы), без флага — только список")
    args = ap.parse_args()

    affected = find_affected()
    if not affected:
        print("✅ Обрезанных по старому багу аннотаций не найдено.")
        return

    print(f"⚠️ {len(affected)} статей с аннотацией, обрубленной старым лимитом:")
    for data, _ in affected:
        print(f"   {data['id']} — {data.get('date', '')}")

    if not args.apply:
        print(f"\nℹ️  Запусти с --apply, чтобы перегенерировать ({len(affected)} × "
              f"(1 генерация + {len(TARGET_LANGS)} перевода) LLM-вызовов).")
        return

    def one(item):
        data, folder = item
        atom = folder / "arxiv-atom.xml"
        summary = ""
        if atom.exists():
            import xml.etree.ElementTree as ET
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            try:
                root = ET.fromstring(atom.read_text(encoding="utf-8"))
                el = root.find(".//atom:entry/atom:summary", ns)
                if el is None:
                    el = root.find(".//atom:summary", ns)
                summary = (el.text or "").strip().replace("\n", " ") if el is not None else ""
            except Exception:
                summary = ""
        if not summary:
            print(f"   ⚠️ {data['id']}: нет arxiv-atom.xml/summary, пропущено")
            return False

        ru = generate_abstract(summary)
        if not ru:
            print(f"   ⚠️ {data['id']}: пустая аннотация от LLM, пропущено")
            return False

        abstract = {DEFAULT_LANG: ru}
        for lang in TARGET_LANGS:
            try:
                abstract[lang] = translate_scipop(ru, lang) or ru
            except Exception as e:
                print(f"   ⚠️ {data['id']}/{lang}: перевод не удался ({e}), оставлен RU")
                abstract[lang] = ru

        data["abstract"] = abstract
        (folder / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"   ✅ {data['id']}")
        return True

    with ThreadPoolExecutor(max_workers=min(8, len(affected))) as ex:
        results = list(ex.map(one, affected))

    print(f"\n✅ Перегенерировано {sum(results)}/{len(affected)} аннотаций.")
    print("   Дальше: python run.py html")


if __name__ == "__main__":
    main()
