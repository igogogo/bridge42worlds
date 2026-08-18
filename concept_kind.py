#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Вид понятия по его следу в статьях. Дополнение к волне 18 августа.

Волна: «дыры кластеров теперь предлагают понятия С ВИДОМ (метод/эффект/уравнение —
по контексту статей)».

Вид можно было бы угадывать по словам в названии: есть «equation» — значит уравнение,
есть «telescope» — прибор. Такое правило работает ровно до первого «уравнения состояния»
и «эффекта Доплера», а главное — его нечем проверить.

Здесь вид предсказывается по СЛЕДУ В КОРПУСЕ: понятие представлено центроидом векторов
статей, которые его несут, и по этому центроиду обучается разделитель. Разметка уже
есть и ничего не стоит — 491 понятие реестра с известным видом и известным пулом работ.

ОСТАТОЧНАЯ КОРЗИНА В ОБУЧЕНИЕ НЕ ИДЁТ, и это результат замера, а не удобство.
Первая версия учила все тринадцать видов сразу и дала 36.4% при контроле «всегда
concept» 37.8% — то есть проиграла контролю. Матрица ошибок объяснила почему:
`concept` угадывался в 5% случаев и рассыпался по всем остальным видам. Он и не мог
угадываться: `concept` означает «не отнесли ни к чему конкретному», у такой категории
нет своего следа по построению — её нельзя предсказать, потому что она определена
отрицанием.

Убрали её из обучения — и на десяти конкретных видах точность 52.2% против контроля
22.1%. Сигнал есть, просто его спрашивали неправильно.

ГЛАВНАЯ МЕРКА ЗДЕСЬ — НЕ ОБЩАЯ ТОЧНОСТЬ, А СРЕДНЯЯ ПОЛНОТА ПО ВИДАМ. Разделитель,
отвечающий «метод» на всё, даёт приличную общую точность (методов и объектов в реестре
больше всего) и при этом бесполезен: человеку он не подскажет ничего. Без балансировки
классов так и выходило — семь видов из десяти не назывались ни разу, средняя полнота
28.5%. С балансировкой 48.1% и названы все десять.

ЧТО ЭТО ДАЁТ И ЧЕГО НЕ ДАЁТ. Проверка перекрёстная, по пяти частям, рядом всегда
печатается контроль «всегда самый частый вид». 47% попадания с первого раза — это
подсказка человеку, а не разметка. Отличать конкретный вид от остаточного по
уверенности получается плохо (AUC 0.680), поэтому автоматически подставлять
`concept` при низкой уверенности нельзя — решает человек.

    python concept_kind.py                обучить, проверить, сохранить
    python concept_kind.py --explain      что путается с чем
"""
import argparse
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
MAIN = pathlib.Path(r"C:\Users\nadez\PycharmProjects\bridge42worlds")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))

MIN_ARTICLES = 5      # меньше — центроид шумный, учить на нём нечему
MIN_PER_KIND = 8      # вид с меньшим числом примеров в обучение не берём
RESIDUAL = "concept"  # остаточная корзина: «не отнесли ни к чему конкретному»


def registry():
    return json.load(open(MAIN / "data/concepts.json", encoding="utf-8"))


def concept_pools(lang="ru"):
    """Понятие → множество работ, которые его несут. Единый реестр: теги и законы
    больше не разделены, поэтому и пул собирается из обоих полей индекса."""
    import field_build as fb
    reg = registry()["concepts"]
    idx = json.load(open(MAIN / f"lang/{lang}/articles-index.json", encoding="utf-8"))
    pool = collections.defaultdict(set)
    for a in idx:
        aid = fb._base_id(str(a.get("id") or ""))
        if not aid:
            continue
        for e in (a.get("tags") or []) + (a.get("laws") or []):
            if e in reg:
                pool[e].add(aid)
    return reg, pool


def centroids(pool, keys=None):
    """Центроид понятия — среднее векторов его работ. Поле читается memmap-ом
    и построчно: тянуть три гигабайта ради пятисот центроидов незачем."""
    import numpy as np
    import vecstore
    import field_build as fb
    from analytics_v2 import _field_dir
    ids, M = vecstore.load(_field_dir() / "field", mmap=True)
    rowof = {}
    for i, s in enumerate(ids):
        rowof[fb._base_id(s)] = i
    names, vecs = [], []
    for k in (keys if keys is not None else sorted(pool)):
        rows = [rowof[a] for a in pool.get(k, ()) if a in rowof]
        if not rows:
            continue
        v = np.zeros(M.shape[1], dtype=np.float32)
        for r in rows:
            v += M[r]
        n = np.linalg.norm(v)
        if n > 0:
            names.append(k)
            vecs.append(v / n)
    return names, (np.vstack(vecs) if vecs else np.zeros((0, 1024), dtype=np.float32))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--explain", action="store_true", help="что с чем путается")
    ap.add_argument("--out", default=str(DATA / "concept-kind.npz"))
    args = ap.parse_args()

    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_predict

    reg, pool = concept_pools()
    good = [k for k in reg if len(pool.get(k, ())) >= MIN_ARTICLES]
    kinds = collections.Counter(reg[k]["kind"] for k in good)
    # RESIDUAL исключается из обучения: см. шапку модуля — категория определена
    # отрицанием, своего следа не имеет и тянет всё разбиение вниз.
    keep = {k for k, n in kinds.items() if n >= MIN_PER_KIND and k != RESIDUAL}
    good = [k for k in good if reg[k]["kind"] in keep]
    print(f"понятий с опорой ≥{MIN_ARTICLES} работ: {len(good)} · "
          f"видов в обучении: {len(keep)}")
    print(f"  не хватило примеров: "
          f"{', '.join(sorted(k for k in kinds if k not in keep)) or 'нет'}")

    names, X = centroids(pool, good)
    y = np.array([reg[k]["kind"] for k in names])
    print(f"центроидов собрано: {len(names)}")

    # class_weight="balanced" — и это тоже замер, а не вкус. Без балансировки
    # разделитель называет всего семь видов из десяти и отвечает «метод» или
    # «объект» почти на всё: общая точность 47.4%, средняя полнота по видам 28.5%.
    # С балансировкой — 52.2% и 48.1%, названы все десять. Для подсказки человеку
    # важна именно полнота по видам: разделитель, отвечающий «метод» на всё,
    # бесполезен, какой бы ни была его общая точность.
    clf = LogisticRegression(max_iter=4000, C=4.0, class_weight="balanced")
    cv = StratifiedKFold(5, shuffle=True, random_state=17)
    pred = cross_val_predict(clf, X, y, cv=cv)
    proba = cross_val_predict(clf, X, y, cv=cv, method="predict_proba")

    acc = float((pred == y).mean())
    # Попадание в первые два: настоящий режим применения — человеку показывают
    # пару кандидатов, а не один. Число честнее описывает пользу, чем top-1.
    order = np.argsort(-proba, axis=1)
    cls = np.array(sorted(set(y.tolist())))
    top2 = float(np.mean([y[i] in cls[order[i, :2]] for i in range(len(y))]))
    # Контроль: «всегда самый частый вид». Без него любая точность выглядит успехом.
    base = collections.Counter(y.tolist()).most_common(1)[0]
    print(f"\n{'=' * 74}\nПЕРЕКРЁСТНАЯ ПРОВЕРКА\n{'=' * 74}")
    print(f"  точность разделителя      {acc * 100:.1f}%")
    print(f"  контроль «всегда {base[0]}»  {base[1] / len(y) * 100:.1f}%")
    print(f"  выигрыш над контролем     {(acc - base[1] / len(y)) * 100:+.1f} п.п.")
    print(f"  попадание в первые два    {top2 * 100:.1f}%  ← режим «покажи человеку пару»")
    rec = [float((pred[y == k] == k).mean()) for k in sorted(set(y.tolist()))]
    print(f"  СРЕДНЯЯ ПОЛНОТА ПО ВИДАМ  {np.mean(rec) * 100:.1f}%  ← главная мерка здесь")

    print(f"\n  {'вид':<12}{'примеров':>10}{'угадано':>9}{'точность':>10}")
    for kind in sorted(keep):
        m = y == kind
        hit = int((pred[m] == kind).sum())
        prec_d = int((pred == kind).sum())
        print(f"  {kind:<12}{int(m.sum()):>10}{hit:>9}"
              f"{hit / max(1, int(m.sum())) * 100:>9.0f}%"
              + (f"   (назначено {prec_d})" if prec_d else ""))

    if args.explain:
        print(f"\n{'=' * 74}\nЧТО С ЧЕМ ПУТАЕТСЯ\n{'=' * 74}")
        conf = collections.Counter(zip(y.tolist(), pred.tolist()))
        for (a, b), n in conf.most_common(12):
            if a != b:
                print(f"  {a:<12} → {b:<12} {n}")

    clf.fit(X, y)
    np.savez(args.out, coef=clf.coef_, intercept=clf.intercept_,
             classes=clf.classes_, accuracy=acc, top2=top2,
             baseline=base[1] / len(y))
    print(f"\n→ {args.out}")
    print("  Применение: predict_kind(вектор) в этом же модуле. Предсказание —")
    print("  подсказка человеку, а не разметка: на редких видах примеров мало.")
    return 0


def predict_kind(vecs, path=None, top=2):
    """Виды по вектору: список из `top` пар (вид, уверенность), лучший первым.

    Двумя, а не одним: замер даёт 47% попадания с первого раза и заметно больше
    с двух. Показывать человеку пару кандидатов честнее, чем один с видом
    уверенного ответа.
    """
    import numpy as np
    d = np.load(path or (DATA / "concept-kind.npz"), allow_pickle=True)
    V = np.atleast_2d(np.asarray(vecs, dtype=np.float32))
    V = V / (np.linalg.norm(V, axis=1, keepdims=True) + 1e-9)
    z = V @ d["coef"].T + d["intercept"]
    e = np.exp(z - z.max(axis=1, keepdims=True))
    p = e / e.sum(axis=1, keepdims=True)
    out = []
    for i in range(len(V)):
        order = np.argsort(-p[i])[:top]
        out.append([(str(d["classes"][k]), float(p[i, k])) for k in order])
    return out


if __name__ == "__main__":
    sys.exit(main())
