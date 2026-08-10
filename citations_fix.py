#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Чистка citations.json: нормализация id, удаление самопар, слияние дублей.

ЧТО ЧИНИТ. Харвест спаривает статьи по идентификаторам как есть, а arXiv отдаёт их
то с версией, то без. Отсюда 14 пар вида `2607.05044 ~ 2607.05044v1` — работа,
сопряжённая сама с собой. Их 0,5% от списка, но у них 175, 117, 70 общих источников
против медианы 3 у чистых пар: при ранжировании по силе сопряжения они встают ПЕРВЫМИ,
и «подтверждающим материалом» читателю показывают ту же самую статью.

Это не метрика, это порча данных, которая доходит до страницы.

ТОТ ЖЕ КЛАСС ОШИБКИ уже стоил проекту дня 21 июля: отбор возвращал id без версии,
живой API отдавал с версией, точное сравнение давало пустое пересечение и день молча
пропадал. Лечение то же самое и там, и здесь — нормализовать ДО сравнения
(`_base_id()` в gen_llm.py).

    python citations_fix.py            # проверить и починить
    python citations_fix.py --dry      # только показать, что не так
"""
import json, pathlib, re, sys, argparse, collections

MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")
LOCAL = pathlib.Path(__file__).resolve().parent / "data" / "citations.json"


def base(s):
    return re.sub(r"v\d+$", "", str(s or ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--path", default="")
    a = ap.parse_args()

    p = pathlib.Path(a.path) if a.path else (LOCAL if LOCAL.exists()
                                             else MAIN / "data" / "citations.json")
    if not p.exists():
        sys.exit(f"нет файла {p}")
    d = json.loads(p.read_text(encoding="utf-8"))

    cp = d.get("coupled") or []
    self_pairs = [e for e in cp if base(e.get("a")) == base(e.get("b"))]

    # слияние дублей: (A,B) и (A,Bv1) — одна и та же пара, берём максимум общих
    merged = {}
    for e in cp:
        x, y = base(e.get("a")), base(e.get("b"))
        if x == y:
            continue
        k = (x, y) if x < y else (y, x)
        sh = e.get("shared") or 0
        if k not in merged or sh > merged[k]["shared"]:
            merged[k] = {"a": k[0], "b": k[1], "shared": sh}
    clean = sorted(merged.values(), key=lambda r: -r["shared"])

    internal = d.get("internal") or []
    si = [e for e in internal
          if isinstance(e, dict) and base(e.get("a") or e.get("from")) ==
          base(e.get("b") or e.get("to"))]

    print(f"файл: {p}")
    print(f"сопряжённых пар было: {len(cp)}")
    print(f"  самопар (та же работа с версией): {len(self_pairs)}")
    if self_pairs:
        top = sorted(self_pairs, key=lambda e: -(e.get('shared') or 0))[:3]
        print("  верх самопар: " + ", ".join(
            f"{e['a']}~{e['b']}({e['shared']})" for e in top))
    print(f"  дублей после нормализации слито: {len(cp) - len(self_pairs) - len(clean)}")
    print(f"стало чистых пар: {len(clean)}")
    print(f"внутренних рёбер: {len(internal)}, самоссылок среди них: {len(si)}")

    if a.dry:
        print("\n--dry: файл не тронут")
        return

    d["coupled"] = clean
    if si:
        d["internal"] = [e for e in internal if e not in si]
    d["_fixed"] = {"self_pairs_removed": len(self_pairs),
                   "merged_duplicates": len(cp) - len(self_pairs) - len(clean),
                   "rule": "id нормализуются регуляркой v\\d+$ ДО спаривания"}
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    print(f"\nзаписано: {p}")


if __name__ == "__main__":
    main()
