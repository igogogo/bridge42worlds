# -*- coding: utf-8 -*-
"""Достроить единицы, обрезанные старым лимитом в 40 символов.

Разбор формул до 27.08 резал имя единицы на сороковом символе, и составные
единицы СИ приезжали половинками: «cubic_metre_per_kilogram_per_second_squa»
вместо «...squared». Причина закрыта (лимит 80 в tools/formula_anatomy.py),
но 61 запись осталась битой — заново гонять разбор ради хвоста слова дорого.

Достраиваем только однозначное: обрезок «squa» может продолжиться единственным
словом «squared», «kelvin_to_the» в единице всегда идёт «to_the_fourth». Где
однозначности нет — не трогаем: лучше английское слово в таблице, чем выдуманная
размерность.

  python tools/fix_truncated_units.py           # показать
  python tools/fix_truncated_units.py --apply
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AN = ROOT / "data" / "formula-anatomy.json"

# Обрезок → чем он был. Каждое правило проверено по списку единиц, что реально
# встречаются в наших формулах: продолжение единственно возможное.
TAILS = (
    ("_squa", "_squared"),
    ("_kelvin_to_the", "_kelvin_to_the_fourth"),
    ("_per_kelvin_to_the_", "_per_kelvin_to_the_fourth"),
    ("_metre_squared_per_h", "_metre_squared_per_hertz"),
    ("_per_metre_squared_per_h", "_per_metre_squared_per_hertz"),
    ("_squared_per_st", "_squared_per_steradian"),
    ("_per_stera", "_per_steradian"),
    ("_per_megaparse", "_per_megaparsec"),
    ("_per_kelv", "_per_kelvin"),
    ("_per_secon", "_per_second"),
    ("_per_kilogra", "_per_kilogram"),
    ("_per_moleku", "_per_mole"),
)


def fix(u):
    for bad, good in TAILS:
        if u.endswith(bad):
            return u[: -len(bad)] + good
    return u


def main():
    apply = "--apply" in sys.argv
    an = json.loads(AN.read_text(encoding="utf-8"))
    n, seen = 0, {}
    for fid, r in an.items():
        for grp in ("variables", "constants"):
            for x in (r.get(grp) or []):
                u = x.get("unit") or ""
                if not u:
                    continue
                g = fix(u)
                if g != u:
                    n += 1
                    seen[u] = g
                    x["unit"] = g
    for bad, good in sorted(seen.items()):
        print(f"  {bad}  →  {good}")
    print(f"починено записей: {n} · разных единиц: {len(seen)}")
    if apply and n:
        AN.write_text(json.dumps(an, ensure_ascii=False), encoding="utf-8")
        print("записано в data/formula-anatomy.json")
    elif not apply:
        print("сухой ход. записать: --apply")
    return 0


if __name__ == "__main__":
    sys.exit(main())
