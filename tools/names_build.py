#!/usr/bin/env python3
"""Крошечный справочник имён: id → название на языке страницы.

Зачем. Учебный курс (и граф-эксплорер) показывают связи параграфа сырыми
идентификаторами: «ideal gas law», «phase transition» — по-английски даже на
арабской странице. Локализованные названия есть, но лежат в полных справочниках
lang/<язык>/data/{tags,laws,scientists}.json, а это 3,6 + 1,4 + 0,45 МБ: тянуть
их на страницу ради подписей — пять мегабайт вместо тридцати килобайт.

Собираем из них только пары «идентификатор → имя». Ничего не генерируем и не
переводим: имена уже написаны и оплачены, задача — сделать их достижимыми.

Выход: lang/<язык>/data/names.json вида
    {"tag": {"phase_transition": "انتقال طوري", ...}, "law": {...}, "sci": {...}}

Запуск: python tools/names_build.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
LANGS = CONFIG.get("languages", ["ru"])
LANG_DIR = CONFIG.get("lang_dir", "lang")

# Что читаем и под каким коротким ключом кладём в выход.
SOURCES = [("tags.json", "tag"), ("laws.json", "law"), ("scientists.json", "sci")]


def names_from(path):
    """Пары id → имя. Справочники — словари {id: {name: ...}}, но у учёных имя
    может лежать под другим ключом, поэтому проверяем несколько."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    out = {}
    for key, val in data.items():
        if not isinstance(val, dict):
            continue
        name = val.get("name") or val.get("name_local") or val.get("title")
        if isinstance(name, str) and name.strip() and name.strip() != key:
            out[key] = name.strip()
    return out


def main():
    total = 0
    for lang in LANGS:
        base = ROOT / LANG_DIR / lang / "data"
        if not base.exists():
            print(f"{lang}: нет каталога данных — пропускаю")
            continue
        payload = {}
        for fname, key in SOURCES:
            payload[key] = names_from(base / fname)
        out = base / "names.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                       encoding="utf-8")
        size = out.stat().st_size // 1024
        counts = " · ".join(f"{k} {len(v)}" for k, v in payload.items())
        print(f"{lang}: {counts} → {out.relative_to(ROOT)} ({size} КБ)")
        total += 1
    if not total:
        print("не собрано ничего — проверь config.json и каталог lang/")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
