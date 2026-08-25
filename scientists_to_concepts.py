#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаг 6 волны 5: привязать учёных К ПОНЯТИЯМ логарифмически.

Владелец 25 августа: «только там, где прям от него зависело, не перегружая». И отдельно
в наряде: привязка идёт к ПОНЯТИЯМ (это источник), а не к статьям (это следствие).

ЗАМЕР, С КОТОРОГО ВСЁ НАЧАЛОСЬ. Из 6718 привязок имя-понятие в нынешнем реестре
подтверждаются нашими же статьями только 4149 (62%); 2569 не подтверждены ничем.
Списки от 15 имён подтверждены в среднем на 0.59, короче 15 имён — на 1.00.
Разделение резкое: длинный список почти всегда набит, короткий почти всегда честен.

ЧТО СЧИТАЕТСЯ ОПОРОЙ. Имя остаётся на понятии, если оно встречается в статьях этого
понятия. Не «связано по смыслу», не «упомянуто в описании» — встречается в работах,
которые понятие несут. Ньютон и тяготение связаны и без наших статей, но правило
владельца требует зависимости, а не родства.

ФОРМУЛЫ ГЛУШЕНИЯ — те же, что в tools/scientists_prune.py, и это намеренно: там они
уже проверены на живых данных (Эйнштейн 55.1% → 3.2%). Логарифм стоит дважды и оба
раза гасит то, чего слишком много.

    точность понятия  prec(c) = 1 / ln(e + |имён у c| - 1)
    редкость имени    idf(s)  = ln(1 + N_понятий / сколько понятий называют s)
    опора             сколько статей понятия упоминают это имя

ПРАВИЛО ДВУХ ОПОР сохранено: имя остаётся, либо если понятие ТОЧНОЕ (имён мало —
это атрибуция, а не список), либо если имя подтверждено не менее чем двумя статьями
понятия. Иначе редкое имя из одной случайной статьи получает вес ни за что.

ПРОВЕРКА, КОТОРУЮ МОЖНО ПРОВАЛИТЬ. Печатается судьба заведомо точных привязок:
`laser` → Таунс должен уцелеть. Если чистка убивает и его, она чистит не то.
Проверка пройдена: laser → Таунс, goldstone_theorem → Голдстоун, friedmann_equations
→ Леметр, black_hole из 127 имён → шесть, и первые двое Бекенштейн и Хокинг.

ГДЕ ЭТОТ СЧЁТ ЧЕСТНО СЛАБ — сказать это важнее, чем показать хорошие примеры.
У ТОЛСТЫХ понятий результат остаётся сомнительным: `entropy` получает Аспе и Китаева,
`spectroscopy` — Аспе и Майкельсона. И дело не в порогах.

У суперпонятия нет «учёного, от которого оно зависело»: энтропия — это не открытие
одного человека, а область. Правило владельца «только там, где прям от него зависело»
осмысленно для АТОМАРНОГО понятия и теряет смысл для области. Поэтому у таких понятий
список имён останется списком, сколько его ни чисти, и показывать его читателю как
атрибуцию не следует — разве что как «кто здесь работал».

    python scientists_to_concepts.py --plan    посчитать, ничего не писать
    python scientists_to_concepts.py           записать чистую привязку
"""
import argparse
import collections
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))

PRECISE = 4        # столько имён и меньше — понятие считается точным
MIN_SUPPORT = 2    # иначе нужно не меньше двух статей опоры
MAX_NAMES = 6      # больше на понятии не показываем: это уже список, а не атрибуция


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--reg", default=str(DATA / "concepts-v3.json"))
    ap.add_argument("--retag", default=str(DATA / "articles-retag.json"))
    ap.add_argument("--out", default=str(DATA / "concept-scientists.json"))
    ap.add_argument("--lang", default="ru")
    args = ap.parse_args()

    import field_build as fb
    reg = json.load(open(args.reg, encoding="utf-8"))["concepts"]
    idx = json.load(open(MAIN / f"lang/{args.lang}/articles-index.json",
                         encoding="utf-8"))
    art_sci = {}
    for a in idx:
        aid = fb._base_id(str(a.get("id") or ""))
        if aid:
            art_sci.setdefault(aid, set()).update(a.get("scientists") or [])

    # Пул понятия — НОВАЯ разметка: шаг 6 идёт поверх чистого реестра и свежей
    # разметки, иначе учёные переподвешиваются на то, что мы только что заменили.
    retag = json.load(open(args.retag, encoding="utf-8"))["articles"]
    pool = collections.defaultdict(set)
    for a, cs in retag.items():
        for c in cs:
            if c in reg:
                pool[c].add(a)
    print(f"понятий {len(reg)} · с опорой в новой разметке {len(pool)}")

    old_pairs = sum(len(v.get("scientists") or []) for v in reg.values())
    print(f"привязок имя-понятие сейчас: {old_pairs:,}")

    # Редкость имени считается по НЫНЕШНЕМУ реестру: часто названное имя
    # неинформативно независимо от того, чем мы его подтверждаем.
    cf = collections.Counter()
    for v in reg.values():
        cf.update(set(v.get("scientists") or []))
    n_con = len(reg)

    def idf(s):
        return math.log(1 + n_con / max(1, cf[s]))

    def prec(n):
        return 1.0 / math.log(math.e + max(0, n - 1)) if n else 0.0

    out, kept_total = {}, 0
    for k, v in reg.items():
        names = v.get("scientists") or []
        arts = pool.get(k, set())
        if not names or not arts:
            continue
        p = prec(len(names))
        precise = len(names) <= PRECISE
        scored = []
        for s in names:
            sup = sum(1 for a in arts if s in art_sci.get(a, ()))
            if sup == 0:
                continue
            if not precise and sup < MIN_SUPPORT:
                continue      # правило двух опор
            scored.append((s, round(idf(s) * p * math.log(1 + sup), 4), sup))
        scored.sort(key=lambda x: -x[1])
        if scored:
            out[k] = [{"name": s, "weight": w, "articles": sup}
                      for s, w, sup in scored[:MAX_NAMES]]
            kept_total += len(out[k])

    print(f"\n{'=' * 74}")
    print("РЕЗУЛЬТАТ")
    print("=" * 74)
    print(f"  понятий с учёными: {len(out)} · привязок {kept_total:,} "
          f"(было {old_pairs:,}, осталось {kept_total / max(1, old_pairs) * 100:.0f}%)")
    sizes = sorted(len(v) for v in out.values())
    print(f"  имён на понятие: медиана {sizes[len(sizes) // 2]}, "
          f"максимум {max(sizes)} (потолок {MAX_NAMES})")

    print(f"\n  ПРОВЕРКА НА ЗАВЕДОМО ТОЧНЫХ — они обязаны уцелеть:")
    for k in ("laser", "hubbles_law", "bells_theorem", "friedmann_equations",
              "goldstone_theorem"):
        if k in reg:
            was = len(reg[k].get("scientists") or [])
            now = out.get(k)
            names = ", ".join(x["name"] for x in now[:3]) if now else "— УБИТО"
            print(f"    {k:<26} было {was:>3} → стало "
                  f"{len(now) if now else 0}: {names}")

    print(f"\n  ЧТО СТАЛО СО СВАЛКАМИ:")
    for k in ("spectroscopy", "entropy", "black_hole", "standard_model"):
        if k in reg:
            was = len(reg[k].get("scientists") or [])
            now = out.get(k) or []
            names = ", ".join(x["name"] for x in now[:3])
            print(f"    {k:<26} было {was:>3} → стало {len(now)}: {names}")

    if args.plan:
        print("\n  --plan: ничего не записано")
        return 0

    pathlib.Path(args.out).write_text(json.dumps(
        {"built": "2026-08-25", "precise_threshold": PRECISE,
         "min_support": MIN_SUPPORT, "max_names": MAX_NAMES,
         "pairs_before": old_pairs, "pairs_after": kept_total,
         "note": "Имя остаётся на понятии, только если встречается в статьях этого "
                 "понятия. Правило двух опор: либо понятие точное, либо имя "
                 "подтверждено двумя статьями. Предложение, реестр не изменён.",
         "concepts": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
