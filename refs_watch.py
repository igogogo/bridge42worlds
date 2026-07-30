"""Контроль справочников: кириллица там, где её быть не должно.

Заведён 2026-07-30. У статей утечка языка ловится валидатором перевода
(gen_llm.validate_translation), а справочники — теги, законы, учёные — не проверял никто.
Французский язык это и вскрыл: русские подписи внутри формул жили во ВСЕХ языках.

Два разных дефекта, и путать их нельзя:

1. Русский текст в нерусском справочнике — перевод не сработал. Лечится перегенерацией
   перевода (reference_translate.py).
2. Русский ВНУТРИ latex — дефект генерации самого справочника, а не перевода:
   latex единственное поле, которое не переводится, оно копируется во все языки как есть.
   Значит, чинить надо русский оригинал, иначе он вернётся при следующей перегенерации.
   Требование «внутри формулы только латиница» добавлено в law-describe.txt и tag-describe.txt
   30 июля — но справочники, сделанные до этого, всё ещё несут старые формулы.

Запуск:
    python refs_watch.py            # сводка
    python refs_watch.py --list     # + id записей и фрагменты
    python refs_watch.py --latex    # только дефект №2, включая русский справочник

Ничего не меняет, только читает. Запускать можно всем.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

DEFAULT_LANG = "ru"
LANG_DIR = "lang"
BOOKS = ("tags.json", "laws.json", "scientists.json")
CYR = re.compile(r"[А-Яа-яЁё]")

# Поля, которые НЕ переводятся по устройству: идентификаторы и связи. Кириллица в них —
# отдельный разговор (битые ссылки), к утечке языка отношения не имеет.
SKIP_FIELDS = frozenset(("id", "related_tags", "related_laws", "tags", "scientists",
                         "laws", "image", "image_model", "slug"))


def languages():
    root = Path(LANG_DIR)
    return sorted(p.name for p in root.iterdir() if p.is_dir() and p.name != DEFAULT_LANG) if root.exists() else []


def walk(node, path, hits, latex_hits):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in SKIP_FIELDS:
                continue
            if key == "latex" and isinstance(value, str):
                if CYR.search(value):
                    latex_hits.append((path, value))
                continue
            walk(value, f"{path}.{key}" if path else key, hits, latex_hits)
    elif isinstance(node, list):
        for item in node:
            walk(item, path, hits, latex_hits)
    elif isinstance(node, str) and len(CYR.findall(node)) > 3:
        hits.append((path, node))


def scan(lang, book):
    path = Path(LANG_DIR) / lang / "data" / book
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    entries = data.values() if isinstance(data, dict) else data
    hits, latex_hits, ids = [], [], []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        before_h, before_l = len(hits), len(latex_hits)
        walk(entry, "", hits, latex_hits)
        if len(hits) > before_h or len(latex_hits) > before_l:
            ids.append(entry.get("id") or entry.get("name") or "?")
    return hits, latex_hits, ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="показать записи и фрагменты")
    ap.add_argument("--latex", action="store_true", help="только русский внутри latex (все языки)")
    args = ap.parse_args()

    langs = languages() if not args.latex else [DEFAULT_LANG] + languages()
    if not langs:
        print(f"нет каталога {LANG_DIR}/ — запускать из корня проекта")
        return

    total_text = total_latex = 0
    for lang in langs:
        for book in BOOKS:
            result = scan(lang, book)
            if result is None:
                continue
            hits, latex_hits, ids = result
            if args.latex:
                hits = []
            if not hits and not latex_hits:
                continue
            total_text += len(hits)
            total_latex += len(latex_hits)
            print(f"\n{lang}/{book}: русского текста {len(hits)}, русского в latex {len(latex_hits)}"
                  f" — записей затронуто {len(ids)}")
            fields = Counter(p for p, _ in hits)
            for field, count in fields.most_common(5):
                print(f"    {count:>4}  {field}")
            if args.list:
                for path, value in (hits + latex_hits)[:20]:
                    print(f"      {path or 'latex':<22} {value[:80]!r}")

    print(f"\nитого: русского текста {total_text}, русского внутри latex {total_latex}")
    if total_latex:
        print("latex чинится в РУССКОМ справочнике: это поле не переводится, "
              "во все языки оно копируется как есть")


if __name__ == "__main__":
    main()
