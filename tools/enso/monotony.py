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


AMP_SMOOTH = 15            # суток: центрированное среднее, от которого считается остаток
AMP_RMS = 15               # суток: окно скользящего RMS остатка — кривая амплитуды


def _nanmean_centered(a, k):
    """Центрированное скользящее среднее с пропусками (NaN не рвут ряд, а не считаются)."""
    n = len(a)
    out = np.full(n, np.nan)
    h = k // 2
    for i in range(n):
        w = a[max(0, i - h):i + h + 1]
        f = w[np.isfinite(w)]
        if len(f) >= max(3, k // 2):
            out[i] = f.mean()
    return out


def amplitude_curve(arr, open_end=False):
    """АМПЛИТУДА КОЛЕБАНИЙ ВО ВРЕМЕНИ (21.09): остаток ряда от 15-суточного центрированного среднего
    и его скользящий RMS за 15 суток. Это «размах качелей» вокруг хода, а не сам ход: ряд может
    расти монотонно и качаться слабо — или расти и качаться сильно. Возвращает массив по тем же
    индексам, что вход."""
    a = np.array([np.nan if v is None else float(v) for v in arr], float)
    if np.isfinite(a).sum() < AMP_SMOOTH:
        return [None] * len(a)
    res = a - _nanmean_centered(a, AMP_SMOOTH)
    r2_ = res * res
    rms = _nanmean_centered(r2_, AMP_RMS)
    out = [None if not np.isfinite(x) else r2(float(np.sqrt(x)), 3) for x in rms]
    # КРАЙ БЕЗ БУДУЩЕГО (21.09): на последних h сутках центрированное среднее одностороннее, остаток
    # раздут, и кривая «взлетала» у правого края. Эти сутки не показываем — честнее, чем рисовать.
    if open_end:
        h = AMP_SMOOTH // 2
        for i in range(max(0, len(out) - h), len(out)):
            out[i] = None
    return out


def amplitude_window(full, lo, hi, open_end):
    """RMS остатка за окно [lo..hi] ряда full: среднее считается с запасом по краям, где ряд есть;
    у открытого конца (этот год) последние h суток окна не входят — там будущего нет."""
    h = AMP_SMOOTH // 2
    a = np.array([np.nan if v is None else float(v) for v in full[max(0, lo - h):hi + 1 + h]], float)
    off = lo - max(0, lo - h)
    res = (a - _nanmean_centered(a, AMP_SMOOTH))[off:off + (hi - lo + 1)]
    if open_end:
        res = res[:-h] if len(res) > h else res[:0]
    f = res[np.isfinite(res)]
    if len(f) < WIN * 0.4:
        return None
    return r2(float(np.sqrt(np.mean(f * f))), 3)


def amplitude_block(this_full, past_full, this_dates, end_idx, all_curves=False):
    """Блок амплитуды: кривые этого года и аналогов по тем же индексам (0..end_idx), метрика окна
    и ранг среди всех лет, у которых есть полное окно."""
    this_curve = amplitude_curve(this_full[:end_idx + 1], open_end=True)
    lo = max(0, end_idx - WIN + 1)
    now = amplitude_window(this_full, lo, end_idx, True)
    years = {}
    curves = {}
    for y, arr in past_full.items():
        if len(arr) <= end_idx:
            continue
        v = amplitude_window(arr, lo, end_idx, False)
        if v is not None:
            years[str(y)] = v
        if str(y) in ANALOGS or all_curves:                      # все годы — для переключателя (24.09)
            curves[str(y)] = amplitude_curve(arr[:end_idx + 1])
    pool = [v for v in years.values() if v is not None]
    blk = {"window_rms": now, "smooth_days": AMP_SMOOTH, "rms_days": AMP_RMS, "edge_days_dropped": AMP_SMOOTH // 2,
           "years": years, "of": len(pool) + 1 if pool else None,
           "rank_low": (1 + sum(1 for x in pool if x < now)) if (now is not None and pool) else None,
           "median": r2(float(np.median(pool)), 3) if pool else None,
           "curve": {"dates": this_dates[:end_idx + 1], "this": this_curve, "analogs": curves}}
    return blk


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
           # окна всех лет — для переключателя «все Эль-Ниньо / все годы» на сцене (23.09)
           "years_values": {y: windows[y] for y in sorted(windows)} if all_years else None,
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
        blk = series_block("n34_daily", "Niño 3.4, daily anomaly", "°C", this, wins, dates, all_years=True,
                           why="the index of the event itself; the spliced daily series the panel runs on")
        y0 = date(cy, 1, 1)
        blk["amplitude"] = amplitude_block(cur, past, [(y0 + timedelta(days=i)).isoformat() for i in range(day + 1)], day, all_curves=True)
        blocks.append(blk)

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
        blk = series_block("box_" + k, names[k], "°C", this, wins, dates, all_years=False,
                           why="daily box mean on the NOAA grid, one day behind; analogues on the same calendar days")
        # аналоги боксов выровнены по концу: дополняем спереди до длины этого года
        past_b = {}
        for y, arr in (b.get("analogs") or {}).items():
            if isinstance(arr, list) and len(arr) >= WIN:
                past_b[str(y)] = [None] * max(0, len(an) - len(arr)) + list(arr[-len(an):])
        blk["amplitude"] = amplitude_block(an, past_b, dts, len(an) - 1)
        blocks.append(blk)

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
                blk = series_block("sst_world", "World ocean 60°S–60°N, daily anomaly", "°C", this, wins, dates, all_years=True,
                                   why="the planet's sea surface; a smoother series, so its monotony is naturally higher")
                y0 = date(cy, 1, 1)
                blk["amplitude"] = amplitude_block(an_by[cy], {str(y): v for y, v in an_by.items() if y < cy},
                                                   [(y0 + timedelta(days=i)).isoformat() for i in range(last + 1)], last, all_curves=True)
                blocks.append(blk)
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
        am = it.get("amplitude") or {}
        if am.get("window_rms") is not None:
            out.setdefault(it["key"], {})   # блок ряда дописывается ниже; амплитуда — отдельными ключами
            out[it["key"] + "_amp"] = {"rms": am["window_rms"], "rank_low": am.get("rank_low"), "of": am.get("of"), "median": am.get("median")}
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
