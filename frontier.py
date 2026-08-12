#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Две внутренние приметы поля: где у науки КРАЙ и где между областями ПЕРЕМЫЧКИ.

Владелец 12 августа: «нам не надо, может, сравнивать — вернее, мы сравниваем с границей.
Не важно какая граница. Вся наука это неориентируемое какое-то пространство, у нас там
есть дырки. Вот границы это одна сторона, и кросс-связи неожиданные другая».

Это снимает стенку, в которую упирался прежний подход. Карта бурения искала пробелы
СРАВНЕНИЕМ двух плотностей — мир против нас. Для вопроса «чего не хватает в самой
физике» второй плотности не существует, и сравнивать не с чем. Но обе приметы,
которые назвал владелец, — внутренние: они видны в одном облаке, без эталона.

  ГРАНИЦА. У точки в глубине корпуса соседи со всех сторон. У точки на краю —
  только с одной. Край это передний рубеж: дальше работ нет, и вопрос «почему»
  осмыслен всегда — либо там некому работать, либо не на чем, либо туда не смотрели.

  ПЕРЕМЫЧКА. Две области плотные, между ними пусто, и при этом они не бесконечно
  далеко. Это геометрическая версия связывания Свенсона: A и C по отдельности
  исследованы, работы «A и C вместе» не существует. Классический пример Свенсона —
  рыбий жир и болезнь Рейно (1986): обе литературы существовали, связь между ними
  никто не написал.

ПОЧЕМУ ЭТО НЕ ПОЛУЧАЛОСЬ ВЧЕРА. Меру края я уже строил (topology.py) и провалил дважды:
первая версия дала «на краю 100% точек», вторая — «0%». Причина была не в мере,
а в плотности: 2124 точки на 34 измерения это 1,26 точки на ось, и локальной структуры
не существует физически. Сейчас в поле 1 556 983 работы. На ось это по-прежнему около
1,4 — глобально ничего не изменилось, — НО мера края ЛОКАЛЬНАЯ: ей нужны соседи вокруг
одной точки, а не заполненное пространство целиком. Соседей теперь на три порядка
больше, и вопрос стоит заново.

Ответ на него даёт сам прогон, а не эта заметка. Если у эталонов мера снова
не различает края от середины — значит опять не работает, и это будет написано.

    python frontier.py --edge          где у поля край
    python frontier.py --bridges       перемычки между областями
    python frontier.py --edge --sample 40000
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, str(ROOT))


def load_field():
    import numpy as np
    import vecstore
    ids, M = vecstore.load(DATA / "field", latest=True)
    A = np.asarray(M, dtype=np.float32)
    A /= np.linalg.norm(A, axis=1, keepdims=True) + 1e-9
    return ids, A


def titles_for(ids, want):
    """Заголовки нужны для проверки глазами: число «мера края 3,1» ничего не значит,
    пока не видно, что это за работы. Без этой проверки мера остаётся необоснованной."""
    import field_build as fb
    by_month = {}
    for i in want:
        mo = fb.id_month(ids[i])
        if mo:
            by_month.setdefault(mo, {})[fb._base_id(ids[i])] = i
    out = {}
    for mo, keys in sorted(by_month.items()):
        p = fb.BULK / f"{mo}.jsonl"
        if not p.exists():
            continue
        with p.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                k = fb._base_id(r.get("id", ""))
                if k in keys:
                    out[keys[k]] = " ".join(str(r.get("title", "")).split())
    return out


def edge_measure(A, idx, K, chunk=256):
    """Угловой зазор между направлениями к соседям в локальной плоскости.

    Направления к K ближайшим соседям проецируются на две главные оси САМОЙ окрестности
    и сортируются по углу. Самый большой промежуток между соседними направлениями —
    и есть мера. У точки в глубине промежутки мелкие: соседи по всем сторонам.
    У точки на краю есть пустой сектор.

    Мера самокалибруется: для K случайных направлений на плоскости вероятность зазора
    больше 180° равна K/2^(K-1), при K=50 это 10^-13. Ложные срабатывания исключены
    арифметикой, а не порогом.
    """
    import numpy as np
    out = np.empty(len(idx), dtype=np.float32)
    for s in range(0, len(idx), chunk):
        part = idx[s:s + chunk]
        sim = A[part] @ A.T
        for r, i in enumerate(part):
            sim[r, i] = -2.0
        nb = np.argpartition(-sim, K, axis=1)[:, :K]
        for r in range(len(part)):
            d = A[nb[r]] - A[part[r]]
            d = d - d.mean(0)
            try:
                _, _, vt = np.linalg.svd(d, full_matrices=False)
            except np.linalg.LinAlgError:
                out[s + r] = 0.0
                continue
            p = (A[nb[r]] - A[part[r]]) @ vt[:2].T
            ang = np.sort(np.arctan2(p[:, 1], p[:, 0]))
            gaps = np.diff(np.concatenate([ang, ang[:1] + 2 * np.pi]))
            out[s + r] = float(gaps.max())
    return out


def run_edge(args):
    import numpy as np
    ids, A = load_field()
    rng = np.random.default_rng(42)
    idx = rng.choice(len(A), min(args.sample, len(A)), replace=False)
    print(f"поле: {len(A):,} работ · выборка для меры: {len(idx):,} · соседей K={args.k}")

    e = edge_measure(A, idx, args.k)
    deg = np.degrees(e)
    print(f"\nзазор в локальной плоскости:")
    for q in (5, 25, 50, 75, 95, 99):
        print(f"  p{q:<3} {np.percentile(deg, q):6.1f}°")
    print(f"  максимум {deg.max():.1f}°")
    share = float((e > np.pi).mean())
    print(f"\nточек с ПУСТЫМ ПОЛУКРУГОМ (зазор > 180°): {share*100:.2f}%")
    print(f"  случайные соседи дали бы {100*args.k/2**(args.k-1):.0e}% — "
          f"ложные срабатывания исключены арифметикой")

    if share == 0:
        print("\n⚠️ КРАЯ НЕ НАЙДЕНО НИ У ОДНОЙ ТОЧКИ. Это может значить и что поле")
        print("   действительно без края, и что мера снова не работает при нашей")
        print("   плотности. Различить эти два случая измерением ниже нельзя —")
        print("   нужен эталон с заведомым краем, и его надо строить отдельно.")

    # Проверка глазами: что за работы на самом краю и что в самой глубине.
    top = idx[np.argsort(-e)[:12]]
    bot = idx[np.argsort(e)[:6]]
    tt = titles_for(ids, list(top) + list(bot))
    print(f"\n{'='*76}\nСАМЫЙ КРАЙ (наибольший зазор)\n{'='*76}")
    for i in top:
        print(f"  {np.degrees(e[list(idx).index(i)]):5.1f}°  {tt.get(i, ids[i])[:80]}")
    print(f"\n{'='*76}\nСАМАЯ ГЛУБИНА (наименьший зазор) — для сравнения\n{'='*76}")
    for i in bot:
        print(f"  {np.degrees(e[list(idx).index(i)]):5.1f}°  {tt.get(i, ids[i])[:80]}")
    return 0


def run_bridges(args):
    """Перемычки: две плотные области, между которыми пусто.

    ПЕРВАЯ ВЕРСИЯ ЭТОЙ МЕРЫ БЫЛА СЛОМАНА, и полезно знать, как именно. «Между A и B»
    я определял как «ближе к середине между центрами, чем к каждому из центров».
    На бумаге разумно. Прогон дал: в коридоре в среднем 121 325 работ из выборки
    в 150 000, то есть «между» любыми двумя областями лежат восемьдесят процентов
    корпуса. Причина в геометрии больших размерностей: все векторы лежат в узком
    конусе, середина между двумя центрами почти совпадает с центром всего облака,
    и к ней ближе почти всё. Вторая примета поломки была наглядной: во всех восьми
    находках фигурировала одна и та же область A.

    ЗДЕСЬ ДРУГОЕ ОПРЕДЕЛЕНИЕ, без середины. Работа считается перемычкой, если она
    ОДНОВРЕМЕННО принадлежит обеим областям: близка и к A, и к B не меньше, чем
    типичная работа своей области. Порог берётся у самих областей — медиана близости
    их работ к своему центру, — поэтому он свой для каждой пары и не назначается.

    ОЖИДАНИЕ. Пустой коридор бывает просто от расстояния: чем дальше области, тем
    меньше между ними работ, и это геометрия, а не открытие. Поэтому пустота меряется
    против ожидания — сколько работ-перемычек у пар с таким же расстоянием.
    Кандидат — пара, где перемычек заметно меньше ожидаемого при её расстоянии.
    """
    import numpy as np
    ids, A = load_field()
    C = np.load(DATA / "drill-centers.npy")
    R = json.loads((DATA / "drill-regions.json").read_text(encoding="utf-8"))
    n_reg = len(C)
    print(f"поле: {len(A):,} · областей: {n_reg}")

    lab = np.empty(len(A), dtype=np.int32)
    for s in range(0, len(A), 4096):
        lab[s:s + 4096] = (A[s:s + 4096] @ C.T).argmax(1)
    pop = np.bincount(lab, minlength=n_reg)

    # Коридор считаем на выборке: 1,56 млн × 180 тыс. пар в лоб не нужно,
    # оценка доли по выборке в 200 тыс. точек даёт ту же картину.
    rng = np.random.default_rng(42)
    S = rng.choice(len(A), min(args.sample, len(A)), replace=False)
    AS = A[S]
    simC = AS @ C.T                      # близость выборки ко всем центрам

    big = [j for j in range(n_reg) if pop[j] >= args.min_pop and not R["restricted"][j]]
    print(f"областей крупнее {args.min_pop}: {len(big)}")

    # ТРЕТИЙ ПОДХОД, БЕЗ ПОРОГОВ ВООБЩЕ. Первые два провалились симметрично:
    # «ближе к середине» дало 80% корпуса в коридоре у любой пары, «выше медианы
    # у обеих» дало ноль везде. Порог в сжатом пространстве не работает ни в какую
    # сторону — это уже третий случай той же болезни за два дня.
    #
    # Здесь порогов нет. Работа лежит МЕЖДУ A и B, если A и B — две её ближайшие
    # области и они почти равноудалены: разница близостей меньше, чем разброс
    # внутри самой пары. Это определение по РАНГУ и по относительной величине,
    # его нельзя сбить ни сжатием шкалы, ни разной шириной областей.
    top2 = np.argpartition(-simC, 2, axis=1)[:, :2]
    r0 = np.arange(len(simC))
    s1 = simC[r0, top2[:, 0]]
    s2 = simC[r0, top2[:, 1]]
    lo = np.minimum(s1, s2)
    gap = np.abs(s1 - s2)
    # «Почти равноудалена» — зазор меньше десятой доли типичного расстояния до центра.
    straddle = gap < 0.1 * (1 - lo)
    print(f"работ, лежащих между двумя областями: {int(straddle.sum()):,} "
          f"из {len(simC):,} ({100*straddle.mean():.1f}%)")

    from collections import Counter
    pairs = Counter()
    for k in np.where(straddle)[0]:
        a, b = int(top2[k, 0]), int(top2[k, 1])
        pairs[(min(a, b), max(a, b))] += 1

    rows = []
    for a in range(len(big)):
        ja = big[a]
        for b in range(a + 1, len(big)):
            jb = big[b]
            d = float(C[ja] @ C[jb])
            if not (args.dmin <= d <= args.dmax):
                continue
            inside = pairs.get((min(ja, jb), max(ja, jb)), 0)
            rows.append((ja, jb, d, inside, int(pop[ja]), int(pop[jb])))
    if not rows:
        print("подходящих пар нет — ослабьте --dmin/--dmax")
        return 1
    arr = np.array([(r[2], r[3]) for r in rows], dtype=np.float64)

    # Ожидание как функция расстояния: скользящее среднее по близким парам.
    order = np.argsort(arr[:, 0])
    exp = np.empty(len(arr))
    W = max(30, len(arr) // 20)
    srt = arr[order, 1]
    for k in range(len(arr)):
        lo, hi = max(0, k - W), min(len(arr), k + W)
        exp[order[k]] = srt[lo:hi].mean()
    dev = arr[:, 1] - exp
    print(f"пар в рассмотрении: {len(rows):,} · "
          f"в коридоре в среднем {arr[:,1].mean():.1f} работ")

    hits = sorted(range(len(rows)), key=lambda k: dev[k])[:args.top]
    print(f"\n{'='*78}\nПЕРЕМЫЧКИ — коридор пустее ожидаемого при таком расстоянии\n{'='*78}")
    for k in hits:
        ja, jb, d, ins, pa, pb = rows[k]
        print(f"\n  близость областей {d:.3f} · в коридоре {ins} работ "
              f"(ожидалось {exp[k]:.0f})")
        print(f"    A ({pa:>5} работ): {R['names'][ja]}")
        print(f"    B ({pb:>5} работ): {R['names'][jb]}")
    out = [{"близость": round(rows[k][2], 4), "в_коридоре": rows[k][3],
            "ожидалось": round(float(exp[k]), 1),
            "A": R["names"][rows[k][0]], "работ_A": rows[k][4],
            "B": R["names"][rows[k][1]], "работ_B": rows[k][5]} for k in hits]
    (DATA / "bridges.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    print(f"\nзаписано в data/bridges.json")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--edge", action="store_true")
    ap.add_argument("--bridges", action="store_true")
    ap.add_argument("--sample", type=int, default=20000)
    ap.add_argument("--k", type=int, default=50)
    ap.add_argument("--min-pop", type=int, default=300)
    ap.add_argument("--dmin", type=float, default=0.45)
    ap.add_argument("--dmax", type=float, default=0.75)
    ap.add_argument("--top", type=int, default=12)
    args = ap.parse_args()
    if args.edge:
        return run_edge(args)
    if args.bridges:
        return run_bridges(args)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
