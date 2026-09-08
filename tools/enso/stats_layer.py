# -*- coding: utf-8 -*-
"""Статистический слой панели El Niño (владелец 08.09: «статистический анализ нами, где это
возможно: кластеризация, регрессии, Байес — на каждый график, с пояснением, что за метод;
порождаем собственные KPI, цель — исследовать текущее явление, выявлять необычные тренды,
кластеры, закономерности; для рисков, для понимания, для самообучения»).

Считается офлайн по уже собранным рядам, без модели и без сети. Один прогон — секунды.
Выход: data/enso/stats.json — список «единиц» (item), у каждой сцена панели, где она
показывается, плашки KPI и описание метода простыми словами и технически. Панель кладёт
их за кнопку `stats ▾` в шапке сцены. Якорь `stat:<id>` — для понятий и чата.

Методы v1:
  trend        — линейная регрессия последних 90 и 30 дней с робастной ошибкой (Ньюи–Уэст),
                 байесовская вероятность роста при плоском априоре;
  changepoint  — точка смены режима (бинарная сегментация по сдвигу среднего), значимость
                 против AR(1)-шума;
  ar1          — инерция ряда AR(1): время памяти, прогноз «по инерции» на 14 и 30 дней с
                 интервалом; рядом прогноз по аналогам панели;
  clusters     — кластеризация лет по ходу Niño 3.4 январь–август (k-средних), где 2026;
                 ближайшие годы по расстоянию; согласие с каноническими аналогами;
  extremes     — эмпирический процентиль и период повторяемости текущего уровня (GEV);
  coherence    — корреляции суточных аномалий поясов и океана, иерархические группы;
                 сдвиг «тропический воздух за океаном» по кросс-корреляции;
  fuel_lead    — опережение объёма тёплой воды над Niño 3.4 (кросс-корреляция по месяцам);
  spectral     — сводка спектрального сторожа (линии 99 % против ожидаемых случайно).

Запуск: python stats_layer.py  (в обёртке после globe_data.py).
"""
import json
import math
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sources as S                                              # noqa: E402

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"
OUT = ROOT / "stats.json"
DAILY = {"sst_nino34": "Niño 3.4 (OISST)", "sst_world": "world ocean (OISST)", "t2_world": "land+ocean 2 m (ERA5)",
         "t2_nh": "northern hemisphere 2 m", "t2_sh": "southern hemisphere 2 m", "t2_tropics": "tropics 2 m",
         "t2_arctic": "Arctic 2 m", "t2_antarctic": "Antarctic 2 m"}
CANON = [1982, 1997, 2015, 2023]


# ------------------------------------------------------------------ ряды
def daily_anom(key):
    """Непрерывный суточный ряд аномалий к 1991–2020: (даты, значения), NaN выброшены."""
    p = S.LAST / f"{key}.json"
    if not p.exists():
        return None
    d = S.read_cr_json(p)
    clim = d.get("clim")
    dates, vals = [], []
    for y in sorted(d["years"]):
        arr = d["years"][y]
        for i, v in enumerate(arr):
            if not np.isfinite(v):
                continue
            c = clim[i] if clim is not None and i < len(clim) and np.isfinite(clim[i]) else np.nan
            if not np.isfinite(c):
                continue
            try:
                dt = S.grid_index_to_date(y, i)
            except Exception:                                    # noqa: BLE001
                continue
            if dt is None:
                continue
            dates.append(dt); vals.append(float(v - c))
    return np.array(dates), np.array(vals, float)


def tail(dates, vals, n):
    return dates[-n:], vals[-n:]


def fmt_date(d):
    return d.isoformat() if hasattr(d, "isoformat") else str(d)[:10]


# ------------------------------------------------------------------ методы
def ols_nw(y, lag=7):
    """Наклон на день, ошибка Ньюи–Уэста, t, p (нормальное приближение), CI 95 %."""
    n = len(y); x = np.arange(n, dtype=float); x -= x.mean()
    b = float((x * (y - y.mean())).sum() / (x * x).sum())
    a = float(y.mean())
    e = y - (a + b * x)
    sxx = float((x * x).sum())
    # HAC: сумма автоковариаций остатков с весами Бартлетта
    v = float((x * e * x * e).sum())
    for k in range(1, lag + 1):
        w = 1 - k / (lag + 1)
        v += 2 * w * float((x[k:] * e[k:] * x[:-k] * e[:-k]).sum())
    se = math.sqrt(max(v, 1e-12)) / sxx
    t = b / se if se > 0 else 0.0
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))
    p_up = 0.5 * (1 + math.erf(t / math.sqrt(2)))                 # байес при плоском априоре
    return {"slope_day": b, "se_day": se, "t": t, "p": p, "p_up": p_up, "ci_day": (b - 1.96 * se, b + 1.96 * se), "resid_sd": float(e.std())}


def trend_item(key, label, dates, vals, watch):
    if len(vals) < 100:
        return None
    d90, y90 = tail(dates, vals, 90); d30, y30 = tail(dates, vals, 30)
    r90, r30 = ols_nw(y90), ols_nw(y30)
    prev60 = ols_nw(vals[-90:-30]) if len(vals) >= 90 else None
    accel = r30["slope_day"] - (prev60["slope_day"] if prev60 else 0)
    s90, s30 = r90["slope_day"] * 30, r30["slope_day"] * 30
    ci90 = tuple(c * 30 for c in r90["ci_day"])
    kpis = [
        {"name": "trend, 90 days", "value": f"{s90:+.2f}", "unit": "°C per 30 d", "plain": f"Over the last 90 days the anomaly moved {s90:+.2f} °C per month on average; 95 % interval {ci90[0]:+.2f} … {ci90[1]:+.2f}."},
        {"name": "trend, 30 days", "value": f"{s30:+.2f}", "unit": "°C per 30 d", "plain": f"The last month alone: {s30:+.2f} °C per month, {'faster' if abs(s30) > abs(s90) else 'slower'} than the 90-day pace."},
        {"name": "probability of rising", "value": f"{r90['p_up'] * 100:.0f}", "unit": "%", "plain": f"With a flat prior, the chance that the true 90-day slope is positive is {r90['p_up'] * 100:.0f} % (p = {r90['p']:.3f} two-sided)."},
        {"name": "acceleration", "value": f"{accel * 30:+.2f}", "unit": "°C/30 d vs the prior 60 d", "plain": "Positive: the rise is speeding up; negative: it is slowing or turning."},
    ]
    verdict = ("rising" if r90["p_up"] > 0.975 else "falling" if r90["p_up"] < 0.025 else "no clear trend")
    fc = (watch or {}).get("forecast14") or {}
    return {"id": f"trend_{key}", "kind": "trend", "scene": f"trend/{key}" if key in ("sst_nino34", "sst_world", "t2_world") else "planet/temperature",
            "also": ["trend"] if key in ("sst_nino34", "sst_world", "t2_world") else ["planet"],
            "title": f"Trend of {label}: {verdict}", "series": key, "window": [fmt_date(d90[0]), fmt_date(d90[-1])],
            "kpis": kpis, "anchors": [f"stat:trend_{key}", "term:trend", "term:anomaly"],
            "method": {"name": "Linear regression with a robust (Newey–West) error",
                       "plain": "We draw the straight line that fits the last 90 days best and ask how sure we are of its slope. Daily values are not independent (warm days come in runs), so the ordinary error would be too optimistic; the Newey–West correction widens it honestly. The “probability of rising” is the Bayesian reading of the same numbers with no prior opinion.",
                       "tech": f"OLS on daily anomalies to 1991–2020, n = 90 and 30; HAC standard error with Bartlett weights, lag 7; two-sided p from the normal approximation; P(slope > 0) = Φ(t) under a flat prior. Residual sd {r90['resid_sd']:.2f} °C. Acceleration = slope(last 30) − slope(days −90…−30).",
                       "caveats": ["a 30-day slope is noisy: read it with its interval, not alone", "a trend says where the series went, not where it will go; the analogue forecast is a separate method"]},
            "compare": {"analog_forecast14": fc.get("value") if isinstance(fc, dict) else None}}


def changepoint_item(key, label, dates, vals):
    d, y = tail(dates, vals, 400)
    n = len(y)
    if n < 120:
        return None
    best, bt = 0.0, None
    cs = np.cumsum(y); tot = cs[-1]
    for t in range(30, n - 30):
        m1 = cs[t - 1] / t; m2 = (tot - cs[t - 1]) / (n - t)
        s = abs(m1 - m2) * math.sqrt(t * (n - t) / n)
        if s > best:
            best, bt = s, t
    sd = float(y.std()) or 1e-9
    stat = best / sd
    # нуль: AR(1) с тем же phi и sd — 300 симуляций, доля с большей статистикой
    phi = float(np.corrcoef(y[:-1], y[1:])[0, 1]) if n > 3 else 0.0
    phi = max(-0.99, min(0.99, phi))
    rng = np.random.default_rng(7)
    se = sd * math.sqrt(max(1e-6, 1 - phi * phi))
    hits = 0; sims = 300
    for _ in range(sims):
        z = np.empty(n); z[0] = rng.normal(0, sd)
        eps = rng.normal(0, se, n)
        for i in range(1, n):
            z[i] = phi * z[i - 1] + eps[i]
        czs = np.cumsum(z); tz = czs[-1]; b2 = 0.0
        for t in range(30, n - 30, 3):
            m1 = czs[t - 1] / t; m2 = (tz - czs[t - 1]) / (n - t)
            s = abs(m1 - m2) * math.sqrt(t * (n - t) / n)
            if s > b2:
                b2 = s
        if b2 / (z.std() or 1e-9) >= stat:
            hits += 1
    p = (hits + 1) / (sims + 1)
    before, after = float(y[:bt].mean()), float(y[bt:].mean())
    kpis = [
        {"name": "most likely break", "value": fmt_date(d[bt]), "unit": "", "plain": f"The day that best splits the last {n} days into “before” and “after”: mean {before:+.2f} °C before, {after:+.2f} °C after."},
        {"name": "shift of the mean", "value": f"{after - before:+.2f}", "unit": "°C", "plain": "How much the average level jumped at the break."},
        {"name": "chance it is noise", "value": f"{p * 100:.0f}", "unit": "%", "plain": f"Out of {sims} random series with the same memory and spread, {hits} produced a break at least this sharp. Small means the shift is real."},
    ]
    return {"id": f"break_{key}", "kind": "changepoint", "scene": f"trend/{key}" if key in ("sst_nino34", "sst_world", "t2_world") else "planet/temperature",
            "also": ["trend"] if key in ("sst_nino34", "sst_world", "t2_world") else ["planet"],
            "title": f"Regime shift in {label}: {fmt_date(d[bt])}, {after - before:+.2f} °C" + (" (significant)" if p < 0.05 else " (could be noise)"),
            "series": key, "window": [fmt_date(d[0]), fmt_date(d[-1])], "kpis": kpis, "anchors": [f"stat:break_{key}", "term:cusum", "term:anomaly"],
            "method": {"name": "Change-point by binary segmentation, tested against red noise",
                       "plain": "We try every day as a possible turning point and pick the one where the average before and after differ most. Then we ask whether a series with no real turn, only memory and noise, could show a jump this big by chance; if it rarely can, the shift is real.",
                       "tech": f"Single mean-shift change-point: max over t of |m₁−m₂|·√(t(n−t)/n)/sd, n = {n}. Null: AR(1) with fitted φ = {phi:.2f} and matched variance, {sims} simulations, p = share with a larger statistic. Multiple breaks are not modelled.",
                       "caveats": ["one break only: a series with several turns shows the biggest", "the break date is uncertain by days to weeks"]}}


def ar1_item(key, label, dates, vals, watch):
    d, y = tail(dates, vals, 400)
    n = len(y)
    if n < 60:
        return None
    phi = float(np.corrcoef(y[:-1], y[1:])[0, 1]); phi = max(-0.99, min(0.99, phi))
    e = y[1:] - phi * y[:-1]; se = float(e.std())
    tau = -1 / math.log(phi) if 0 < phi < 1 else float("nan")
    last = float(y[-1])
    def fc(h):
        m = last * phi ** h
        var = se * se * (1 - phi ** (2 * h)) / max(1e-9, 1 - phi * phi)
        return m, 1.28 * math.sqrt(var)
    m14, w14 = fc(14); m30, w30 = fc(30)
    an = (watch or {}).get("forecast14") or {}
    anv = an.get("value") if isinstance(an, dict) else None
    kpis = [
        {"name": "memory of the series", "value": f"{tau:.0f}" if np.isfinite(tau) else "·", "unit": "days", "plain": f"Day-to-day persistence φ = {phi:.2f}: a departure fades to a third in about {tau:.0f} days if nothing pushes it." if np.isfinite(tau) else "No positive persistence found."},
        {"name": "persistence forecast, +14 d", "value": f"{m14:+.2f}", "unit": "°C", "plain": f"If the series only had its memory, in two weeks it would sit at {m14:+.2f} °C (80 % band ±{w14:.2f})."},
        {"name": "persistence forecast, +30 d", "value": f"{m30:+.2f}", "unit": "°C", "plain": f"In a month: {m30:+.2f} °C (80 % band ±{w30:.2f}). The analogue forecast of the panel for +14 d is {anv:+.2f} °C." if isinstance(anv, (int, float)) else f"In a month: {m30:+.2f} °C (80 % band ±{w30:.2f})."},
    ]
    return {"id": f"ar1_{key}", "kind": "ar1", "scene": f"trend/{key}" if key in ("sst_nino34", "sst_world", "t2_world") else "planet/temperature",
            "also": ["trend"] if key in ("sst_nino34", "sst_world", "t2_world") else ["planet"],
            "title": f"Inertia of {label}: memory {tau:.0f} days, persistence says {m14:+.2f} °C in two weeks" if np.isfinite(tau) else f"Inertia of {label}",
            "series": key, "window": [fmt_date(d[0]), fmt_date(d[-1])], "kpis": kpis, "anchors": [f"stat:ar1_{key}", "term:analog", "term:anomaly"],
            "method": {"name": "AR(1) persistence model",
                       "plain": "The simplest forecast is “tomorrow looks like today, a little less so each day”. We measure how strongly each day follows the previous one and let that memory fade forward. It is the baseline any real forecast must beat; the analogue forecast on the panel is the other reading.",
                       "tech": f"AR(1) on daily anomalies, φ from lag-1 autocorrelation over n = {n}, innovation sd {se:.2f} °C; e-folding time −1/ln φ; h-step forecast x·φ^h with variance σ²(1−φ^{{2h}})/(1−φ²), 80 % band ±1.28σ_h. Mean reversion is to the 1991–2020 climatology, which is what makes this a floor, not a prediction, during an event.",
                       "caveats": ["during an El Niño the anomaly does not revert to zero on this timescale: persistence underestimates the coming months on purpose", "no seasonality, no forcing: a baseline only"]},
            "compare": {"analog_forecast14": anv}}


def clusters_item(psl):
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    years = sorted(y for y in psl if y >= 1950)
    cur = max(years)
    rows, ys = [], []
    for y in years:
        v = psl[y][:8]
        if all(np.isfinite(v)):
            rows.append(v); ys.append(y)
    if cur not in ys:
        return None
    X = np.array(rows); Xs = (X - X.mean(0)) / (X.std(0) + 1e-9)
    km = KMeans(n_clusters=4, n_init=10, random_state=0).fit(Xs)
    lab = km.labels_; sil = float(silhouette_score(Xs, lab))
    ci = int(lab[ys.index(cur)])
    members = [y for y, l in zip(ys, lab) if l == ci and y != cur]
    full = [y for y in members if all(np.isfinite(psl[y]))]
    peaks = [(int(np.nanargmax(psl[y])) + 1, float(np.nanmax(psl[y]))) for y in full]
    pk_month = int(round(np.mean([p[0] for p in peaks]))) if peaks else None
    pk_val = float(np.mean([p[1] for p in peaks])) if peaks else None
    # ближайшие годы по расстоянию январь–август
    xc = Xs[ys.index(cur)]
    dist = sorted(((float(np.linalg.norm(Xs[i] - xc)), y) for i, y in enumerate(ys) if y != cur))
    near = [y for _, y in dist[:6]]
    canon_same = [y for y in CANON if y in members]
    MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    kpis = [
        {"name": "cluster of 2026", "value": f"{len(members)}", "unit": "years like it", "plain": f"By the shape of January–August, {cur} sits with {', '.join(str(y) for y in members[-8:])}{'…' if len(members) > 8 else ''}."},
        {"name": "where that cluster peaks", "value": MON[pk_month - 1] if pk_month else "·", "unit": f"at {pk_val:+.2f} °C on average" if pk_val is not None else "", "plain": "Among the complete years of the cluster, the average month and height of the peak of Niño 3.4."},
        {"name": "nearest years", "value": ", ".join(str(y) for y in near[:5]), "unit": "", "plain": "The five years whose January–August path is closest to this one, by plain distance."},
        {"name": "canonical analogues in the cluster", "value": f"{len(canon_same)} of 4", "unit": "", "plain": f"Of the panel’s hand-picked analogues (1982, 1997, 2015, 2023), {', '.join(str(y) for y in canon_same) or 'none'} fall in the same statistical cluster."},
    ]
    return {"id": "clusters_nino34", "kind": "clusters", "scene": "now/analogs", "also": ["now"],
            "title": f"Years like {cur} by the January–August path: {len(members)} in the cluster, nearest {near[0]}, {near[1]}, {near[2]}",
            "series": "psl_nino34_monthly", "window": [f"{years[0]}-01", f"{cur}-08"], "kpis": kpis,
            "anchors": ["stat:clusters_nino34", "term:analog", "term:nino34", "block:peak"],
            "method": {"name": "k-means clustering of yearly trajectories",
                       "plain": "Every year since 1950 is a short line: the monthly Niño 3.4 anomaly from January to August. We let the computer sort those lines into four families by shape, with no names attached, and see which family this year lands in and what those years did next. It is a second opinion on the hand-picked analogues.",
                       "tech": f"Features: ERSST Niño 3.4 monthly anomalies Jan–Aug (8 dims, standardised), years 1950–{cur}; k-means, k = 4, 10 inits, seed 0; silhouette {sil:.2f}. Nearest years by Euclidean distance in the same space. Peak month and height from complete years of the cluster.",
                       "caveats": ["k = 4 is a choice, not a discovery; the silhouette is modest, so cluster edges are soft", "eight months of one index cannot see the subsurface, which is where events are decided"]},
            "members": members, "near": near, "silhouette": sil}


def extremes_item(psl):
    from scipy.stats import genextreme
    years = sorted(y for y in psl if y >= 1950)
    cur = max(years)
    ja = {y: float(np.nanmean(psl[y][6:8])) for y in years if np.isfinite(psl[y][6:8]).all()}
    if cur not in ja:
        return None
    v = ja[cur]
    others = [ja[y] for y in years if y != cur and y in ja]
    pct = 100 * sum(1 for x in others if x < v) / len(others)
    amax = [float(np.nanmax(psl[y])) for y in years if y != cur and np.isfinite(psl[y]).all()]
    c, loc, scale = genextreme.fit(amax)
    p_exceed = float(1 - genextreme.cdf(v, c, loc=loc, scale=scale))
    rp = 1 / p_exceed if p_exceed > 0 else float("inf")
    rec = max((ja[y], y) for y in years if y != cur and y in ja)
    kpis = [
        {"name": "July–August level", "value": f"{v:+.2f}", "unit": "°C", "plain": f"The mean of July and August {cur} in the monthly ERSST index."},
        {"name": "percentile among years", "value": f"{pct:.0f}", "unit": "%", "plain": f"Higher than {pct:.0f} % of all July–August values since 1950; the previous highest was {rec[1]} at {rec[0]:+.2f}."},
        {"name": "return period of this height as a yearly peak", "value": f"{rp:.0f}" if np.isfinite(rp) and rp < 1e4 else "·", "unit": "years", "plain": f"Fitting a distribution to the yearly maxima of the index, a peak of {v:+.2f} °C or more is expected about once in {rp:.0f} years — and this is only the summer value, before the usual winter peak." if np.isfinite(rp) and rp < 1e4 else "Outside what the fitted distribution can rate."},
    ]
    return {"id": "extremes_nino34", "kind": "extremes", "scene": "now/analogs", "also": ["now"],
            "title": f"How unusual: July–August {cur} at {v:+.2f} °C is the {pct:.0f}th percentile, a once-in-{rp:.0f}-years height for a yearly peak" if np.isfinite(rp) and rp < 1e4 else f"How unusual: July–August {cur} at {v:+.2f} °C, {pct:.0f}th percentile",
            "series": "psl_nino34_monthly", "window": [f"{years[0]}", f"{cur}"], "kpis": kpis,
            "anchors": ["stat:extremes_nino34", "term:rank", "term:percentile", "term:nino34"],
            "method": {"name": "Empirical percentile and a GEV return period",
                       "plain": "Two ways to say “how rare”: the plain count of past years below this level, and a fitted curve for yearly peaks (the generalised extreme-value distribution) that turns the height into “once in N years”. The curve is the standard tool for floods and heatwaves; here it rates an El Niño peak.",
                       "tech": f"ERSST Niño 3.4 monthly anomalies, 1950–{cur}. Percentile: share of years with a lower Jul–Aug mean. GEV fitted by maximum likelihood (scipy) to the annual maxima of the monthly index (n = {len(amax)}); return period 1/(1−F(v)). The fit treats years as independent and stationary, which warming makes only approximately true.",
                       "caveats": ["the summer value is compared with yearly peaks that usually come in winter: the true peak of this event is still ahead", "GEV on ~75 points has wide uncertainty above the record; treat the return period as an order of magnitude"]}}


def coherence_item(series):
    keys = [k for k in series if series[k] is not None]
    if len(keys) < 4:
        return None
    n = 120
    # общая сетка дат за последние 120 дней
    dmin = max(series[k][0][-n] for k in keys); dmax = min(series[k][0][-1] for k in keys)
    cols = {}
    for k in keys:
        d, v = series[k]
        m = (d >= dmin) & (d <= dmax)
        cols[k] = dict(zip([fmt_date(x) for x in d[m]], v[m]))
    days = sorted(set.intersection(*[set(c.keys()) for c in cols.values()]))
    if len(days) < 60:
        return None
    M = np.array([[cols[k][dd] for dd in days] for k in keys])
    M = M - M.mean(1, keepdims=True)
    C = np.corrcoef(M)
    from scipy.cluster.hierarchy import linkage, fcluster
    from scipy.spatial.distance import squareform
    D = 1 - C; np.fill_diagonal(D, 0); D = (D + D.T) / 2
    Z = linkage(squareform(D, checks=False), "average")
    lab = fcluster(Z, t=0.6, criterion="distance")
    groups = {}
    for k, l in zip(keys, lab):
        groups.setdefault(int(l), []).append(DAILY.get(k, k))
    pairs = sorted(((float(C[i, j]), keys[i], keys[j]) for i in range(len(keys)) for j in range(i + 1, len(keys))), reverse=True)
    top = pairs[0]; low = pairs[-1]
    # сдвиг: тропический воздух за Niño 3.4, ±45 дней, последние 400 дней
    lag_txt, best = "", None
    if series.get("sst_nino34") is not None and series.get("t2_tropics") is not None:
        a = dict(zip([fmt_date(x) for x in series["sst_nino34"][0]], series["sst_nino34"][1]))
        b = dict(zip([fmt_date(x) for x in series["t2_tropics"][0]], series["t2_tropics"][1]))
        common = sorted(set(a) & set(b))[-400:]
        xa = np.array([a[d] for d in common]); xb = np.array([b[d] for d in common])
        xa -= xa.mean(); xb -= xb.mean()
        best = (0, -2)
        for L in range(-45, 46):
            if L >= 0:
                r = np.corrcoef(xa[:len(xa) - L] if L else xa, xb[L:])[0, 1]
            else:
                r = np.corrcoef(xa[-L:], xb[:len(xb) + L])[0, 1]
            if r > best[1]:
                best = (L, float(r))
        lag_txt = f"the tropical air follows Niño 3.4 with a lag of about {best[0]} days (r = {best[1]:.2f})" if best[0] > 0 else f"the tropical air leads or moves with Niño 3.4 (best lag {best[0]} d, r = {best[1]:.2f})"
    kpis = [
        {"name": "groups moving together", "value": f"{len(groups)}", "unit": "", "plain": "; ".join(" + ".join(g) for g in groups.values())},
        {"name": "closest pair", "value": f"r {top[0]:.2f}", "unit": "", "plain": f"{DAILY.get(top[1])} and {DAILY.get(top[2])} rise and fall together over the last {len(days)} days."},
        {"name": "most independent pair", "value": f"r {low[0]:.2f}", "unit": "", "plain": f"{DAILY.get(low[1])} and {DAILY.get(low[2])} hardly share day-to-day moves."},
    ]
    if best:
        kpis.append({"name": "ocean → tropical air lag", "value": f"{best[0]}", "unit": "days", "plain": lag_txt})
    return {"id": "coherence_daily", "kind": "coherence", "scene": "planet/temperature", "also": ["planet", "trend"],
            "title": f"Who moves with whom: {len(groups)} groups among {len(keys)} daily series; " + (lag_txt if lag_txt else ""),
            "series": keys, "window": [days[0], days[-1]], "kpis": kpis,
            "anchors": ["stat:coherence_daily", "term:teleconnection", "term:anomaly"],
            "method": {"name": "Correlation matrix, hierarchical clustering and cross-correlation lag",
                       "plain": "We line up the daily anomalies of the ocean and of the air over the world, the hemispheres, the tropics and the poles over the same days and see which pairs breathe together. Then we group them by similarity and ask whether the tropical air trails the Pacific surface by some days.",
                       "tech": f"Pearson correlations of daily anomalies over {len(days)} common days; average-linkage hierarchical clustering on 1−r, cut at 0.6; lag by maximising the cross-correlation of Niño 3.4 against tropics 2 m over the last 400 days, ±45 days.",
                       "caveats": ["correlation over 120 days is dominated by the seasonal march and weather, not by El Niño alone", "a lag of days is not a mechanism; it says which series turns first"]},
            "groups": groups, "matrix": {"keys": keys, "r": [[round(float(x), 2) for x in row] for row in C]}}


def fuel_item(latest, psl):
    fuel = ((latest.get("air") or {}).get("fuel") or {}).get("series") or {}
    months, vals = fuel.get("months") or [], fuel.get("values") or []
    if len(months) < 24:
        return None
    x = []; y = []
    for m, v in zip(months, vals):
        yy, mm = int(m[:4]), int(m[5:7])
        if v is None or yy not in psl:
            continue
        x.append((yy, mm, float(v)))
    if len(x) < 24:
        return None
    def n34(yy, mm, lead):
        # Niño 3.4 через lead месяцев после (yy, mm)
        t = yy * 12 + (mm - 1) + lead; y2, m2 = divmod(t, 12)
        v = psl.get(y2, [np.nan] * 12)[m2] if y2 in psl else np.nan
        return v
    best = (0, -2.0, 0)
    for lead in range(0, 13):
        pairs = [(v, n34(yy, mm, lead)) for yy, mm, v in x]
        pairs = [(a, b) for a, b in pairs if np.isfinite(b)]
        if len(pairs) < 20:
            continue
        a = np.array([p[0] for p in pairs]); b = np.array([p[1] for p in pairs])
        r = float(np.corrcoef(a, b)[0, 1])
        if r > best[1]:
            best = (lead, r, len(pairs))
    lead, r, npairs = best
    # регрессия Niño 3.4(t+lead) на WWV(t)
    pairs = [(v, n34(yy, mm, lead)) for yy, mm, v in x]; pairs = [(a, b) for a, b in pairs if np.isfinite(b)]
    a = np.array([p[0] for p in pairs]); b = np.array([p[1] for p in pairs])
    A = np.vstack([a, np.ones_like(a)]).T
    coef, *_ = np.linalg.lstsq(A, b, rcond=None)
    last_v = x[-1][2]; proj = coef[0] * last_v + coef[1]
    kpis = [
        {"name": "best lead of the fuel", "value": f"{lead}", "unit": "months", "plain": f"The warm-water volume correlates most with Niño 3.4 {lead} months later (r = {r:.2f}, {npairs} months)."},
        {"name": "what the fuel implies", "value": f"{proj:+.2f}", "unit": f"°C in {lead} mo", "plain": f"A straight-line fit of Niño 3.4 on the fuel {lead} months earlier, applied to the latest fuel value {last_v:.2f}: {proj:+.2f} °C. A rough scale, not a forecast."},
    ]
    return {"id": "fuel_lead", "kind": "leadlag", "scene": "air", "also": ["now"],
            "title": f"The fuel leads the surface by {lead} months (r = {r:.2f}) in our own record",
            "series": "wwv vs psl_nino34_monthly", "window": [months[0], months[-1]], "kpis": kpis,
            "anchors": ["stat:fuel_lead", "term:wwv", "term:nino34", "block:peak"],
            "method": {"name": "Cross-correlation at monthly leads and a linear map",
                       "plain": "The recharge–discharge idea says the warm water stored below the equator feeds the surface months later. We check it on our own numbers: shift the fuel series forward month by month and see where it lines up best with Niño 3.4, then use that alignment as a crude ruler.",
                       "tech": f"Pearson r between PMEL warm water volume (monthly, {months[0]}…{months[-1]}) and ERSST Niño 3.4 at leads 0–12 months; best lead {lead}, r = {r:.2f}, n = {npairs}. Linear regression of Niño 3.4(t+{lead}) on WWV(t): slope {coef[0]:.2f} °C per unit, intercept {coef[1]:+.2f}.",
                       "caveats": ["the record here is short (a few years): the lead is indicative, the literature puts it at 6–9 months over decades", "the fit mixes the charge and discharge phases; during an event the relation flattens"]}}


def spectral_item():
    p = ROOT / "spectral.json"
    if not p.exists():
        return None
    sp = json.loads(p.read_text(encoding="utf-8"))
    now = sp.get("lines_99_now"); exp = sp.get("lines_99_expected_by_chance"); summ = sp.get("summary") or {}
    if isinstance(summ, str):
        summ = {"verdict": summ.split(".")[0][:60], "text": summ}
    kpis = [
        {"name": "lines at 99 % now", "value": f"{now}" if now is not None else "·", "unit": "", "plain": f"Across all daily series and periods 1–7 days, {now} spectral lines pass the 99 % level; by chance alone about {exp} would." if now is not None else ""},
        {"name": "verdict of the watch", "value": str(summ.get("verdict") or summ.get("state") or "·"), "unit": "", "plain": str(summ.get("text") or summ.get("note") or "")[:220]},
    ]
    return {"id": "spectral_watch", "kind": "spectral", "scene": "trend/spectral", "also": ["trend"],
            "title": f"Spectral watch: {now} lines at 99 % against {exp} expected by chance" if now is not None else "Spectral watch",
            "series": "all daily", "window": [str(sp.get("built") or "")[:10], ""], "kpis": kpis,
            "anchors": ["stat:spectral_watch", "term:spectral"],
            "method": {"name": "Periodogram against a red-noise background (already on the panel)",
                       "plain": "Each daily series is tested for a regular beat of one to seven days in a sliding 30-day window; a line counts only if it stands far above what a noisy series with memory would show. The count of such lines against the number expected by chance is the watch.",
                       "tech": "See Dynamics · Spectral watch: Lomb–Scargle power over AR(1) red-noise background, χ² thresholds at 95 % and 99 %, multiplicity-corrected expectation.",
                       "caveats": ["the owner’s hypothesis (a comb before a spontaneous transition) is being watched, not assumed"]}}


# ------------------------------------------------------------------ сборка
def build(verbose=True):
    t0 = time.time()
    latest = json.loads((ROOT / "latest.json").read_text(encoding="utf-8"))
    watch = latest.get("watch") or {}
    items, errors = [], []
    series = {}
    for key, label in DAILY.items():
        try:
            series[key] = daily_anom(key)
        except Exception as e:                                   # noqa: BLE001
            series[key] = None; errors.append(f"{key}: {str(e)[:100]}")
    for key, label in DAILY.items():
        s = series.get(key)
        if s is None:
            continue
        for fn in (trend_item, changepoint_item, ar1_item):
            try:
                it = fn(key, label, s[0], s[1], watch.get(key)) if fn is not changepoint_item else fn(key, label, s[0], s[1])
                if it:
                    items.append(it)
            except Exception as e:                               # noqa: BLE001
                errors.append(f"{fn.__name__} {key}: {str(e)[:100]}")
    psl = None
    try:
        psl = S.read_psl_monthly(S.LAST / "psl_nino34_monthly.txt")
    except Exception as e:                                       # noqa: BLE001
        errors.append(f"psl: {str(e)[:100]}")
    if psl:
        for fn in (clusters_item, extremes_item):
            try:
                it = fn(psl)
                if it:
                    items.append(it)
            except Exception as e:                               # noqa: BLE001
                errors.append(f"{fn.__name__}: {str(e)[:100]}")
        try:
            it = fuel_item(latest, psl)
            if it:
                items.append(it)
        except Exception as e:                                   # noqa: BLE001
            errors.append(f"fuel: {str(e)[:100]}")
    try:
        it = coherence_item(series)
        if it:
            items.append(it)
    except Exception as e:                                       # noqa: BLE001
        errors.append(f"coherence: {str(e)[:100]}")
    try:
        it = spectral_item()
        if it:
            items.append(it)
    except Exception as e:                                       # noqa: BLE001
        errors.append(f"spectral: {str(e)[:100]}")
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "n_items": len(items), "items": items, "errors": errors,
           "note": ("Our own statistics on the panel’s series: regression with robust errors, change-points against red noise, AR(1) persistence, "
                    "k-means clusters of years, extreme-value return periods, correlation groups, lead–lag of the fuel, the spectral watch. "
                    "Computed offline from the same data the charts show; no model. Each item names its method in plain words and technically, "
                    "with the caveats that apply."),
           "secs": round(time.time() - t0, 1)}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, allow_nan=False, default=str), encoding="utf-8")
    if verbose:
        print(f"stats.json: {len(items)} items, {OUT.stat().st_size // 1024} KB, {doc['secs']} s" + (f"; errors: {errors}" if errors else ""))
        for it in items:
            print("  ", it["scene"], "·", it["title"][:110])
    try:
        import ops as OPSLOG
        OPSLOG.record_run("stats", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ok" if not errors else "partial", note=f"{len(items)} items" + (f"; {len(errors)} errors" if errors else ""))
    except Exception:                                            # noqa: BLE001
        pass
    return doc


if __name__ == "__main__":
    build()
