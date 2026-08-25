#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Второй проход дублей реестра: слить семьи вроде diamond_nv_center.

ЧТО ВСКРЫЛА ПЛОТНАЯ РАЗМЕТКА. После переразметки статья «Алмазная память для квантового
процессора» получила СЕМЬ понятий про одно и то же: nv_center_sensing, diamond_nv_center,
nv_center_diamond_sensors, diamond_nv_center_spectroscopy, diamond_quantum_memory,
nitrogen_vacancy_center, diamond_defect_sensing. Читателю это не разметка, а рябь.

ПОЧЕМУ ОНИ УЦЕЛЕЛИ — ошибка в моём же правиле. На шаге 2 я нашла эти пары (сходство
карточек 0.92) и написала в отчёте, что пересечение пулов статей НЕ является
необходимым условием дубля: понятия пришли из расщепления разных родителей и одних
статей видеть не могли. А в код слияния при этом оставила условие
`косинус ≥ 0.95 ИЛИ Жаккар ≥ 0.20` — то есть ровно то требование к пулам, которое сама
же и отвергла. Вывод сделала, правило не поправила.

ПРАВИЛО ЗДЕСЬ. Свидетельство по названию обязательно (общие слова или вложенность) —
это не изменилось и меняться не должно: геометрия отвечает на «про близкое ли это»,
а не «про одно ли». Но при наличии такого свидетельства достаточно сходства КАРТОЧЕК;
пересечение пулов, если оно есть, только добавляет уверенности.

Семьи сливаются целиком, а не парами: если A~B и B~C, все трое становятся одним
понятием, и переживает то, у кого больше опорных работ.

    python concepts_dedup2.py --plan     показать семьи, ничего не писать
    python concepts_dedup2.py            слить и записать реестр v3
"""
import argparse
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))

STOP = {"of", "the", "and", "in", "a", "for", "with", "based", "using"}
CARD_COS = 0.90       # при свидетельстве по названию этого довольно
NAME_MIN = 0.50       # доля общих слов в более коротком названии


def words(s):
    return {w for w in re.split(r"[^a-z0-9]+", (s or "").lower())
            if w and w not in STOP}


def name_evidence(a, b):
    x, y = a.lower().replace("-", "_"), b.lower().replace("-", "_")
    if x in y or y in x or x.rstrip("s") == y.rstrip("s"):
        return 1.0
    wa, wb = words(a), words(b)
    return len(wa & wb) / max(1, min(len(wa), len(wb)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--reg", default=str(DATA / "concepts-v2.json"))
    ap.add_argument("--out", default=str(DATA / "concepts-v3.json"))
    args = ap.parse_args()

    import numpy as np
    import concepts_super as cs
    import concepts_grow as g

    doc = json.load(open(args.reg, encoding="utf-8"))
    reg = doc["concepts"]
    ids, V = cs.load_cards()
    print(f"понятий {len(reg)} · карточек {len(ids)}")

    art = g.load_corpus("ru")
    pool = collections.defaultdict(set)
    for a, r in art.items():
        for e in r["con"]:
            if e in reg:
                pool[e].add(a)
    for k, v in reg.items():
        for a in (v.get("support") or []):
            pool[k].add(a)

    S = V @ V.T
    np.fill_diagonal(S, -1)
    parent = list(range(len(ids)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    merged = 0
    for i in range(len(ids)):
        for j in np.where(S[i] >= CARD_COS)[0]:
            j = int(j)
            if j <= i:
                continue
            if name_evidence(ids[i], ids[j]) < NAME_MIN:
                continue
            a, b = find(i), find(j)
            if a != b:
                parent[a] = b
                merged += 1

    fam = collections.defaultdict(list)
    for i in range(len(ids)):
        fam[find(i)].append(ids[i])
    families = [v for v in fam.values() if len(v) > 1]
    families.sort(key=len, reverse=True)
    print(f"\nсемей дублей: {len(families)} · понятий в них "
          f"{sum(len(f) for f in families)}")
    for f in families[:8]:
        f2 = sorted(f, key=lambda k: -len(pool.get(k, ())))
        print(f"  {len(f)}: {f2[0]}  ←  {', '.join(f2[1:5])}"
              + (" …" if len(f2) > 5 else ""))

    keep_map = {}
    for f in families:
        f2 = sorted(f, key=lambda k: (-len(pool.get(k, ())), len(k)))
        for x in f2[1:]:
            keep_map[x] = f2[0]
    print(f"\nбудет слито: {len(keep_map)} · реестр станет "
          f"{len(reg) - len(keep_map)}")

    if args.plan:
        print("  --plan: ничего не записано")
        return 0

    v3 = {}
    for k, v in reg.items():
        if k in keep_map:
            continue
        v3[k] = dict(v)
    # опоры слитых переезжают к выжившему
    for src, dst in keep_map.items():
        if dst in v3:
            sup = set(v3[dst].get("support") or []) | set(reg[src].get("support") or [])
            v3[dst]["support"] = sorted(sup)[:20]
            v3[dst]["article_count"] = max(v3[dst].get("article_count") or 0,
                                           len(pool.get(src, ())))
    doc["concepts"] = v3
    doc["merged_v3"] = keep_map
    doc["_"] = ("Реестр v3: v2 после второго прохода дублей. Слиты семьи, "
                "у которых есть свидетельство по названию и сходство карточек "
                "≥0.90 — пересечение пулов не требуется, оно только подтверждает.")
    pathlib.Path(args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    print(f"→ {args.out}")
    print("  Карточки надо перевекторизовать: python concepts_super.py --embed "
          f"--reg {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
