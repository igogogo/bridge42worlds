# -*- coding: utf-8 -*-
"""Детектор перелома: то, чего не было, — кричать; то, что меняет ход, — внимание.

Правила детерминированные и проверяемые: каждое сравнивает свежее число с потолком
ряда, с предыдущим снимком или с распределением того же сезона. Модель (summary.py)
получает эти срабатывания как факты и не имеет права их придумать сама.

Уровни (в данных латиницей — дашборд английский, владелец 03.09):
  SHOUT — случилось то, чего в данных не было никогда, или ход события развернулся
  WATCH — сильный сдвиг, который через неделю может стать переломом
"""
SHOUT, WATCH = "SHOUT", "WATCH"


def _lvl(alerts, level, title, detail, kind="climate"):
    alerts.append({"level": level, "title": title, "detail": detail, "kind": kind})


def detect(cur, prev=None):
    A = []
    W = cur["watch"]; N = cur["nino34"]; NW = cur["noaa"]
    n34, sw, tw = W["sst_nino34"], W["sst_world"], W["t2_world"]
    lat = NW["latest"]; hm = NW.get("hist_max", {})

    # ---- 1. выше всего измеренного
    if hm.get("n34a") is not None and lat["n34a"] > hm["n34a"]:
        _lvl(A, SHOUT, "Niño 3.4 is above anything measured since 1981",
             f"weekly index {lat['n34a']:+.1f} °C against the previous maximum {hm['n34a']:+.1f}")
    for k, name in (("n12a", "Niño 1+2"), ("n3a", "Niño 3"), ("n4a", "Niño 4")):
        if hm.get(k) is not None and lat[k] > hm[k]:
            _lvl(A, SHOUT, f"{name} is above anything measured",
                 f"{lat[k]:+.1f} °C against the previous maximum {hm[k]:+.1f}")
    pe = N["peak_estimate"]
    if N["current_day"] > pe["hist_ceiling"]:
        _lvl(A, SHOUT, "Daily Niño 3.4 broke the record of the series",
             f"{N['current_day']:+.2f} °C against a record of {pe['hist_ceiling']:+.2f}")
    # ускорение невиданное для сезона при уже высоком уровне
    for w, name in ((n34, "Niño 3.4"), (sw, "world ocean")):
        s = w["slope14"]
        if s["pct"] is not None and s["pct"] >= 98 and w["level30"]["rank_raw"] == 1:
            _lvl(A, SHOUT, f"{name}: 14-day rise faster than anything in the history of this season",
                 f"slope {s['now']:+.2f} °C, {s['pct']:.0f}th percentile, at a record level")

    # ---- 2. разворот хода события
    s = n34["slope14"]
    if s["prev"] is not None and s["prev"] > 0.15 and s["now"] < -0.05 and n34["level30"]["anom"] > 1.5:
        _lvl(A, SHOUT, "Niño 3.4 turned: rise became fall",
             f"14-day slope {s['prev']:+.2f} → {s['now']:+.2f} °C at a level of {n34['level30']['anom']:+.2f}")
    ser = NW["series"]
    if len(ser) >= 3:
        d2w = ser[-1]["n34a"] - ser[-3]["n34a"]
        if d2w <= -0.3 and ser[-3]["n34a"] >= 1.5:
            _lvl(A, SHOUT, "Weekly Niño 3.4 fell by 0.3 or more in two weeks",
                 f"{ser[-3]['n34a']:+.1f} → {ser[-1]['n34a']:+.1f} °C ({ser[-3]['date']} → {ser[-1]['date']})")
        elif d2w >= 0.4:
            _lvl(A, WATCH, "Weekly Niño 3.4 jumped by 0.4 or more in two weeks",
                 f"{ser[-3]['n34a']:+.1f} → {ser[-1]['n34a']:+.1f} °C")
        d12 = ser[-1]["n12a"] - ser[-3]["n12a"]
        if d12 <= -0.8:
            _lvl(A, WATCH, "Niño 1+2 is cooling fast: the coastal phase may be ending",
                 f"{ser[-3]['n12a']:+.1f} → {ser[-1]['n12a']:+.1f} °C in two weeks")
    # CUSUM отрицательный — режим отпустило
    for w, name in ((n34, "Niño 3.4"), (sw, "world ocean"), (tw, "land+ocean")):
        c = w["cusum"]
        if len(c["path"]) >= 30:
            tail = c["path"][-30:]
            if tail[-1] < tail[0] - 3 and w["level30"]["anom"] > 0.5:
                _lvl(A, WATCH, f"{name}: CUSUM turned down, the accumulated excess is deflating",
                     f"over 30 days {tail[0]:+.0f} → {tail[-1]:+.0f}")
    # серия рекордов оборвалась
    if prev:
        pW = prev["watch"]
        for k, name in (("sst_world", "world ocean"), ("sst_nino34", "Niño 3.4")):
            ps, cs = pW[k]["records"]["streak"], W[k]["records"]["streak"]
            if ps >= 20 and cs == 0:
                _lvl(A, WATCH, f"{name}: the run of daily records has ended",
                     f"was {ps} days, now 0: the first day below the historical maximum")
        pl = prev["noaa"]["latest"]
        if NW["date"] != prev["noaa"]["date"]:
            j = lat["n34a"] - pl["n34a"]
            if abs(j) >= 0.4:
                _lvl(A, WATCH if j > 0 else SHOUT,
                     f"Niño 3.4 moved by {j:+.1f} °C in one update",
                     f"{pl['n34a']:+.1f} ({prev['noaa']['date']}) → {lat['n34a']:+.1f} ({NW['date']})")

    # ---- 2б. модели прогноза против реальности (IRI)
    iri = cur.get("iri") or {}
    ao = iri.get("against_observed") if isinstance(iri, dict) else None
    if ao:
        if ao["reality_above_all"]:
            _lvl(A, SHOUT, "Reality has overtaken every forecast model",
                 f"weekly Niño 3.4 {ao['observed_weekly']:+.1f} °C is above the maximum of all {ao['n']} IRI models "
                 f"for {ao['season']} ({ao['max']:+.2f}); issue {iri.get('issued')}")
        elif ao["reality_above_mean_sd"]:
            _lvl(A, WATCH, "Reality is more than one spread above the model mean",
                 f"{ao['observed_weekly']:+.1f} °C against a mean of {ao['mean']:+.2f} ± {ao['sd']:.2f} over {ao['n']} models "
                 f"for {ao['season']}; {ao['share_below']} % of models are already below reality")
    if prev and isinstance(iri, dict) and iri.get("issued") and isinstance(prev.get("iri"), dict) \
            and prev["iri"].get("issued") and prev["iri"]["issued"] != iri["issued"]:
        rv = iri.get("revisions") or {}
        _lvl(A, WATCH, f"A new IRI forecast issue is out: {iri['issued']}",
             f"combined peak {rv.get('combined_peak_prev')} → {rv.get('combined_peak_cur')} °C; "
             f"{rv.get('n_up')} of {rv.get('n')} models raised their peak, {rv.get('n_down')} lowered it")

    # ---- 3. официальный порог
    oni = cur["oni"]; ls = oni["last_season"]; v = oni["current"].get(ls)
    if v is not None and v >= 2.0:
        prev_v = None
        if prev:
            prev_v = prev["oni"]["current"].get(prev["oni"]["last_season"])
        if prev_v is None or prev_v < 2.0:
            _lvl(A, SHOUT, "ONI crossed +2.0: officially a “very strong” event",
                 f"{ls} {v:+.2f}")

    # ---- 4. данные молчат
    for w in (n34, sw, tw):
        if w["days_stale"] > 21:
            _lvl(A, WATCH, f"A source is silent: {w['label']}",
                 f"last point {w['last_date']}, {w['days_stale']} days ago; the watchdog is blind on this series")

    shout = any(a["level"] == SHOUT for a in A)
    return A, shout
