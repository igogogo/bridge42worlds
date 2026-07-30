#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Мерка поиска: тестовые запросы на 4 языках + подсчёт качества.

ИДЕЯ. Эталон не размечается человеком, он известен заранее. Запрос строится из статьи X —
значит правильный ответ поиска это X. Проверяем, находится ли он и на каком месте.
Так мерка получается бесплатной, воспроизводимой и растёт вместе с архивом.

ПОЧЕМУ НЕТ УТЕЧКИ. В индекс идёт `original_title` + `abstract.en.advanced`
(см. embeddings_export.py). Запросы берём из ДРУГИХ полей — `popular.<lang>.title`
и `popular.<lang>.oneliner`, которые в индекс не попадают никогда. Иначе мы бы искали
текст по нему же самому и померили бы не поиск, а совпадение строк.

ЧТО ЭТО ПРОВЕРЯЕТ ГЛАВНОЕ. Индекс английский, а запросы на четырёх языках. Русский запрос
обязан находить английский вектор — это требование владельца «нашёл по-русски английский
абстракт», и до сих пор оно ничем не подтверждено. Разница recall между en и ru/es/ar —
это и есть цена мультиязычности.

    python search_eval.py build --archive <путь> [--n 100]
    python search_eval.py score --results results.json

Формат results.json, который отдаёт DevOps после прогона через /api/search:
    {"<qid>": ["<id1>", "<id2>", ...], ...}   # id статей по убыванию релевантности
"""
import json, os, random, sys, pathlib, argparse, collections

ROOT = pathlib.Path(__file__).resolve().parent
import json as _json
from pathlib import Path as _Path
# Языки берём из config.json, а не списком: хардкод ["ru","en","es","ar"] — причина того,
# что пятый язык (fr) прошёл мимо половины инструментов (аудит 2026-07-30).
LANGS = _json.loads(_Path("config.json").read_text(encoding="utf-8")).get("languages", ["ru"])
KINDS = ["title", "oneliner"]
SEED = 42  # фиксируем: мерка должна повторяться, иначе её нельзя сравнивать с собой


def build(args):
    archive = pathlib.Path(args.archive or os.environ.get("B42_ARCHIVE", ""))
    if not archive.exists():
        sys.exit(f"нет папки архива: {archive}\nукажи --archive или B42_ARCHIVE")

    pool = []
    for p in sorted(archive.rglob("data.json")):
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        aid = j.get("id")
        pop = j.get("popular") or {}
        # берём только статьи, у которых есть текст запроса на ВСЕХ четырёх языках,
        # иначе сравнение языков между собой будет нечестным
        fields = {}
        ok = True
        for lg in LANGS:
            o = pop.get(lg) or {}
            t = (o.get("title") or "").strip()
            ol = (o.get("oneliner") or "").strip()
            if len(t) < 10 or len(ol) < 20:
                ok = False
                break
            fields[lg] = {"title": t, "oneliner": ol}
        if ok and aid:
            pool.append((aid, bool(j.get("express")), fields))

    if not pool:
        sys.exit("не набралось ни одной статьи с полным набором языков")

    rnd = random.Random(SEED)
    rnd.shuffle(pool)

    # доля экспрессов в выборке держим как в корпусе — иначе мерка соврёт:
    # у экспрессов разметка и текст беднее, и поиск по ним объективно хуже
    full = [x for x in pool if not x[1]]
    expr = [x for x in pool if x[1]]
    share_full = len(full) / len(pool)
    n_full = min(len(full), round(args.n * share_full))
    n_expr = min(len(expr), args.n - n_full)
    picked = full[:n_full] + expr[:n_expr]
    rnd.shuffle(picked)

    rows = []
    for aid, is_expr, fields in picked:
        for lg in LANGS:
            for kind in KINDS:
                rows.append({
                    "qid": f"{aid}|{lg}|{kind}",
                    "expect": aid,          # эталон: эта статья и должна найтись
                    "lang": lg,
                    "kind": kind,
                    "express": is_expr,
                    "query": fields[lg][kind],
                })

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    chars = sum(len(r["query"]) for r in rows)
    tokens = chars / 4
    print(f"статей в выборке: {len(picked)}  (полных {n_full}, экспресс {n_expr})")
    print(f"запросов: {len(rows)} = {len(picked)} × {len(LANGS)} языка × {len(KINDS)} вида")
    print(f"знаков {chars:,}  ~токенов {tokens:,.0f}")
    print(f"эмбеддинг запросов @cf/baai/bge-m3: ${tokens/1e6*0.012:.5f}")
    print(f"запрошенных измерений: {len(rows)*1024:,}")
    print(f"файл: {out}")


def score(args):
    results = json.loads(pathlib.Path(args.results).read_text(encoding="utf-8"))
    queries = {}
    for line in (ROOT / args.queries).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            queries[r["qid"]] = r

    missing = [q for q in queries if q not in results]
    buckets = collections.defaultdict(lambda: {"n": 0, "r1": 0, "r5": 0, "r10": 0, "mrr": 0.0})

    for qid, q in queries.items():
        if qid not in results:
            continue
        ranked = results[qid]
        want = q["expect"]
        pos = ranked.index(want) + 1 if want in ranked else 0
        for key in ("ВСЕГО", f"язык {q['lang']}", f"вид {q['kind']}",
                    "экспресс" if q["express"] else "полные"):
            b = buckets[key]
            b["n"] += 1
            if pos == 1: b["r1"] += 1
            if 0 < pos <= 5: b["r5"] += 1
            if 0 < pos <= 10: b["r10"] += 1
            if pos: b["mrr"] += 1.0 / pos

    print(f"{'срез':<14} {'запросов':>9} {'нашёл@1':>9} {'@5':>7} {'@10':>7} {'MRR':>7}")
    for key in sorted(buckets, key=lambda k: (k != "ВСЕГО", k)):
        b = buckets[key]
        n = b["n"] or 1
        print(f"{key:<14} {b['n']:>9} {100*b['r1']/n:>8.1f}% {100*b['r5']/n:>6.1f}% "
              f"{100*b['r10']/n:>6.1f}% {b['mrr']/n:>7.3f}")
    if missing:
        print(f"\n!! без ответа осталось {len(missing)} запросов — считаны как ненайденные")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--archive", default="")
    b.add_argument("--n", type=int, default=100)
    b.add_argument("--out", default="data/search-eval-queries.jsonl")
    b.set_defaults(fn=build)
    s = sub.add_parser("score")
    s.add_argument("--results", required=True)
    s.add_argument("--queries", default="data/search-eval-queries.jsonl")
    s.set_defaults(fn=score)
    a = ap.parse_args()
    a.fn(a)
