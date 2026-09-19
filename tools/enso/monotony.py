# -*- coding: utf-8 -*-
"""Характер роста: насколько монотонно идёт ряд в текущем окне против тех же дней прошлых лет.

Владелец 19.09: «по прошлым важным годам Niño 3.4 хорошо так колеблется с периодом неделя-две,
а сейчас почти монотонно растёт — проверить, сделать метрикой, отдельная визуализация, то же по
остальным метрикам».

Окно — последние 60 суток до последнего дня ряда; у прошлых лет то же окно по дню года. Метрики
одного окна, все считаются из самого ряда, без сглаживания там, где оно не названо:
  net        — сдвиг за окно (последний минус первый), °C;
  path       — длина пути, сумма модулей суточных шагов, °C;
  monotony   — |net| / path: 1.0 значит «ни одного шага назад», 0 — вернулись, откуда вышли;
  up_share   — доля суточных шагов вверх;
  turns      — число разворотов 5-суточного скользящего среднего (сколько раз ход менял знак);
  drawdown   — самый глубокий откат от бегущего максимума внутри окна, °C.
Где есть все годы (Niño 3.4 по climatereanalyzer с 1982, мировой океан с 1981) — место этого
года среди всех; где только аналоги (боксы OISST держат 120 суток и четыре аналога) — против них.

Это описание формы ряда, не прогноз: монотонный подъём говорит, что внутрисезонные качели
(MJO, порывы ветра) сейчас не ломают рост, — и только это.
"""
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio   # noqa: E402
import sources as S   # noqa: E402
from numfmt import r2   # noqa: E402

OUT = ROOT / "data" / "enso" / "monotony.json"
DATA = ROOT / "data" / "enso"
WIN = 60
SMOOTH = 5
ANALOGS = ("1982", "1997", "2015", "2023")

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def metrics(v):
    """Метрики одного окна по массиву значений (None пропускаются, но окно должно быть почти полным)."""
    a = np.array([np.nan if x is None else float(x) for x in v], float)
    a = a[np.isfinite(a)]
    # аналоги боксов за 1997 лежат через день (stride 2 у OISST-копии): считаем по имеющимся точкам,
    # но не меньше половины окна — иначе форма не про этот ряд
    if len(a) < WIN * 0.4:
        return None
    d = np.diff(a)
    path = float(np.abs(d).sum())
    net = float(a[-1] - a[0])
    k = np.ones(SMOOTH) / SMOOTH
    sm = np.convolve(a, k, mode="valid")
    ds = np.diff(sm)
    ds = ds[np.abs(ds) > 1e-9]
    turns = int(np.sum(np.sign(ds[1:]) != np.sign(ds[:-1]))) if len(ds) > 1 else 0
    runmax = np.maximum.accumulate(a)
    dd = float(np.max(runmax - a))
    return {"n": int(len(a)), "net": r2(net), "path": r2(path), "monotony": r2(abs(net) / path, 2) if path > 0 else None,
            "up_share": r2(float(np.mean(d > 0)), 2), "turns": turns, "drawdown": r2(dd)}


def rank_desc(val, pool):
    """Место значения среди пула по убыванию (1 = самое большое)."""
    if val is None:
        return None
    return 1 + sum(1 for x in pool if x is not None and x > val)


def window_by_doy(series_by_year, end_doy, win=WIN):
    """Для каждого года — окно [end_doy-win+1 .. end_doy] по индексу дня года (0-based)."""
    out = {}
    for y, arr in series_by_year.items():
        a = np.array([np.nan if v is None else v for v in arr], float)
        lo, hi = end_doy - win + 1, end_doy + 1
        if lo < 0 or hi > len(a):
            continue
        w = a[lo:hi]
        if np.isfinite(w).sum() >= win * 0.8:
            out[str(y)] = [None if not np.isfinite(x) else r2(float(x), 3) for x in w]
    return out


def series_block(key, name, unit, this_year, windows, dates, all_years, why):
    """Сводка одного ряда: этот год, аналоги, распределение по всем годам (если есть)."""
    m_now = metrics(this_year)
    per_year = {y: metrics(w) for y, w in windows.items()}
    per_year = {y: m for y, m in per_year.items() if m}
    pool_mon = [m["monotony"] for m in per_year.values()]
    pool_dd = [m["drawdown"] for m in per_year.values()]
    pool_turns = [m["turns"] for m in per_year.values()]
    blk = {"key": key, "name": name, "unit": unit, "why": why, "window_days": WIN,
           "dates": dates, "this_year": {"values": [None if v is None else r2(float(v), 3) for v in this_year], "metrics": m_now},
           "analogs": {y: {"values": windows.get(y), "metrics": per_year.get(y)} for y in ANALOGS if y in windows},
           "all_years": all_years}
    if m_now and per_year:
        blk["rank"] = {"of": len(per_year) + 1,
                       "monotony": rank_desc(m_now["monotony"], pool_mon),
                       "drawdown_low": 1 + sum(1 for x in pool_dd if x is not None and x < m_now["drawdown"]),
                       "turns_low": 1 + sum(1 for x in pool_turns if x is not None and x < m_now["turns"]),
                       "net": rank_desc(m_now["net"], [m["net"] for m in per_year.values()]),
                       "years_monotony": {y: m["monotony"] for y, m in per_year.items()},
                       "years_drawdown": {y: m["drawdown"] for y, m in per_year.items()},
                       "years_turns": {y: m["turns"] for y, m in per_year.items()},
                       "median_monotony": r2(float(np.median([x for x in pool_mon if x is not None])), 2) if pool_mon else None,
                       "median_turns": r2(float(np.median(pool_turns)), 1) if pool_turns else None,
                       "median_drawdown": r2(float(np.median(pool_dd)), 2) if pool_dd else None}
    return blk


def build(D):
    """Все блоки по словарю разбора (latest.json или тот же словарь ещё в памяти refresh.py)."""
    blocks = []

    # 1. Niño 3.4 суточная (склейка climatereanalyzer + NOAA): этот год — current_series по дню года;
    #    прошлые годы — копия источника (все годы с 1982); аналоги оттуда же.
    N = D.get("nino34") or {}
    cur = N.get("current_series") or []
    day = int(N.get("day") or 0)
    if cur and day >= WIN:
        try:
            _cr = S.read_cr_json(S.LAST / "sst_nino34.json")
            years, clim = _cr["years"], _cr["clim"]
        except Exception:                                        # noqa: BLE001
            years, clim = {}, None
        cy = int(str(D.get("generated") or date.today().isoformat())[:4])
        past = {y: (np.array(v, float) - (np.array(clim, float) if clim is not None else 0.0)).tolist()
                for y, v in years.items() if y < cy}
        this = cur[day - WIN + 1:day + 1]
        d0 = date(cy, 1, 1) + timedelta(days=day - WIN + 1)
        dates = [(d0 + timedelta(days=i)).isoformat() for i in range(WIN)]
        wins = window_by_doy(past, day)
        blocks.append(series_block("n34_daily", "Niño 3.4, daily anomaly", "°C", this, wins, dates, all_years=True,
                                   why="the index of the event itself; the spliced daily series the panel runs on"))

    # 2. Боксы OISST: 120 суток этого года и четыре аналога на тех же датах
    ob = ((D.get("oisst") or {}).get("boxes") or {})
    names = {"nino34": "Niño 3.4, our box", "nino3": "Niño 3, our box", "nino4": "Niño 4, our box", "nino12": "Niño 1+2, our box"}
    for k in ("nino34", "nino3", "nino4", "nino12"):
        b = ob.get(k) or {}
        an, dts = b.get("anom") or [], b.get("dates") or []
        if len(an) < WIN:
            continue
        this = an[-WIN:]
        dates = dts[-WIN:]
        wins = {}
        for y, arr in (b.get("analogs") or {}).items():
            if isinstance(arr, list) and len(arr) >= WIN:
                wins[str(y)] = [None if v is None else r2(float(v), 3) for v in arr[-WIN:]]
        blocks.append(series_block("box_" + k, names[k], "°C", this, wins, dates, all_years=False,
                                   why="daily box mean on the NOAA grid, one day behind; analogues on the same calendar days"))

    # 3. Мировой океан: все годы из planet.json (абсолют минус климатология по дню года)
    try:
        PL = json.loads((DATA / "planet.json").read_text(encoding="utf-8"))
        T = ((PL.get("temperature") or {}).get("sst_world") or {})
        yrs, clim = T.get("years") or {}, T.get("clim")
        if yrs and clim:
            cy = max(int(y) for y in yrs)
            ca = np.array([np.nan if v is None else v for v in clim], float)
            an_by = {int(y): (np.array([np.nan if v is None else v for v in v_], float) - ca[:len(v_)]).tolist() for y, v_ in yrs.items()}
            arr = np.array([np.nan if v is None else v for v in an_by[cy]], float)
            last = int(np.where(np.isfinite(arr))[0][-1])
            if last >= WIN:
                this = an_by[cy][last - WIN + 1:last + 1]
                d0 = date(cy, 1, 1) + timedelta(days=last - WIN + 1)
                dates = [(d0 + timedelta(days=i)).isoformat() for i in range(WIN)]
                wins = window_by_doy({y: v for y, v in an_by.items() if y < cy}, last)
                blocks.append(series_block("sst_world", "World ocean 60°S–60°N, daily anomaly", "°C", this, wins, dates, all_years=True,
                                           why="the planet's sea surface; a smoother series, so its monotony is naturally higher"))
    except Exception as e:                                       # noqa: BLE001
        print("  world ocean skipped:", str(e)[:100])

    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "assessed_stamp": D.get("stamp"), "window_days": WIN, "smooth_days": SMOOTH,
           "items": blocks,
           "note": ("Shape of the rise, not its size: over the last 60 days, how much of the path went straight (|net| / path), "
                    "how many times the 5-day mean turned, how deep the deepest dip from the running maximum was, and the share of "
                    "up-days. The same window on the same calendar days of past years is the comparison. Where the whole record "
                    "is daily (Niño 3.4 since 1982, the world ocean since 1981) the rank is among all years; the OISST boxes hold "
                    "120 days and four analogues, so their comparison is against those four. Description of the series, not a forecast: "
                    "a straight climb says the intraseasonal swings — MJO pulses, wind bursts — are not breaking the rise right now.")}
    return doc


def summary(doc):
    """Короткий блок для latest.json — журнал и полоса KPI читают его оттуда (19.09)."""
    out = {"window_days": doc.get("window_days"), "built": doc.get("built")}
    for it in doc.get("items") or []:
        m, rk = (it.get("this_year") or {}).get("metrics") or {}, it.get("rank") or {}
        out[it["key"]] = {"straightness": m.get("monotony"), "drawdown": m.get("drawdown"), "turns": m.get("turns"),
                          "up_share": m.get("up_share"), "net": m.get("net"), "to": (it.get("dates") or [None])[-1],
                          "rank": rk.get("monotony"), "of": rk.get("of"), "median": rk.get("median_monotony")}
    return out


def main():
    t0 = time.time()
    D = json.loads((DATA / "latest.json").read_text(encoding="utf-8"))
    doc = build(D)
    blocks = doc["items"]
    safeio.write_text(OUT, json.dumps(doc, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
    for b in blocks:
        m, rk = b["this_year"]["metrics"], b.get("rank") or {}
        print(f"  {b['name']:36s} net {m['net']:+.2f} path {m['path']:.2f} monotony {m['monotony']:.2f} up {m['up_share']:.2f} turns {m['turns']} dd {m['drawdown']:.2f}"
              + (f" | rank monotony {rk.get('monotony')}/{rk.get('of')}, turns-low {rk.get('turns_low')}, dd-low {rk.get('drawdown_low')}; median monotony {rk.get('median_monotony')}, turns {rk.get('median_turns')}" if rk else ""))
        for y, a in b["analogs"].items():
            mm = a.get("metrics")
            if mm:
                print(f"      {y}: net {mm['net']:+.2f} monotony {mm['monotony']:.2f} turns {mm['turns']} dd {mm['drawdown']:.2f}")
    print(f"monotony.json: {len(blocks)} series, {OUT.stat().st_size // 1024} KB, {time.time() - t0:.1f} s")
    try:
        import ops as OPSLOG
        OPSLOG.record_run("monotony", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ok", note=f"{len(blocks)} series, window {WIN} d")
    except Exception:                                            # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
