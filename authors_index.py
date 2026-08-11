#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Кто чем занимается: указатель авторов по полю. Не вектор, а таблица.

Владелец 11 августа: «что ещё сразу в вектор, что ещё есть в нашей базе… список
литературы, его кажется нет, но может авторы полезны».

СПИСКА ЛИТЕРАТУРЫ В ДАМПЕ НЕТ — чутьё верное. В выгрузке arXiv лежат заголовок,
аннотация, авторы, разделы и дата, и всё. Ссылки есть только у наших 3203 разобранных
PDF, оттуда и взялись 2817 связей цитирования. Построить граф цитирований по полю
из этих данных нельзя; для этого нужен Semantic Scholar, а он идёт по своей квоте.

АВТОРЫ ЕСТЬ, НО В ВЕКТОР ИМ НЕЛЬЗЯ. Имя не несёт смысла: «J. Smith» модель разложит
по созвучию с другими строками, а не по науке, и такой вектор будет уверенно врать.
Тот же урок, что с тегами: в вектор идёт ОПИСАНИЕ, а не название.

Зато автор — прекрасный указатель, и он бесплатен: ни одного обращения к модели,
только чтение того, что уже лежит на диске. Что он даёт:

  · у дырки в карте бурения появляется адрес. «Здесь пусто, а работают там вот эти
    группы» — это уже не наблюдение, а зацепка;
  · для рекомендаций автору: кто ещё занят его вопросом прямо сейчас;
  · плотность по автору — сколько работ, за какой срок, в каких разделах.

    python authors_index.py --months 2025,2026     построить указатель
    python authors_index.py --who "Hawking"        кто это и чем занят
    python authors_index.py --near data/field --top 5   кто работает у дырок бурения
"""
import argparse
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = DATA / "authors-index.json"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))
import field_build as fb


def name_of(a):
    """`authors_parsed` — это [фамилия, имя, суффикс]. Склеиваем «Фамилия И.»:
    полное имя пишут по-разному от статьи к статье, и без нормализации один человек
    рассыпается на трёх. Инициал оставляем — без него склеятся однофамильцы."""
    if isinstance(a, (list, tuple)):
        last = str(a[0]).strip()
        first = str(a[1]).strip() if len(a) > 1 else ""
        return f"{last} {first[:1]}." if first else last
    return str(a).strip()


def build(months_spec, cats):
    by_author = collections.defaultdict(list)
    by_work = {}
    for m in fb.months(months_spec):
        p = fb.BULK / f"{m}.jsonl"
        with p.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                c = r.get("categories")
                lst = c if isinstance(c, list) else str(c or "").split()
                if not lst:
                    continue
                g = str(lst[0]).split(".")[0]
                if cats and g not in cats:
                    continue
                names = [name_of(a) for a in (r.get("authors_parsed") or [])]
                names = [n for n in names if len(n) > 2]
                if not names or not r.get("id"):
                    continue
                wid = f"arx:{r['id']}"
                by_work[wid] = {"a": names, "c": g, "d": (r.get("published") or "")[:7]}
                for n in names:
                    by_author[n].append(wid)
    return by_author, by_work


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", default="2025,2026")
    ap.add_argument("--cats", default="physics")
    ap.add_argument("--who")
    ap.add_argument("--near", help="путь к полю: показать авторов у пустых областей")
    ap.add_argument("--top", type=int, default=5)
    args = ap.parse_args()

    if args.who or args.near:
        if not OUT.exists():
            sys.exit("указателя нет — сначала соберите его без --who/--near")
        d = json.loads(OUT.read_text(encoding="utf-8"))
        by_author, by_work = d["authors"], d["works"]

    if args.who:
        hits = [a for a in by_author if args.who.lower() in a.lower()]
        for a in sorted(hits, key=lambda x: -len(by_author[x]))[:10]:
            ws = by_author[a]
            cats = collections.Counter(by_work[w]["c"] for w in ws if w in by_work)
            print(f"\n{a}: работ {len(ws)}")
            print(f"  разделы: {', '.join(f'{c} {n}' for c, n in cats.most_common(4))}")
            print(f"  примеры: {', '.join(ws[:3])}")
        return 0

    if args.near:
        # Дырка с адресом. У пустых областей карты смотрим, кто работает В САМИХ этих
        # областях: там пусто у НАС, а не у науки — работы там есть, и у них есть авторы.
        import numpy as np
        import vecstore
        C = np.load(DATA / "drill-centers.npy")
        R = json.loads((DATA / "drill-regions.json").read_text(encoding="utf-8"))
        ids, M = vecstore.load(args.near, latest=True)
        A = np.asarray(M, dtype=np.float32)
        A /= np.linalg.norm(A, axis=1, keepdims=True) + 1e-9
        lab = np.empty(len(A), dtype=np.int32)
        for s in range(0, len(A), 4096):
            lab[s:s + 4096] = (A[s:s + 4096] @ C.T).argmax(1)
        holes = [j for j in range(len(C))
                 if R["n_ours"][j] == 0 and not R["restricted"][j]
                 and R["n_arxiv"][j] >= R["min_arxiv"]]
        holes.sort(key=lambda j: -R["n_arxiv"][j])
        for j in holes[:args.top]:
            who = collections.Counter()
            for i in np.where(lab == j)[0]:
                for n in (by_work.get(ids[i]) or {}).get("a", []):
                    who[n] += 1
            print(f"\n· {R['names'][j]} — у науки {R['n_arxiv'][j]}, у нас 0")
            print(f"  работают: {', '.join(f'{n} ({k})' for n, k in who.most_common(6)) or '—'}")
        return 0

    cats = None if args.cats == "all" else (set(fb.PHYSICS) if args.cats == "physics"
                                            else {x.strip() for x in args.cats.split(",")})
    by_author, by_work = build(args.months, cats)
    print(f"работ: {len(by_work):,} · авторов: {len(by_author):,}")
    n = collections.Counter({a: len(w) for a, w in by_author.items()})
    print(f"в среднем работ на автора: {sum(n.values())/max(len(n),1):.1f}")
    print("самые плодовитые:")
    for a, k in n.most_common(8):
        print(f"  {k:>4}  {a}")
    OUT.write_text(json.dumps({"authors": by_author, "works": by_work},
                              ensure_ascii=False), encoding="utf-8")
    print(f"\nуказатель в {OUT.name} ({OUT.stat().st_size/1e6:.0f} МБ)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
