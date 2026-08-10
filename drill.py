#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""План бурения: где в науке густо, а у нас пусто.

Наряд архитектора, круг 3: «бурение — где дырки в смысловом пространстве; план бурения
вместо ручного выбора дат». Сейчас день выбирается рукой, и что попадёт в ленту, решает
календарь. Здесь вместо календаря — карта.

ПОЧЕМУ НЕ ИЩЕМ ДЫРКИ НАПРЯМУЮ. Соблазн такой: раз есть векторы, найдём пустые места
между точками. Так нельзя, и это замер, а не осторожность (topology.py, 2026-08-10):
внутренняя размерность нашего пространства — 34, а точек 2124. На одну ось приходится
1,26 точки. При такой плотности пусто ВОКРУГ КАЖДОЙ точки, и слово «дырка» перестаёт
что-либо значить: любой ответ будет артефактом, а не находкой.

ЧТО РАБОТАЕТ ВМЕСТО. Сравнение двух плотностей в одних и тех же областях. Режем
вспомогательный индекс arXiv на области, и в каждой считаем два числа: сколько там
работ у науки и сколько у нас. Область, где у науки густо, а у нас ноль — это и есть
слепая зона, причём «окружённая плотностью», как и просил владелец. Это одномерное
сравнение на каждую область, и на наших объёмах оно честно.

ЧЕГО ЭТОТ ИНСТРУМЕНТ НЕ ДЕЛАЕТ. Он не говорит «здесь предрассудок, а не невозможность».
Пустая область может быть пустой потому, что тема нам не подходит — и таких большинство.
Поэтому в плане есть фильтр профиля и колонка «почему пусто», а решение остаётся
за человеком. Дырка — это вопрос, а не ответ.

    python drill.py --regions 200          карта: где густо у науки и пусто у нас
    python drill.py --regions 200 --plan 20  план бурения: 20 областей с примерами
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

# Разделы под ограничением владельца: пустота в них — не слепая зона, а наше решение.
# Список тот же, что в vector_select.py: одно правило, два места применения.
RESTRICTED = ("cs.", "math.", "stat.", "econ.", "q-fin.", "q-bio.PE")


def load_ours():
    import numpy as np
    vecs, ids = [], []
    with (DATA / "embeddings-articles.jsonl").open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                if r.get("vec"):
                    vecs.append(r["vec"])
                    ids.append(r.get("id", ""))
    m = np.asarray(vecs, dtype=np.float32)
    m /= np.linalg.norm(m, axis=1, keepdims=True) + 1e-9
    return m, ids


def load_arxiv():
    """Вектора вспомогательного индекса + метаданные (раздел, заголовок) из jsonl."""
    import numpy as np
    import vecstore
    ids, m = vecstore.load(DATA / "arxiv")
    m = np.asarray(m, dtype=np.float32)
    m /= np.linalg.norm(m, axis=1, keepdims=True) + 1e-9
    meta = {}
    p = DATA / "embeddings-arxiv.jsonl"
    if p.exists():
        with p.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                meta[r["id"]] = {"cat": r.get("cat", ""), "published": r.get("published", "")}
    # Заголовки — из выгрузки arXiv в главной папке. Без них план читает только машина:
    # строка «arx:2607.23786» не позволяет человеку сказать «да, сюда бурим» или «нет».
    months = {v.get("published", "")[:7] for v in meta.values() if v.get("published")}
    want = {i.split(":", 1)[-1] for i in ids}
    for mo in sorted(m for m in months if m):
        f = MAIN / "data" / "arxiv-bulk" / f"{mo}.jsonl"
        if not f.exists():
            continue
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("id") in want:
                    meta.setdefault(f"arx:{r['id']}", {})["title"] = r.get("title", "")
    return m, ids, meta


def load_tags():
    """Векторы тегов — ими будем НАЗЫВАТЬ области. Область без имени бесполезна:
    «регион 137» обсуждать нельзя, «сверхпроводимость при высоком давлении» — можно."""
    import numpy as np
    p = DATA / "embeddings-tags.jsonl"
    if not p.exists():
        return None, []
    vecs, names = [], []
    with p.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                if r.get("vec"):
                    vecs.append(r["vec"])
                    names.append(str(r.get("id", "")).split(":", 1)[-1])
    m = np.asarray(vecs, dtype=np.float32)
    m /= np.linalg.norm(m, axis=1, keepdims=True) + 1e-9
    return m, names


def kmeans(X, k, iters=25, seed=42):
    """k-means на единичной сфере (косинус). Своя реализация в тридцать строк вместо
    sklearn: тут нужен ровно один вариант — косинусное расстояние и фиксированное зерно,
    чтобы карта не менялась от запуска к запуску и её можно было обсуждать."""
    import numpy as np
    rng = np.random.default_rng(seed)
    C = X[rng.choice(len(X), k, replace=False)].copy()
    lab = np.zeros(len(X), dtype=np.int32)
    for _ in range(iters):
        # По кускам: матрица 29000 × 200 помещается, 29000 × 29000 — нет.
        new = np.empty(len(X), dtype=np.int32)
        for s in range(0, len(X), 4096):
            new[s:s + 4096] = (X[s:s + 4096] @ C.T).argmax(1)
        if (new == lab).all():
            break
        lab = new
        for j in range(k):
            sel = X[lab == j]
            if len(sel):
                v = sel.mean(0)
                C[j] = v / (np.linalg.norm(v) + 1e-9)
    return C, lab


def name_region(center, T, tag_names, top=3):
    import numpy as np
    if T is None:
        return "—"
    s = T @ center
    return ", ".join(tag_names[j] for j in np.argsort(-s)[:top])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--regions", type=int, default=200)
    ap.add_argument("--plan", type=int, default=0, help="показать N самых пустых областей")
    ap.add_argument("--min-arxiv", type=int, default=20,
                    help="область меньше этого — не область, а шум выборки")
    args = ap.parse_args()
    import numpy as np

    A, aids, ameta = load_arxiv()
    O, _ = load_ours()
    T, tag_names = load_tags()
    print(f"arXiv: {len(A):,} работ · наших: {len(O):,} · областей: {args.regions}")

    C, lab = kmeans(A, args.regions)
    # Наши статьи не участвуют в НАРЕЗКЕ, только в подсчёте. Иначе карта подстроится
    # под нас и покажет, что мы покрываем всё: области возникнут вокруг наших тем.
    ours_lab = np.empty(len(O), dtype=np.int32)
    for s in range(0, len(O), 4096):
        ours_lab[s:s + 4096] = (O[s:s + 4096] @ C.T).argmax(1)

    n_arx = np.bincount(lab, minlength=args.regions)
    n_our = np.bincount(ours_lab, minlength=args.regions)
    # Доля, а не разность: область на 900 работ и область на 30 нельзя сравнивать штуками.
    share_arx = n_arx / max(n_arx.sum(), 1)
    share_our = n_our / max(n_our.sum(), 1)

    # Профиль области — по разделам работ, которые в ней лежат. Пустота в cs./math. —
    # это наше решение, а не слепая зона; в план бурения такие области не идут.
    cats = {}
    for i, aid in enumerate(aids):
        c = (ameta.get(aid) or {}).get("cat", "")
        cats.setdefault(int(lab[i]), []).append(c)
    restricted = np.zeros(args.regions, dtype=bool)
    for j, cs in cats.items():
        if cs:
            share = sum(1 for c in cs if c.startswith(RESTRICTED)) / len(cs)
            restricted[j] = share > 0.5

    big = n_arx >= args.min_arxiv
    print(f"областей крупнее {args.min_arxiv}: {int(big.sum())} · "
          f"из них под ограничением владельца: {int((big & restricted).sum())}")
    empty = big & (n_our == 0)
    print(f"\nПУСТЫХ У НАС ОБЛАСТЕЙ: {int(empty.sum())} "
          f"({int((empty & ~restricted).sum())} из них в нашем профиле)")
    covered = float(n_arx[big & (n_our > 0)].sum()) / max(float(n_arx[big].sum()), 1)
    print(f"Доля работ arXiv в областях, где у нас есть хоть одна статья: {covered*100:.1f}%")

    # Перекос — вторая половина картины. Слепая зона это не только «ноль», но и
    # «двадцать работ там, где у науки тысяча»: такую область мы формально покрыли,
    # и она никогда не попадётся на глаза как дырка.
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(share_our > 0, share_arx / np.maximum(share_our, 1e-9), np.inf)
    thin = big & ~restricted & (n_our > 0) & (ratio > 3)
    print(f"Тонких мест (есть, но втрое реже, чем у науки): {int(thin.sum())}")

    if args.plan:
        print(f"\n{'='*78}\nПЛАН БУРЕНИЯ — области, где у науки густо, а у нас пусто\n{'='*78}")
        cand = [j for j in range(args.regions) if empty[j] and not restricted[j]]
        cand.sort(key=lambda j: -n_arx[j])
        for j in cand[:args.plan]:
            near = np.argsort(-(A[lab == j] @ C[j]))[:3]
            idx = np.where(lab == j)[0][near]
            print(f"\n· {name_region(C[j], T, tag_names)}")
            print(f"  работ у науки: {n_arx[j]} ({share_arx[j]*100:.2f}% arXiv) · у нас: 0")
            print(f"  разделы: {', '.join(sorted(set(cats.get(j, [])))[:6])}")
            for i in idx:
                t = (ameta.get(aids[i]) or {}).get("title", "")
                print(f"     {' '.join(t.split())[:88] if t else aids[i]}")
        # ГЛАВНОЕ ПРЕВРАЩЕНИЕ: карта → действие. Дырка сама по себе — наблюдение;
        # действием она становится, когда названа причина. А причина у большинства
        # наших дырок одна и лежит ДО отбора: лента по умолчанию запрашивает у arXiv
        # только `astro-ph.*` (run.py, --category). Работы про кварк-глюонную плазму
        # или про квантовые материалы не проигрывают отбор — они до него не доходят.
        # Поэтому план бурения — это не «выбери другой день», а «добавь раздел».
        need = collections.Counter()
        for j in cand:
            for c in cats.get(j, []):
                if c and not c.startswith(RESTRICTED):
                    need[c.split(".")[0] if "." in c else c] += 1
        print(f"\n{'='*78}\nЧТО ДОБАВИТЬ В ЛЕНТУ (сейчас запрашивается только astro-ph.*)"
              f"\n{'='*78}")
        for c, n in need.most_common(10):
            mark = "  ← уже берём" if c.startswith("astro-ph") else ""
            print(f"  {c:<18} работ в пустых областях: {n}{mark}")

        print(f"\n{'='*78}\nТОНКИЕ МЕСТА — есть, но заметно реже, чем у науки\n{'='*78}")
        thin_idx = [j for j in range(args.regions) if thin[j]]
        thin_idx.sort(key=lambda j: -ratio[j])
        for j in thin_idx[:args.plan]:
            print(f"· {name_region(C[j], T, tag_names)}: "
                  f"у науки {n_arx[j]}, у нас {n_our[j]} — реже в {ratio[j]:.1f} раза")

    out = {"областей": args.regions, "пустых": int(empty.sum()),
           "пустых в профиле": int((empty & ~restricted).sum()),
           "тонких": int(thin.sum()), "покрытие": round(covered, 4)}
    (DATA / "drill-map.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    print(f"\nсводка записана в data/drill-map.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
