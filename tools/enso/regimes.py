# -*- coding: utf-8 -*-
"""РЕЖИМЫ ЦИРКУЛЯЦИИ: как долго стоит картина давления и где стоят блокинги.

Владелец 25.09: «упорядоченность всей системы, когда погода застывает надолго — по давлению, не по
температуре, глобально, смена паттерна раз в неделю-две, циклон завис». Две операциональные меры
на поле геопотенциала 500 гПа (Северное полушарие, 2,5°, кэш regimes_fetch.py):

  · ВРЕМЯ ЖИЗНИ КАРТИНЫ. Аномалия поля к норме 1991–2020 на тот же день года; корреляция
    сегодняшней карты с картой k суток назад (по площади, 30–80°N); время жизни τ — первый лаг,
    на котором корреляция падает ниже 0,5: «через столько суток картина сменилась наполовину».
    Считается на каждый день; сравнивается с теми же днями года у прошлых лет.
  · БЛОКИНГ по Тибальди–Мольтени (1990): по каждой долготе градиенты Z500 между 40/60/80°N
    (с вариантами ±5°); долгота заблокирована, когда южный градиент положителен, а северный
    круче −10 м/градус. Доля заблокированных долгот в сутки, эпизоды ≥ 5 суток по секторам.

Шов источников: реанализ NCEP R1 до 17.03.2026, дальше анализы GFS 00Z. Обе меры считаются
внутри суток (корреляция карт, градиенты), поэтому к сдвигу уровней между источниками
чувствительны слабо; сравнение через шов помечено в паспорте.
"""
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio                      # noqa: E402
from numfmt import r2              # noqa: E402
from regimes_fetch import load_year, CACHE   # noqa: E402
from air import EVENT_YEARS, ANALOG_YEARS    # noqa: E402

OUT = ROOT / "data" / "enso" / "regimes.json"
CLIM = (1991, 2020)
LAT_BAND = (30.0, 80.0)
LAG_MAX = 20
R_HALF = 0.5
WIN = 90                    # окно сравнения с прошлыми годами
STRIP = 120                 # лента блокинга на сцене
MIN_EPISODE = 5

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _doy(iso):
    d = date.fromisoformat(iso)
    k = d.timetuple().tm_yday - 1
    return k if (k < 59 or d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0)) else k + 1   # сетка 366 как у панели


def load_all():
    years = sorted(int(p.stem) for p in CACHE.glob("*.npz") if p.stem.isdigit())
    days, src, H, S = [], [], [], []
    lat = lon = None
    for y in years:
        got = load_year(y)
        if not got or not got[0]:
            continue
        d, s, h, sl, lat, lon = got
        days += d; src += s; H.append(h); S.append(sl)
    if not H:
        raise SystemExit("кэш regimes пуст")
    return days, src, np.concatenate(H), np.concatenate(S), lat, lon


def climatology(days, H):
    """Норма по дню года (сетка 366), сглаженная ±7 суток по кругу, годы CLIM."""
    acc = np.zeros((366,) + H.shape[1:]); cnt = np.zeros(366)
    for i, d in enumerate(days):
        y = int(d[:4])
        if CLIM[0] <= y <= CLIM[1]:
            k = _doy(d); acc[k] += H[i]; cnt[k] += 1
    with np.errstate(all="ignore"):
        raw = acc / cnt[:, None, None]
    ok = cnt > 0
    raw[~ok] = np.nan
    sm = np.empty_like(raw)
    for k in range(366):
        idx = [(k + j) % 366 for j in range(-7, 8)]
        sm[k] = np.nanmean(raw[idx], axis=0)
    return sm


def lifetime(days, A, lat):
    """τ по дням: первый лаг, где корреляция аномалий с картой k суток назад < 0,5 (по площади)."""
    li = np.where((lat >= LAT_BAND[0]) & (lat <= LAT_BAND[1]))[0]
    w = np.cos(np.deg2rad(lat[li]))[:, None] * np.ones((1, A.shape[2]))
    w = w / w.sum()
    X = A[:, li, :]
    X = X - (X * w).sum(axis=(1, 2))[:, None, None]
    n = len(days)
    norm = np.sqrt((X * X * w).sum(axis=(1, 2)))
    tau = np.full(n, np.nan); r7 = np.full(n, np.nan)
    for t in range(LAG_MAX, n):
        if not np.isfinite(norm[t]) or norm[t] == 0:
            continue
        found = None; r_prev = 1.0
        for k in range(1, LAG_MAX + 1):
            if not np.isfinite(norm[t - k]) or norm[t - k] == 0:
                break
            r = (X[t] * X[t - k] * w).sum() / (norm[t] * norm[t - k])
            if k == 7:
                r7[t] = r
            if r < R_HALF:
                # точка пересечения 0,5 между лагами k−1 и k — линейно, чтобы τ была дробной и
                # годы различались (на целых лагах все годы давали 2,5)
                found = (k - 1) + (r_prev - R_HALF) / max(1e-9, r_prev - r)
                break
            r_prev = r
        tau[t] = found if found is not None else float(LAG_MAX)
    return tau, r7


def blocking(H, lat, lon):
    """Индекс Тибальди–Мольтени на каждый день и долготу: True — заблокирована."""
    def at(phi):
        return int(np.argmin(np.abs(lat - phi)))
    out = np.zeros((H.shape[0], H.shape[2]), bool)
    for dlt in (-5.0, 0.0, 5.0):
        s, c, nn = at(40 + dlt), at(60 + dlt), at(80 + dlt)
        ghgs = (H[:, c, :] - H[:, s, :]) / (lat[c] - lat[s])
        ghgn = (H[:, nn, :] - H[:, c, :]) / (lat[nn] - lat[c])
        out |= (ghgs > 0) & (ghgn < -10.0)
    return out


def episodes(days, B, lon, min_days=MIN_EPISODE):
    """Эпизоды: сектор из ≥3 соседних долгот, заблокированный ≥ min_days подряд (по последним STRIP суткам)."""
    n = B.shape[0]; a0 = max(0, n - STRIP)
    sect = np.zeros((n - a0, B.shape[1]), bool)
    for t in range(a0, n):
        row = B[t]
        for j in range(B.shape[1]):
            if row[j] and row[(j - 1) % B.shape[1]] and row[(j + 1) % B.shape[1]]:
                sect[t - a0, j] = True
    eps = []
    for j in range(B.shape[1]):
        run = 0; start = None
        for t in range(sect.shape[0]):
            if sect[t, j]:
                run += 1
                if run == 1:
                    start = t
            if (not sect[t, j] or t == sect.shape[0] - 1) and run >= min_days:
                end = t if sect[t, j] else t - 1
                eps.append({"lon": float(lon[j]), "start": days[a0 + start], "end": days[a0 + end], "days": run})
                run = 0
            elif not sect[t, j]:
                run = 0
    # сливаем соседние долготы с пересекающимися датами в сектора
    eps.sort(key=lambda e: (e["start"], e["lon"]))
    merged = []
    for e in eps:
        for m in merged:
            if abs(((e["lon"] - m["lon1"] + 180) % 360) - 180) <= 5.0 and not (e["end"] < m["start"] or e["start"] > m["end"]):
                m["lon1"] = e["lon"]; m["start"] = min(m["start"], e["start"]); m["end"] = max(m["end"], e["end"]); m["days"] = max(m["days"], e["days"])
                break
        else:
            merged.append({"lon0": e["lon"], "lon1": e["lon"], "start": e["start"], "end": e["end"], "days": e["days"]})
    merged.sort(key=lambda m: -m["days"])
    return merged[:12]


def lon_label(x):
    return f"{x:.0f}°E" if x <= 180 else f"{360 - x:.0f}°W"


def build(verbose=True):
    t0 = time.time()
    days, src, H, S, lat, lon = load_all()
    n = len(days)
    if verbose:
        print(f"кэш: {n} суток, {days[0]} … {days[-1]}, {H.shape[1]}×{H.shape[2]}")
    clim = climatology(days, H)
    A = H - clim[[_doy(d) for d in days]]
    tau, r7 = lifetime(days, A, lat)
    B = blocking(H, lat, lon)
    share = B.mean(axis=1)
    # скользящие 30 суток
    def roll(x, k=30):
        out = np.full(len(x), np.nan)
        for i in range(k - 1, len(x)):
            w = x[i - k + 1:i + 1]; w = w[np.isfinite(w)]
            if len(w) >= k * 0.7:
                out[i] = w.mean()
        return out
    tau30, share30 = roll(tau), roll(share)
    cy = int(days[-1][:4]); doy_last = _doy(days[-1])
    # окно WIN суток до того же дня года у каждого года: медиана τ и доля блокинга
    by_year = {}
    idx_by_year = {}
    for i, d in enumerate(days):
        idx_by_year.setdefault(int(d[:4]), []).append(i)
    for y, ids in idx_by_year.items():
        sel = [i for i in ids if 0 <= doy_last - _doy(days[i]) < WIN]
        if len(sel) >= WIN * 0.7:
            tv = tau[sel]; tv = tv[np.isfinite(tv)]
            by_year[str(y)] = {"tau_median": r2(float(np.median(tv)), 2) if len(tv) else None,
                               "tau_p90": r2(float(np.percentile(tv, 90)), 2) if len(tv) else None,
                               "block_share": r2(float(share[sel].mean()), 3),
                               "n": len(sel), "src": sorted(set(src[i] for i in sel))}
    now = by_year.get(str(cy)) or {}
    pool = [v["tau_median"] for y, v in by_year.items() if int(y) < cy and v["tau_median"] is not None]
    poolb = [v["block_share"] for y, v in by_year.items() if int(y) < cy]
    rank_tau = (1 + sum(1 for v in pool if v > now.get("tau_median", -1))) if now.get("tau_median") is not None else None
    rank_blk = (1 + sum(1 for v in poolb if v > now.get("block_share", -1))) if now.get("block_share") is not None else None
    # кривые по дню года для сравнения: τ30 этого года и каждого года (для переключателя)
    curves = {}
    for y, ids in idx_by_year.items():
        arr = [None] * 366
        for i in ids:
            v = tau30[i]
            if np.isfinite(v):
                arr[_doy(days[i])] = r2(float(v), 1)
        if sum(v is not None for v in arr) >= 100 or y == cy:
            curves[str(y)] = arr
    bcurves = {}
    for y, ids in idx_by_year.items():
        arr = [None] * 366
        for i in ids:
            v = share30[i]
            if np.isfinite(v):
                arr[_doy(days[i])] = r2(float(v), 3)
        if sum(v is not None for v in arr) >= 100 or y == cy:
            bcurves[str(y)] = arr
    # ПРОВЕРКА ШВА: на днях, где есть и R1, и GFS (январь–март текущего года), считаем τ и долю
    # блокинга на обоих источниках и пишем расхождение — чтобы сравнение «сейчас против прошлых
    # лет» не было сравнением GFS с реанализом.
    seam_check = None
    ov = CACHE / f"{cy}_gfs_overlap.npz"
    if ov.exists():
        try:
            z = np.load(ov); od = json.loads(str(z["days"])); Hg = z["hgt"].astype(float)
            idx = {d: i for i, d in enumerate(days)}
            keep = [k for k, d in enumerate(od) if d in idx and src[idx[d]] == "ncep_r1"]
            if len(keep) > LAG_MAX + 10:
                Ag = Hg[keep] - clim[[_doy(od[k]) for k in keep]]
                tg, _ = lifetime([od[k] for k in keep], Ag, lat)
                tr = np.array([tau[idx[od[k]]] for k in keep])
                Bg = blocking(Hg[keep], lat, lon).mean(axis=1); Br = np.array([share[idx[od[k]]] for k in keep])
                m = np.isfinite(tg) & np.isfinite(tr)
                seam_check = {"days": int(m.sum()), "tau_gfs": r2(float(np.median(tg[m])), 2), "tau_r1": r2(float(np.median(tr[m])), 2),
                              "tau_diff": r2(float(np.median(tg[m] - tr[m])), 2), "tau_corr": r2(float(np.corrcoef(tg[m], tr[m])[0, 1]), 2),
                              "block_gfs": r2(float(Bg.mean()), 3), "block_r1": r2(float(Br.mean()), 3)}
        except Exception as e:                                   # noqa: BLE001
            seam_check = {"error": str(e)[:120]}
    # поправка на шов: если окно «сейчас» целиком на GFS, даём и «в единицах реанализа»
    adj = None
    if seam_check and not seam_check.get("error") and now.get("tau_median") is not None and now.get("src") == ["gfs_anl"]:
        ta = now["tau_median"] - seam_check["tau_diff"]
        adj = {"tau_median": r2(float(ta), 2), "rank_tau_desc": 1 + sum(1 for v in pool if v > ta)}
    a0 = max(0, n - STRIP)
    strip = ["".join("1" if v else "0" for v in B[t]) for t in range(a0, n)]
    seam = next((days[i] for i in range(1, n) if src[i] != src[i - 1]), None)
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "first": days[0], "last": days[-1], "n_days": n,
           "sources": {"ncep_r1": sum(1 for s in src if s == "ncep_r1"), "gfs_anl": sum(1 for s in src if s == "gfs_anl"), "seam": seam},
           "clim_years": list(CLIM), "lat_band": list(LAT_BAND), "r_half": R_HALF, "lag_max": LAG_MAX, "window_days": WIN,
           "lifetime": {"dates": days[a0:], "tau": [None if not np.isfinite(v) else r2(float(v), 1) for v in tau[a0:]],
                        "tau30": [None if not np.isfinite(v) else r2(float(v), 1) for v in tau30[a0:]],
                        "r7": [None if not np.isfinite(v) else r2(float(v), 2) for v in r7[a0:]],
                        "now": now, "now_adjusted": adj, "rank_tau_desc": rank_tau, "of": len(pool) + 1, "median_years": r2(float(np.median(pool)), 1) if pool else None,
                        "by_year": by_year, "curves": curves},
           "blocking": {"dates": days[a0:], "lons": [float(v) for v in lon], "strip": strip,
                        "share": [r2(float(v), 3) for v in share[a0:]], "share30": [None if not np.isfinite(v) else r2(float(v), 3) for v in share30[a0:]],
                        "rank_share_desc": rank_blk, "of": len(poolb) + 1, "median_years": r2(float(np.median(poolb)), 3) if poolb else None,
                        "episodes": [dict(e, sector=lon_label(e["lon0"]) + "–" + lon_label(e["lon1"])) for e in episodes(days, B, lon)],
                        "curves": bcurves},
           "strong": list(ANALOG_YEARS), "events": list(EVENT_YEARS),
           "note": ("Two operational measures of how ‘stuck’ the northern hemisphere circulation is, on the daily 500 hPa height field "
                    "(2.5°, NCEP/NCAR reanalysis since 1948, GFS analyses after the reanalysis file ends). Pattern lifetime: the number of days "
                    "until today’s anomaly map correlates below 0.5 with itself — half the pattern has changed. Blocking: the Tibaldi–Moltemi "
                    "index, the share of longitudes where the flow is blocked. Both are compared with the same days of the year in every "
                    "year of the record; this is a description of the circulation, not a forecast."),
           "seam_check": seam_check,
           "warnings": {"seam": ("the record switches from the NCEP/NCAR reanalysis to GFS 00Z analyses on " + seam + "; both measures are computed within a day "
                                 "(map correlations, meridional gradients), so a level offset between the sources barely touches them, but the days across the "
                                 "seam are not one homogeneous series") if seam else None,
                        "resolution": "2.5° and one field per day: small or fast features are invisible by construction; the measures describe the large-scale flow"}}
    safeio.write_text(OUT, json.dumps(doc, ensure_ascii=False, allow_nan=False))
    if verbose:
        print(f"regimes.json: τ now {now.get('tau_median')} d (rank {rank_tau} of {len(pool) + 1}, median {doc['lifetime']['median_years']}), "
              f"blocked share {now.get('block_share')} (rank {rank_blk}), episodes {len(doc['blocking']['episodes'])}, "
              f"{OUT.stat().st_size // 1024} KB, {time.time() - t0:.0f} s")
    return doc


def main():
    build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
