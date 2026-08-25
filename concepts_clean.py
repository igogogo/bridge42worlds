#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаг 1 волны 5: очистить понятия и подготовить рост до 1000-2000.

Владелец 25 августа: «сейчас 536 и они грязные. Вычистить свалки (127 имён у black_hole
— маркер), слить дубли, добить дыры».

СВАЛКА ОПОЗНАЁТСЯ ОПОРОЙ В СТАТЬЯХ, А НЕ АЛФАВИТОМ. Владелец назвал маркером алфавитный
порядок имён, и я начала с него — проверка не сошлась. У `black_hole` алфавитно только
начало списка (76 имён из 127), дальше дописано вручную; у `spectroscopy` алфавитная
доля 0.25. Зато короткие списки из восьми имён бывают отсортированы просто для порядка.
Признак не отличает «свалили всё» от «расставили по алфавиту», и я его сняла.

Работает другое, и оно по существу: подтверждается ли имя НАШИМИ ЖЕ статьями. Для
понятия берутся все его работы, из них — все упомянутые учёные, и считается, какая доля
списка там встретилась. Разделение резкое:

    списки от 15 имён   медианная подтверждённость 0.59
    списки короче 15    медианная подтверждённость 1.00

Из 6718 привязок имя-понятие 2569 (38%) не подтверждаются ни одной нашей статьёй.
Это и есть свалка, названная числом. Оговорка обязательная: неподтверждённая привязка
не доказана ложной — Ньютон связан с тяготением и без наших статей. Но по плану
владельца (шаг 6) учёные привязываются «только там, где прям от него зависело»,
и неподтверждённые — ровно те, что под это не подходят.

ТОЛСТОЕ ПОНЯТИЕ — НЕ ГРЯЗЬ, А СУПЕРПОНЯТИЕ НЕ НА СВО�ём МЕСТЕ. `spectroscopy` с сотнями
статей не «плохо размечен» — он просто не атомарен, и по плану владельца (шаг 4) такие
становятся суперпонятиями, а под ними появляются настоящие понятия. Поэтому толстые
считаются отдельно от грязных: их не чистить надо, а расщеплять.

ЧТО СЧИТАЕТСЯ И ЧЕГО НЕ ДЕЛАЕТСЯ. Скрипт ничего не переписывает: он готовит
предложение с опорой на конкретные статьи. Названия новым понятиям здесь не
придумываются — это платный шаг, и смета на него идёт владельцу до запуска.

    python concepts_clean.py
    python concepts_clean.py --fat 150 --out data/concepts-clean.json
"""
import argparse
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))


def supported(names, arts, art_sci):
    """Сколько имён списка подтверждено статьями самого понятия."""
    seen = set()
    for a in arts:
        seen |= art_sci.get(a, set())
    return sum(1 for n in names if n in seen)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fat", type=int, default=150,
                    help="сколько работ делает понятие кандидатом в суперпонятия")
    ap.add_argument("--dump", type=int, default=15,
                    help="сколько имён учёных считать подозрительным")
    ap.add_argument("--out", default=str(DATA / "concepts-clean.json"))
    ap.add_argument("--lang", default="ru")
    args = ap.parse_args()

    import field_build as fb
    reg = json.load(open(MAIN / "data/concepts.json", encoding="utf-8"))["concepts"]
    idx = json.load(open(MAIN / f"lang/{args.lang}/articles-index.json",
                         encoding="utf-8"))
    arts = {}
    for a in idx:
        aid = fb._base_id(str(a.get("id") or ""))
        if aid:
            arts.setdefault(aid, set()).update((a.get("tags") or [])
                                               + (a.get("laws") or []))
    art_sci = {}
    for a in idx:
        aid = fb._base_id(str(a.get("id") or ""))
        if aid:
            art_sci.setdefault(aid, set()).update(a.get("scientists") or [])
    pool = collections.defaultdict(set)
    for aid, es in arts.items():
        for e in es:
            if e in reg:
                pool[e].add(aid)
    print(f"понятий {len(reg)} · работ {len(arts):,} · "
          f"проставлений {sum(len(v) for v in arts.values()):,}")

    # 1. СВАЛКИ ИМЁН — по опоре в статьях
    rows = []
    for k, v in reg.items():
        names = v.get("scientists") or []
        if not names or not pool.get(k):
            continue
        hit = supported(names, pool[k], art_sci)
        rows.append({"id": k, "names": len(names), "supported": hit,
                     "share": round(hit / len(names), 3)})
    rows.sort(key=lambda r: -(r["names"] - r["supported"]))
    tot = sum(r["names"] for r in rows)
    conf = sum(r["supported"] for r in rows)
    print(f"\n{'=' * 76}")
    print("1. ПРИВЯЗКИ УЧЁНЫХ — сколько подтверждено нашими же статьями")
    print("=" * 76)
    print(f"  всего привязок имя-понятие: {tot:,}")
    print(f"  подтверждено статьями: {conf:,} ({conf / tot * 100:.0f}%)")
    print(f"  БЕЗ ОПОРЫ: {tot - conf:,} ({(tot - conf) / tot * 100:.0f}%) ← это свалка")
    print(f"\n{'понятие':<28}{'имён':>6}{'подтв.':>8}{'лишних':>8}")
    for r in rows[:8]:
        print(f"  {r['id']:<28}{r['names']:>6}{r['supported']:>8}"
              f"{r['names'] - r['supported']:>8}")
    big = [r for r in rows if r["names"] >= 15]
    small = [r for r in rows if r["names"] < 15]
    import statistics as _st
    if big and small:
        print(f"\nсписки от 15 имён ({len(big)}): медианная подтверждённость "
              f"{_st.median([r['share'] for r in big]):.2f}")
        print(f"  списки короче 15 ({len(small)}): "
              f"{_st.median([r['share'] for r in small]):.2f}")
        print("  Разделение резкое: длинный список почти всегда набит, "
              "короткий почти всегда честен.")

    # 2. ТОЛСТЫЕ — кандидаты в суперпонятия (шаг 4), а не в чистку
    fat = sorted(((k, len(pool.get(k, ()))) for k in reg
                  if len(pool.get(k, ())) >= args.fat), key=lambda x: -x[1])
    covered = len({a for k, _ in fat for a in pool[k]})
    print(f"\n{'=' * 76}\n2. ТОЛСТЫЕ ПОНЯТИЯ — в суперпонятия, а не в чистку\n{'=' * 76}")
    print(f"  понятий с опорой ≥{args.fat} работ: {len(fat)}")
    print(f"  они покрывают {covered:,} работ из {len(arts):,} "
          f"({covered / len(arts) * 100:.0f}% архива)")
    for k, n in fat[:8]:
        print(f"    {k:<32} работ {n:>4} · вид {reg[k].get('kind')}")

    # 3. БЕЗ ОПОРЫ
    dead = sorted((k for k in reg if not pool.get(k)), key=str)
    print(f"\n{'=' * 76}\n3. БЕЗ ОПОРЫ В СТАТЬЯХ\n{'=' * 76}")
    print(f"  понятий: {len(dead)} — {', '.join(dead[:10])}"
          + (" …" if len(dead) > 10 else ""))

    # 4. СКОЛЬКО МЕСТА ПОД РОСТ
    tot = sum(len(v) for v in arts.values())
    print(f"\n{'=' * 76}\n4. МЕСТО ПОД РОСТ ДО 1000-2000\n{'=' * 76}")
    print(f"  проставлений понятий: {tot:,} · на статью {tot / len(arts):.1f}")
    for thr in (3, 5, 8):
        print(f"    потолок при опоре ≥{thr}: {tot // thr:,} понятий")
    print(f"  Цель 1000-2000 внутри потолка. Но потолок считает РАВНОМЕРНОЕ")
    print(f"  распределение, а сейчас {len(fat)} толстых понятий держат "
          f"{covered / len(arts) * 100:.0f}% архива.")
    print(f"  Значит рост идёт не только дырами, но и расщеплением толстых.")

    out = {"built": "2026-08-25", "concepts": len(reg), "articles": len(arts),
           "attribution": rows,
           "attribution_total": tot, "attribution_supported": conf,
           "fat": [{"id": k, "articles": n, "kind": reg[k].get("kind")} for k, n in fat],
           "dead": dead,
           "placements": tot,
           "note": "Свалка опознаётся ОПОРОЙ В СТАТЬЯХ, а не алфавитом: алфавитный "
                   "признак проверен и не разделяет. Толстые понятия — кандидаты "
                   "в суперпонятия (шаг 4), их не чистят, а расщепляют. Файл — "
                   "предложение, реестр не изменён.",
           }
    pathlib.Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    print(f"\n→ {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
