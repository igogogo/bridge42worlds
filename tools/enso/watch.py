# -*- coding: utf-8 -*-
"""Сторожевая аналитика: последний год, последний месяц, две недели вперёд.

Каждый суточный ряд проходит один и тот же осмотр, и каждая цифра сравнивается не
с «нормой вообще», а с распределением ТОГО ЖЕ календарного окна по всем прошлым
годам — иначе сентябрьский наклон сравнивался бы с мартовским, а это разные
физики. Тренд снимается всюду, где сравниваются годы между собой.

Что считается по каждому ряду:
  уровень      — аномалия последних 30 дней и её ранг среди тех же 30 дней всех лет
  наклон       — скорость за 14 дней против таких же 14-дневных наклонов истории
  ускорение    — наклон последних 14 минус наклон предыдущих 14
  шум          — размах суточных приращений за 30 дней против истории
  CUSUM        — накопленный сдвиг за 180 дней: ловит смену режима раньше среднего
  рекорды      — сколько из последних 30 дней выше всех лет и длина текущей серии
  прогноз      — аналоговый: к сегодняшнему уровню прибавляется приращение каждого
                 прошлого года за те же 14 календарных дней; получаем распределение
  свежесть     — сколько дней данным

Отдельно для Niño 3.4: наложение на 1982, 1997, 2015, 2023 по тем же дням и оценка
пика зимы по аналогам. Отдельно по недельным индексам NOAA: четыре региона, где
стоит текущая неделя в истории и восточный ли это тип события.
"""
import json
from datetime import date, timedelta

import numpy as np
from scipy import stats as st

import sources as S
import iri_plume as IP

ANALOGS = [1982, 1997, 2015, 2023]         # годы зарождения очень сильных Эль-Ниньо
ANALOG_PEAK_YEAR = {1982: 1983, 1997: 1998, 2015: 2016, 2023: 2024}
NINO_PEAK_YEARS = {1958, 1966, 1973, 1983, 1988, 1992, 1998, 2016, 2024}
NINA_YEARS = {1974, 1976, 1989, 1999, 2000, 2008, 2011, 2021, 2022}


def _finite_years(years, min_days=360, exclude=()):
    return [y for y in sorted(years)
            if y not in exclude and np.isfinite(years[y]).sum() >= min_days]


def _annual_fit(years, clim, ylist):
    ys = np.array(ylist, float)
    av = np.array([np.nanmean(years[y] - clim) for y in ylist])
    sl, ic, r, p, se = st.linregress(ys, av)
    return sl, ic, av


def _pct_rank(value, sample):
    sample = np.asarray(sample, float)
    sample = sample[np.isfinite(sample)]
    if len(sample) == 0:
        return None
    return float((sample < value).mean() * 100)


def _slope(y):
    y = np.asarray(y, float)
    m = np.isfinite(y)
    if m.sum() < 4:
        return np.nan
    x = np.arange(len(y))[m]
    return float(np.polyfit(x, y[m], 1)[0])


def _window(arr, end_idx, n):
    """n значений, заканчивающихся индексом end_idx включительно (в 366-сетке одного года)."""
    lo = max(0, end_idx - n + 1)
    return arr[lo:end_idx + 1]


def _cross_year(years, y, end_idx, n):
    """Окно длиной n дней, кончающееся end_idx года y, с переходом через 1 января."""
    if end_idx + 1 >= n or (y - 1) not in years:
        return _window(years[y], end_idx, n)
    prev = years[y - 1]
    take_prev = n - (end_idx + 1)
    return np.concatenate([prev[366 - take_prev:], years[y][:end_idx + 1]])


def series_watch(ds, label, analog_years=None):
    years, clim = ds["years"], ds["clim"]
    ycur, idx = ds["last_year"], ds["last_idx"]
    anom = {y: years[y] - clim for y in years}
    hist = _finite_years(years, exclude=(ycur,))
    sl, ic, _ = _annual_fit(years, clim, hist)
    trend_now = sl * ycur + ic

    cur = anom[ycur]
    out = {"label": label, "last_date": ds["last_date"].isoformat(),
           "days_stale": (date.today() - ds["last_date"]).days,
           "trend_per_decade": round(sl * 10, 3)}

    # --- уровень: последние 30 дней против того же окна в каждом году (тренд снят)
    w30 = _cross_year(anom, ycur, idx, 30)
    lvl = float(np.nanmean(w30))
    same = []
    for y in hist:
        w = _cross_year(anom, y, idx, 30)
        if np.isfinite(w).sum() >= 24:
            same.append(np.nanmean(w) - (sl * y + ic))
    lvl_det = lvl - trend_now
    out["level30"] = {"anom": round(lvl, 3), "det": round(lvl_det, 3),
                      "pct": round(_pct_rank(lvl_det, same), 1),
                      "z": round(float((lvl_det - np.mean(same)) / np.std(same, ddof=1)), 2),
                      "rank_raw": 1 + sum(1 for y in hist
                                          if np.isfinite(_cross_year(anom, y, idx, 30)).sum() >= 24
                                          and np.nanmean(_cross_year(anom, y, idx, 30)) > lvl),
                      "of": len(same) + 1}
    # последние 7 дней отдельно — самое свежее
    w7 = _cross_year(anom, ycur, idx, 7)
    out["level7"] = round(float(np.nanmean(w7)), 3)
    out["last_value"] = round(float(cur[idx]), 3)

    # --- наклон и ускорение (°C за 14 дней), против таких же окон истории
    s_now = _slope(_cross_year(anom, ycur, idx, 14)) * 14
    s_prev = _slope(_cross_year(anom, ycur, idx - 14, 14)) * 14 if idx >= 27 else np.nan
    s_hist = [_slope(_cross_year(anom, y, idx, 14)) * 14 for y in hist]
    out["slope14"] = {"now": round(s_now, 3),
                      "prev": None if not np.isfinite(s_prev) else round(s_prev, 3),
                      "accel": None if not np.isfinite(s_prev) else round(s_now - s_prev, 3),
                      "pct": round(_pct_rank(s_now, s_hist), 1),
                      "hist_sd": round(float(np.nanstd(s_hist, ddof=1)), 3)}

    # --- шум: размах суточных приращений
    d_now = np.nanstd(np.diff(_cross_year(anom, ycur, idx, 30)), ddof=1)
    d_hist = [np.nanstd(np.diff(_cross_year(anom, y, idx, 30)), ddof=1) for y in hist]
    out["noise30"] = {"now": round(float(d_now), 4), "pct": round(_pct_rank(d_now, d_hist), 1)}

    # --- CUSUM за 180 дней: базовый уровень — первые 60 из них, масштаб — разброс
    # суточных детрендированных аномалий ВСЕЙ истории (иначе тихая весна даёт
    # смешной порог и тревогу в сотни единиц). Считается в единицах этого разброса.
    w180 = _cross_year(anom, ycur, idx, 180) - trend_now
    base = np.nanmean(w180[:60])
    scale = float(np.nanstd(np.concatenate([anom[y] - (sl * y + ic) for y in hist]), ddof=1))
    k, h = 0.5, 5.0                      # в единицах scale
    S_pos = S_neg = 0.0; path = []
    for v in w180[60:]:
        if not np.isfinite(v):
            path.append(path[-1] if path else 0.0); continue
        u = (v - base) / scale
        S_pos = max(0.0, S_pos + u - k)
        S_neg = min(0.0, S_neg + u + k)
        path.append(S_pos if S_pos > -S_neg else S_neg)
    out["cusum"] = {"final": round(float(path[-1]), 2), "threshold": h, "scale": round(scale, 3),
                    "base": round(float(base), 3),
                    "alarm": bool(abs(path[-1]) > h),
                    "first_alarm_days_ago": next((len(path) - i for i, v in enumerate(path)
                                                  if abs(v) > h), None),
                    "path": [round(float(v), 2) for v in path]}

    # --- рекорды за последние 30 дней и серия
    rec_flags = []
    for d0 in range(max(0, idx - 29), idx + 1):
        prev = [years[y][d0] for y in hist if np.isfinite(years[y][d0])]
        rec_flags.append(bool(prev) and np.isfinite(years[ycur][d0]) and years[ycur][d0] > max(prev))
    streak = 0
    for f in reversed(rec_flags):
        if f: streak += 1
        else: break
    rec_year = 0
    for d0 in range(0, idx + 1):
        prev = [years[y][d0] for y in hist if np.isfinite(years[y][d0])]
        if prev and np.isfinite(years[ycur][d0]) and years[ycur][d0] > max(prev):
            rec_year += 1
    out["records"] = {"last30": int(sum(rec_flags)), "streak": streak,
                      "year": rec_year, "year_days": int(np.isfinite(years[ycur]).sum())}

    # --- прогноз на 14 дней по аналогам: приращение каждого года за те же дни
    H = 14
    deltas, deltas_analog = [], []
    for y in hist:
        a = anom[y]
        if idx + H < 366 and np.isfinite(a[idx]) and np.isfinite(a[idx + H]):
            d = a[idx + H] - a[idx]
        elif idx + H >= 366 and (y + 1) in anom:
            b = anom[y + 1]
            j = idx + H - 366
            if np.isfinite(a[idx]) and np.isfinite(b[j]):
                d = b[j] - a[idx]
            else:
                continue
        else:
            continue
        deltas.append(d)
        if analog_years and y in analog_years:
            deltas_analog.append(d)
    deltas = np.array(deltas)
    base_now = float(cur[idx])
    q = np.percentile(deltas, [10, 50, 90]) if len(deltas) else [np.nan] * 3
    out["forecast14"] = {
        "from": round(base_now, 3),
        "p10": round(base_now + q[0], 3), "p50": round(base_now + q[1], 3),
        "p90": round(base_now + q[2], 3), "n": int(len(deltas)),
        "analog_p50": round(base_now + float(np.median(deltas_analog)), 3) if deltas_analog else None,
        "persistence_trend": round(base_now + s_now, 3),
    }

    # --- ряд последних 400 дней для графика (аномалии), и полосы истории по календарю
    seq = _cross_year(anom, ycur, idx, 400)
    out["recent"] = [None if not np.isfinite(v) else round(float(v), 3) for v in seq]
    # хвосты для карточек рисков: 45 дней с датами, скользящий 14-дневный наклон, флаги рекордов
    last = ds["last_date"]
    seq45 = _cross_year(anom, ycur, idx, 45)
    out["tail45"] = {"dates": [(last - timedelta(days=44 - i)).isoformat() for i in range(45)],
                     "anom": [None if not np.isfinite(v) else round(float(v), 3) for v in seq45]}
    # ТЕ ЖЕ СОРОК ПЯТЬ ДНЕЙ У ПРОШЛЫХ СОБЫТИЙ И У ПРОШЛОГО ГОДА. Владелец 04.09: «у риска
    # про мировой океан на графике нечего показать для прошлых значимых событий; проверь все
    # рисковые карточки — где уместно, покажи прошлый год, где уместно, важные годы события».
    # Считается для ЛЮБОГО ряда, а не только для Niño 3.4: данные по годам у нас есть на всех
    # трёх, раньше просто не брали. Сравнение по календарю — тот же день года.
    tails = {}
    for y in (ANALOGS + [ycur - 1]):
        if y not in anom:
            continue
        seq = _cross_year(anom, y, idx, 45)
        vals = [None if not np.isfinite(v) else round(float(v), 3) for v in seq]
        if any(v is not None for v in vals):
            tails[str(y)] = vals
    if tails:
        out["tail45_analogs"] = tails
    sp = []
    for j in range(45):
        e = idx - (44 - j)
        if e >= 13 or (ycur - 1) in anom:
            v = _slope(_cross_year(anom, ycur, e, 14)) * 14
            sp.append(None if not np.isfinite(v) else round(float(v), 3))
        else:
            sp.append(None)
    out["slope14_path"] = sp
    fl = []
    for d0 in range(max(0, idx - 44), idx + 1):
        prev = [years[y][d0] for y in hist if np.isfinite(years[y][d0])]
        fl.append(1 if (prev and np.isfinite(years[ycur][d0]) and years[ycur][d0] > max(prev)) else 0)
    out["records"]["flags45"] = fl
    band = np.array([[anom[y][d] for y in hist] for d in range(366)])
    out["band_p10"] = [round(float(v), 3) for v in np.nanpercentile(band, 10, axis=1)]
    out["band_p90"] = [round(float(v), 3) for v in np.nanpercentile(band, 90, axis=1)]
    out["band_max"] = [round(float(v), 3) for v in np.nanmax(band, axis=1)]
    out["band_min"] = [round(float(v), 3) for v in np.nanmin(band, axis=1)]
    out["cur_year"] = [None if not np.isfinite(v) else round(float(v), 3) for v in cur]
    out["last_idx"] = idx
    out["year"] = ycur
    out["prev_year"] = [None if not np.isfinite(v) else round(float(v), 3) for v in anom.get(ycur - 1, np.full(366, np.nan))]

    # --- последние 13 месяцев помесячно: аномалия и место среди тех же месяцев всех лет
    ME = np.cumsum([0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
    months = []
    y, m = ycur, int(np.searchsorted(ME, idx, side="right") - 1)
    for _ in range(13):
        seg = anom[y][ME[m]:ME[m+1]] if y in anom else np.array([np.nan])
        if np.isfinite(seg).sum() >= 10:
            v = float(np.nanmean(seg))
            others = [float(np.nanmean(anom[yy][ME[m]:ME[m+1]])) for yy in hist
                      if yy != y and np.isfinite(anom[yy][ME[m]:ME[m+1]]).sum() >= 24]
            months.append({"y": y, "m": m + 1, "anom": round(v, 3),
                           "rank": 1 + sum(1 for o in others if o > v), "of": len(others) + 1,
                           "days": int(np.isfinite(seg).sum())})
        m -= 1
        if m < 0:
            m = 11; y -= 1
    out["months13"] = months[::-1]

    # --- долгий контекст: годовые детрендированные z
    ys = np.array(hist, float)
    av = np.array([np.nanmean(anom[y]) for y in hist])
    res = av - (sl * ys + ic)
    zz = (res - res.mean()) / res.std(ddof=1)
    out["annual"] = {int(y): round(float(a), 3) for y, a in zip(hist, av)}
    out["annual_z_top"] = [(int(ys[i]), round(float(zz[i]), 2)) for i in np.argsort(-np.abs(zz))[:5]]
    # текущий год по одинаковым дням
    mask = np.isfinite(cur)
    same_days = {y: float(np.nanmean(anom[y][mask])) for y in hist
                 if np.isfinite(anom[y][mask]).sum() >= mask.sum() * .95}
    cur_mean = float(np.nanmean(cur[mask]))
    out["ytd"] = {"mean": round(cur_mean, 3),
                  "rank": 1 + sum(1 for v in same_days.values() if v > cur_mean),
                  "of": len(same_days) + 1,
                  "det_z": round(float((cur_mean - trend_now - np.mean([v - (sl*y+ic) for y, v in same_days.items()]))
                                       / np.std([v - (sl*y+ic) for y, v in same_days.items()], ddof=1)), 2)}
    return out


def nino34_analogs(ds):
    """Niño 3.4: текущая траектория против 1982/1997/2015/2023 по тем же дням и оценка пика."""
    years, clim, ycur, idx = ds["years"], ds["clim"], ds["last_year"], ds["last_idx"]
    anom = {y: years[y] - clim for y in years}
    cur = anom[ycur]
    out = {"analogs": {}, "day": idx}
    for y in ANALOGS:
        if y not in anom:
            continue
        a = anom[y]
        nxt = anom.get(y + 1)
        # пик: максимум с сентября года y по февраль y+1 (индексы 244.. и 0..59)
        tail = a[244:]
        head = nxt[:60] if nxt is not None else np.array([])
        peak = float(np.nanmax(np.concatenate([tail, head])))
        peak_idx = int(np.nanargmax(np.concatenate([tail, head])))
        peak_date = (S.grid_index_to_date(y, 244 + peak_idx) if peak_idx < len(tail)
                     else S.grid_index_to_date(y + 1, peak_idx - len(tail)))
        same_day = float(a[idx]) if np.isfinite(a[idx]) else float(np.nanmean(a[idx-3:idx+4]))
        # средняя за те же 30 дней
        same30 = float(np.nanmean(a[max(0, idx-29):idx+1]))
        out["analogs"][y] = {
            "same_day": round(same_day, 2), "same30": round(same30, 2),
            "peak": round(peak, 2), "peak_date": peak_date.isoformat(),
            "gain_to_peak": round(peak - same30, 2),
            "series": [None if not np.isfinite(v) else round(float(v), 2) for v in a],
            "next": [None if not np.isfinite(v) else round(float(v), 2) for v in (nxt[:120] if nxt is not None else [])],
        }
    cur30 = float(np.nanmean(cur[max(0, idx-29):idx+1]))
    gains = [v["gain_to_peak"] for v in out["analogs"].values()]
    out["current30"] = round(cur30, 2)
    out["current_day"] = round(float(cur[idx]), 2)
    ratios = [v["peak"] / v["same30"] for v in out["analogs"].values() if v["same30"] > 0.3]
    hist_ceiling = max(float(np.nanmax(anom[y])) for y in years if y != ycur)
    out["peak_estimate"] = {
        "additive_low": round(cur30 + min(gains), 2), "additive_mid": round(cur30 + float(np.median(gains)), 2),
        "additive_high": round(cur30 + max(gains), 2),
        "ratio_mid": round(cur30 * float(np.median(ratios)), 2) if ratios else None,
        "hist_ceiling": round(hist_ceiling, 2),
        "typical_peak_window": "November to January",
        "note": ("The current level is already above every analogue on these same days, so both adding and "
                 "multiplying their gain lead beyond anything measured (record of the series "
                 f"{hist_ceiling:+.2f} °C). The real question is not how much higher but when the growth "
                 "stops: for the analogues that happened in November or December."),
    }
    out["rank_same30"] = 1 + sum(1 for v in out["analogs"].values() if v["same30"] > cur30)
    out["current_series"] = [None if not np.isfinite(v) else round(float(v), 2) for v in cur]
    # все годы: ранг текущих 30 дней среди всех
    allsame = []
    for y in sorted(years):
        if y == ycur: continue
        w = anom[y][max(0, idx-29):idx+1]
        if np.isfinite(w).sum() >= 24:
            allsame.append((y, float(np.nanmean(w))))
    allsame.sort(key=lambda t: -t[1])
    out["all_years_rank"] = 1 + sum(1 for _, v in allsame if v > cur30)
    out["all_years_top"] = allsame[:6]
    return out


def noaa_weekly_watch(rows):
    last = rows[-1]
    out = {"date": last["date"].isoformat(), "latest": {k: last[k] for k in ("n12a", "n3a", "n34a", "n4a")}}
    # изменение за 4 и 8 недель
    for n in (4, 8):
        if len(rows) > n:
            out[f"chg{n}w"] = {k: round(last[k] - rows[-1 - n][k], 2) for k in ("n12a", "n3a", "n34a", "n4a")}
    # ранг текущей недели среди недель того же времени года (±14 дней) по всем годам
    doy = last["date"].timetuple().tm_yday
    same = [r["n34a"] for r in rows[:-1] if abs(r["date"].timetuple().tm_yday - doy) <= 14]
    out["n34_rank_pct"] = round(_pct_rank(last["n34a"], same), 1)
    out["n34_max_same_season"] = max((r["n34a"], r["date"].isoformat()) for r in rows[:-1]
                                     if abs(r["date"].timetuple().tm_yday - doy) <= 14)
    # тип события: восточный (Niño1+2 > Niño4) или центральный
    out["east_minus_central"] = round(last["n12a"] - last["n4a"], 2)
    out["type"] = ("eastern Pacific, canonical" if last["n12a"] - last["n4a"] > 1.0
                   else ("central Pacific (Modoki)" if last["n4a"] > last["n12a"] + 0.3
                         else "mixed"))
    # ряд последних 60 недель
    out["series"] = [{"date": r["date"].isoformat(), **{k: r[k] for k in ("n12a", "n3a", "n34a", "n4a")}}
                     for r in rows[-60:]]
    # Аналоги ПО НЕДЕЛЯМ, по каждому региону: та же календарная неделя 1982/1997/2015/2023
    # и пик их события. Владелец 03.09: «на карте показать, где недельный индекс, сравнение
    # с самым сильным явлением». Без этого карта отвечала только «сколько сейчас».
    keys4 = ("n12a", "n3a", "n34a", "n4a")
    out["analog_week"], out["analog_peak"] = {}, {}
    for y in ANALOGS:
        near = [r for r in rows if r["date"].year == y
                and abs(r["date"].timetuple().tm_yday - doy) <= 4]
        if near:
            r = min(near, key=lambda r: abs(r["date"].timetuple().tm_yday - doy))
            out["analog_week"][y] = dict({"date": r["date"].isoformat()},
                                         **{k: r[k] for k in keys4})
        ev = [r for r in rows if (r["date"].year == y and r["date"].month >= 7)
              or (r["date"].year == y + 1 and r["date"].month <= 6)]
        if ev:
            pk = {k: max(r[k] for r in ev) for k in keys4}
            pk["date_n34"] = max(ev, key=lambda r: r["n34a"])["date"].isoformat()
            out["analog_peak"][y] = pk

    # Месячные средние по неделям: из них считается «сезон на сегодня» — единственное
    # честное, с чем можно сравнивать трёхмесячный прогноз до конца сезона.
    mm = {}
    for r in rows:
        mm.setdefault((r["date"].year, r["date"].month), []).append(r["n34a"])
    out["monthly"] = {f"{y}-{m:02d}": round(sum(v) / len(v), 2)
                      for (y, m), v in sorted(mm.items())[-24:]}
    out["monthly_weeks"] = {f"{y}-{m:02d}": len(v) for (y, m), v in sorted(mm.items())[-24:]}

    # Ряды аналогов ПО ТОМУ ЖЕ КАЛЕНДАРЮ: 20 недель до той же даты у каждого сильного
    # события. Нужны графикам рисков — владелец 03.09: «на графиках рисков нет сравнения
    # с самым сильным событием, которое мы знаем, это 97-98».
    out["analog_series"] = {}
    for y in ANALOGS:
        same = [r for r in rows if r["date"].year in (y, y + 1)
                and -140 <= (r["date"].timetuple().tm_yday - doy if r["date"].year == y
                             else r["date"].timetuple().tm_yday + 365 - doy) <= 0]
        if same:
            out["analog_series"][y] = [{"date": r["date"].isoformat(),
                                        **{k: r[k] for k in keys4}} for r in same[-20:]]

    # исторические максимумы по каждому региону, без текущей недели — потолки для детектора
    out["hist_max_n34"] = max(rows[:-1], key=lambda r: r["n34a"])
    out["hist_max_n34"] = {"date": out["hist_max_n34"]["date"].isoformat(), "n34a": out["hist_max_n34"]["n34a"]}
    out["hist_max"] = {k: max(r[k] for r in rows[:-1]) for k in ("n12a", "n3a", "n34a", "n4a")}
    out["hist_max_date"] = {k: max(rows[:-1], key=lambda r: r[k])["date"].isoformat() for k in ("n12a", "n3a", "n34a", "n4a")}
    return out


def oni_watch(oni, psl):
    """ONI текущего года против аналогов на тех же сезонах; месячный PSL так же."""
    seasons = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
    by = {}
    for s, y, v in oni:
        by.setdefault(y, {})[s] = v
    ycur = max(by)
    cur = by[ycur]
    last_season = [s for s in seasons if s in cur][-1]
    cmp = {}
    for y in ANALOGS:
        if y in by:
            cmp[y] = {s: by[y].get(s) for s in seasons}
    out = {"year": ycur, "current": {s: cur.get(s) for s in seasons}, "last_season": last_season,
           "analogs": cmp, "peak_of_analogs": {y: max(v for v in by[y].values()) if y in by else None for y in ANALOGS}}
    # пик события — максимум ONI от JAS y до FMA y+1
    peaks = {}
    for y in ANALOGS:
        vals = [by[y].get(s) for s in seasons[6:]] + [by.get(y + 1, {}).get(s) for s in seasons[:3]]
        vals = [v for v in vals if v is not None]
        peaks[y] = max(vals) if vals else None
    out["analog_event_peak"] = peaks
    # ONI по годам — нужен оценке моделей: сезон плюма (ASO, DJF…) надо сверять с ONI ТОГО
    # ЖЕ календарного сезона, а не текущего года. Держим четыре последних года, это мелочь.
    out["by_year"] = {y: {s: by[y].get(s) for s in seasons} for y in sorted(by)[-4:]}
    # Что было ПОСЛЕ пика каждого аналога: следующий год и год за ним. Владелец 03.09:
    # «в рисках это нарушение не только текущего года, но и последующие проблемы на 27 год,
    # здесь есть аналогия с прошлыми глобальными событиями». Без этих двух лет сказать
    # нечего — в снимке лежал только год зарождения.
    out["analogs_after"] = {}
    for y in ANALOGS:
        after = {}
        for k in (1, 2):
            if y + k in by:
                after[y + k] = {s: by[y + k].get(s) for s in seasons}
        if after:
            out["analogs_after"][y] = after
    out["psl_current"] = psl.get(ycur)
    out["psl_analogs"] = {y: psl.get(y) for y in ANALOGS}
    # Весь месячный ряд ERSST — он нужен блоку «воздух», чтобы искать опережение объёма воды
    # и задержку слоёв атмосферы перебором сдвигов. В latest.json не уходит: слишком длинный
    # для панели и там не нужен (см. чистку в конце run()).
    out["psl_raw"] = psl
    return out


def roni_watch(roni, ONI):
    """RONI текущего года против аналогов, пики событий, и разница ONI − RONI по сезонам."""
    seasons = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
    by = {}
    for sn, y, v in roni:
        by.setdefault(y, {})[sn] = v
    if not by:
        return {}
    ycur = max(by)
    cur = by[ycur]
    last_season = [sn for sn in seasons if sn in cur][-1]
    peaks = {}
    for y in ANALOGS:
        vals = [by.get(y, {}).get(sn) for sn in seasons[6:]] + [by.get(y + 1, {}).get(sn) for sn in seasons[:3]]
        vals = [v for v in vals if v is not None]
        peaks[y] = max(vals) if vals else None
    oni_cur = (ONI or {}).get("current") or {}
    gap = {sn: round(oni_cur[sn] - cur[sn], 2) for sn in seasons if sn in cur and oni_cur.get(sn) is not None}
    return {"year": ycur, "current": {sn: cur.get(sn) for sn in seasons}, "last_season": last_season,
            "last": cur.get(last_season),
            "analogs": {y: {sn: by.get(y, {}).get(sn) for sn in seasons} for y in ANALOGS if y in by},
            "analogs_same_season": {y: by.get(y, {}).get(last_season) for y in ANALOGS},
            "analog_event_peak": peaks,
            "oni_event_peak": (ONI or {}).get("analog_event_peak"),
            "gap": gap, "gap_last": gap.get(last_season),
            "src": "NOAA CPC RONI.ascii.txt",
            "note": ("RONI is the Niño 3.4 anomaly minus the mean anomaly of the whole tropics (20°S–20°N). "
                     "NOAA switched its classification to it in February 2026 because a warm tropical ocean "
                     "makes the plain ONI overstate how strongly the atmosphere is being pushed. The gap "
                     "between the two is the warm background this event runs on.")}


def _m_daily(w, name, analogs=None):
    analogs = analogs or w.get("tail45_analogs")
    """Ряд для карточки риска + ТЕ ЖЕ ДНИ прошлых сильных событий.

    Владелец 04.09: «желательно, чтобы все карточки рисков справа показывали графики со
    сравнением с событиями, как и везде, а то опять же не с чем сравнивать». Сравнение идёт
    по календарю: тот же день года у 1997-98 и 2015-16, а не «через столько-то недель от
    начала» — иначе сезонный ход путает картину.
    """
    m = {"name": name, "unit": "°C", "step": "day",
         "dates": w["tail45"]["dates"], "values": w["tail45"]["anom"],
         "flags": w["records"].get("flags45")}
    if analogs:
        m["analogs"] = analogs
    return m


def _daily_analogs(N34, days=45):
    """Те же последние 45 дней у прошлых сильных событий — по дню года, а не по фазе.

    Ряды аналогов уже посчитаны для сцены «Against analogues» и лежат по дням года, так что
    здесь остаётся вырезать то же окно. Сравнение по календарю: сезонный ход у всех один и
    тот же, и разница в линиях — это разница событий, а не времени года."""
    out, day = {}, N34.get("day")
    if not day:
        return out
    for y, a in (N34.get("analogs") or {}).items():
        ser = a.get("series") or []
        if len(ser) >= day:
            vv = ser[max(0, day - days):day]
            if any(v is not None for v in vv):
                out[str(y)] = vv
    return out


def _m_weekly(NW, key, name):
    ser = NW["series"][-20:]
    m = {"name": name, "unit": "°C", "step": "week",
         "dates": [r["date"] for r in ser], "values": [r[key] for r in ser]}
    # недельные ряды аналогов уже посчитаны для вкладки «Weekly vs strongest» — берём их же
    out = {}
    for y, rows in (NW.get("analog_series") or {}).items():
        vv = [r.get(key) for r in rows][-len(ser):]
        if any(v is not None for v in vv):
            out[y] = vv
    if out:
        m["analogs"] = out
    return m


def _m_series(vals, name, unit, step, dates=None, analogs=None, levels=None):
    m = {"name": name, "unit": unit, "step": step, "dates": dates, "values": vals}
    if analogs:
        m["analogs"] = analogs
    if levels:
        # планки: уровень, которого этот же показатель достигал у прошлых событий или
        # порог правила — чтобы число на карточке не висело в пустоте (владелец 04.09)
        m["levels"] = levels
    return m


def _weekly_expr(NW, fn, n=20):
    """Тот же расчёт по недельным рядам прошлых событий: контрасты и разности зон.

    Без этого карточки вроде «восточная часть греется» показывали одну нашу линию и
    сравнивать её было не с чем (владелец 04.09)."""
    out = {}
    for y, rows in (NW.get("analog_series") or {}).items():
        vv = []
        for r in rows[-n:]:
            try:
                vv.append(fn(r))
            except (TypeError, KeyError):
                vv.append(None)
        if any(v is not None for v in vv):
            out[y] = vv
    return out


def _next_year_risks(W, ONI, cur_year=None):
    """Что было у аналогов ПОСЛЕ пика — и потому стоит в рисках на следующий год.

    Три вещи, каждая считается из наших рядов, а не из общих слов:
      · год ПОСЛЕ зарождения был теплее года зарождения (годовые средние ERA5);
      · ONI разворачивался в Ла-Нинью на второй год;
      · индекс цен FAO догонял событие с запозданием (наложение считает food.py, здесь
        только климатическая часть — цены живут своей карточкой).
    Возвращает список кортежей под add(): title, level, horizon, evidence, plain, watch,
    metric, kind."""
    out = []
    tw = W["t2_world"]
    ann = {int(k): v for k, v in (tw.get("annual") or {}).items()}
    # Год берём ТЕКУЩИЙ (series_watch кладёт его в out["year"]), а не последний в годовых
    # средних: те считаются по завершённым годам, и без этого карточка говорила «2026 будет
    # теплее 2025», хотя речь про год после пика.
    year = cur_year or tw.get("year") or (max(ann) if ann else None)

    # 1. следующий календарный год теплее
    gains = []
    for y in ANALOGS:
        if y in ann and (y + 1) in ann:
            gains.append((y, round(ann[y + 1] - ann[y], 3)))
    if gains and year:
        warmer = [g for g in gains if g[1] > 0]
        med = sorted(g[1] for g in gains)[len(gains) // 2]
        out.append((
            f"The year after the peak: {year + 1} is likely to be warmer than {year}",
            4, "next year",
            "In " + ", ".join(f"{y}→{y + 1} {d:+.2f} °C" for y, d in gains) +
            f" (annual land+ocean mean, ERA5); warmer in {len(warmer)} of {len(gains)} analogues, median {med:+.2f}.",
            "El Niño releases the ocean's heat into the air with a lag of a few months, so the calendar year that "
            "follows the peak is usually the warmer one. That is why 1998, 2016 and 2024 each became the warmest year "
            "measured up to that point. On the same arithmetic, next year is the one to plan for, not this one.",
            "annual land+ocean mean once the peak passes; the first months of next year already carry the signal",
            _m_series([ann[y] for y in sorted(ann)][-30:], "Land+ocean, annual mean", "°C", "year",
                      [str(y) for y in sorted(ann)][-30:],
                      # планки: каким был год ПОСЛЕ каждого прошлого события — ровно то, чем
                      # этот риск и меряется (владелец 04.09: «важные года события подписать»)
                      levels={str(y): ann[y + 1] for y in ANALOGS if (y + 1) in ann}),
            "climate"))

    # 2. разворот в Ла-Нинью на второй год
    after = ONI.get("analogs_after") or {}
    flips = []
    for y, rows in after.items():
        vals = []
        for yy in sorted(rows):
            vals += [v for v in (rows[yy] or {}).values() if v is not None]
        if vals:
            flips.append((int(y), round(min(vals), 2)))
    if flips:
        cold = [f for f in flips if f[1] <= -0.5]
        out.append((
            "A La Niña usually follows within a year or two",
            3, "2027",
            "After the analogues the ONI fell to " + ", ".join(f"{y}: {v:+.2f}" for y, v in flips) +
            f"; it crossed the La Niña threshold of −0.5 in {len(cold)} of {len(flips)} cases.",
            "The ocean does not simply return to normal: after a strong El Niño it usually swings the other way. "
            "A La Niña flips the map of impacts, so the regions that are dry now tend to be wet then, and the "
            "grain exporters that had a good year tend to have a bad one. Planning that only covers this winter "
            "misses the swing.",
            "the ONI trend after the peak; a fall of 0.3 or more per month is the usual signature of the swing",
            None, "climate"))

    # 3. воздух догоняет воду — уже есть отдельным риском, здесь про горизонт
    lag = tw["level30"]["det"]
    out.append((
        # Экспертиза 04.09, п. 3.10(6): трёхмесячный лаг доказан для ГЛОБАЛЬНОЙ температуры
        # (r ≈ 0.7); у региональных последствий свои задержки. Заголовок — про то, что измерено.
        "Global temperature in 2027 is likely to run above 2026; regional impacts follow their own lags",
        3, "6–18 months",
        f"Land+ocean is {lag:+.2f} °C above trend now, while the ocean heat that drives it is still rising; "
        "in the analogues the air-temperature records, the harvest failures and the price effects all came in "
        "the year after the onset.",
        "The dashboard measures the ocean today, but people meet an El Niño through harvests, water and prices, "
        "and those arrive with a delay of six to eighteen months. The plans that matter are for next year: "
        "import contracts, reserves, water rationing, insurance.",
        "the first harvests after the peak season and the food price index six to twelve months from the onset",
        _m_daily(tw, "Land+ocean, daily anomaly"), "climate"))
    return out


SEASON_MONTHS = {"DJF": (12, 1, 2), "JFM": (1, 2, 3), "FMA": (2, 3, 4), "MAM": (3, 4, 5),
                 "AMJ": (4, 5, 6), "MJJ": (5, 6, 7), "JJA": (6, 7, 8), "JAS": (7, 8, 9),
                 "ASO": (8, 9, 10), "SON": (9, 10, 11), "OND": (10, 11, 12), "NDJ": (11, 12, 1)}


def season_todate(NW, label, year):
    """Среднее ТЕХ месяцев сезона, что уже измерены: {value, months_done, months, parts}.

    Месяц считается измеренным, если в нём есть хотя бы две недели: одна неделя — это ещё
    не месяц, и среднее по ней сдвигает картину сильнее, чем помогает.
    """
    months = SEASON_MONTHS.get(label)
    if not months:
        return None
    monthly, weeks = NW.get("monthly") or {}, NW.get("monthly_weeks") or {}
    vals, parts, y = [], [], year
    prev = None
    for m in months:
        if prev is not None and m < prev:          # сезон переваливает через новый год
            y += 1
        prev = m
        key = f"{y}-{m:02d}"
        if key in monthly and weeks.get(key, 0) >= 2:
            vals.append(monthly[key])
            parts.append({"month": key, "value": monthly[key], "weeks": weeks.get(key, 0)})
    if not vals:
        return None
    return {"season": label, "value": round(sum(vals) / len(vals), 2), "months_done": len(vals),
            "months": 3, "parts": parts}


def models_vs_todate(IRI, td):
    """Кто из моделей уже ниже прожитой части сезона — то есть уже не может быть прав."""
    if not IRI or "error" in IRI or not td:
        return None
    seasons = IRI.get("seasons") or []
    if td["season"] not in seasons:
        return None
    i = seasons.index(td["season"])
    vals = [(nm, m["values"][i]) for nm, m in (IRI.get("models") or {}).items()
            if m.get("section") in ("dyn", "stat") and m.get("values") and m["values"][i] is not None]
    if not vals:
        return None
    below = sorted(nm for nm, v in vals if v < td["value"])
    return {"season": td["season"], "observed_todate": td["value"], "months_done": td["months_done"],
            "n": len(vals), "below": below, "share_below": round(100 * len(below) / len(vals)),
            "note": ("the models forecast a three-month mean; this compares them with the part of that season "
                     "already measured, so a model below this number would need the rest of the season to be "
                     "colder than the part already lived")}


def _slug(title):
    """Запасное имя риска, когда правило его не задало: из английского заголовка."""
    return "".join(c if c.isalnum() else "_" for c in title.lower()).strip("_")[:48]


def risks(W, N34, NW, ONI, IRI=None, AIR=None):
    """Реестр рисков. У каждого: уровень 1-5, горизонт, что видно в данных,
    что это значит по-человечески, за чем следить, и ряд, по которому риск живёт.
    Тексты по-английски: дашборд на сайте английский (владелец 03.09)."""
    R = []

    def add(title, level, horizon, evidence, plain, watch, metric=None, kind="climate", rid=None):
        # У РИСКА ЕСТЬ ИМЯ, НЕ ЗАВИСЯЩЕЕ ОТ ЗАГОЛОВКА. Журнал значений (tools/enso/journal.py)
        # ведёт историю уровня по каждому риску, а заголовок — это текст: его переписывают, а
        # 3 сентября его ещё и перевели с русского на английский — и вся история риска
        # обрывается на ровном месте. `rid` задаётся правилом и живёт, пока живёт правило.
        # Где правило одно, а состояния разные («очень сильное» / «развивается»), rid общий:
        # это один и тот же риск в двух состояниях, и уровень между ними должен идти подряд.
        R.append({"id": rid or _slug(title),
                  "title": title, "level": level, "horizon": horizon, "evidence": evidence,
                  "plain": plain, "watch": watch, "metric": metric, "kind": kind})

    n34 = W["sst_nino34"]; sw = W["sst_world"]; tw = W["t2_world"]
    lat = NW["latest"]

    # 1. сила события
    if lat["n34a"] >= 2.0:
        add("A very strong El Niño is under way", 5, "now",
            f"Niño 3.4 by the NOAA weekly index {lat['n34a']:+.1f} °C on {NW['date']}; daily OISST "
            f"{N34['current_day']:+.2f}. Among all years since 1982 for the same 30 days: rank {N34['all_years_rank']}.",
            f"Water in the key patch of the Pacific is {lat['n34a']:.1f} degrees warmer than normal. The threshold for a "
            "“very strong” event is two degrees. This is not a forecast, it is already measured, and it has never "
            "happened this early in the year.",
            f"the NOAA weekly index; the official ONI is now {ONI['current'][ONI['last_season']]:+.2f} ({ONI['last_season']}), "
            "the “very strong” category starts at +2.0 on the three-month average",
            metric=_m_weekly(NW, "n34a", "Niño 3.4, NOAA weekly"), rid="event_strength")
    elif lat["n34a"] >= 1.0:
        add("El Niño is developing", 3, "now", f"Niño 3.4 {lat['n34a']:+.1f} °C",
            "The warm phase is here, but it has not reached “very strong” yet.", "the NOAA weekly index",
            metric=_m_weekly(NW, "n34a", "Niño 3.4, NOAA weekly"), rid="event_strength")

    # 2. пик впереди
    pe = N34["peak_estimate"]
    # Экспертиза 04.09, п. 3.10(4): опережение объёма воды в полгода при r 0.49 хватает на
    # «событию есть чем расти», но не на «пик впереди». Заголовок — по тому, что измерено.
    add("The event has room to grow: the fuel is charged and the analogues peaked in winter", 4, "8–16 weeks",
        f"Past analogues peaked in {pe['typical_peak_window']}. Adding their gain from the same date gives "
        f"{pe['additive_low']:+.1f} … {pe['additive_high']:+.1f} °C, above the record of the series {pe['hist_ceiling']:+.2f}.",
        "Every past event of this strength peaked in winter, November to January. It is the end of summer now, so "
        "two or three more months of growth are likely. How much higher cannot be said: we are already above anything "
        "the ocean has shown at this time of year, and past events are no guide here. The real question is when the "
        "growth stops.",
        "if the weekly Niño 3.4 stops rising before November, the event has reached its plateau earlier than the analogues",
        metric=_m_daily(n34, "Niño 3.4, daily anomaly", _daily_analogs(N34)), rid="peak_ahead")

    # 3. восточный тип
    if NW["east_minus_central"] > 1.0:
        diff_series = [round(r["n12a"] - r["n4a"], 2) for r in NW["series"][-20:]]
        add("The eastern Pacific is heating, off the coast of South America", 4, "now",
            f"Niño 1+2 {lat['n12a']:+.1f}, Niño 4 {lat['n4a']:+.1f}: difference {NW['east_minus_central']:+.1f} °C.",
            "There are two kinds of El Niño: one heats the middle of the ocean, the other the east, off Peru and Ecuador. "
            "This is the second kind, the harshest in its consequences: 1982 and 1997 were like this. Such events brought "
            "downpours and floods to the coast of South America and droughts to Indonesia and Australia.",
            "the difference staying above 1 °C through September and October",
            metric=_m_series(diff_series, "Niño 1+2 minus Niño 4", "°C", "week",
                             [r["date"] for r in NW["series"][-20:]],
                             analogs=_weekly_expr(NW, lambda r: (r["n12a"] - r["n4a"])
                                                  if r.get("n12a") is not None and r.get("n4a") is not None else None)),
            rid="east_pacific")

    # 4. океан в рекордной серии
    if sw["records"]["streak"] >= 14 or sw["records"]["last30"] >= 20:
        add("The world ocean is warmer every day than it has ever been on that day", 4, "now",
            f"{sw['records']['last30']} record days out of the last 30, a run of {sw['records']['streak']} days in a row; "
            f"{sw['records']['year']} of {sw['records']['year_days']} days this year.",
            f"On each of the last {sw['records']['streak']} days the ocean, averaged over the planet, was warmer than on "
            "the same day of any year since 1982. Not one hot day, but an unbroken stretch.",
            "the first day below the record without a change of season is the first sign of a turn",
            metric=_m_daily(sw, "World ocean, daily anomaly"), rid="world_ocean_record_streak")

    # 5. скорость изменения
    for key, name in (("sst_nino34", "Niño 3.4"), ("sst_world", "world ocean"), ("t2_world", "land+ocean")):
        sl = W[key]["slope14"]
        if sl["pct"] is not None and (sl["pct"] >= 90 or sl["pct"] <= 10):
            fast = sl["pct"] >= 90
            add(f"{name}: unusually {'fast rise' if fast else 'fast fall'}", 3, "2 weeks",
                f"14-day slope {sl['now']:+.2f} °C, the {sl['pct']:.0f}th percentile for this time of year"
                + (f"; acceleration {sl['accel']:+.2f}" if sl["accel"] is not None else ""),
                f"In two weeks the series moved by {sl['now']:+.2f} degrees. For this time of year that happens in only "
                f"{100 - sl['pct'] if fast else sl['pct']:.0f} % of years.",
                "a change of sign in the acceleration marks the start of a plateau",
                metric=_m_series(W[key]["slope14_path"], f"{name}: 14-day slope", "°C", "day",
                                 W[key]["tail45"]["dates"]), rid=f"fast_{key}")

    # 6. CUSUM — новый уровень
    for key, name in (("sst_nino34", "Niño 3.4"), ("sst_world", "world ocean"), ("t2_world", "land+ocean")):
        c = W[key]["cusum"]
        if c["alarm"]:
            add(f"{name}: not a spike but a new level", 4 if key == "sst_nino34" else 3, "already happened",
                f"accumulated shift {c['final']:+.0f} against a threshold of {c['threshold']:.0f}; first over the threshold "
                f"{c['first_alarm_days_ago']} days ago",
                f"The series did not jump and come back; it rose and stayed. The gauge that accumulates the excess over the "
                f"spring level crossed its threshold {c['first_alarm_days_ago']} days ago and has only grown since.",
                "if the accumulated gauge starts to fall, the regime is letting go",
                metric=_m_series(c["path"][-60:], f"{name}: accumulated shift (CUSUM)", "σ", "day",
                             # планка — сам порог правила: видно, насколько его перешли
                             levels={"threshold": c["threshold"]}), rid=f"new_level_{key}")

    # 7. суша отстаёт от океана
    lag_gap = sw["level30"]["det"] - tw["level30"]["det"]
    if lag_gap > 0.05:
        add("The air has not caught up with the water yet", 3, "1–3 months",
            f"Ocean over 30 days {sw['level30']['det']:+.2f} °C above trend, land+ocean {tw['level30']['det']:+.2f}: "
            f"gap {lag_gap:+.2f}.",
            "The ocean is already further above its usual than the air over land and sea together. In past events the air "
            "caught up with the water in about a month, and the warmest year after an El Niño is usually the next one. "
            "So the air-temperature records are still ahead.",
            "land+ocean rising above the seasonal norm in October to December",
            metric=_m_daily(tw, "Land+ocean, daily anomaly"), rid="air_lags_water")

    # 8. свежесть данных
    for key in ("sst_nino34", "sst_world", "t2_world"):
        if W[key]["days_stale"] > 10:
            add(f"Data “{W[key]['label']}” is lagging", 2, "now",
                f"last point {W[key]['last_date']}, {W[key]['days_stale']} days ago",
                f"The daily series is {W[key]['days_stale']} days behind: the source publishes with a delay. While it is "
                "silent, the watchdog sees the past on this series; the NOAA weekly data is fresher and shows everything.",
                "a source update", kind="data", rid=f"stale_{key}")

    # 9. самые тёплые 30 дней
    for key, name in (("sst_world", "world ocean"), ("t2_world", "land+ocean")):
        l = W[key]["level30"]
        if l["rank_raw"] == 1:
            add(f"{name}: the last 30 days are the warmest in the whole record", 3, "now",
                f"anomaly {l['anom']:+.2f} °C, rank 1 of {l['of']}; above trend {l['det']:+.2f} (z = {l['z']})",
                f"For these same dates none of the {l['of']} years was warmer. Even after subtracting the general warming, "
                f"{l['det']:+.2f} degrees remain above it: that is what the event itself adds.",
                "whether the lead holds after the change of season",
                metric=_m_daily(W[key], f"{name}, daily anomaly"), rid=f"warmest30_{key}")

    # 10. модели прогноза против реальности
    if IRI and IRI.get("against_observed"):
        ao = IRI["against_observed"]; rv = IRI.get("revisions") or {}
        hist_peaks = [(h["issued"], max(v for v in (h["combined"] or []) if v is not None))
                      for h in IRI["history"] if h["combined"]]
        hist_peaks = hist_peaks[::-1]
        metric = _m_series([p for _, p in hist_peaks], "Combined forecast peak by IRI issue", "°C", "issue",
                           [i for i, _ in hist_peaks])
        if ao["reality_above_all"]:
            add("Reality is above every forecast model", 5, "now",
                f"Weekly Niño 3.4 {ao['observed_weekly']:+.1f} °C is above the maximum of all {ao['n']} models for {ao['season']} "
                f"({ao['max']:+.2f}).",
                "None of the models collected by IRI expected this level already. When reality overtakes every model at "
                "once, the winter forecasts should be read as a lower bound.",
                "the next IRI issue: whether the models lift their peak above reality", metric=metric, rid="reality_above_models")
        elif ao["share_below"] >= 35:
            add("Some forecast models are already below reality", 4 if ao["share_below"] >= 50 else 3, "now",
                f"{len(ao['below'])} of {ao['n']} models gave less for {ao['season']} than the already reached "
                f"{ao['observed_weekly']:+.1f} °C: {', '.join(ao['below'][:6])}{'…' if len(ao['below']) > 6 else ''}. "
                f"Model mean {ao['mean']:+.2f}, spread {ao['min']:+.2f}…{ao['max']:+.2f}.",
                f"Of {ao['n']} models, {len(ao['below'])} have already fallen behind what the ocean showed this week. "
                "They are not “wrong about the future”; they are not keeping up with the present. Their winter "
                "forecasts are most likely too low.",
                "the next IRI issue: how many models catch up", metric=metric, rid="models_below_reality")
        if rv and rv.get("combined_peak_prev") is not None and rv["combined_peak_cur"] - rv["combined_peak_prev"] >= 0.2:
            add("The models are revising the forecast upward for the second month running", 3, "until the next issue",
                f"Since the {rv['prev_issued']} issue {rv['n_up']} of {rv['n']} models raised their peak, {rv['n_down']} lowered it; "
                f"combined peak {rv['combined_peak_prev']:+.2f} → {rv['combined_peak_cur']:+.2f} °C.",
                "When almost all models move their forecast in the same direction, the event is outrunning them. The shift "
                "itself is a signal: the next issue will probably be higher again.",
                "the IRI issue around the 19th", metric=metric, rid="models_revise_up")

    # ---- 11. следующий год: чем прошлые события кончались ПОСЛЕ пика
    nxt = _next_year_risks(W, ONI, cur_year=W["t2_world"].get("year"))
    for r in nxt:
        add(*r[:6], metric=r[6], kind=r[7])

    # ---- 12. атмосфера, топливо и слои: правила лежат в air.py, рядом с их данными
    if AIR and not AIR.get("error"):
        try:
            import air as AR
            for r in AR.risks(AIR, lat["n34a"]):
                add(*r[:6], metric=r[6], kind=r[7], rid=r[8])
        except Exception as e:                                   # noqa: BLE001
            add("Atmospheric rules failed", 2, "now", str(e)[:160],
                "The air block did not produce its risks; the numbers themselves are on the panel.",
                "the next update", kind="data", rid="air_rules_failed")

    return _finish(R)


def _finish(R):
    R.sort(key=lambda r: -r["level"])
    load = sum(r["level"] ** 1.5 for r in R if r["kind"] == "climate")
    idx = int(round(100 * (1 - np.exp(-load / 25.0))))
    return R, idx


# ------------------------------------------------------------------ MJO
def mjo_block(omi, days=90):
    """OMI от PSL → фаза и амплитуда по дням. Kiladis et al. 2014: PC1 OMI ≈ RMM2, PC2 ≈ −RMM1,
    поэтому угол берём от (−PC2, PC1) — тот же круг фаз, что у BoM."""
    import math
    if not omi:
        return None
    keys = sorted(omi)[-days:]
    rows = []
    for k in keys:
        pc1, pc2, amp = omi[k]
        ang = math.degrees(math.atan2(pc1, -pc2)) % 360
        phase = int(((ang - 180) % 360) // 45) + 1
        rows.append({"d": k, "pc1": round(pc1, 2), "pc2": round(pc2, 2), "amp": round(amp, 2), "phase": phase})
    last = rows[-1]
    # доля последних 15 дней в фазах 6–8 при амплитуде ≥ 1 — «окно для всплесков»
    recent = rows[-15:]
    west = sum(1 for r in recent if r["amp"] >= 1 and r["phase"] in (6, 7, 8))
    return {"dates": [r["d"] for r in rows], "phase": [r["phase"] for r in rows], "amp": [r["amp"] for r in rows],
            "pc1": [r["pc1"] for r in rows], "pc2": [r["pc2"] for r in rows],
            "last": last, "active": last["amp"] >= 1.0, "days_in_6_8_of_15": west,
            "burst_window": last["amp"] >= 1.0 and last["phase"] in (5, 6, 7, 8),
            "src": "NOAA PSL ROMI (real-time OMI from CPC OLR), daily",
            "note": ("The Madden–Julian Oscillation is a pulse of cloud and wind that circles the tropics every "
                     "30–60 days. Phases 6–8 put its westerly winds over the western Pacific, and that is where "
                     "the wind bursts that feed an El Niño cluster. Amplitude below 1 means no organised pulse.")}


def mjo_risks(M, WIND):
    out = []
    if M.get("burst_window"):
        e = (WIND or {}).get("era5") or {}
        out.append((
            "The MJO is in the phases that launch wind bursts", 2, "next two weeks",
            f"OMI phase {M['last']['phase']}, amplitude {M['last']['amp']} on {M['last']['d']}; "
            f"{M['days_in_6_8_of_15']} of the last 15 days in phases 6–8. Westerly anomaly over 130°E–180° "
            f"in the last week {e.get('mean7')} m/s against a burst threshold of {e.get('threshold')}.",
            "When the pulse sits over the western Pacific the trade winds there give way for a week or two. "
            "That is the trigger: a burst now would send another Kelvin wave east and add to the peak two to "
            "three months later.",
            "the daily wind over 130°E–180°: five days above the threshold makes a burst",
            {"name": "MJO amplitude, daily", "unit": "", "step": "day", "dates": M["dates"], "values": M["amp"]},
            "climate", "mjo_burst_window"))
    return out


def run(fetch=True):
    if fetch:
        status, stamp = S.fetch_all()
    else:
        status, stamp = {k: (S.LAST / (k + S.ext_of(v[1])), True, "")
                         for k, v in S.SOURCES.items()}, "cached"
    ds = {k: S.read_cr_json(status[k][0]) for k in ("t2_world", "t2_nh", "t2_sh", "sst_world", "sst_nino34")}
    # OISST НАПРЯМУЮ (экспертиза 04.09, п. 3.1). Суточные боксы с сетки NOAA через ERDDAP,
    # задержка сутки; хвост NRT вшивается в ряды climatereanalyzer ДО всех правил, так что
    # рекорды, CUSUM, аналоги и «дней назад» считаются по свежему ряду. Смещение между
    # нашим боксом и их рядом меряется на перекрытии и показывается на панели.
    try:
        import oisst as OI
        OIS = OI.build(cr_nino34=ds["sst_nino34"], cr_world=ds["sst_world"])
    except Exception as e:                                       # noqa: BLE001
        OIS = {"error": str(e)[:200]}
    W = {k: series_watch(ds[k], S.LABELS[k], analog_years=ANALOGS if k == "sst_nino34" else None) for k in ds}
    for k in ("sst_nino34", "sst_world"):
        if ds[k].get("prelim_from"):
            W[k]["prelim_from"] = ds[k]["prelim_from"]
            W[k]["splice_offset"] = ds[k].get("splice_offset")
            W[k]["tail_source"] = "NOAA OISST v2.1 NRT via ERDDAP, spliced"
    N34 = nino34_analogs(ds["sst_nino34"])
    # ЧТО БЫЛО У ПРОШЛЫХ СОБЫТИЙ ПОСЛЕ ЭТОГО ЖЕ ДНЯ — ряд на год вперёд для сцены «Динамика»
    # (владелец 04.09: «продли вправо, чтобы видно было развитие ещё на год»). Данных из
    # будущего нет ни у кого; вправо уходит чужой опыт, и он подписан как чужой.
    try:
        _day = N34.get("day") or 0
        fwd = {}
        for _y, _a in (N34.get("analogs") or {}).items():
            _seq = (_a.get("series") or []) + (_a.get("next") or [])
            if len(_seq) > _day:
                fwd[str(_y)] = _seq[_day:_day + 365]
        if fwd:
            W["sst_nino34"]["analog_forward"] = fwd
    except Exception:                                            # noqa: BLE001
        pass
    NW = noaa_weekly_watch(S.read_noaa_weekly(status["noaa_weekly"][0]))
    ONI = oni_watch(S.read_oni(status["oni"][0]), S.read_psl_monthly(status["psl_nino34_monthly"][0]))
    # RONI РЯДОМ С ONI (экспертиза 04.09, п. 3.5): с февраля 2026 NOAA классифицирует события по
    # относительному индексу; на тёплом фоне он ниже ONI на десятые. Считаем то же, что для ONI:
    # текущий год, аналоги на тех же сезонах, пики событий.
    try:
        if status.get("roni", (None,))[0]:
            ONI["roni"] = roni_watch(S.read_roni(status["roni"][0]), ONI)
    except Exception as e:                                       # noqa: BLE001
        ONI["roni"] = {"error": str(e)[:160]}
    # IRI: плюм моделей, три последних выпуска; при сбое сети — из сохранённых файлов
    try:
        psl_cur = ONI.get("psl_current") or []
        psl_last = next((v for v in reversed(psl_cur) if v is not None and np.isfinite(v)), None)
        IRI = IP.watch(observed_weekly=NW["latest"]["n34a"], observed_monthly=psl_last)
    except Exception as e:                                       # noqa: BLE001
        IRI = {"error": str(e)[:200]}
    # Классы моделей по завершённым сезонам (ТЗ 5.4): считаются из сохранённых выпусков без сети.
    if IRI and "error" not in IRI:
        try:
            import models as MD
            cl = MD.classify(IRI, ONI, NW["latest"]["n34a"])
            IRI["classes"] = cl["classes"]; IRI["class_tally"] = cl["tally"]
            IRI["class_targets"] = cl["targets"]; IRI["class_issues"] = cl["issues"]
            # Как ломаются модели во времени: доля ниже реальности по выпускам и постоянные
            # отстающие (владелец 03.09: «часть моделей постоянно отваливается»).
            IRI["breakdown"] = MD.breakdown(cl, IRI, ONI)
            # Три последних выпуска ЦЕЛИКОМ (все модели, а не только сводное): панель кладёт
            # их друг под другом, и видно, как прогноз догоняет событие от месяца к месяцу
            # (владелец 03.09: «три сета графиком, вверху самый свежий, и точка где мы сейчас»).
            IRI["stack"] = [{"issued": i["issued"], "seasons": i["seasons"],
                             "models": {nm: {"section": m["section"], "values": m["values"]}
                                        for nm, m in i["models"].items()
                                        if m.get("values") and m["section"] in ("dyn", "stat", "avg")}}
                            for i in MD._issues()[-3:]][::-1]
        except Exception as e:                                   # noqa: BLE001
            IRI["classes_error"] = str(e)[:200]
    # Сезон на сегодня и последний прожитый целиком — честная опора для сравнения с плюмом.
    if IRI and "error" not in IRI:
        ao = IRI.get("against_observed") or {}
        yr = int(NW["date"][:4])
        td = season_todate(NW, ao.get("season") or "", yr)
        IRI["todate"] = models_vs_todate(IRI, td) if td else None
        for lab in ("JJA", "JAS", "ASO", "SON"):
            full = season_todate(NW, lab, yr)
            if full and full["months_done"] == 3:
                IRI["last_full_season"] = full
        if IRI.get("todate"):
            IRI["todate"]["parts"] = td["parts"]
        # ГДЕ МЫ СТОИМ НА ШКАЛЕ ПЛЮМА, честно по каждому сезону. Точка на прожитом целиком,
        # полоса — на прожитом наполовину: остаток сезона неизвестен, и его границы берём
        # из разброса живых моделей (владелец 04.09). Плюс сводное по живым: сломанные
        # модели в среднее не входят вовсе.
        try:
            import models as MD3
            IRI["live"] = MD3.live(IRI, IRI.get("classes") or {})
            # ГОД СЕЗОНА, А НЕ ТРИ БУКВЫ. Подписи в плюме повторяются каждый год, и первая
            # версия радостно нашла «прожитый целиком» JFM — январь-март ЭТОГО года, тогда
            # как столбец JFM в августовском выпуске означает следующий. Берём настоящий год
            # каждого столбца (та же функция, что чинила сравнение моделей) и оставляем
            # только сезоны, которые уже НАЧАЛИСЬ в этом году.
            # ПРОЖИТЫЕ СЕЗОНЫ, А НЕ ТОЛЬКО ТЕ, ЧТО РИСУЮТ МОДЕЛИ. Владелец 04.09: «нужно ещё
            # назад периоды показать, JJA и JAS; на JAS мы сейчас в большей степени, а не на
            # ASO». Плюм августовского выпуска начинает прогноз с ASO, где прожит ОДИН месяц
            # из трёх, — а JAS прожит на два из трёх, и это куда более твёрдая опора. JJA
            # прожит целиком и вовсе не является столбцом плюма. Поэтому кандидатов берём
            # не из плюма, а из календаря: три последних сезона, которые уже начались.
            mnow = int(NW["date"][5:7])
            tds = []
            for lab, mons in SEASON_MONTHS.items():
                if not mons or mons[0] > mnow or mons[0] < mnow - 2:
                    continue
                t = season_todate(NW, lab, yr)
                if t:
                    tds.append(t)
            tds.sort(key=lambda t: SEASON_MONTHS[t["season"]][0])
            # Коридор для неизмеренных месяцев: с ближайшего сезона, который модели дают.
            ss = IRI.get("seasons") or []
            fi = next((i for i, lab in enumerate(ss)
                       if any(v is not None for v in [(m.get("values") or [None] * (i + 1))[i]
                                                      for m in (IRI.get("models") or {}).values()
                                                      if m.get("section") in ("dyn", "stat") and m.get("values")
                                                      and len(m["values"]) > i])), None)
            td_fi = next((t for t in tds if fi is not None and t["season"] == ss[fi]), None)
            mrange = MD3._monthly_range(td_fi, IRI["live"], fi)
            IRI["position"] = MD3.position(IRI, tds, IRI["live"], mrange)
            IRI["position_note"] = ("Where we stand is read off the seasons we have actually lived, "
                                    "not off the first season the models publish: the plume starts at "
                                    + (ss[fi] if fi is not None else "?") + ", but by then only "
                                    + str((td_fi or {}).get("months_done", "?")) + " of its 3 months are measured. "
                                    "For seasons the models do not publish (JJA, JAS) the spread of the unmeasured "
                                    "months is BORROWED from the nearest forecast season — an assumption, not a measurement.")
        except Exception as e:                                   # noqa: BLE001
            IRI["live_error"] = str(e)[:200]

    # Блок F: индекс FAO (живой ряд) и регионы (справочник × сила события). Любая беда здесь
    # не должна ронять остальное: блок пустой с причиной, страница живёт.
    import food as FD
    import regions as RG
    try:
        fao = S.read_fao(status["fao_fpi"][0]) if status.get("fao_fpi", (None,))[0] else None
        FOOD = FD.analyze(fao, ONI["current"], ONI.get("analogs"), ONI["year"]) if fao else {"error": "FAO source missing"}
    except Exception as e:                                       # noqa: BLE001
        FOOD = {"error": str(e)[:200]}
    try:
        REG = RG.build(IRI if IRI and "error" not in IRI else None, NW["latest"]["n34a"],
                       record_weekly=(NW.get("hist_max") or {}).get("n34a"))
    except Exception as e:                                       # noqa: BLE001
        REG = {"error": str(e)[:200]}
    # Блок «воздух»: атмосфера, топливо, слои и цены поимённо (владелец 04.09). Любая беда
    # здесь не должна ронять остальное — блок пустой с причиной, панель живёт.
    try:
        import air as AIR
        parsed = {}
        for key in ("soi", "olr", "u850_west", "u850_centre", "u850_east"):
            if status.get(key, (None,))[0]:
                parsed[key] = S.read_cpc_table(status[key][0])
        for key in ("wwv", "t300"):
            if status.get(key, (None,))[0]:
                parsed[key] = S.read_pmel(status[key][0])
        for key in ("uah_tlt", "uah_tmt", "uah_ttp", "uah_tls"):
            if status.get(key, (None,))[0]:
                parsed[key] = S.read_uah(status[key][0])
        if status.get("wb_pink", (None,))[0]:
            parsed["wb_pink"] = S.read_pink(status["wb_pink"][0])
        onset = (FOOD or {}).get("overlay", {}).get("onset") if isinstance(FOOD, dict) else None
        # ДЛИННЫЙ месячный ряд Niño 3.4, а не наш недельный огрызок: опережение и задержки
        # ищутся перебором сдвигов, и на пятнадцати месяцах перебор бессмыслен — берём
        # ERSST от PSL, он с 1948 года. Первая версия молча возвращала «задержка неизвестна».
        n34m = {}
        for y, vals in (ONI.get("psl_raw") or {}).items():
            for mi, v in enumerate(vals, 1):
                if v is not None and v == v:
                    n34m[f"{y}-{mi:02d}"] = float(v)
        AIRB = AIR.build(parsed, n34m or (NW.get("monthly") or {}), onset)
        # пути товаров от начала события — свои и у прошлых событий (владелец 04.09, вечер)
        try:
            an_on = {y: (v or {}).get("onset") for y, v in (((FOOD or {}).get("overlay") or {}).get("analogs") or {}).items()}
            # 1982-й: индекса FAO тогда ещё не было, а Pink Sheet идёт с 1960-го — месяц начала берём из ONI
            for _y in ANALOGS:
                if str(_y) not in an_on and _y not in an_on:
                    _on = FD._onset_month((ONI.get("analogs") or {}).get(_y), _y)
                    if _on:
                        an_on[str(_y)] = _on
            AIRB["onset_paths"] = AIR.onset_paths(parsed.get("wb_pink"), onset, an_on)
        except Exception as e:                                   # noqa: BLE001
            AIRB["onset_paths"] = {"error": str(e)[:160]}
    except Exception as e:                                       # noqa: BLE001
        AIRB = {"error": str(e)[:200]}

    # ПОД ПОВЕРХНОСТЬЮ, ВЕТЕР ПО ДНЯМ, ЗАЛИВ, ФОН (экспертиза 04.09, пп. 3.2–3.8). Каждый блок
    # падает сам по себе: ошибка сети в одном не должна ронять панель.
    try:
        import subsurface as SB
        SUB = {"tao": SB.tao(), "godas": SB.godas()}
    except Exception as e:                                       # noqa: BLE001
        SUB = {"error": str(e)[:200]}
    try:
        import wind as WN
        WIND = WN.build()
    except Exception as e:                                       # noqa: BLE001
        WIND = {"error": str(e)[:200]}
    try:
        import gulf as GF
        kw = S.read_json(status["kuwait_era5"][0]) if status.get("kuwait_era5", (None,))[0] else None
        GULF = GF.build(((OIS or {}).get("boxes") or {}).get("gulf"), kw, parsed.get("wb_pink"), onset)
    except Exception as e:                                       # noqa: BLE001
        GULF = {"error": str(e)[:200]}
    try:
        import background as BG
        bparsed = {}
        for d_ in (700, 2000):
            rows = []
            for q_ in S.OHC_QUARTERS:
                key = f"ohc_{d_}_{q_}"
                if status.get(key, (None,))[0]:
                    rows += S.read_ohc(status[key][0])
            if rows:
                bparsed[f"ohc_{d_}"] = sorted(rows)
        for key in ("mei", "dmi"):
            if status.get(key, (None,))[0]:
                bparsed[key] = S.read_psl_monthly(status[key][0])
        BACK = BG.build(bparsed, ONI)
    except Exception as e:                                       # noqa: BLE001
        BACK = {"error": str(e)[:200]}
    try:
        OMI = mjo_block(S.read_omi(status["omi"][0])) if status.get("omi", (None,))[0] else None
    except Exception as e:                                       # noqa: BLE001
        OMI = {"error": str(e)[:200]}

    RR, ridx = risks(W, N34, NW, ONI, IRI if IRI and "error" not in IRI else None, AIRB)
    # правила новых блоков — тем же форматом, что у воздуха; индекс пересчитывается после
    extra = []
    for mod, blk in (("subsurface", SUB), ("wind", WIND), ("gulf", GULF), ("background", BACK)):
        if not blk or blk.get("error"):
            continue
        try:
            m = __import__(mod)
            extra += list(m.risks(blk)) if hasattr(m, "risks") else []
        except Exception as e:                                   # noqa: BLE001
            extra.append((f"{mod} rules failed", 2, "now", str(e)[:160],
                          "This block did not produce its risks; its numbers are on the panel.",
                          "the next update", None, "data", f"{mod}_rules_failed"))
    if OMI and not OMI.get("error"):
        extra += mjo_risks(OMI, WIND)
    for r in extra:
        RR.append({"id": r[8] if len(r) > 8 else _slug(r[0]), "title": r[0], "level": r[1], "horizon": r[2],
                   "evidence": r[3], "plain": r[4], "watch": r[5], "metric": r[6], "kind": r[7]})
    RR, ridx = _finish(RR)
    # Сопоставимое ядро индекса — сегодня и у прошлых событий на тот же день года
    # (владелец 04.09: «риск-индекс посчитать для других событий, по годам хотя бы основных»).
    try:
        import history_index as HX
        CORE = HX.build(NW, N34, roni=ONI.get("roni"))
    except Exception as e:                                       # noqa: BLE001
        CORE = {"error": str(e)[:200]}
    out = {"generated": date.today().isoformat(), "stamp": stamp,
           "sources": {k: {"fresh": v[1], "error": v[2], "label": S.LABELS[k]} for k, v in status.items()},
           "watch": W, "nino34": N34, "noaa": NW, "oni": ONI, "iri": IRI, "risks": RR, "risk_index": ridx,
           "food": FOOD, "regions": REG, "air": AIRB, "risk_core": CORE,
           "oisst": OIS, "subsurface": SUB, "wind": WIND, "gulf": GULF, "background": BACK, "mjo": OMI}
    ONI.pop("psl_raw", None)          # служебный длинный ряд наружу не отдаём
    return out


if __name__ == "__main__":
    import sys
    out = run(fetch="--cached" not in sys.argv)
    p = S.ROOT / "latest.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    W = out["watch"]
    for k in ("sst_nino34", "sst_world", "t2_world"):
        w = W[k]
        print(f"== {w['label']} (до {w['last_date']}, {w['days_stale']} дн.)")
        print(f"   30 дн: {w['level30']['anom']:+.2f} °C, сверх тренда {w['level30']['det']:+.2f}, "
              f"место {w['level30']['rank_raw']}/{w['level30']['of']}, z={w['level30']['z']}")
        print(f"   наклон14: {w['slope14']['now']:+.2f} (pct {w['slope14']['pct']}), ускор. {w['slope14']['accel']}")
        print(f"   CUSUM: {w['cusum']['final']:+.2f} / порог {w['cusum']['threshold']:.2f} тревога={w['cusum']['alarm']}")
        print(f"   рекорды: 30дн={w['records']['last30']} серия={w['records']['streak']} за год={w['records']['year']}")
        f = w["forecast14"]
        print(f"   прогноз 14д: {f['from']:+.2f} → p10 {f['p10']:+.2f} | p50 {f['p50']:+.2f} | p90 {f['p90']:+.2f}"
              + (f" | аналоги {f['analog_p50']:+.2f}" if f['analog_p50'] is not None else ""))
    n = out["nino34"]
    print("== Niño 3.4 аналоги на те же 30 дней:", {y: v["same30"] for y, v in n["analogs"].items()},
          "| текущие", n["current30"], "| место", n["rank_same30"])
    print("   оценка пика:", n["peak_estimate"])
    print("== NOAA неделя", out["noaa"]["date"], out["noaa"]["latest"], "| тип:", out["noaa"]["type"],
          "| pct Niño3.4:", out["noaa"]["n34_rank_pct"], "| ист. макс:", out["noaa"]["hist_max_n34"])
    print("== ONI", out["oni"]["year"], out["oni"]["current"], "| пики аналогов:", out["oni"]["analog_event_peak"])
    print("== РИСКИ, индекс", out["risk_index"])
    for r in out["risks"]:
        print(f"   [{r['level']}] {r['title']} — {r['horizon']}")
