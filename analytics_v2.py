#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Карта статей на эмбеддингах: UMAP + HDBSCAN вместо TF-IDF + t-SNE.

Волна 17 августа, пункты 1 и 2 раздела ML. Аудит: мегакластер, «бульоны» с одинаковыми
топ-тегами, жёсткий кап k=24, и каждый день новая укладка — читатель через неделю
не узнаёт карту.

ТРИ ПОЛОМКИ НЫНЕШНЕЙ КАРТЫ, И ВСЕ ТРИ ОТ ОДНОГО КОРНЯ — от того, что статья
представлена своими ТЕГАМИ, а не своим содержанием.

  · На карту попадают только размеченные работы: TF-IDF строится по строке тегов,
    `min_df=2` выбрасывает редкие, статья без тегов исчезает молча. Сейчас на карте
    2108 точек при 4664 работах с вектором — почти половина корпуса не показана.
  · «Бульоны» неизбежны: если четыре кластера получили `spacetime_curvature` в топ,
    это не сбой кластеризации, а следствие того, что тег один на четыре темы.
    Разрешение карты ограничено разрешением справочника, а не данных.
  · Число кластеров задано формулой `len(arts)//60` с капом 24. Оно не выводится
    из данных вообще.

Здесь статья представлена своим вектором. Кластеры ищет HDBSCAN — он сам определяет,
сколько их, и, в отличие от k-средних, имеет право сказать «эта работа ни к чему
не примыкает» вместо того, чтобы приписать её к ближайшему центру. Такие работы
получают метку -1, и это честный ответ, а не дыра.

УЗНАВАЕМОСТЬ КАРТЫ — ПУНКТ 2 И ГЛАВНОЕ РАЗЛИЧИЕ. t-SNE не умеет доставлять новую точку
в готовую картину: чтобы добавить статью, надо пересчитать всё, и всё уезжает. UMAP
умеет: проекция запоминается (`data/analytics/map-basis.joblib`), новая работа
подсаживается в неё вызовом transform, старые не двигаются ВООБЩЕ — не «почти»,
а ровно. Полная переукладка становится редкой «пересъёмкой» по явному флагу.

Это проверяется, а не декларируется: `--check` обучает проекцию на 90% работ,
подсаживает остальные 10% и отдельно переобучает на всех, после чего печатает,
насколько сдвинулись СТАРЫЕ точки в обоих случаях.

    python analytics_v2.py                    собрать карту (подсадка в готовую проекцию)
    python analytics_v2.py --resurvey         пересъёмка: проекция строится заново
    python analytics_v2.py --check            замер устойчивости, ничего не пишет
"""
import argparse
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"


def _field_dir():
    """Где лежит поле вектора. Скрипт писался в копии ML — там поле в data/; у ведущей
    и остальных ролей оно в соседней копии ../b42-ml/data. Тот же порядок поиска, что
    в tools/field.py: своя папка → папка ML → переменная окружения B42_FIELD_DIR.
    Без этого сборка падала у всех, кроме автора, — классическая «работает у меня»."""
    import os
    for c in (DATA, ROOT.parent / "b42-ml" / "data",
              pathlib.Path(os.environ.get("B42_FIELD_DIR", "")) if os.environ.get("B42_FIELD_DIR") else None):
        if c and (c / "field.ids").exists():
            return c
    return DATA
# lang/** в рабочие копии не выкладывается — индекс статей и готовые карты живут
# в главной папке, читать и писать их надо там. Поле остаётся локальным: оно большое
# и в git не идёт.
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")
OUT = MAIN / "data" / "analytics"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))

BASIS = OUT / "map-basis.joblib"


def load_articles(lang):
    idx = json.loads((MAIN / f"lang/{lang}/articles-index.json")
                     .read_text(encoding="utf-8"))
    import field_build as fb
    art = {}
    for a in idx:
        # Номер работы в индексе идёт С ВЕРСИЕЙ (2505.00266v1), а в поле — без.
        # Без приведения к одному виду 1010 работ (18% корпуса) молча не находят
        # свой вектор и исчезают с карты — ровно та потеря, которую эта карта
        # и должна была устранить.
        aid = fb._base_id(str(a.get("id") or ""))
        if not aid:
            continue
        r = art.setdefault(aid, {"tags": set(), "title": "", "date": "", "url": ""})
        r["tags"] |= set(a.get("tags") or [])
        # Полная версия важнее экспресса: у неё разметка богаче и заголовок точнее.
        if a.get("version") == "popular" or not r["title"]:
            r["title"] = a.get("title") or r["title"]
            r["date"] = a.get("date") or r["date"]
            r["url"] = a.get("url") or r["url"]
    return art


def fit_umap(X, seed=17, n=3):
    """Укладка для показа: три измерения, точки разведены (min_dist).

    random_state фиксирован намеренно: без него UMAP параллелится и даёт разную
    укладку от запуска к запуску. Скорость здесь неважна, воспроизводимость важна —
    ради неё вся затея.
    """
    import umap
    return umap.UMAP(n_components=n, n_neighbors=15, min_dist=0.12,
                     metric="cosine", random_state=seed).fit(X)


def fit_cluster_space(X, seed=17, n=10):
    """Отдельное пространство для КЛАСТЕРИЗАЦИИ, и это не перестраховка.

    Первая версия искала кластеры прямо в трёхмерной картинке — по той же логике,
    по которой их видит глаз. Замер показал, чего это стоит: мегакластер на 779 работ,
    16.5% корпуса, ровно та беда, из-за которой волна и началась. В десяти измерениях
    при тех же настройках крупнейший кластер — 3.7%.

    Причина простая: три измерения слишком тесны, чтобы развести четыре с половиной
    тысячи работ, и разные темы слипаются в один ком просто от нехватки места.
    Показывать по-прежнему надо в трёх — смотреть больше нечем, — но искать группы
    в них нельзя.

    min_dist=0 здесь потому, что сжимать плотные места полезно для поиска групп
    и вредно для картинки: это разные задачи, и параметр у них разный.
    """
    import umap
    return umap.UMAP(n_components=n, n_neighbors=15, min_dist=0.0,
                     metric="cosine", random_state=seed).fit(X)


def norm01(P):
    import numpy as np
    lo, hi = P.min(0), P.max(0)
    return (P - lo) / (hi - lo + 1e-9), lo, hi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--resurvey", action="store_true",
                    help="перестроить проекцию заново (карта поедет)")
    ap.add_argument("--check", action="store_true",
                    help="замерить устойчивость и выйти")
    ap.add_argument("--min-cluster", type=int, default=25)
    ap.add_argument("--method", default="leaf", choices=("leaf", "eom"),
                    help="leaf — дробно и честно, eom — крупно и с комом")
    ap.add_argument("--out", default=str(OUT / "articles-map-v2.json"))
    args = ap.parse_args()

    import numpy as np
    import joblib
    import vecstore
    import field_build as fb
    from sklearn.cluster import HDBSCAN

    art = load_articles(args.lang)
    # Поле открывается как memmap, и строки берутся поштучно. Через vecstore.load
    # с latest=True numpy материализует всю матрицу 1 556 983 × 1024 — три гигабайта
    # в памяти ради четырёх с половиной тысяч строк, и на этом сборка падала.
    ids, M = vecstore.load(_field_dir() / "field", mmap=True)
    rowof = {}
    for i, s in enumerate(ids):
        rowof[fb._base_id(s)] = i      # позже встреченное затирает раннее — как latest
    keys = sorted(a for a in art if a in rowof)
    X = np.empty((len(keys), M.shape[1]), dtype=np.float32)
    for i, a in enumerate(keys):
        X[i] = M[rowof[a]]
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-9
    print(f"работ в индексе {len(art)} · с вектором в поле {len(keys)}")

    if args.check:
        print(f"\n{'=' * 78}\nУСТОЙЧИВОСТЬ УКЛАДКИ\n{'=' * 78}")
        rng = np.random.default_rng(0)
        perm = rng.permutation(len(keys))
        cut = int(len(keys) * 0.9)
        old, new = perm[:cut], perm[cut:]
        print(f"  обучаю проекцию на {len(old)} работах…")
        m1 = fit_umap(X[old])
        P_old = m1.embedding_
        print(f"  подсаживаю {len(new)} новых через transform…")
        P_new = m1.transform(X[new])
        print(f"  переобучаю на всех {len(keys)} — так делает нынешняя карта…")
        m2 = fit_umap(X)
        P_all = m2.embedding_

        # Сравнивать координаты в лоб нельзя: UMAP определён с точностью до поворота,
        # отражения и сдвига. Поэтому сначала совмещаем две укладки наилучшим жёстким
        # преобразованием (задача Прокруста), и только остаток — настоящий сдвиг.
        A = P_old - P_old.mean(0)
        B = P_all[old] - P_all[old].mean(0)
        A /= np.linalg.norm(A) + 1e-9
        B /= np.linalg.norm(B) + 1e-9
        U, S, Vt = np.linalg.svd(A.T @ B)
        R = U @ Vt
        resid = np.linalg.norm(A @ R - B, axis=1)
        scale = np.linalg.norm(B, axis=1).mean() + 1e-9
        print(f"\n  ПОДСАДКА (transform): старые точки сдвинулись на 0.000 — "
              f"по построению, они не пересчитываются")
        print(f"  ПЕРЕУКЛАДКА (как сейчас): медианный сдвиг старой точки "
              f"{np.median(resid) / scale * 100:.1f}% от радиуса облака,")
        print(f"     90-й процентиль {np.percentile(resid, 90) / scale * 100:.1f}%")
        print(f"\n  Вывод: пересъёмку делать по явному флагу и редко, ежедневно —")
        print(f"  только подсадка. Иначе читатель каждый день видит другую карту.")
        return 0

    # ПРОЕКЦИЯ. Либо берём сохранённую и подсаживаем в неё, либо строим заново.
    if BASIS.exists() and not args.resurvey:
        saved = joblib.load(BASIS)
        model, cmodel = saved["model"], saved["cmodel"]
        base_keys = cluster_keys = saved["keys"]
        P = np.zeros((len(keys), model.n_components), dtype=np.float32)
        known = {k: i for i, k in enumerate(base_keys)}
        seat = [i for i, k in enumerate(keys) if k not in known]
        for i, k in enumerate(keys):
            if k in known:
                P[i] = model.embedding_[known[k]]
        if seat:
            print(f"подсаживаю {len(seat)} новых работ в готовую проекцию…")
            P[seat] = model.transform(X[seat])
        else:
            print("новых работ нет — проекция без изменений")
        lo, hi = saved["lo"], saved["hi"]
        P01 = np.clip((P - lo) / (hi - lo + 1e-9), -0.05, 1.05)
        mode = "подсадка"
    else:
        print("ПЕРЕСЪЁМКА: строю проекцию заново, координаты изменятся у всех")
        model = fit_umap(X)
        P = model.embedding_
        P01, lo, hi = norm01(P)
        OUT.mkdir(parents=True, exist_ok=True)
        cmodel = fit_cluster_space(X)
        cluster_keys = keys
        joblib.dump({"model": model, "cmodel": cmodel, "keys": keys,
                     "lo": lo, "hi": hi}, BASIS)
        mode = "пересъёмка"

    # КЛАСТЕРЫ — в десятимерном пространстве, не в картинке. См. fit_cluster_space:
    # поиск групп по трёхмерной укладке давал мегакластер на 16.5% корпуса.
    E = np.zeros((len(keys), cmodel.n_components), dtype=np.float32)
    known_c = {k: i for i, k in enumerate(cluster_keys)}
    seat_c = [i for i, k in enumerate(keys) if k not in known_c]
    for i, k in enumerate(keys):
        if k in known_c:
            E[i] = cmodel.embedding_[known_c[k]]
    if seat_c:
        E[seat_c] = cmodel.transform(X[seat_c])
    # eom против leaf — развилка, и она не про вкус. eom предпочитает крупные
    # устойчивые группы и покупает низкий шум тем, что сваливает всё сомнительное
    # в один ком: 48 кластеров, крупнейший 13.8% корпуса, вне групп 28%. leaf берёт
    # самое дробное разбиение: 60 кластеров, крупнейший 4.0%, вне групп 40%.
    #
    # То есть мегакластер и «мало серых точек» — одно и то же явление, а не два
    # разных достоинства. Волна началась именно из-за кома, поэтому здесь leaf,
    # а работа, не примыкающая ни к одной группе, честно помечается -1 вместо того,
    # чтобы утяжелять ком.
    hdb = HDBSCAN(min_cluster_size=args.min_cluster, min_samples=3,
                  cluster_selection_method=args.method)
    lab = hdb.fit_predict(np.asarray(E, dtype=np.float64))
    cnt = collections.Counter(lab.tolist())
    noise = cnt.get(-1, 0)
    real = {c: n for c, n in cnt.items() if c != -1}
    print(f"\nHDBSCAN: кластеров {len(real)} · вне кластеров {noise} "
          f"({noise / len(keys) * 100:.0f}%)")
    if real:
        big = max(real.values())
        print(f"  крупнейший {big} = {big / len(keys) * 100:.1f}% корпуса")

    # Топ-теги кластера — по превышению над фоном, а не по частоте. Иначе во всех
    # кластерах первым выйдет `spacetime_curvature`: он просто частый. Именно так
    # и получаются «бульоны» с одинаковыми топами.
    base = collections.Counter()
    for k in keys:
        base.update(art[k]["tags"])
    tops = {}
    for c in sorted(real):
        mem = [keys[i] for i in np.where(lab == c)[0]]
        cc = collections.Counter()
        for k in mem:
            cc.update(art[k]["tags"])
        lift = {t: (cc[t] / len(mem)) / (base[t] / len(keys) + 1e-9)
                for t in cc if cc[t] >= max(3, len(mem) * 0.08)}
        tops[int(c)] = [t for t, _ in sorted(lift.items(), key=lambda x: -x[1])[:4]]

    dup = collections.Counter(v[0] for v in tops.values() if v)
    broth = sum(n for t, n in dup.items() if n > 1)
    print(f"  кластеров с одинаковым первым тегом («бульоны»): {broth}")

    points = [{"id": k, "t": art[k]["title"], "d": art[k]["date"],
               "x": round(float(P01[i, 0]), 4), "y": round(float(P01[i, 1]), 4),
               "z": round(float(P01[i, 2]), 4) if P01.shape[1] > 2 else 0.5,
               "c": int(lab[i]), "url": art[k]["url"]}
              for i, k in enumerate(keys)]
    out = {"points": points, "clusters": tops, "n": len(points),
           "mode": mode, "noise": noise,
           "note": "Кластер -1 — работа не примыкает к плотной группе. Это ответ, "
                   "а не пропуск: k-средние такого сказать не могут и приписывают "
                   "каждую работу к ближайшему центру.",
           "tops_note": "Топ-теги кластера — по превышению над фоном корпуса, "
                        "а не по частоте: частый тег иначе выходит первым везде."}
    pathlib.Path(args.out).write_text(json.dumps(out, ensure_ascii=False),
                                      encoding="utf-8")
    print(f"\n→ {args.out}  ({pathlib.Path(args.out).stat().st_size / 1e6:.2f} МБ)")

    # Сравнение со старой картой — там, где она есть.
    old_p = OUT / "articles-map.json"
    if old_p.exists():
        o = json.loads(old_p.read_text(encoding="utf-8"))
        oc = collections.Counter(p["c"] for p in o["points"])
        ob = collections.Counter(
            (o["clusters"].get(str(c)) or [""])[0] for c in oc)
        print(f"\n{'=' * 78}\nСТАРАЯ КАРТА ПРОТИВ НОВОЙ\n{'=' * 78}")
        print(f"  {'':<28}{'TF-IDF + t-SNE':>16}{'эмбеддинги':>16}")
        print(f"  {'работ на карте':<28}{len(o['points']):>16}{len(points):>16}")
        print(f"  {'кластеров':<28}{len(oc):>16}{len(real):>16}")
        print(f"  {'крупнейший, % корпуса':<28}"
              f"{max(oc.values()) / len(o['points']) * 100:>15.1f}%"
              f"{(max(real.values()) if real else 0) / len(points) * 100:>15.1f}%")
        print(f"  {'кластеров с общим топом':<28}"
              f"{sum(n for t, n in ob.items() if n > 1):>16}{broth:>16}")
        print(f"  {'координаты переживают день':<28}{'нет':>16}{'да':>16}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
