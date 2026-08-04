#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Привязка тегов, законов и учёных к статьям ПО СМЫСЛУ, а не по списку в промпте.

ЗАЧЕМ. Сейчас список из 363 названий тегов уходит в промпт, и модель выбирает знакомое:
179 тегов из 363 не проставлены ни одной статье, на топ-10 приходится 45% всех
проставлений. Причина в механизме, а не в лени модели — редкое и точное название
в длинном списке не выбирается никогда.

ПОЧЕМУ НЕ TF-IDF. Черновик на совпадении слов «оживил» все 179 тегов, но статье про
радиовсплески предложил «эффект дизъюнкции» из психологии: пересеклись служебные слова,
а не смысл. Совпадение слов — не совпадение смысла, поэтому здесь настоящие эмбеддинги
(embeddings_build.py).

ПИШЕМ В ОТДЕЛЬНОЕ ПОЛЕ `tags_vec`. Нынешние теги не трогаем: переключение — решение
владельца после того, как он посмотрит глазами.

    python tag_by_vector.py --report              # распределение сходства, выбор порога
    python tag_by_vector.py --blind 30            # слепая выборка на проверку глазами
    python tag_by_vector.py --apply --threshold 0.55 --top 8
"""
import json, math, random, sys, pathlib, argparse, collections

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
SEED = 42


def load(kind):
    p = DATA / f"embeddings-{kind}.jsonl"
    if not p.exists():
        sys.exit(f"нет {p} — сначала embeddings_build.py --kinds {kind}")
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def normed(recs):
    """Нормируем один раз — тогда косинус это просто скалярное произведение."""
    out = []
    for r in recs:
        v = r["vec"]
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        out.append((r, [x / n for x in v]))
    return out


def sims(avec, refs):
    return sorted(((sum(a * b for a, b in zip(avec, rv)), r["id"]) for r, rv in refs),
                  reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", default="tags", choices=["tags", "laws", "scientists"])
    ap.add_argument("--threshold", type=float, default=0.55)
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--blind", type=int, default=0)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--out", default="data/tags-vec.json")
    args = ap.parse_args()

    arts = normed(load("articles"))
    refs = normed(load(args.kind))
    print(f"статей {len(arts)}, {args.kind} {len(refs)}")

    # ---- распределение сходства: на чём вообще выбирать порог ----
    if args.report:
        best, allsim = [], []
        for r, av in arts:
            s = sims(av, refs)
            best.append(s[0][0])
            allsim.extend(x[0] for x in s[:20])
        best.sort()
        allsim.sort()
        def q(a, p): return a[int(p * (len(a) - 1))]
        print("\nсходство ЛУЧШЕГО кандидата на статью:")
        for p in (0.05, 0.25, 0.5, 0.75, 0.95):
            print(f"  {int(p*100):>2}-й перцентиль: {q(best, p):.3f}")
        print("\nсходство любого из топ-20:")
        for p in (0.5, 0.75, 0.9, 0.99):
            print(f"  {int(p*100):>2}-й перцентиль: {q(allsim, p):.3f}")

        print(f"\n{'порог':>6} {'тегов в ходу':>13} {'на статью':>11} {'без единого':>12}")
        for th in (0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70):
            used, per, empty = set(), 0, 0
            for r, av in arts:
                s = [x for x in sims(av, refs)[:args.top] if x[0] >= th]
                if not s:
                    empty += 1
                per += len(s)
                used.update(i for _, i in s)
            print(f"{th:>6.2f} {len(used):>13} {per/len(arts):>11.1f} {empty:>12}")
        return

    # ---- слепая выборка: качество смотрит человек, а не метрика ----
    if args.blind:
        rnd = random.Random(SEED)
        sample = rnd.sample(arts, min(args.blind, len(arts)))
        lines = []
        for r, av in sample:
            s = [x for x in sims(av, refs)[:args.top] if x[0] >= args.threshold]
            lines.append({
                "id": r["id"],
                "предложено": [{"что": i.split(":", 1)[1], "сходство": round(v, 3)}
                               for v, i in s],
            })
        out = DATA / f"blind-{args.kind}-{args.threshold}.json"
        out.write_text(json.dumps(lines, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nслепая выборка на {len(lines)} статей: {out}")
        print("Смотреть ГЛАЗАМИ и считать долю уместных. Ниже 80% — порог не годится.")
        print("Метрика тут не поможет: она не знает, уместен ли «эффект дизъюнкции»\n"
              "в статье про радиовсплески — а человек знает с одного взгляда.")
        return

    # ---- применение: пишем в отдельный файл, data.json не трогаем ----
    if args.apply:
        res, used = {}, collections.Counter()
        for r, av in arts:
            s = [x for x in sims(av, refs)[:args.top] if x[0] >= args.threshold]
            aid = r["id"].split(":", 1)[1]
            res[aid] = [{"id": i.split(":", 1)[1], "sim": round(v, 4)} for v, i in s]
            for _, i in s:
                used[i.split(":", 1)[1]] += 1
        out = ROOT / args.out
        out.write_text(json.dumps({
            "kind": args.kind, "threshold": args.threshold, "top": args.top,
            "model": "@cf/baai/bge-m3", "dim": 1024,
            "articles": res,
        }, ensure_ascii=False), encoding="utf-8")
        print(f"записано: {out}")
        print(f"{args.kind} в ходу: {len(used)} из {len(refs)}")
        print(f"на статью в среднем: {sum(len(v) for v in res.values())/len(res):.1f}")
        print("самые частые:", ", ".join(f"{k}({v})" for k, v in used.most_common(8)))
        return

    ap.print_help()


if __name__ == "__main__":
    main()
