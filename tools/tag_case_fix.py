#!/usr/bin/env python3
"""Чистка испорченного регистра аббревиатур в справочниках: «дНК», «lIGO», «мРТ простаты».

Находка 3 аудита 16 августа. Причина — в коде, а не в данных: tag_describe.lc_name строчил
первую букву любого однословного имени («Спектроскопия»→«спектроскопия»), не отличая слово
от аббревиатуры. Причина закрыта функцией common.keeps_case; этот скрипт разбирает то, что
уже записано в словари прошлыми прогонами.

Признак порчи — строчная буква, за которой сразу идёт заглавная: «дНК», «vLBI». Признак
даёт ложные срабатывания на законных обозначениях («pH», «mRNA», «iPS») — они перечислены
в KEEP и никогда не трогаются. Правится только первая буква; остальное не наше дело.

Запуск: python tools/tag_case_fix.py [--dry]
"""
import io
import json
import re
import sys
from pathlib import Path

DRY = "--dry" in sys.argv
ROOT = Path(__file__).resolve().parent.parent

# Строчная первая буква + заглавная сразу за ней. У обычного слова вторая буква строчная,
# поэтому «спектроскопия» под признак не попадает и остаётся как есть.
BROKEN = re.compile(r"^[a-zа-яё][A-ZА-ЯЁ]")

# Законные обозначения со строчной первой буквой: подъём регистра их СЛОМАЕТ («mRNA»→«MRNA»).
# Сравнение по первому слову, регистрозависимое.
KEEP = {
    "pH", "pKa", "pKb", "mRNA", "tRNA", "rRNA", "miRNA", "siRNA", "snRNA", "lncRNA",
    "cDNA", "cRNA", "gRNA", "sgRNA", "dsRNA", "ssDNA", "dsDNA", "iPS", "iPSC",
    "eV", "keV", "mAb", "kT", "nm", "pN", "fMRI", "eDNA", "cAMP", "cGMP",
    "pQCD", "eROSITA", "eLISA", "gVLBI", "eV/c",
}

# Словари, где живут отображаемые имена. Языковые ветки берутся все: перевод копирует
# имя из русского вместе с порчей (в es так и уехало «eHT»).
NAMES = ("ru", "name", "title")
FILES = ["data/tags.json", "data/tags-list.json", "data/tags-list-educational.json",
         "data/laws.json", "data/laws-list.json"]


def fix(value):
    """Поднимает первую букву, если это испорченная аббревиатура. Иначе отдаёт как есть."""
    s = (value or "").strip()
    if not s or not BROKEN.match(s):
        return value
    if s.split()[0] in KEEP or s.split("-")[0] in KEEP:
        return value
    return s[:1].upper() + s[1:]


def walk(node, hits):
    """Обходит любой JSON и правит только поля имён — описания не трогаем: там строчная
    буква после заглавной встречается внутри текста законно."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in NAMES and isinstance(v, str):
                new = fix(v)
                if new != v:
                    node[k] = new
                    hits.append((v, new))
            else:
                walk(v, hits)
    elif isinstance(node, list):
        for v in node:
            walk(v, hits)


def main():
    langs = sorted(d.name for d in (ROOT / "lang").iterdir()
                   if d.is_dir() and (d / "data").exists())
    total = 0
    for lg in langs:
        for rel in FILES:
            p = ROOT / "lang" / lg / rel
            if not p.exists():
                continue
            data = json.loads(io.open(p, encoding="utf-8").read())
            hits = []
            walk(data, hits)
            if not hits:
                continue
            total += len(hits)
            print(f"{'(сухо) ' if DRY else ''}{lg}/{rel}: {len(hits)}")
            for old, new in hits:
                print(f"    {old!r} → {new!r}")
            if not DRY:
                io.open(p, "w", encoding="utf-8").write(
                    json.dumps(data, ensure_ascii=False, indent=2))
    print(f"\nВсего исправлено: {total}" if not DRY else f"\nВсего к исправлению: {total}")


if __name__ == "__main__":
    main()
