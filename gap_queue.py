#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Очередь полноты: кандидаты из областей, где у arXiv густо, а у нас пусто.

ЗАЧЕМ ОЧЕРЕДЬ, А НЕ СПИСОК. Дыры — не отчёт, а постоянный источник ленты: `daily`
берёт верх очереди и вычёркивает сгенерированное. Пересчёт — раз в неделю или при
обновлении дампа.

ПОЧЕМУ ДЫРА СЧИТАЕТСЯ ПО ОБЛАСТЯМ, А НЕ ПО СТАТЬЯМ. «Отрыв от фона» по вектору для
каждой из 3,12 млн работ — это 13 часов и $13 при каждом пересчёте. Но дыра — свойство
ОБЛАСТИ, а не отдельной работы: если у arXiv в q-bio.PE тысячи статей, а у нас три,
дыра там, и она видна простым счётом. Счёт по разделам точен, бесплатен и считается
за минуты. Тонкое ранжирование внутри области — работа отбора V2, он уже есть.

ЧЕГО В ДАМПЕ НЕТ. Поля лицензии (проверено 2026-08-05: ключи записи — id, title,
abstract, authors_parsed, categories, published). Фильтровать лицензии на этом шаге
нечем; их забирает конвейер при генерации через API arXiv, где лицензия есть.
Кандидат с непроходной лицензией отсеется там же, где отсеивался всегда.

    python gap_queue.py --scan      # пересчёт: счёт по разделам + очередь
"""
import json, pathlib, random, sys, collections, argparse, time

ROOT = pathlib.Path(__file__).resolve().parent
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")
BULK = MAIN / "data" / "arxiv-bulk"
DATA = ROOT / "data"
SEED = 42
PER_AREA = 60          # сколько кандидатов держать на область: очередь, а не свалка
QUEUE_MAX = 4000


def ours():
    c = collections.Counter()
    n = 0
    for p in (MAIN / "lang" / "ru" / "archive").rglob("data.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        n += 1
        prim = d.get("primary_category") or "?"
        c[prim] += 1
    return c, n


def scan():
    our, our_n = ours()
    print(f"наших статей: {our_n}, разделов у нас: {len(our)}")

    rnd = random.Random(SEED)
    arx = collections.Counter()
    pool = collections.defaultdict(list)   # раздел -> резервуарная выборка кандидатов
    seen = collections.Counter()
    total = 0
    files = sorted(p for p in BULK.glob("*.jsonl") if p.stat().st_size > 0)
    t0 = time.time()
    for k, f in enumerate(files, 1):
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    j = json.loads(line)
                except Exception:
                    continue
                cats = j.get("categories") or []
                if isinstance(cats, str):
                    cats = cats.split()
                if not cats:
                    continue
                prim = cats[0]
                arx[prim] += 1
                total += 1
                seen[prim] += 1
                rec = (j.get("id"), (j.get("title") or "")[:120], j.get("published"))
                buf = pool[prim]
                if len(buf) < PER_AREA:
                    buf.append(rec)
                else:
                    i = rnd.randint(0, seen[prim] - 1)
                    if i < PER_AREA:
                        buf[i] = rec
        if k % 100 == 0:
            print(f"  {k}/{len(files)} файлов, {total:,} записей, {time.time()-t0:.0f}с")

    print(f"\nвсего в дампе: {total:,}, разделов: {len(arx)}")

    # Дыра области = сколько статей НЕ ХВАТАЕТ, чтобы наша доля совпала с долей arXiv.
    # Считаем в штуках, а не в процентах: процент обманчив на мелких разделах.
    rows = []
    for cat, n_arx in arx.items():
        share = n_arx / total
        expected = share * our_n
        have = our.get(cat, 0)
        gap = expected - have
        if gap <= 0.5 or n_arx < 200:      # мелочь и то, что уже покрыто, в очередь не идёт
            continue
        rows.append({"area": cat, "arxiv": n_arx, "ours": have,
                     "expected": round(expected, 1), "gap_score": round(gap, 2)})
    rows.sort(key=lambda r: -r["gap_score"])

    print(f"\n{'область':<20} {'в arXiv':>9} {'у нас':>6} {'ожидалось':>10} {'дыра':>7}")
    for r in rows[:15]:
        print(f"{r['area']:<20} {r['arxiv']:>9,} {r['ours']:>6} "
              f"{r['expected']:>10.1f} {r['gap_score']:>7.1f}")

    # Очередь: кандидаты из дырявых областей, доля мест пропорциональна дыре.
    total_gap = sum(r["gap_score"] for r in rows)
    queue = []
    for r in rows:
        quota = max(1, round(QUEUE_MAX * r["gap_score"] / total_gap))
        cands = pool.get(r["area"], [])[:quota]
        for aid, title, pub in cands:
            queue.append({
                "id": aid, "area": r["area"], "gap_score": r["gap_score"],
                "title": title, "published": pub,
                "why": f"{r['area']}: у arXiv {r['arxiv']:,}, у нас {r['ours']} "
                       f"при ожидаемых {r['expected']:.0f}",
            })
    queue.sort(key=lambda q: -q["gap_score"])
    queue = queue[:QUEUE_MAX]

    out = DATA / "gap-queue.json"
    out.write_text(json.dumps({
        "built_from_dump_files": len(files), "arxiv_total": total,
        "ours_total": our_n, "areas": rows[:80], "queue": queue,
    }, ensure_ascii=False), encoding="utf-8")
    print(f"\nочередь: {len(queue)} кандидатов из {len(set(q['area'] for q in queue))} "
          f"областей\nфайл: {out}")
    print("\nЛицензии здесь не фильтруются — в дампе нет поля; отсев на генерации.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", action="store_true")
    a = ap.parse_args()
    if a.scan:
        scan()
    else:
        ap.print_help()
