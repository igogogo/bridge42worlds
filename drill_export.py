#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Карта бурения в человекочитаемом виде — для страницы ведущей.

Ведущая 13 августа: «для пустых областей drill-map — есть ли у вас человекочитаемое
описание каждой области (что там за тема), или пока только координаты? Без названия
области показать её нельзя».

Названия есть: каждая область подписывается тремя ближайшими к её центру понятиями
из нашего справочника тегов. Но одних понятий мало — «neutrino, neutrino_oscillations»
человеку говорит немного. Поэтому здесь на каждую область собирается карточка:

    имя по понятиям · сколько работ у мира · сколько у нас · разделы arXiv
    три реальных заголовка из этой области — по ним тема видна сразу
    кто там работает — фамилии из указателя авторов, если он собран

ОТДЕЛЬНО И ОБЯЗАТЕЛЬНО: значимость. При 3723 наших работах на 600 областей ожидание
около шести работ на область. Для мелкой области ноль возникает случайно, и такую
область показывать как «слепую зону» нельзя. Поэтому у каждой карточки считается,
сколько наших работ там ОЖИДАЛОСЬ бы, если бы наша подборка была распределена как мир,
и вероятность получить ноль случайно. В выгрузку идёт только то, что прошло порог.

    python drill_export.py --out data/drill-cards.json
    python drill_export.py --pmax 0.05     строже: только области с P(0) < 5%
"""
import argparse
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/drill-cards.json")
    ap.add_argument("--pmax", type=float, default=0.05,
                    help="максимальная вероятность случайного нуля")
    ap.add_argument("--titles", type=int, default=3)
    args = ap.parse_args()

    import numpy as np
    import vecstore
    import field_build as fb
    import drill

    C = np.load(DATA / "drill-centers.npy")
    R = json.loads((DATA / "drill-regions.json").read_text(encoding="utf-8"))
    ids, M = vecstore.load(DATA / "field", latest=True)
    A = np.asarray(M, dtype=np.float32)
    A /= np.linalg.norm(A, axis=1, keepdims=True) + 1e-9

    ours = drill.our_ids()
    is_ours = np.array([(i.split(":", 1)[-1].split("v")[0]
                         if "v" in i.split(":", 1)[-1][-3:] else i.split(":", 1)[-1]) in ours
                        for i in ids])
    lab = np.empty(len(A), dtype=np.int32)
    for s in range(0, len(A), 4096):
        lab[s:s + 4096] = (A[s:s + 4096] @ C.T).argmax(1)
    n_world = np.bincount(lab, minlength=len(C))
    n_ours = np.bincount(lab[is_ours], minlength=len(C))
    total_ours = int(is_ours.sum())
    total_world = len(A)
    print(f"поле {total_world:,} · наших в нём {total_ours:,} · областей {len(C)}")

    # ЗНАЧИМОСТЬ. Нулевая гипотеза: наша подборка распределена как мир. Тогда число
    # наших работ в области — биномиальное с p = доля области в мире, и вероятность
    # ровно нуля равна (1-p)^n. Это то самое число, без которого список «74 адреса»
    # отдавать человеку нельзя: часть из них — просто мелкие области.
    cards, weak = [], 0
    for j in range(len(C)):
        if n_ours[j] > 0 or R["restricted"][j] or n_world[j] < R["min_arxiv"]:
            continue
        p = n_world[j] / total_world
        p_zero = math.exp(total_ours * math.log1p(-p)) if p < 1 else 0.0
        expected = total_ours * p
        if p_zero > args.pmax:
            weak += 1
            continue
        cards.append({"region": j, "name": R["names"][j], "world": int(n_world[j]),
                      "ours": 0, "expected_ours": round(expected, 1),
                      "p_zero": round(p_zero, 5),
                      "cats": R["cats"].get(str(j), [])[:5]})
    cards.sort(key=lambda c: c["p_zero"])
    print(f"пустых областей в профиле: {len(cards) + weak}")
    print(f"  значимых (P(0) < {args.pmax}): {len(cards)}")
    print(f"  отброшено как случайный ноль: {weak}")

    # Заголовки: без них «neutrino, neutrino_oscillations» человеку почти ничего
    # не говорит, а три реальных названия показывают тему за секунду.
    need = {}
    for c in cards:
        rows = np.where(lab == c["region"])[0]
        top = rows[np.argsort(-(A[rows] @ C[c["region"]]))][:args.titles]
        c["_rows"] = [int(x) for x in top]
        for i in top:
            mo = fb.id_month(ids[i])
            if mo:
                need.setdefault(mo, {})[fb._base_id(ids[i])] = int(i)
    tt = {}
    for mo, keys in sorted(need.items()):
        p = fb.BULK / f"{mo}.jsonl"
        if not p.exists():
            continue
        with p.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                k = fb._base_id(r.get("id", ""))
                if k in keys:
                    tt[keys[k]] = {"id": r.get("id", ""),
                                   "title": " ".join(str(r.get("title", "")).split()),
                                   "authors": [a[0] for a in (r.get("authors_parsed") or [])[:4]]}
    for c in cards:
        c["examples"] = [tt[i] for i in c.pop("_rows") if i in tt]
        who = {}
        for e in c["examples"]:
            for a in e.get("authors", []):
                who[a] = who.get(a, 0) + 1
        c["who"] = sorted(who, key=lambda x: -who[x])[:5]

    out = {"built": "2026-08-13", "field": total_world, "ours_in_field": total_ours,
           "regions": len(C), "p_threshold": args.pmax,
           "note": "Пустая область — это вопрос, а не ответ: пусто может быть и потому, "
                   "что тема нам не подходит. Показывать только с оговоркой.",
           "cards": cards}
    pathlib.Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    print(f"\n{'='*74}\nКАРТОЧКИ (первые 6)\n{'='*74}")
    for c in cards[:6]:
        print(f"\n· {c['name']}")
        print(f"  у мира {c['world']}, у нас 0 · ожидалось {c['expected_ours']} · "
              f"P(0) = {c['p_zero']}")
        for e in c["examples"][:2]:
            print(f"    {e['title'][:82]}")
        if c["who"]:
            print(f"    работают: {', '.join(c['who'][:4])}")
    print(f"\n→ {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
