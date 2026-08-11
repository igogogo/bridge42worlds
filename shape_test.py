#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сфера, бублик, бутылка Клейна — или ничего из этого. Проверка формы корпуса.

Владелец 11 августа: «можем ли мы задать общую топологию полученного пространства —
тип бублик, бутылка Клейна и так далее… проверь и бутылку тоже, ну и бублик уж заодно,
сферу».

КАК ЭТО ВООБЩЕ РАЗЛИЧАЮТ. Форму облака точек различают по числам Бетти: сколько у него
связных кусков (β₀), сквозных петель (β₁) и полостей (β₂). У каждой поверхности свой
отпечаток, и его нельзя подделать:

    сфера            β₀=1  β₁=0  β₂=1     полость есть, петель нет
    бублик           β₀=1  β₁=2  β₂=1     две независимые петли: вдоль и поперёк
    бутылка Клейна   β₀=1  β₁=2  β₂=1     ПО МОДУЛЮ 2 — как у бублика
    плоскость/шар    β₀=1  β₁=0  β₂=0     ничего

Бутылку от бублика по этим числам не отличить: над полем из двух элементов, в котором
считает ripser, отпечатки совпадают. Различие видно только по кручению в целочисленных
гомологиях, и это отдельная работа. Поэтому вопрос ставится честно так: похоже ли
на «что-то с петлями» (бублик ИЛИ бутылка), на сферу, или ни на что.

ГЛАВНОЕ — ЭТАЛОНЫ. Сегодня я уже получил бессмысленный ответ ровно потому, что построил
эталон-дерево в 1024 измерениях, где ветвление стирается размерностью (см. hyperbolic.py).
Здесь эталоны строятся честно: настоящие сфера, бублик и бутылка Клейна, с тем же числом
точек и тем же шумом, что у наших данных. Если инструмент не находит петли у настоящего
бублика — верить его ответу про наши данные нельзя, и это видно сразу по таблице.

ЧЕГО ЖДАТЬ. Скорее всего — «ни на что». Замер плотности (topology.py) дал 34 независимых
измерения при 1,26 точки на ось: на такой разреженности гомологии находят шум. Поэтому
проверяем не всё облако, а его ПРОЕКЦИЮ в 3–5 измерений, где точек на единицу объёма
хватает. Отрицательный ответ тут тоже ответ: он закрывает вопрос числом, а не мнением.

    python shape_test.py                 наши статьи, проекция в 3 измерения
    python shape_test.py --dim 4 --n 400
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"

CUT = 0.25   # порог «настоящей» дырки в единицах среднего расстояния; калибруется ниже

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def sphere(n, rng, noise=0.0):
    v = rng.standard_normal((n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    return v + rng.standard_normal((n, 3)) * noise


def torus(n, rng, noise=0.0, R=2.0, r=1.0):
    u = rng.uniform(0, 2 * np.pi, n)
    v = rng.uniform(0, 2 * np.pi, n)
    x = (R + r * np.cos(v)) * np.cos(u)
    y = (R + r * np.cos(v)) * np.sin(u)
    z = r * np.sin(v)
    p = np.stack([x, y, z], axis=1)
    return p + rng.standard_normal(p.shape) * noise


def klein(n, rng, noise=0.0):
    """Бутылка Клейна не помещается в три измерения без самопересечения, поэтому
    берём её честное вложение в четыре («восьмёрочное» представление)."""
    u = rng.uniform(0, 2 * np.pi, n)
    v = rng.uniform(0, 2 * np.pi, n)
    cu, su = np.cos(u), np.sin(u)
    p = np.stack([(2 + np.cos(v)) * cu,
                  (2 + np.cos(v)) * su,
                  np.sin(v) * np.cos(u / 2),
                  np.sin(v) * np.sin(u / 2)], axis=1)
    return p + rng.standard_normal(p.shape) * noise


def betti(X, maxdim=2, cut=CUT):
    """Числа Бетти: сколько признаков живёт дольше порога, заданного МАСШТАБОМ облака.

    Первая версия считала долгоживущим всё, что прожило больше трети самого долгого
    признака В СВОЕЙ размерности. На бумаге разумно, на деле бессмысленно: у сферы
    настоящих петель нет вовсе, значит «самая долгая петля» — это шум, и треть шума
    тоже шум. Прогон показал у сферы 31 петлю вместо нуля.

    Здесь порог привязан к размеру самого облака: каждое облако сначала приводится
    к среднему попарному расстоянию, равному единице, и признак считается настоящим,
    если прожил дольше `cut` в этих единицах. Правило одно на все наборы.

    Значение `cut` подобрано НА ЭТАЛОНАХ — так, чтобы сфера дала (0,1), а бублик (2,1).
    Это не подгонка под желаемый ответ: настройка прибора по известным образцам и есть
    единственный способ узнать, что он вообще меряет. Про наши данные при подборе
    ничего не известно — они в калибровке не участвуют.
    """
    from ripser import ripser
    from scipy.spatial.distance import pdist
    X = np.asarray(X, dtype=np.float64)
    D = pdist(X)
    X = X / D.mean()                      # общая единица длины для всех наборов
    res = ripser(X, maxdim=maxdim, thresh=float(np.quantile(pdist(X), 0.92)))
    out = []
    for d, dg in enumerate(res["dgms"]):
        if d == 0:
            out.append(int(np.sum(~np.isfinite(dg[:, 1]))) or 1)
            continue
        if len(dg) == 0:
            out.append(0)
            continue
        life = dg[:, 1] - dg[:, 0]
        life = life[np.isfinite(life)]
        out.append(int(np.sum(life > cut)))
    return out


def load_ours(n, dim, rng):
    vecs = []
    with (DATA / "embeddings-articles.jsonl").open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                if r.get("vec"):
                    vecs.append(r["vec"])
    M = np.asarray(vecs, dtype=np.float32)
    M /= np.linalg.norm(M, axis=1, keepdims=True) + 1e-9
    M = M[rng.choice(len(M), min(n, len(M)), replace=False)]
    # Проекция на главные оси: в 34 измерениях точек не хватает ни на что, в трёх —
    # хватает. Это не упрощение ради красоты, а единственный масштаб, где вопрос
    # вообще имеет смысл при нашей плотности.
    mu = M.mean(0)
    _, _, Vt = np.linalg.svd(M - mu, full_matrices=False)
    return (M - mu) @ Vt[:dim].T


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--dim", type=int, default=3)
    ap.add_argument("--noise", type=float, default=0.08)
    ap.add_argument("--cut", type=float, default=0)
    ap.add_argument("--calibrate", action="store_true",
                    help="подобрать порог по эталонам: сфера (0,1), бублик (2,1)")
    args = ap.parse_args()
    global np
    import numpy as np

    rng = np.random.default_rng(42)
    ours = load_ours(args.n, args.dim, rng)
    n = len(ours)

    sets = [
        ("СФЕРА (эталон)", sphere(n, rng, args.noise)),
        ("БУБЛИК (эталон)", torus(n, rng, args.noise)),
        ("БУТЫЛКА КЛЕЙНА (эталон)", klein(n, rng, args.noise)),
        ("случайное облако (эталон)", rng.standard_normal((n, args.dim))),
        ("НАШИ СТАТЬИ", ours),
    ]
    if args.calibrate:
        # Прибор настраивается по образцам с ИЗВЕСТНЫМ ответом. Ищем порог, при котором
        # сфера даёт (0,1), а бублик (2,1); если такого нет — прибор к задаче негоден,
        # и это надо знать до того, как смотреть на свои данные.
        sp, to = sphere(n, rng, args.noise), torus(n, rng, args.noise)
        print(f"{'порог':>7} {'сфера β₁,β₂':>14} {'бублик β₁,β₂':>15}  годен")
        for c in (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50):
            a1 = betti(sp, cut=c); a2 = betti(to, cut=c)
            ok = (a1[1], a1[2], a2[1], a2[2]) == (0, 1, 2, 1)
            print(f"{c:>7.2f} {str(a1[1:]):>14} {str(a2[1:]):>15}  {'ДА' if ok else ''}")
        return 0

    print(f"точек в каждом наборе: {n} · проекция наших данных в {args.dim} измерения")
    print(f"\n{'что':<28} {'β₀':>4} {'β₁':>4} {'β₂':>4}   отпечаток")
    for name, X in sets:
        X = np.asarray(X, dtype=np.float64)
        b = betti(X, cut=args.cut or CUT)
        b += [0] * (3 - len(b))
        shape = ("сфера" if (b[1], b[2]) == (0, 1) else
                 "бублик или бутылка" if b[1] == 2 else
                 "одна петля" if b[1] == 1 else
                 "без дырок")
        print(f"{name:<28} {b[0]:>4} {b[1]:>4} {b[2]:>4}   {shape}")
    print("\nСмотреть сначала на ЭТАЛОНЫ: если у настоящего бублика не нашлись две петли,")
    print("инструмент не работает, и строка про наши данные ничего не значит.")
    return 0


if __name__ == "__main__":
    import numpy as np
    sys.exit(main())
