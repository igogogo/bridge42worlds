#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Особые точки: где рекомендации разным авторам показывают в одно место.

Владелец 11 августа: «в пространстве нашего поля бурения эти рекомендации будут
отмечены как особые точки, и если несколько точек совпадут от разных статей — туда
можно отдельно список вести, что мы рекомендуем исследовать, и со ссылками почему».

Мысль сильная: совет одному автору — это совет. Три независимых совета, показавших
в одну точку, — это уже не совет, а сигнал. Мы не сговаривались: каждое направление
написано из своей статьи и своих соседей.

ГЛАВНАЯ ТРУДНОСТЬ — НЕ КЛАСТЕРИЗАЦИЯ, А ПОРОГ. «Совпали» нельзя определить числом
косинуса, и это не придирка к точности:

  · у нас узкий коридор — по корпусу лучший сосед лежит между 0,606 и 0,760;
  · направления вдобавок написаны ОДНИМ ЖАНРОМ. Все они устроены как «может быть
    интересно проверить, что будет, если…». Два направления похожи уже потому, что
    оба — направления, а не потому, что они про одно и то же. Замер жанровой прибавки
    печатается ниже: это те самые проценты, которые иначе примешь за находку.

Поэтому здесь совпадение определяется НЕ порогом косинуса, а отклонением от того,
как выглядит обычная пара направлений. Считаем все пары из РАЗНЫХ статей, берём их
среднее и разброс, и совпадением называем пару, ушедшую вверх на z сигм. Такое
определение переживёт и смену модели, и рост корпуса: жанровая прибавка входит
в среднее и вычитается сама.

    python special_points.py                 карта особых точек, порог по умолчанию
    python special_points.py --z 3 --min-src 3   строже: три сигмы и три разные статьи
    python special_points.py --need           сколько направлений нужно до первой находки

СВЯЗЬ С БУРЕНИЕМ. Особая точка ценна тем, что лежит НЕ там, где густо: совпадение
трёх направлений в области, где у нас пусто, — это и есть «где бурить». Поэтому
каждая находка сверяется с картой drill.py, и в списке видно, пустая область или нет.
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")
CACHE = DATA / "points-cache.jsonl"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def collect():
    """Направления из всех разобранных статей. Одна точка = одно направление."""
    pts = []
    for p in sorted(MAIN.glob("lang/ru/archive/*/*/data.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        rec = (d.get("recommend") or {}).get("ru") or {}
        for i, dr in enumerate(rec.get("directions") or []):
            t = " ".join(str(dr.get("text", "")).split())
            if len(t) < 40:
                continue
            pts.append({"src": p.parent.name, "n": i, "text": t,
                        "based_on": dr.get("based_on") or [],
                        "frontier": rec.get("frontier") or {}})
    return pts


def vectors(pts):
    sys.path.insert(0, str(ROOT))
    from embeddings_build import embed_cached, load_env
    import numpy as np
    key = load_env(MAIN).get("DEEPINFRA_API_KEY", "")
    if not key:
        sys.exit("нет DEEPINFRA_API_KEY")
    M = np.asarray(embed_cached([p["text"] for p in pts], key, CACHE, "направления"),
                   dtype=np.float32)
    M /= np.linalg.norm(M, axis=1, keepdims=True) + 1e-9
    return M


def genre_shift(M, pts):
    """Насколько направления похожи друг на друга ПРОСТО ПОТОМУ, что они направления.

    Сравниваем среднюю близость пар направлений со средней близостью пар наших статей.
    Разница — это жанровая прибавка. Её нельзя вычесть один раз и забыть, но её надо
    знать: без неё «0,72 — они про одно и то же!» звучит убедительно и означает ноль.
    """
    import numpy as np
    S = M @ M.T
    iu = np.triu_indices(len(M), 1)
    dif = np.array([S[i, j] for i, j in zip(*iu)
                    if pts[i]["src"] != pts[j]["src"]])
    try:
        import recommend_ml
        A = recommend_ml._load("abstract")[0][:800]
        SA = A @ A.T
        ja = np.triu_indices(len(A), 1)
        base = float(SA[ja].mean())
    except Exception:
        base = float("nan")
    return dif, base


def auto_z(n_pairs, budget=0.5):
    """Порог, при котором на ВЕСЬ список ожидается меньше одного ложного совпадения.

    Фиксированное число сигм здесь — ловушка, и она сработает не сразу, а когда список
    станет ценным. Пар растёт как квадрат числа направлений: при 31 направлении их 441,
    при 1000 — полмиллиона. Порог 2,5σ пропускает 0,6% пар, то есть на 31 направлении
    даст пару ложных срабатываний, а на тысяче — три тысячи. Страница «что мы
    рекомендуем исследовать» превратится в шум ровно тогда, когда её начнут читать.

    Поэтому порог считается от объёма: берём такое z, при котором ожидаемое число
    случайных пар выше него меньше половины. Это обычная поправка на множественную
    проверку; здесь она не формальность, а разница между списком и мусором.
    """
    from math import erfc, sqrt
    lo, hi = 1.0, 8.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if n_pairs * erfc(mid / sqrt(2)) / 2 > budget:
            lo = mid
        else:
            hi = mid
    return round(hi, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--z", type=float, default=0,
                    help="во сколько сигм над обычной парой начинается «совпали»; "
                         "0 = подобрать под объём (по умолчанию, см. auto_z)")
    ap.add_argument("--min-src", type=int, default=2, help="из скольких РАЗНЫХ статей")
    ap.add_argument("--need", action="store_true",
                    help="прикинуть, сколько направлений нужно до первой находки")
    args = ap.parse_args()
    import numpy as np

    pts = collect()
    srcs = {p["src"] for p in pts}
    print(f"направлений: {len(pts)} из {len(srcs)} статей")
    if len(pts) < 4:
        sys.exit("слишком мало точек — механику проверять не на чем")

    M = vectors(pts)
    dif, base = genre_shift(M, pts)
    mu, sd = float(dif.mean()), float(dif.std())
    if not args.z:
        args.z = auto_z(len(dif))
        print(f"\nпорог подобран под объём: {args.z}σ "
              f"(на {len(dif)} парах ожидается меньше одного ложного)")
    print(f"\nОБЫЧНАЯ пара направлений из разных статей: {mu:.3f} ± {sd:.3f}"
          f"  (пар: {len(dif)})")
    if base == base:
        print(f"обычная пара НАШИХ СТАТЕЙ:                {base:.3f}")
        print(f"жанровая прибавка: +{mu - base:.3f} — столько дают одинаковые обороты,")
        print(f"                   а не одинаковый смысл. Порог по косинусу это съест.")
    print(f"порог «совпали»: {mu + args.z * sd:.3f} (это {args.z}σ), "
          f"максимум в данных {float(dif.max()):.3f}")

    if args.need:
        # Сколько пар нужно, чтобы хотя бы одна ушла за z сигм, если пары ведут себя
        # как сейчас. Это НЕ предсказание находки — это ответ на вопрос «мало ли данных».
        from math import erfc, sqrt
        p_hit = erfc(args.z / sqrt(2)) / 2
        pairs_needed = 1 / max(p_hit, 1e-12)
        n_needed = int((1 + (1 + 8 * pairs_needed) ** 0.5) / 2) + 1
        per_article = len(pts) / len(srcs)
        print(f"\nПри случайном раскладе пара уходит за {args.z}σ с вероятностью "
              f"{p_hit:.5f}.\nЗначит на одно СЛУЧАЙНОЕ срабатывание нужно "
              f"~{pairs_needed:,.0f} пар, то есть ~{n_needed} направлений "
              f"(~{n_needed/per_article:.0f} статей).")
        print(f"Сейчас {len(pts)} направлений — {len(dif)} пар. Всё, что найдётся "
              f"на этом объёме, скорее находка, чем случайность; но и не найтись "
              f"ничему — нормально.")

    S = M @ M.T
    hits = []
    thr = mu + args.z * sd
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            if pts[i]["src"] == pts[j]["src"] or S[i, j] < thr:
                continue
            # Опора на ОДНУ И ТУ ЖЕ соседнюю работу — не совпадение, а общий источник.
            # Два автора, которых мы отправили читать одну статью, обязаны совпасть.
            shared = set(pts[i]["based_on"]) & set(pts[j]["based_on"])
            hits.append((float(S[i, j]), i, j, shared))
    hits.sort(reverse=True)

    # Пары с общей опорой считаем ОТДЕЛЬНО и в находки не берём. Это главная ловушка
    # всей затеи, и она выглядит убедительнее настоящих находок: замер 11 августа —
    # все три пары выше порога совпали ровно потому, что мы сами отправили обоих
    # авторов читать одну и ту же статью. Лучшая из них дала +5,5σ. Это не сходящиеся
    # независимые линии, а эхо нашей собственной рекомендации.
    echo = [h for h in hits if h[3]]
    real = [h for h in hits if not h[3]]
    print(f"\n{'='*76}\nОСОБЫЕ ТОЧКИ: независимых пар — {len(real)}, "
          f"эха общей опоры — {len(echo)}\n{'='*76}")
    if not real:
        print("Независимых совпадений нет. Это нормальный ответ при таком объёме,")
        print("а не поломка: список «что исследовать» начнёт наполняться, когда")
        print("ночной автомат наберёт статей. Механика готова и ждёт данных.")
    for s, i, j, shared in (real + echo)[:20]:
        z = (s - mu) / sd
        mark = "  ⚠ общая опора " + ", ".join(shared) if shared else ""
        print(f"\n{s:.3f} ({z:+.1f}σ){mark}")
        print(f"  [{pts[i]['src']}] {pts[i]['text'][:150]}")
        print(f"  [{pts[j]['src']}] {pts[j]['text'][:150]}")

    # Сгущение = не пара, а группа. Собираем связные группы по парам выше порога
    # и требуем, чтобы в группе было min_src РАЗНЫХ статей: три направления из одной
    # статьи — это одна мысль автора разбора, а не сходящиеся независимые линии.
    parent = list(range(len(pts)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for _, i, j, shared in hits:
        if not shared:
            parent[find(i)] = find(j)
    groups = {}
    for i in range(len(pts)):
        groups.setdefault(find(i), []).append(i)
    good = [g for g in groups.values()
            if len({pts[i]["src"] for i in g}) >= args.min_src]
    print(f"\nсгущений из {args.min_src}+ разных статей: {len(good)}")
    for g in good:
        print(f"\n· статьи: {', '.join(sorted({pts[i]['src'] for i in g}))}")
        for i in g:
            print(f"    {pts[i]['text'][:130]}")
        hint = drill_check(M[g].mean(0))
        if hint:
            print(f"  ГДЕ ЛЕЖИТ: {hint}")

    # Сводка — это числа для нас, а на страницу нужны сами точки. Пишем их отдельным
    # файлом: ведущая показывает сгущения читателю (раздел «Что исследовать»), и брать
    # их из печати в консоль было бы единственным способом — то есть никаким.
    points_out = []
    for g in good:
        srcs_g = sorted({pts[i]["src"] for i in g})
        points_out.append({
            "статьи": srcs_g,
            "направления": [pts[i]["text"] for i in g],
            "область": drill_check(M[g].mean(0)) or "",
        })
    (DATA / "special-points-list.json").write_text(
        json.dumps({"сгущения": points_out, "порог": round(thr, 4),
                    "из_направлений": len(pts), "из_статей": len(srcs)},
                   ensure_ascii=False, indent=1), encoding="utf-8")

    out = {"направлений": len(pts), "статей": len(srcs),
           "обычная_пара": round(mu, 4), "разброс": round(sd, 4),
           "жанровая_прибавка": None if base != base else round(mu - base, 4),
           "порог_сигм": args.z, "порог": round(thr, 4),
           "независимых_пар": len(real), "эха_общей_опоры": len(echo),
           "сгущений": len(good)}
    (DATA / "special-points.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                              encoding="utf-8")
    print(f"\nсводка в data/special-points.json")
    return 0


def drill_check(v):
    """В пустой области лежит эта точка или в обжитой. Связь с задачей о бурении."""
    import numpy as np
    cp, rp = DATA / "drill-centers.npy", DATA / "drill-regions.json"
    if not (cp.exists() and rp.exists()):
        return ""
    C = np.load(cp)
    R = json.loads(rp.read_text(encoding="utf-8"))
    v = v / (np.linalg.norm(v) + 1e-9)
    j = int((C @ v).argmax())
    where = "ПУСТО у нас" if R["n_ours"][j] == 0 else f"у нас {R['n_ours'][j]} статей"
    return f"{R['names'][j]} — у науки {R['n_arxiv'][j]} работ, {where}"


if __name__ == "__main__":
    sys.exit(main())
