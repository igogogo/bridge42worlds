#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Шаг 5 волны 5: переразметить статьи по карточкам понятий.

Владелец 25 августа: «векторизовать карточки понятий (на английском) и переразметить
все статьи. Плотно: цель — статья охвачена ссылками почти сплошь, статья это вектор
готовый».

ЧТО ИЗМЕНИЛОСЬ ПО СРАВНЕНИЮ СО СТАРОЙ РАЗМЕТКОЙ. Раньше понятие сравнивалось со статьёй
через посредника: у тега было русское описание из витрины, у закона — своё, и оба
писались для читателя, а не для сравнения. Теперь у понятия есть карточка — одна
английская фраза, описывающая его так, как оно проявляется в нашем корпусе, — и статья
сравнивается прямо с ней. Посредник исчез.

ПОРОГ ВЫБИРАЕТСЯ ЗАМЕРОМ, А НЕ НАЗНАЧАЕТСЯ. Печатается плотность и удержание старого.

И вот про удержание — первая версия этой проверки была неверной, что видно на числах:
она давала 3-18% совпадения при любом пороге, и я чуть не приняла это за поломку.
Смотреть надо было на примеры. «Два сверхпроводника в одном кристалле» получили
`superconducting_phase_transition` вместо старого `superconductivity`; статья про
фторид алюминия — `laser_trapping` вместо `laser`. Новая разметка не потеряла старую,
она стала ТОЧНЕЕ: новые понятия — дети расщепления толстых, и они обыгрывают родителя,
как и задумано.

Поэтому засчитывается и родитель, и его ребёнок: старое понятие считается удержанным,
если в новой разметке есть оно само ИЛИ любое понятие, выведенное из него
расщеплением. Иначе проверка наказывает ровно за то, ради чего всё делалось.

РАЗНООБРАЗИЕ ОБЯЗАТЕЛЬНО, И ЭТО НАШЛОСЬ НА ЖИВОМ ПРИМЕРЕ. Первая плотная разметка дала
статье «Алмазная память для квантового процессора» семь понятий про одно и то же:
nv_center_sensing, diamond_nv_center, nv_center_diamond_sensors,
diamond_nv_center_spectroscopy, diamond_quantum_memory, nitrogen_vacancy_center,
diamond_defect_sensing. Читателю это рябь, а не разметка.

Слить их в реестре нельзя: карточки не тождественны (сходство 0.74-0.93), и различия
настоящие — nitrogen_vacancy_center это сам дефект, diamond_quantum_memory это хранение
информации, diamond_defect_sensing это измерение поля. Реестр обязан их различать.

Значит чинить надо не реестр, а ОТБОР. Первая попытка отсеивала по сходству КАРТОЧЕК —
и почти не помогла: доля статей с тремя и более однокоренными понятиями упала с 79%
всего до 77%. Причина в том, что родственники различаются карточками (nitrogen_vacancy_center
это дефект, diamond_quantum_memory это хранение), а совпадают СЛОВАМИ В НАЗВАНИИ.

Поэтому правило простое и по словам: одно слово не может встречаться больше чем
в двух взятых понятиях. Замер: нагромождение падает с 79% до НУЛЯ, плотность —
с 15.2 до 13.8 понятий на статью. Отсев по карточкам оставлен вторым рубежом:
он ловит синонимы, у которых нет общих слов.

ПОТОЛОК НА СТАТЬЮ ЕСТЬ, И ОН НЕ ОТ ЖАДНОСТИ. «Охвачена почти сплошь» не значит «все
1244 понятия»: сорок понятий на статью — это не разметка, а шум, в котором тонет
и сильное совпадение. Верх ограничен, и в отчёте видно, скольким статьям потолок
реально пришлось применить.

    python articles_retag.py --tune      подобрать порог замером
    python articles_retag.py             переразметить и записать
"""
import argparse
import collections
import json
import re
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))

MAX_PER_ARTICLE = 20
SIB_COS = 0.88        # выше — синоним уже взятого, пропускаем
MAX_WORD_REPEAT = 2   # одно слово не чаще чем в двух понятиях статьи


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tune", action="store_true")
    ap.add_argument("--thr", type=float, default=0.60)
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--out", default=str(DATA / "articles-retag.json"))
    args = ap.parse_args()

    import numpy as np
    import concepts_grow as g
    import concepts_super as cs

    art = g.load_corpus(args.lang)
    rowof, M = g.field_rows()
    have = [a for a in art if a in rowof]
    X = np.empty((len(have), M.shape[1]), dtype=np.float32)
    for i, a in enumerate(have):
        X[i] = M[rowof[a]]
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
    cids, CV = cs.load_cards()
    print(f"статей {len(have):,} · карточек понятий {len(cids)}")

    # Родословная: какое новое понятие из какого старого выведено.
    reg = json.load(open(DATA / "concepts-v2.json", encoding="utf-8"))["concepts"]
    children = collections.defaultdict(set)
    for k, v in reg.items():
        o = str(v.get("origin") or "")
        if o.startswith("wave5-split:"):
            children[o.split(":", 1)[1]].add(k)
    print(f"понятий с родословной: {sum(len(v) for v in children.values())} "
          f"у {len(children)} родителей")

    old_n = sum(len(art[a]["con"]) for a in have) / max(1, len(have))
    print(f"старая разметка: {old_n:.1f} понятий на статью")

    S = X @ CV.T          # 6656 × 1244 — одно умножение, локально и бесплатно
    print(f"сходство: медиана {np.median(S):.3f}, "
          f"90-й процентиль {np.percentile(S, 90):.3f}, "
          f"максимум {S.max():.3f}")

    CC = CV @ CV.T        # сходство понятий между собой — второй рубеж отсева
    STOP_W = {"of", "the", "and", "in", "a", "for", "with", "based", "using"}
    WORDS = [set(w for w in re.split(r"[^a-z0-9]+", c.lower())
                 if w and w not in STOP_W) for c in cids]

    def apply(thr):
        keep, kept_old, tot_old, capped = [], 0, 0, 0
        for i, a in enumerate(have):
            j = np.where(S[i] >= thr)[0]
            j = j[np.argsort(-S[i, j])]
            picked, seen = [], collections.Counter()
            for x in j:
                x = int(x)
                # Правило слов: одно слово не чаще чем в двух взятых понятиях.
                if WORDS[x] and max(seen[w] for w in WORDS[x]) >= MAX_WORD_REPEAT:
                    continue
                # Второй рубеж: синоним без общих слов.
                if any(CC[x, y] >= SIB_COS for y in picked):
                    continue
                picked.append(x)
                seen.update(WORDS[x])
                if len(picked) >= MAX_PER_ARTICLE:
                    capped += 1
                    break
            new = {cids[x] for x in picked}
            keep.append((a, [cids[x] for x in picked]))
            old = art[a]["con"]
            tot_old += len(old)
            # Родитель считается удержанным, если пришёл он сам или его ребёнок.
            kept_old += sum(1 for o in old
                            if o in new or (children.get(o, set()) & new))
        dens = sum(len(k[1]) for k in keep) / max(1, len(keep))
        return keep, dens, (kept_old / max(1, tot_old)), capped

    if args.tune:
        print(f"\n{'=' * 74}")
        print("ПОДБОР ПОРОГА")
        print("=" * 74)
        print(f"  {'порог':>7}{'понятий/статью':>17}{'удержано старого':>19}"
              f"{'уперлось в потолок':>21}")
        for thr in (0.50, 0.55, 0.60, 0.65, 0.70):
            _, dens, keep_old, capped = apply(thr)
            print(f"  {thr:>7.2f}{dens:>17.1f}{keep_old * 100:>18.0f}%{capped:>21}")
        print("\n  «Удержано старого» — не мерило истины: старую разметку мы и заменяем.")
        print("  Но обвал этой доли означал бы, что новая разметка про другое,")
        print("  а не что она смелее.")
        return 0

    keep, dens, keep_old, capped = apply(args.thr)
    print(f"\nпорог {args.thr}: {dens:.1f} понятий на статью "
          f"(было {old_n:.1f}), удержано старого {keep_old * 100:.0f}%, "
          f"в потолок уперлось {capped} статей")
    empty = sum(1 for _, cs_ in keep if not cs_)
    print(f"статей без единого понятия: {empty}")

    out = {"built": "2026-08-25", "threshold": args.thr,
           "max_per_article": MAX_PER_ARTICLE,
           "density": round(dens, 2), "density_before": round(old_n, 2),
           "kept_old_share": round(keep_old, 3),
           "note": "Разметка по карточкам понятий: статья сравнивается с текстом "
                   "понятия напрямую, без посредника-описания из витрины. "
                   "Предложение, боевой индекс не тронут.",
           "articles": {a: cs_ for a, cs_ in keep}}
    pathlib.Path(args.out).write_text(json.dumps(out, ensure_ascii=False),
                                      encoding="utf-8")
    print(f"→ {args.out}")

    print("\nпример — три статьи и что им поставилось:")
    for a, cs_ in keep[:3]:
        print(f"  {art[a]['title'][:70]}")
        print(f"    {', '.join(cs_[:8])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
