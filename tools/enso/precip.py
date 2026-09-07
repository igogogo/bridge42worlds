# -*- coding: utf-8 -*-
"""Осадки: по регионам и в целом по планете (владелец 07.09: «нет источников по осадкам? бери всё что есть»).

ИСТОЧНИКИ.
1. ERA5 по дням через Open-Meteo (precipitation_sum), те же шесть боксов, что у температуры
   (spectral.REGIONS), сетка 3×3, вес cos(широты), с 1981 года. Склад data/enso/spectral/<ключ>-precip.json.
   Реанализ: в тропиках осадки смещены, но аномалии и сравнение годов держит.
2. GPCP v2.3 месячный (NOAA PSL, OPeNDAP, 2.5°, с 1979): среднее по планете и по тем же боксам.
   Единственный ряд с океаном — для вопроса «в целом выпало больше или меньше».
3. CHIRPS (UCSB) как второй источник по суше: пробуется через ClimateSERV; при отказе пропускается.

ЧТО СЧИТАЕТ. По каждому боксу: сумма за последние 30 и 90 дней против нормы того же
календарного окна 1991–2020, процентиль среди всех лет с 1981, те же окна в 1982/1997/2015/2023,
месячные суммы за 24 месяца с нормой (для столбиков). GPCP: месячный ряд планеты за 36 месяцев с
нормой и рангом последнего месяца; по боксам — последний месяц против нормы.

Выход: data/enso/precip.json. Ловушка Open-Meteo: большой запрос считается за много вызовов (429),
полная история тянется по точке с паузами, дальше только 90-дневный хвост одним запросом на бокс.
"""
import json
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spectral as SPX                                          # noqa: E402

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"
OUT = ROOT / "precip.json"
PCACHE = ROOT / "precip"
CLIM = (1991, 2020)
ANALOGS = [1982, 1997, 2015, 2023]
UA = {"User-Agent": "bridge42worlds enso"}
GPCP = "https://psl.noaa.gov/thredds/dodsC/Datasets/gpcp/precip.mon.mean.nc"


# ── ERA5 осадки по боксам ────────────────────────────────────────────────────────────────
def _om_points(box):
    la0, la1, lo0, lo1 = box
    G = SPX.GRID
    return [(la0 + (la1 - la0) * (i + .5) / G, lo0 + (lo1 - lo0) * (j + .5) / G) for i in range(G) for j in range(G)]


def _om_get(url, timeout=180):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _merge(acc, wsum, la, daily):
    w = float(np.cos(np.radians(la)))
    for t, v in zip(daily["time"], daily["precipitation_sum"]):
        if v is None:
            continue
        acc[t] = acc.get(t, 0.0) + w * v; wsum[t] = wsum.get(t, 0.0) + w


def fetch_box_precip(box, d0, d1, per_point=False, verbose=False):
    pts = _om_points(box)
    acc, wsum = {}, {}
    if not per_point:
        u = ("https://archive-api.open-meteo.com/v1/archive?latitude=" + ",".join(f"{p[0]:.3f}" for p in pts) +
             "&longitude=" + ",".join(f"{p[1]:.3f}" for p in pts) + f"&start_date={d0}&end_date={d1}&daily=precipitation_sum&timezone=UTC")
        res = _om_get(u)
        for (la, lo), one in zip(pts, [res] if isinstance(res, dict) else res):
            _merge(acc, wsum, la, one["daily"])
    else:
        for n, (la, lo) in enumerate(pts):
            u = f"https://archive-api.open-meteo.com/v1/archive?latitude={la:.3f}&longitude={lo:.3f}&start_date={d0}&end_date={d1}&daily=precipitation_sum&timezone=UTC"
            for attempt in range(6):
                try:
                    _merge(acc, wsum, la, _om_get(u)["daily"]); break
                except Exception as e:                           # noqa: BLE001
                    if verbose:
                        print(f"    point {n} attempt {attempt}: {str(e)[:40]}", flush=True)
                    time.sleep(90)
            time.sleep(8)
    return {t: round(acc[t] / wsum[t], 3) for t in acc if wsum[t] > 0}


def era5_box(key, box, verbose=False):
    SPX.RCACHE.mkdir(parents=True, exist_ok=True)
    p = SPX.RCACHE / f"{key}-precip.json"
    m = json.load(open(p, encoding="utf-8")) if p.exists() else {}
    today = date.today()
    if not m:
        m = fetch_box_precip(box, "1981-01-01", today.isoformat(), per_point=True, verbose=verbose)
    else:
        try:
            m.update(fetch_box_precip(box, (today - timedelta(days=90)).isoformat(), today.isoformat()))
        except Exception as e:                                   # noqa: BLE001
            if verbose:
                print(f"    tail: {str(e)[:60]}")
    if m:
        p.write_text(json.dumps(m), encoding="utf-8")
    return m


def _sum_window(m, end, days):
    vals = [m.get((end - timedelta(days=k)).isoformat()) for k in range(days)]
    vals = [v for v in vals if v is not None]
    return (sum(vals), len(vals)) if vals else (None, 0)


def box_stats(m):
    ks = sorted(m)
    end = date.fromisoformat(ks[-1])
    out = {"last_date": ks[-1]}
    for days in (30, 90):
        now, n = _sum_window(m, end, days)
        same = {}
        for y in range(1981, end.year):
            try:
                e = end.replace(year=y)
            except ValueError:
                e = end.replace(year=y, day=28)
            s, k = _sum_window(m, e, days)
            if k >= days - 3:
                same[y] = s
        clim = [same[y] for y in same if CLIM[0] <= y <= CLIM[1]]
        allv = list(same.values())
        out[f"sum{days}"] = {"now": None if now is None else round(now, 1), "days": n,
                             "normal": round(float(np.mean(clim)), 1) if clim else None,
                             "pct_of_normal": round(100 * now / np.mean(clim)) if (now is not None and clim and np.mean(clim) > 0) else None,
                             "rank_pct": round(100 * sum(1 for v in allv if v < now) / len(allv)) if (now is not None and allv) else None,
                             "of_years": len(allv),
                             "analogs": {str(y): round(same[y], 1) for y in ANALOGS if y in same}}
    # месячные суммы за 24 месяца с нормой
    months, normal = [], []
    y, mo = end.year, end.month
    for _ in range(24):
        pref = f"{y}-{mo:02d}"
        tot = sum(v for k, v in m.items() if k.startswith(pref))
        months.append({"ym": pref, "mm": round(tot, 1), "partial": (y == end.year and mo == end.month)})
        cl = [sum(v for k, v in m.items() if k.startswith(f"{yy}-{mo:02d}")) for yy in range(CLIM[0], CLIM[1] + 1)]
        normal.append(round(float(np.mean(cl)), 1))
        mo -= 1
        if mo == 0:
            mo = 12; y -= 1
    out["months"] = months[::-1]; out["months_normal"] = normal[::-1]
    return out


# ── GPCP месячный ─────────────────────────────────────────────────────────────────────────
def gpcp(boxes, verbose=False):
    PCACHE.mkdir(parents=True, exist_ok=True)
    p = PCACHE / "gpcp.json"
    try:
        import netCDF4
        ds = netCDF4.Dataset(GPCP)
        lat = np.array(ds["lat"][:], float); lon = np.array(ds["lon"][:], float)
        tm = ds["time"]; dates = netCDF4.num2date(tm[:], tm.units)
        # ЧИТАТЬ КУСКАМИ: запрос всего массива через OPeNDAP вернул сплошную маску (нули в среднем),
        # срезы по 60 месяцев приходят верно
        v = ds["precip"]; nt = v.shape[0]; parts = []
        for i0 in range(0, nt, 60):
            a = v[i0:min(nt, i0 + 60), :, :]
            parts.append(np.ma.filled(np.ma.masked_invalid(a), np.nan).astype(float))
        pr = np.concatenate(parts, axis=0)                          # (t, lat, lon) mm/day
        pr = np.where((pr < 0) | (pr > 100), np.nan, pr)
        ds.close()
        w = np.cos(np.radians(lat))[:, None] * np.ones((1, len(lon)))
        glob = [float(np.nansum(np.where(np.isfinite(a), a, 0) * w) / np.nansum(np.where(np.isfinite(a), w, 0))) for a in pr]
        ym = [f"{d.year}-{d.month:02d}" for d in dates]
        out = {"ym": ym, "global": [round(g, 3) for g in glob], "boxes": {}}
        for key, box in boxes.items():
            la0, la1, lo0, lo1 = box
            lo0 %= 360; lo1 %= 360
            mi = (lat >= la0) & (lat <= la1)
            mj = (lon >= lo0) & (lon <= lo1) if lo0 <= lo1 else ((lon >= lo0) | (lon <= lo1))
            if mi.sum() == 0 or mj.sum() == 0:
                # бокс меньше ячейки 2.5°: ближайшая ячейка
                mi = np.abs(lat - (la0 + la1) / 2) <= 1.3; mj = np.abs(lon - ((lo0 + lo1) / 2)) <= 1.3
            sub = pr[:, mi][:, :, mj]
            ww = np.cos(np.radians(lat[mi]))[:, None] * np.ones((1, int(mj.sum())))
            out["boxes"][key] = [round(float(np.nansum(np.where(np.isfinite(a), a, 0) * ww) / np.nansum(np.where(np.isfinite(a), ww, 0))), 3) for a in sub]
        p.write_text(json.dumps(out), encoding="utf-8")
        if verbose:
            print(f"  GPCP: {ym[0]}..{ym[-1]}, {len(ym)} months")
        return out, True
    except Exception as e:                                       # noqa: BLE001
        if verbose:
            print(f"  GPCP failed: {str(e)[:100]}")
        if p.exists():
            return json.load(open(p, encoding="utf-8")), False
        return None, False


def gpcp_stats(g, series, months_back=36):
    ym = g["ym"]; vals = series
    fin_idx = [i for i, v in enumerate(vals) if np.isfinite(v)]
    last = fin_idx[-1] if fin_idx else len(ym) - 1          # последний месяц бывает пустым (маска) — берём последний с числом
    lm = int(ym[last][5:7])
    same = [(int(ym[i][:4]), vals[i]) for i in range(len(ym)) if int(ym[i][5:7]) == lm and np.isfinite(vals[i])]
    clim = [v for y, v in same if CLIM[0] <= y <= CLIM[1]]
    allv = [v for y, v in same if y < int(ym[last][:4])]
    now = vals[last]
    normal = []
    for i in range(last - months_back + 1, last + 1):
        mo = int(ym[i][5:7])
        cl = [vals[j] for j in range(len(ym)) if int(ym[j][5:7]) == mo and CLIM[0] <= int(ym[j][:4]) <= CLIM[1]]
        normal.append(round(float(np.mean(cl)), 3) if cl else None)
    return {"last": ym[last], "now": round(now, 3), "normal": round(float(np.mean(clim)), 3) if clim else None,
            "pct_of_normal": round(100 * now / np.mean(clim)) if clim and np.mean(clim) > 0 else None,
            "rank_pct": round(100 * sum(1 for v in allv if v < now) / len(allv)) if allv else None, "of_years": len(allv),
            "analogs": {str(y): round(v, 3) for y, v in same if y in ANALOGS},
            "ym": ym[last - months_back + 1:], "values": [round(v, 3) for v in vals[last - months_back + 1:]], "normal_series": normal}


# ── CHIRPS (проба) ─────────────────────────────────────────────────────────────────────
def chirps_probe(verbose=False):
    """ClimateSERV отдаёт CHIRPS по полигону асинхронно; здесь только проверка доступности."""
    try:
        with urllib.request.urlopen(urllib.request.Request("https://climateserv.servirglobal.net/api/getDataSetList/", headers=UA), timeout=40) as r:
            txt = r.read().decode("utf-8", "replace")
        ok = "CHIRPS" in txt.upper()
        if verbose:
            print(f"  CHIRPS via ClimateSERV: {'reachable' if ok else 'list without CHIRPS'}")
        return ok
    except Exception as e:                                       # noqa: BLE001
        if verbose:
            print(f"  CHIRPS probe failed: {str(e)[:80]}")
        return False


def build(verbose=True):
    t0 = time.time()
    regions, errors = {}, []
    boxes = {}
    for key, label, box, rid in SPX.REGIONS:
        boxes[key] = box
        try:
            m = era5_box(key, box, verbose=verbose)
            if len(m) < 400:
                raise RuntimeError(f"only {len(m)} days")
            st = box_stats(m)
            st.update({"label": label.replace("2 m air", "precipitation").replace("ERA5 box mean", "ERA5 box sum"), "box": list(box), "region": rid})
            regions["land_" + key] = st
            if verbose:
                s30 = st["sum30"]
                print(f"  {key:<14} 30 d {s30['now']} mm vs normal {s30['normal']} ({s30['pct_of_normal']} %), rank {s30['rank_pct']} % of {s30['of_years']} yrs")
        except Exception as e:                                   # noqa: BLE001
            errors.append(f"{key}: {str(e)[:100]}")
            if verbose:
                print(f"  {key}: {str(e)[:100]}")
        time.sleep(3)
    g, fresh = gpcp(boxes, verbose=verbose)
    gl = None
    if g:
        gl = {"global": gpcp_stats(g, [np.nan if v is None else v for v in g["global"]]),
              "boxes": {("land_" + k): gpcp_stats(g, [np.nan if v is None else v for v in v_], months_back=24) for k, v_ in g["boxes"].items()},
              "fresh": fresh, "source": "GPCP v2.3 monthly, NOAA PSL OPeNDAP, 2.5°, mm/day"}
    chirps = chirps_probe(verbose=verbose)
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "regions": regions, "gpcp": gl, "chirps_reachable": chirps,
           "errors": errors, "secs": int(time.time() - t0),
           "note": ("Rain by region and for the planet. Regions: ERA5 daily precipitation summed over the box (Open-Meteo, "
                    "3×3 grid, cosine weights) since 1981, the last 30 and 90 days against the 1991–2020 normal of the same "
                    "calendar window and against every year since 1981; a reanalysis is biased in the tropics, so read the "
                    "percentages, not the millimetres. Planet: GPCP monthly (satellites and gauges, land and ocean) since 1979, "
                    "the only series that answers whether the world as a whole got more or less rain.")}
    OUT.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    if verbose:
        print(f"precip.json: {len(regions)} regions, GPCP {'ok' if gl else 'none'}, {doc['secs']} s")
    try:
        import ops as OPSLOG
        OPSLOG.record_run("precip", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ok" if not errors and gl else "partial",
                          note=f"{len(regions)} regions, GPCP {'ok' if gl else 'none'}" + ("; " + "; ".join(errors) if errors else ""))
    except Exception:                                            # noqa: BLE001
        pass
    return doc


if __name__ == "__main__":
    build()
