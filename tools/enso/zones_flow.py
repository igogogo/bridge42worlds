# -*- coding: utf-8 -*-
"""Переток между зонами Niño: кто теплеет первым, кто следом и можно ли из этого прогноз.

Владелец 15.09: «хочу увидеть статистику по нашим выделенным годам: переток тепла между зонами,
как там из 3.4 в 3, потом 1+2, у нас есть исторически, а сейчас, допустим, 3 прямо горячая, потом
она перейдёт — это же тоже прогноз можно построить».

ЧТО ЗДЕСЬ ЧЕСТНО НАЗЫВАТЬ ПЕРЕТОКОМ. Четыре зоны Niño — это четыре куска одной и той же полосы
экватора, и мы меряем у них температуру ПОВЕРХНОСТИ, а не поток энергии. Сказать «тепло перешло
из 3.4 в 3» по этим числам нельзя: можно сказать только, что в одной зоне потеплело раньше, чем
в другой, и что форма события сместилась к востоку или к центру. Настоящий перенос идёт под
поверхностью, волной Кельвина по термоклину, и он у нас тоже измерен — глубиной изотермы 20 °C
вдоль экватора (Ховмёллер). Поэтому здесь два слоя: поверхность (кто раньше) и глубина (что
куда едет на самом деле, в градусах долготы за месяц).

ПОРЯДОК ЗОН — С ЗАПАДА НА ВОСТОК: Niño 4 (160° в.д. — 150° з.д.), Niño 3.4 (170–120° з.д.),
Niño 3 (150–90° з.д.), Niño 1+2 (90–80° з.д.). Именно в этом порядке они стоят на экваторе и
именно в нём должны стоять на всех представлениях панели. Обратите внимание: 3.4 и 3
ПЕРЕКРЫВАЮТСЯ по долготе (150–120° з.д. входит в обе), поэтому часть их сходства — это просто
одна и та же вода, посчитанная дважды. На экране это сказано вслух.

ТРИ ВЕЩИ, БЕЗ КОТОРЫХ ЭТА СТАТИСТИКА ВРЁТ:
  · НЕДЕЛИ НЕ НЕЗАВИСИМЫ. Соседние недели почти повторяют друг друга: у ряда из 2350 недель
    независимых точек десятки, а не тысячи. Поэтому у каждой корреляции считается эффективный
    размер выборки, и он пишется рядом с коэффициентом.
  · СОБЫТИЙ МАЛО. Их тринадцать за сорок пять лет, и «наших особенных» из них четыре. Медиана
    по четырём случаям — это не закон природы; квартили печатаются всегда.
  · СОСЕДНЯЯ ЗОНА МОЖЕТ НЕ ДАВАТЬ НИЧЕГО. Прежде чем строить прогноз «из зоны в зону», он
    проверяется против собственного прошлого зоны блочной проверкой по годам. Если сосед не
    добавляет точности — так и пишется, и никакой уверенной линии не рисуется.

    python tools/enso/zones_flow.py            посчитать и записать zones-flow.json
    python tools/enso/zones_flow.py --show     напечатать главное в консоль
"""
import argparse
import json
import re
import sys
import time
from datetime import date, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"
# Своя запись файлов: повтор при осечке файловой системы и подмена целиком (17.09).
import sys as _sys
import pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import safeio   # noqa: E402
SRC = ROOT / "last_good" / "noaa_weekly.txt"
HOV = ROOT / "hovmoller.json"
OUT = ROOT / "zones-flow.json"

# С ЗАПАДА НА ВОСТОК. Порядок здесь — источник истины для всей панели.
ZONES = [
    {"id": "n4", "key": "n4a", "box": "nino4", "name": "Niño 4", "lon": "160°E–150°W", "lon_mid": 185.0,
     "what": "the western patch, over the warm pool"},
    {"id": "n34", "key": "n34a", "box": "nino34", "name": "Niño 3.4", "lon": "170°W–120°W", "lon_mid": 215.0,
     "what": "the patch El Niño is judged by"},
    {"id": "n3", "key": "n3a", "box": "nino3", "name": "Niño 3", "lon": "150°W–90°W", "lon_mid": 240.0,
     "what": "the eastern patch; it overlaps 3.4"},
    {"id": "n12", "key": "n12a", "box": "nino12", "name": "Niño 1+2", "lon": "90°W–80°W", "lon_mid": 275.0,
     "what": "the coastal strip off Peru and Ecuador"},
]
IDS = [z["id"] for z in ZONES]
SPECIAL = (1982, 1997, 2015, 2023)      # «наши особенные годы» — те же, что у аналогов панели
MON = dict(JAN=1, FEB=2, MAR=3, APR=4, MAY=5, JUN=6, JUL=7, AUG=8, SEP=9, OCT=10, NOV=11, DEC=12)
ROW = re.compile(r"^\s*(\d{2})([A-Z]{3})(\d{4})\s+(.*)$")
EVENT_PEAK = 1.0                        # событие: недельный 3.4 дошёл хотя бы до +1.0 °C
EVENT_EDGE = 0.5                        # края события — там, где ряд опустился ниже +0.5
CROSS = 1.0                             # «зона потеплела» — первый переход через +1.0 °C

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


# ── ЧТЕНИЕ ──────────────────────────────────────────────────────────────────────────────────
def read_weekly(path=SRC):
    """Недельный файл NOAA: пары SST/SSTA по четырём зонам, с сентября 1981.

    Колонки в нём местами слипаются («20.6-0.1»), поэтому числа вынимаются разбором, а не
    по позициям: позиции в этом файле не гарантированы и однажды уже разъезжались.
    """
    dates, vals = [], {z: [] for z in IDS}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = ROW.match(line)
        if not m:
            continue
        nums = re.findall(r"-?\d+\.\d", m.group(4))
        if len(nums) < 8:
            continue
        v = [float(x) for x in nums[:8]]
        dates.append(date(int(m.group(3)), MON[m.group(2)], int(m.group(1))))
        # порядок колонок в файле: 1+2, 3, 3.4, 4 — с востока на запад
        vals["n12"].append(v[1]); vals["n3"].append(v[3]); vals["n34"].append(v[5]); vals["n4"].append(v[7])
    order = np.argsort(dates)
    dates = [dates[i] for i in order]
    A = {z: np.array([vals[z][i] for i in order], dtype=float) for z in IDS}
    return dates, A


# ── СОБЫТИЯ ─────────────────────────────────────────────────────────────────────────────────
def find_events(D, A):
    """Пики недельного Niño 3.4 выше EVENT_PEAK, слитые, если стоят ближе сорока недель."""
    n34, N = A["n34"], len(D)
    peaks, i = [], 0
    while i < N:
        if n34[i] >= EVENT_PEAK:
            j = i
            while j < N and n34[j] >= EVENT_EDGE:
                j += 1
            k = i + int(np.argmax(n34[i:j]))
            peaks.append(k)
            i = j
        else:
            i += 1
    merged = []
    for k in peaks:
        if merged and k - merged[-1] < 40:
            if n34[k] > n34[merged[-1]]:
                merged[-1] = k
        else:
            merged.append(k)
    return merged


def event_row(D, A, k, N):
    """Одно событие: где пик каждой зоны и когда каждая перешла порог, относительно пика 3.4.

    Окно ±52 недели вокруг пика 3.4. Если окно упирается в конец ряда, событие считается
    НЕЗАКОНЧЕННЫМ: его пик ещё впереди, и ставить его в статистику запаздываний нельзя —
    «максимум из того, что успели измерить» это не пик.
    """
    lo, hi = max(0, k - 52), min(N, k + 53)
    running = hi >= N                      # правый край окна упёрся в сегодня
    out = {"peak_date": D[k].isoformat(), "peak_n34": round(float(A["n34"][k]), 2),
           "year": D[k].year, "special": D[k].year in SPECIAL, "running": bool(running), "zones": {}}
    for z in IDS:
        seg = A[z][lo:hi]
        kk = lo + int(np.argmax(seg))
        # первый переход через порог внутри окна, до пика 3.4
        cross = None
        for t in range(lo, k + 1):
            if A[z][t] >= CROSS:
                cross = t
                break
        out["zones"][z] = {
            "peak": round(float(A[z][kk]), 2),
            "peak_date": D[kk].isoformat(),
            "peak_lag": int(kk - k),                      # + значит позже 3.4
            "cross_date": D[cross].isoformat() if cross is not None else None,
            "cross_lag": int(cross - k) if cross is not None else None,
            "at_peak34": round(float(A[z][k]), 2),
        }
    # ОДНА ФОРМУЛА НА ВСЮ ПАНЕЛЬ: восток минус запад = Niño 1+2 минус Niño 4, ровно так же,
    # как её считает watch.py для типа события. Прежде здесь была своя (полусумма пар), в
    # «сейчас» — третья (1+2 минус 3.4), и все три назывались одинаково.
    out["east_minus_west"] = round(out["zones"]["n12"]["at_peak34"] - out["zones"]["n4"]["at_peak34"], 2)
    g = out["east_minus_west"]
    out["shape"] = "east-heavy" if g > 1.0 else ("west-heavy" if g < -0.3 else "mixed")
    return out


# ── СВЯЗЬ МЕЖДУ ЗОНАМИ ──────────────────────────────────────────────────────────────────────
def eff_n(x, y):
    """Сколько в этой паре независимых точек на самом деле (Bartlett через связь соседних недель).

    Недельный ряд почти повторяет сам себя: r1 около 0.97. Без этой поправки корреляция 0.9
    по 2350 неделям выглядит железной, хотя стоит на десятках независимых случаев.
    """
    def r1(v):
        v = v - v.mean()
        d = float(np.dot(v, v))
        return float(np.dot(v[:-1], v[1:]) / d) if d else 0.0
    a, b = r1(x), r1(y)
    f = (1 - a * b) / (1 + a * b) if (1 + a * b) else 0.0
    return max(3.0, len(x) * max(f, 0.0))


def timing_counts(done):
    """Сколько событий из скольких каждая зона взяла пик рядом с 3.4, и каков полный разброс.

    Нужно, чтобы на экране стояло посчитанное, а не впечатление: «три зоны берут пик вместе»
    выглядело правдой по медиане и разваливалось по счёту (у Niño 4 разброс от −26 до +45 недель).
    """
    out = {}
    for z in IDS:
        v = [e["zones"][z]["peak_lag"] for e in done]
        if not v:
            continue
        near = sum(1 for x in v if abs(x) <= 2)
        early = sum(1 for x in v if x < -2)
        out[z] = {"within2": near, "early": early, "late": len(v) - near - early, "of": len(v),
                  "min": int(min(v)), "max": int(max(v))}
    return out


def chain_test(done):
    """Идёт ли тепло цепочкой с запада на восток — как цепочка, а не как шесть отдельных пар.

    Владелец спросил ровно это: «как там из 3.4 в 3, потом 1+2». Проверка прямая: выстраиваем
    четыре зоны по неделе их пика и смотрим, совпал ли порядок с географическим (4 → 3.4 → 3 →
    1+2), с обратным, или ни с тем ни с другим. Ничьи (пики в одну неделю) не ломают порядок:
    зоны перекрываются, и требовать от них строгого неравенства значило бы требовать
    невозможного. Считаем события, а не впечатления.
    """
    west_east, east_west, mixed, rows = 0, 0, 0, []
    for e in done:
        lag = {z: e["zones"][z]["peak_lag"] for z in IDS}
        seq = sorted(IDS, key=lambda z: (lag[z], IDS.index(z)))
        ok_we = all(lag[IDS[i]] <= lag[IDS[i + 1]] for i in range(3))
        ok_ew = all(lag[IDS[i]] >= lag[IDS[i + 1]] for i in range(3))
        kind = "west to east" if (ok_we and not ok_ew) else ("east to west" if (ok_ew and not ok_we) else
               ("all at once" if (ok_we and ok_ew) else "neither"))
        if kind == "west to east":
            west_east += 1
        elif kind == "east to west":
            east_west += 1
        elif kind == "neither":
            mixed += 1
        rows.append({"year": e["year"], "special": e["special"], "order": seq, "kind": kind,
                     "lags": {z: lag[z] for z in IDS}})
    return {"west_to_east": west_east, "east_to_west": east_west, "neither": mixed,
            "all_at_once": len(rows) - west_east - east_west - mixed, "of": len(rows), "events": rows,
            "note": ("The order asked about — the centre first, then the east — is tested here as one sequence, "
                     "not as six separate pairs: the four patches are sorted by the week each reached its own "
                     "highest, and that order is compared with the geography.")}


def lag_pairs(A, maxlag=26):
    """Для каждой пары зон: сдвиг, при котором связь сильнее всего, и связь без сдвига."""
    out = []
    for i in range(len(IDS) - 1):
        for j in range(i + 1, len(IDS)):
            a, b = A[IDS[i]], A[IDS[j]]
            best, rbest = 0, -2.0
            for lag in range(-maxlag, maxlag + 1):
                x, y = (a[:len(a) - lag], b[lag:]) if lag >= 0 else (a[-lag:], b[:len(b) + lag])
                r = float(np.corrcoef(x, y)[0, 1])
                if r > rbest:
                    best, rbest = lag, r
            r0 = float(np.corrcoef(a, b)[0, 1])
            out.append({"a": IDS[i], "b": IDS[j], "best_lag": int(best), "r_best": round(rbest, 3),
                        "r0": round(r0, 3), "n_eff": int(round(eff_n(a, b))),
                        "leader": (IDS[i] if best > 0 else IDS[j]) if best else None})
    return out


def event_blocks(D, A, ev_idx, half=26):
    """Границы каждого события плюс буфер: обучение не должно касаться проверяемого события.

    Делить недели случайно нельзя совсем: соседняя неделя почти повторяет проверяемую, и модель
    учится на ней же. Делить по календарным годам мало: 1997 и 1998 — одно событие. Поэтому
    блок — само событие (непрерывный кусок выше +0.5 вокруг пика) плюс по полгода с каждой стороны.
    """
    n34, N = A["n34"], len(D)
    out = []
    for k in ev_idx:
        i = k
        while i > 0 and n34[i - 1] >= EVENT_EDGE:
            i -= 1
        j = k
        while j < N - 1 and n34[j + 1] >= EVENT_EDGE:
            j += 1
        out.append((max(0, i - half), min(N - 1, j + half), D[k].year))
    return out


def skill_table(D, A, horizons=(4, 8, 13, 26)):
    """Даёт ли соседняя зона хоть что-то сверх собственного прошлого зоны.

    Проверка БЛОЧНАЯ ПО ГОДАМ, а не по случайным неделям: соседние недели почти одинаковы, и
    случайное деление положило бы в обучение почти ту же неделю, что и в проверку. Сравниваются
    четыре прогноза: собственная регрессия зоны, она же плюс соседняя зона, стойкость (значение
    не меняется) и «нормально» (аномалия ноль).
    """
    blocks = event_blocks(D, A, find_events(D, A))
    rows = []
    for target, src in (("n4", "n34"), ("n34", "n4"), ("n34", "n12"), ("n3", "n34"),
                        ("n3", "n12"), ("n12", "n3"), ("n12", "n34")):
        for h in horizons:
            n = len(D) - h
            xs, xn, y = A[target][:n], A[src][:n], A[target][h:]
            per_event, acc = [], {"self": [], "both": [], "pers": [], "zero": []}
            for (a, b, yr) in blocks:
                te = np.zeros(n, dtype=bool)
                te[a:min(b + 1, n)] = True
                if te.sum() < 10:
                    continue
                # обучение — всё, кроме этого события И буфера вокруг него
                tr = ~te
                if tr.sum() < 100:
                    continue
                X1 = np.c_[np.ones(tr.sum()), xs[tr]]
                b1 = np.linalg.lstsq(X1, y[tr], rcond=None)[0]
                X2 = np.c_[np.ones(tr.sum()), xs[tr], xn[tr]]
                b2 = np.linalg.lstsq(X2, y[tr], rcond=None)[0]
                e_self = np.abs(b1[0] + b1[1] * xs[te] - y[te])
                e_both = np.abs(b2[0] + b2[1] * xs[te] + b2[2] * xn[te] - y[te])
                per_event.append(float(e_both.mean() - e_self.mean()))
                acc["self"].append(e_self); acc["both"].append(e_both)
                acc["pers"].append(np.abs(xs[te] - y[te])); acc["zero"].append(np.abs(y[te]))
            if len(per_event) < 5:
                continue
            mae = {k: float(np.concatenate(v).mean()) for k, v in acc.items()}
            d = np.array(per_event, dtype=float)
            # интервал — перевыборкой СОБЫТИЙ (не недель: недели зависимы, и интервал вышел бы вдесятеро уже)
            rng = np.random.default_rng(42)
            boot = np.array([rng.choice(d, size=len(d), replace=True).mean() for _ in range(4000)])
            lo, hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
            rows.append({"target": target, "src": src, "h": h,
                         "mae_self": round(mae["self"], 3), "mae_both": round(mae["both"], 3),
                         "mae_pers": round(mae["pers"], 3), "mae_zero": round(mae["zero"], 3),
                         "d_mae": round(float(d.mean()), 4), "ci_lo": round(lo, 4), "ci_hi": round(hi, 4),
                         "events": len(per_event), "helped": int((d < 0).sum()),
                         "gain_pct": round((mae["self"] - mae["both"]) / mae["self"] * 100, 1)})
    # лучший — тот, у кого польза (отрицательный d_mae) больше всего, и его интервал
    best = min(rows, key=lambda r: r["d_mae"]) if rows else None
    return rows, best


def composite(D, A, gap_now, lvl_now, ev_idx, horizons=(4, 8, 13, 26)):
    """Что было дальше в неделях, похожих на сегодняшнюю по ФОРМЕ события.

    Похожая неделя — та, где восток так же оторвался от центра и событие было не слабее.
    Это не прогноз и не модель: это выборка прошлых недель и что в них было потом. Сколько
    их и из каких лет — печатается рядом, потому что сорок недель из четырёх событий это
    четыре случая, а не сорок.
    """
    gap = A["n12"] - A["n4"]
    N = len(D)
    # ОТБОР ПО МЕСТУ, А НЕ ПО ГРАДУСАМ. Порог «в пределах 0,4 °C от сегодняшнего» годился, пока
    # разрыв считался между соседними зонами; у контраста «восток минус запад» сегодняшние +3.6
    # такие, что в этот допуск попадает один 1997 год. Берём недели, когда событие уже шло
    # (3.4 ≥ 1.5) и разрыв был в верхней трети с лишним таких недель: это четыре события —
    # ровно те четыре года, которые панель и так держит за особенные.
    lmin = 1.5
    on = A["n34"][:-1] >= lmin
    gmin = float(np.percentile(gap[:-1][on], 60)) if on.any() else 1.0
    sel = np.where(on & (gap[:-1] >= gmin))[0]
    # ТЕКУЩЕЕ СОБЫТИЕ ИЗ ВЫБОРКИ ВОН. Его собственные недели тоже похожи на сегодняшнюю — ещё бы,
    # это оно и есть, — и «что было дальше» превратилось бы в рассказ события о самом себе.
    cur = ev_idx[-1] if ev_idx else None
    if cur is not None:
        sel = sel[np.abs(sel - cur) > 78]
    # Считаем СОБЫТИЯ, а не календарные годы: 1997 и 1998 — это одно событие, а не два случая.
    evs = {}
    for i in sel:
        near = min(ev_idx, key=lambda k: abs(k - int(i))) if ev_idx else None
        if near is not None and abs(near - int(i)) <= 78:
            evs.setdefault(D[near].year, 0)
            evs[D[near].year] += 1
    years = sorted(evs)
    # СОБЫТИЕ — ОДИН СЛУЧАЙ, А НЕ ДВАДЦАТЬ НЕДЕЛЬ. Из 29 подходящих недель девятнадцать были
    # из одного события: медиана по неделям — это рассказ 1997 года о самом себе. Считаем медиану
    # ВНУТРИ события, а по событиям показываем их все поимённо, без усреднения трёх в одно.
    by_ev = {}
    for i in sel:
        near = min(ev_idx, key=lambda k: abs(k - int(i))) if ev_idx else None
        if near is None or abs(near - int(i)) > 78:
            continue
        by_ev.setdefault(D[near].year, {"weeks": [], "peak": near})["weeks"].append(int(i))
    steps = []
    for h in horizons:
        rec = {"h": h, "events": [], "zones": {}}
        per_zone = {z: [] for z in IDS}
        for y in sorted(by_ev):
            ok = [i for i in by_ev[y]["weeks"] if i + h < N]
            if not ok:
                continue
            row = {"year": str(y), "n_weeks": len(ok), "zones": {}}
            for z in IDS:
                d = np.array([A[z][i + h] - A[z][i] for i in ok], dtype=float)
                m = float(np.median(d))
                row["zones"][z] = round(m, 2)
                per_zone[z].append(m)
            rec["events"].append(row)
        if len(rec["events"]) < 2:
            continue
        for z in IDS:
            v = per_zone[z]
            rec["zones"][z] = {"median": round(float(np.median(v)), 2),
                               "lo": round(float(min(v)), 2), "hi": round(float(max(v)), 2), "n_events": len(v)}
        steps.append(rec)
    # ФАЗА: где в своём событии стояли эти недели. Сегодняшняя фаза неизвестна — пик ещё не настал,
    # и без этой оговорки подборка читалась бы как «вот что будет», хотя она про другую точку пути.
    phase = [int(i - by_ev[y]["peak"]) for y in by_ev for i in by_ev[y]["weeks"]]
    ph = {"before_peak": sum(1 for x in phase if x < 0), "after_peak": sum(1 for x in phase if x > 0),
          "min": int(min(phase)) if phase else None, "max": int(max(phase)) if phase else None}
    pool_max = float(gap[sel].max()) if len(sel) else None
    return {"gap_min": round(gmin, 2), "level_min": round(lmin, 2), "n_weeks": int(len(sel)),
            "pool_max_gap": (round(pool_max, 2) if pool_max is not None else None),
            "today_gap": round(float(gap_now), 2),
            # Сегодня разрыв больше, чем в любой отобранной неделе: подборка — это не «такое же»,
            # а «самое похожее из бывшего», и слабее сегодняшнего. Без этой строки её прочли бы
            # как обещание.
            "today_above_pool": bool(pool_max is not None and gap_now > pool_max),
            "years": [str(y) for y in years], "n_events": len(years), "steps": steps,
            "weeks_per_event": {str(y): n for y, n in sorted(evs.items())},
            "phase": ph, "excludes_current": True,
            "formula": "Niño 1+2 minus Niño 4, the same contrast the panel uses for the type of an event"}


# ── ГЛУБИНА ─────────────────────────────────────────────────────────────────────────────────
def subsurface_drift():
    """Куда и как быстро едет тёплая аномалия под поверхностью (Ховмёллер, D20).

    Центр тяжести берётся только по ТЁПЛОЙ части разреза и только когда тёплого достаточно:
    при слабой аномалии центр скачет через полокеана и «скорость» получается из ничего.
    """
    if not HOV.exists():
        return None
    H = json.loads(HOV.read_text(encoding="utf-8"))
    cur = H.get("current") or {}
    lons = np.array(cur.get("lons") or [], dtype=float)
    # ТОТ ЖЕ РЯД, ЧТО У stats_layer.hov_speed_item: аномалия на 100 м, центр масс тёплой части,
    # окно в восемь месяцев. Иначе на двух экранах панели стояли бы две скорости одной и той же воды.
    months, grid = cur.get("months") or [], cur.get("anom100") or []
    if len(lons) < 10 or not months:
        return None
    pts = []
    for i, row in enumerate(grid):
        v = np.array([np.nan if x is None else x for x in row], dtype=float)
        w = np.clip(v, 0, None)
        area = float(np.nansum(w))
        if area < 20:                                   # тёплого слишком мало, чтобы был центр
            pts.append({"month": months[i], "centre": None, "peak": None, "area": round(area, 1)})
            continue
        c = float(np.nansum(w * lons) / area)
        pts.append({"month": months[i], "centre": round(c, 1),
                    "peak": round(float(lons[int(np.nanargmax(v))]), 1), "area": round(area, 1)})
    good = [(i, p["centre"]) for i, p in enumerate(pts) if p["centre"] is not None]
    drift = None
    if len(good) >= 5:
        tail = good[-8:]
        x = np.array([g[0] for g in tail], dtype=float)
        y = np.array([g[1] for g in tail], dtype=float)
        slope = float(np.polyfit(x, y, 1)[0])           # градусов долготы в месяц
        drift = {"deg_per_month": round(slope, 1), "months": len(tail),
                 # 1° долготы на экваторе = 111 км; месяц считаем в 30,4 суток — как в stats_layer
                 "m_per_s": round(slope * 111e3 / (30.4 * 86_400), 2),
                 "from": pts[good[-len(tail)][0]]["month"], "to": pts[good[-1][0]]["month"]}
    return {"points": pts, "drift": drift, "level": H.get("level"),
            "field": "anom100",
            "note": "Temperature anomaly at 100 m along the equator, month by month. The mark is the centre of mass "
                    "of the warm part, not a current: it also travels east when the west simply cools. The steps are "
                    "months, so a speed read from them is a slope over months, not a measured current, and the same "
                    "number is shown on Heat on the move."}


ZONE_SPAN = (("n4", 160.0, 210.0), ("n34", 190.0, 240.0), ("n3", 210.0, 270.0), ("n12", 270.0, 280.0))


def zone_of_lon(lon):
    """Под какой зоной сидит центр тёплой аномалии (долготы восточные, 0–360).

    Зоны ПЕРЕКРЫВАЮТСЯ: 210–240° в.д. принадлежит и 3.4, и 3. Брать первую подошедшую нельзя —
    на 240° (120° з.д.) так получалась «3.4», хотя это ровно середина зоны 3. Берём ту, к чьей
    середине долгота ближе.
    """
    if lon is None:
        return None
    hits = [(abs(lon - (a + b) / 2), zid) for zid, a, b in ZONE_SPAN if a <= lon <= b]
    return min(hits)[1] if hits else None


# ── СБОРКА ──────────────────────────────────────────────────────────────────────────────────
def _skill_verdict(best):
    """Одна фраза о том, даёт ли соседняя зона хоть что-то. Считается из интервала, не из порога.

    Порог «меньше пяти процентов — значит нет» был бы выдумкой: пять процентов от чего? Здесь
    сравнение с ценой деления самого индекса — он публикуется с точностью 0,1 °C.
    """
    if not best:
        return "Not enough finished events to test whether one patch helps forecast another."
    d, lo, hi = best["d_mae"], best["ci_lo"], best["ci_hi"]
    nm = {z["id"]: z["name"] for z in ZONES}
    who = f"{nm.get(best['src'], best['src'])} into {nm.get(best['target'], best['target'])} at {best['h']} weeks"
    size = ("changes the error by " + f"{abs(d):.3f} °C" + (" in its favour" if d < 0 else " for the worse"))
    span = f"between {lo:+.3f} and {hi:+.3f} °C once the events are resampled"
    if hi < 0 and abs(d) >= 0.05:
        return ("The best pair, " + who + ", " + size + " (" + span + "), which is large enough to matter "
                "against an index printed to 0.1 °C.")
    return ("Even the best pair, " + who + ", only " + size + " — " + span + ". Against an index published to "
            "0.1 °C that is nothing: a patch is not forecast by its neighbour, it is forecast by its own past. "
            "So this scene shows what happened before, not what will happen.")


def now_block(D, A, events):
    """Где каждая зона стоит сегодня: место в собственном сорокапятилетнем ряду и рекорд.

    Без этого сцена молчала бы о том, что Niño 3 сейчас стоит на максимуме всего ряда: соседние
    сцены об этом говорят, а здесь бы не было ни слова.
    """
    out = {}
    for z in IDS:
        v = float(A[z][-1])
        higher = int((A[z][:-1] > v).sum())
        out[z] = {"value": round(v, 2), "higher_weeks": higher, "of": len(D) - 1,
                  "record": higher == 0,
                  "pct": round(float((A[z][:-1] <= v).mean() * 100), 1)}
    return out


def vs_special(D, A, events):
    """Наши четыре года на ТОЙ ЖЕ неделе календаря — единственное честное «а сейчас».

    Сравнивать по фазе события нельзя: фаза известна только задним числом, пик ещё не настал.
    Календарь же известен всегда, и панель сравнивает аналоги именно так на других сценах.
    """
    last = D[-1]
    doy = last.timetuple().tm_yday
    out = []
    for y in SPECIAL:
        best, bi = 400, None
        for i, d in enumerate(D):
            if d.year != y:
                continue
            k = abs(d.timetuple().tm_yday - doy)
            if k < best:
                best, bi = k, i
        if bi is None or best > 7:
            continue
        out.append({"year": str(y), "date": D[bi].isoformat(),
                    "values": {z: round(float(A[z][bi]), 2) for z in IDS},
                    "diff": {z: round(float(A[z][-1] - A[z][bi]), 2) for z in IDS},
                    "east_minus_west": round(float(A["n12"][bi] - A["n4"][bi]), 2)})
    return out


def build(show=False):
    t0 = time.time()
    if not SRC.exists():
        sys.exit(f"нет исходника {SRC} — его кладёт ежедневный сбор (sources.noaa_weekly)")
    D, A = read_weekly()
    N = len(D)
    ev_idx = find_events(D, A)
    events = [event_row(D, A, k, N) for k in ev_idx]
    done = [e for e in events if not e["running"]]

    # запаздывание пика относительно 3.4 — только по законченным событиям
    lags = {}
    for z in IDS:
        v = [e["zones"][z]["peak_lag"] for e in done]
        c = [e["zones"][z]["cross_lag"] for e in done if e["zones"][z]["cross_lag"] is not None]
        lags[z] = {"peak_median": float(np.median(v)) if v else None,
                   "peak_p25": float(np.percentile(v, 25)) if v else None,
                   "peak_p75": float(np.percentile(v, 75)) if v else None,
                   "cross_median": float(np.median(c)) if c else None,
                   "n": len(v), "n_cross": len(c)}

    gap = A["n12"] - A["n4"]                 # одна формула на панель: watch.py:387
    gap_now, lvl_now = float(gap[-1]), float(A["n34"][-1])
    pct = float((gap[:-1] <= gap_now).mean() * 100)
    rows, best = skill_table(D, A)
    comp = composite(D, A, gap_now, lvl_now, ev_idx)
    sub = subsurface_drift()

    doc = {
        "built": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "NOAA CPC weekly Niño indices (wksst9120), anomalies against 1991–2020",
        "weeks": N, "first": D[0].isoformat(), "last": D[-1].isoformat(),
        "order": IDS, "zones": ZONES, "special_years": [str(y) for y in SPECIAL],
        "now": {"date": D[-1].isoformat(),
                "values": {z: round(float(A[z][-1]), 2) for z in IDS},
                "east_minus_west": round(gap_now, 2),
                "east_minus_west_formula": "Niño 1+2 minus Niño 4",
                "gap_percentile": round(pct, 1),
                "shape": "east-heavy" if gap_now > 1.0 else ("west-heavy" if gap_now < -0.3 else "mixed"),
                # последний месяц, в котором тёплая аномалия вообще была: последний по счёту
                # может оказаться пустым, и тогда «под какой зоной» — вопрос без ответа
                "under_the_surface": zone_of_lon(next((p["centre"] for p in reversed((sub or {}).get("points") or [])
                                                       if p.get("centre") is not None), None)),
                "under_the_surface_month": next((p["month"] for p in reversed((sub or {}).get("points") or [])
                                                 if p.get("centre") is not None), None)},
        "series": {"dates": [d.isoformat() for d in D],
                   **{z: [round(float(v), 2) for v in A[z]] for z in IDS}},
        "events": events,
        "lag_of_peak": lags, "timing": timing_counts(done), "chain": chain_test(done),
        "standing": now_block(D, A, events), "vs_special": vs_special(D, A, events),
        "special_events": [e for e in events if e["special"] or e["running"]],
        "overlap": ("Niño 3.4 (170–120°W) and Niño 3 (150–90°W) share 30° of longitude — 60 % of the width of 3.4 "
                    "and half of 3. Niño 4 (160°E–150°W) and Niño 3.4 share 20°. Only Niño 1+2 (90–80°W) touches "
                    "none of the others, which is why it is the only patch with a timing of its own."),
        "pairs": lag_pairs(A),
        "skill": {"rows": rows, "best": best,
                  "verdict": _skill_verdict(best)},
        "composite": comp,
        "subsurface": sub,
        "note": ("Four patches of the same equator, measured at the surface. The panel can say which patch warmed "
                 "first and how far the event leans east or centre; it cannot say that heat moved from one patch to "
                 "another, because a surface temperature is not a flow of energy. Niño 3.4 and Niño 3 overlap between "
                 "150°W and 120°W, so part of what they share is the same water counted twice. The water that does "
                 "move is below: the subsurface panel shows it, measured."),
    }
    safeio.write_text(OUT, json.dumps(doc, ensure_ascii=False))
    kb = OUT.stat().st_size / 1024
    print(f"zones-flow.json: {N} недель, {len(events)} событий ({len(done)} законченных), {kb:.0f} КБ, {time.time()-t0:.0f} с")
    if show:
        print("\n  событие      " + "".join(f"{z:>17}" for z in IDS))
        for e in events:
            mark = " ←наш" if e["special"] else ("  идёт" if e["running"] else "")
            line = f"  {e['peak_date']}  "
            for z in IDS:
                q = e["zones"][z]
                line += f"{q['peak']:+6.1f} @{q['peak_lag']:+4d}н"
            print(line + mark)
        print("\n  запаздывание пика к 3.4 (недель, по законченным событиям):")
        for z in IDS:
            L = lags[z]
            print(f"    {z:>4}: медиана {L['peak_median']:+.0f}, квартили {L['peak_p25']:+.0f}…{L['peak_p75']:+.0f} (n={L['n']})")
        print("\n  связь между зонами:")
        for p in doc["pairs"]:
            print(f"    {p['a']:>4} и {p['b']:<4} лучший сдвиг {p['best_lag']:+3d} нед, r={p['r_best']:.2f}, "
                  f"без сдвига {p['r0']:.2f}, независимых точек ≈{p['n_eff']}")
        if best:
            print(f"\n  сосед против собственного прошлого: лучшая пара {best['src']}→{best['target']} "
                  f"на {best['h']} нед: {best['d_mae']:+.4f} °C (интервал {best['ci_lo']:+.4f}…{best['ci_hi']:+.4f}), "
                  f"помог в {best['helped']} событиях из {best['events']}")
        print(f"  сегодня: " + ", ".join(f"{z} {doc['now']['values'][z]:+.1f}" for z in IDS)
              + f"; восток−центр {gap_now:+.1f} ({pct:.0f}-й процентиль)")
        if comp["steps"]:
            print(f"  похожих недель {comp['n_weeks']} из {comp['n_events']} событий ({', '.join(comp['years'])}),"
                  f" по неделям на событие: {comp['weeks_per_event']}")
            print(f"  фаза этих недель: {comp['phase']['before_peak']} до пика, {comp['phase']['after_peak']} после,"
                  f" от {comp['phase']['min']} до {comp['phase']['max']} недель")
            for s in comp["steps"]:
                print(f"    через {s['h']:>2} нед  " + "  ".join(
                    f"{z} {s['zones'][z]['median']:+.2f} [{s['zones'][z]['lo']:+.2f}…{s['zones'][z]['hi']:+.2f}]" for z in IDS))
        if sub and sub.get("drift"):
            d = sub["drift"]
            print(f"  под поверхностью: центр тёплой аномалии едет {d['deg_per_month']:+.1f}° долготы в месяц "
                  f"({d['m_per_s']:+.2f} м/с), {d['from']} → {d['to']}")
    try:
        import ops as OPSLOG
        OPSLOG.record_run("zones_flow", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ok",
                          note=f"{N} weeks, {len(events)} events")
    except Exception:                                            # noqa: BLE001
        pass
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true", help="напечатать главное в консоль")
    a = ap.parse_args()
    build(a.show)


if __name__ == "__main__":
    main()
