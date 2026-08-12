#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сколько мы теряем, сжимая вектор с 1024 измерений. Замер под решение о хранении.

Вопрос ведущей 11 августа: хранить полное поле на 3,13 млн работ в Vectorize при
1024 измерениях — $128/мес, при 256 — $32/мес. Вопрос «сколько теряем при сжатии»
решает, можно ли вообще обсуждать второй вариант.

КАК МЕРИМ. Правда — это соседи при полной размерности: их выдаёт та самая модель,
которой мы пользуемся, и другой истины у нас нет. Сжатие оценивается по тому, много
ли из них оно теряет: берём топ-10 при 1024 и смотрим, сколько из них осталось
в топ-10 при 256. Это recall@10, и он отвечает ровно на тот вопрос, который задан.

ДВА СПОСОБА СЖАТИЯ, и их важно не перепутать.
  · PCA — поворот пространства так, чтобы главное легло в первые оси. Требует обучения
    на выборке, но сохраняет почти всё.
  · Простое отсечение первых 256 чисел. Так можно с «матрёшечными» моделями, которые
    специально этому обучены. bge-m3 к ним НЕ относится, и проверить это стоит замером,
    а не верой: цена ошибки — тихо испорченный поиск по всему корпусу.

ОБУЧАЕМ НА ОДНОЙ ПОЛОВИНЕ, ПРОВЕРЯЕМ НА ДРУГОЙ. Иначе PCA подгонится под те самые
точки, на которых её и проверяют, и покажет качество, которого на новых работах
не будет.

    python compress_eval.py                 arXiv, 1024 → 512/256/128/64
    python compress_eval.py --what ours     на наших статьях
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def load(what):
    import numpy as np
    if what == "arxiv":
        import vecstore
        _, m = vecstore.load(DATA / "arxiv")
        M = np.asarray(m, dtype=np.float32)
    else:
        vecs = []
        with (DATA / "embeddings-articles.jsonl").open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    if r.get("vec"):
                        vecs.append(r["vec"])
        M = np.asarray(vecs, dtype=np.float32)
    M /= np.linalg.norm(M, axis=1, keepdims=True) + 1e-9
    return M


def topk(M, Q, k):
    """Номера k ближайших к каждой строке Q, кроме себя самой."""
    import numpy as np
    out = np.empty((len(Q), k), dtype=np.int32)
    for s in range(0, len(Q), 256):
        sim = Q[s:s + 256] @ M.T
        for r in range(len(sim)):
            sim[r, s + r] = -2.0
        idx = np.argpartition(-sim, k, axis=1)[:, :k]
        rows = np.arange(len(sim))[:, None]
        out[s:s + 256] = idx[rows, np.argsort(-sim[rows, idx], axis=1)]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", default="arxiv", choices=("arxiv", "ours"))
    ap.add_argument("--dims", default="512,256,128,64")
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--queries", type=int, default=1000)
    args = ap.parse_args()
    import numpy as np

    M = load(args.what)
    n, d = M.shape
    print(f"{args.what}: {n:,} векторов по {d} измерений")

    # Половина на обучение сжатия, половина — рабочий корпус. Разрез через один,
    # а не пополам подряд: файл сложен по месяцам, и «первая половина» — это срез
    # моды за полгода, а не выборка из корпуса.
    fit, work = M[0::2], M[1::2]
    rng = np.random.default_rng(42)
    qi = rng.choice(len(work), min(args.queries, len(work)), replace=False)
    true = topk(work, work[qi], args.k)

    mu = fit.mean(0)
    # SVD на выборке в 20 тысяч строк вместо всей половины: матрица ковариаций
    # одна и та же с точностью до третьего знака, а времени в разы меньше.
    sample = fit[rng.choice(len(fit), min(20000, len(fit)), replace=False)]
    _, _, Vt = np.linalg.svd(sample - mu, full_matrices=False)

    deep = {}
    print(f"\n{'размер':>7} {'PCA@' + str(args.k):>9} {'+пересчёт':>11} {'отсечение':>11}"
          f" {'память 3,13 млн':>17} {'Vectorize/мес':>14}")
    for dim in [int(x) for x in args.dims.split(",")]:
        P = Vt[:dim]
        # PCA
        A = (work - mu) @ P.T
        A /= np.linalg.norm(A, axis=1, keepdims=True) + 1e-9
        got = topk(A, A[qi], args.k)
        pca = float(np.mean([len(set(a) & set(b)) for a, b in zip(true, got)])) / args.k
        # ГЛАВНОЕ ЧИСЛО. Сжатый вектор в рабочей схеме — не ответ, а первая ступень:
        # он достаёт широкий черпак, который затем пересчитывается ПОЛНЫМ вектором
        # (он лежит на диске, это бесплатно). Поэтому важно не «сколько настоящих
        # соседей в топ-10 сжатого», а «сколько их в топ-100 сжатого» — потерянное
        # на этом шаге не вернёт уже ничто, а лишнее отсеет точный пересчёт.
        wide = topk(A, A[qi], 100)
        deep[dim] = float(np.mean([len(set(a) & set(b[:100])) for a, b in zip(true, wide)])) / args.k
        # простое отсечение
        B = work[:, :dim].copy()
        B /= np.linalg.norm(B, axis=1, keepdims=True) + 1e-9
        got2 = topk(B, B[qi], args.k)
        cut = float(np.mean([len(set(a) & set(b)) for a, b in zip(true, got2)])) / args.k
        gb = 3_130_000 * dim * 2 / 1e9
        vec = 3_130_000 * dim / 1e6 * 0.04
        print(f"{dim:>7} {pca*100:>8.1f}% {deep[dim]*100:>10.1f}% {cut*100:>10.1f}%"
              f" {gb:>14.1f} ГБ {vec:>12,.0f} $")
    print(f"\n(память — float16 на диске; Vectorize — $0,04 за млн измерений в месяц)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
