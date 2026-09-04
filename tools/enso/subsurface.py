# -*- coding: utf-8 -*-
"""Под поверхностью: буи TAO по дням и разрез GODAS по месяцам.

ЗАЧЕМ. Эль-Ниньо живёт не на поверхности: тёплая вода копится под термоклином на западе и
идёт на восток волной Кельвина, а всплывает у Америки через месяцы. До 4 сентября панель
видела это одним числом — месячным объёмом тёплой воды с задержкой в полтора месяца.
Экспертиза 04.09 (п. 3.2): NOAA CPC пишет о подповерхностной аномалии до +10 °C, и её
надо показывать числом, а «расход топлива» — по неделям, не по месяцам.

ДВА ИСТОЧНИКА, ДВА ШАГА.
  · TAO/TRITON (PMEL, через ERDDAP CoastWatch) — буи на экваторе, температура по глубинам
    1–500 м КАЖДЫЙ ДЕНЬ. Аномалия у каждого буя — от его же собственной климатологии
    1991–2020 по дню года и глубине (строится один раз, кэш). Глубина изотермы 20 °C —
    классическая мера термоклина, климатологии не требует.
  · GODAS (NCEP, через OPeNDAP PSL) — океанский реанализ, потенциальная температура на
    сетке 1°×⅓°, 40 уровней, ПО МЕСЯЦАМ, отстаёт на полтора месяца. Даёт непрерывный разрез
    вдоль экватора там, где буёв нет, и индекс теплосодержания 0–300 м в полосе 180–100°W,
    который CPC называет «upper-ocean heat content».
Течения ADCP на буях Пацифики в 2026 году не передаются (проверено 04.09: данные есть
только у атлантических буёв) — прямого замера течений в открытом доступе сейчас нет.
"""
import json
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"
CACHE = ROOT / "subsurface"
E = "https://coastwatch.pfeg.noaa.gov/erddap/tabledap/pmelTaoDyT.csv"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

# станции на экваторе: имя → долгота в системе ERDDAP (0–360)
STATIONS = [("0n165e", 165), ("0n180w", 180), ("0n170w", 190), ("0n155w", 205),
            ("0n140w", 220), ("0n125w", 235), ("0n110w", 250), ("0n95w", 265)]
DEPTHS = [1, 5, 10, 20, 40, 60, 80, 100, 120, 140, 160, 180, 200, 250, 300]
CLIM_YEARS = (1991, 2020)
RECENT_DAYS = 75
GODAS = "https://psl.noaa.gov/thredds/dodsC/Datasets/godas/pottmp.{y}.nc"
GODAS_LON = (130, 280)         # 130°E … 80°W
GODAS_LAT = 2.0                # ±2° от экватора
GODAS_LEVELS = 26              # до ~300 м


def lon_label(lon360):
    lon = lon360 if lon360 <= 180 else lon360 - 360
    return f"{abs(lon):g}°{'E' if lon > 0 else 'W'}" if lon != 180 else "180°"


def _doy(d):
    import calendar
    doy = d.timetuple().tm_yday - 1
    return doy if calendar.isleap(d.year) or doy < 59 else doy + 1


def _load(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                            # noqa: BLE001
        return default


def _save(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------------------ TAO
def _tao_rows(lon, t0, t1=None):
    # Tomcat за ERDDAP отвергает сырые «>» и «<» в строке запроса (400 без текста): кодируем.
    q = (f"{E}?time,depth,T_20&longitude={lon}&latitude=0&time%3E%3D{t0}" + (f"&time%3C%3D{t1}" if t1 else ""))
    req = urllib.request.Request(q, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        txt = r.read().decode("utf-8", "replace")
    by = {}
    for ln in txt.splitlines()[2:]:
        p = ln.split(",")
        if len(p) < 3:
            continue
        try:
            dep, t = float(p[1]), float(p[2])
        except ValueError:
            continue
        if not np.isfinite(t) or dep > 320:
            continue
        by.setdefault(p[0][:10], {})[dep] = t
    return by


def _profile(prof):
    """Профиль на стандартных глубинах: линейная интерполяция только внутри измеренного."""
    ds = sorted(prof)
    if len(ds) < 4:
        return None
    xs, ys = np.array(ds, float), np.array([prof[d] for d in ds], float)
    out = np.full(len(DEPTHS), np.nan)
    for i, d in enumerate(DEPTHS):
        if xs[0] - 2 <= d <= xs[-1] + 2:
            out[i] = np.interp(d, xs, ys)
    return out


def d20(profile):
    """Глубина изотермы 20 °C, м; None — если по всему профилю теплее (или холоднее)."""
    if profile is None:
        return None
    for i in range(1, len(DEPTHS)):
        a, b = profile[i - 1], profile[i]
        if np.isfinite(a) and np.isfinite(b) and a >= 20 > b:
            return round(DEPTHS[i - 1] + (a - 20) / (a - b) * (DEPTHS[i] - DEPTHS[i - 1]), 1)
    return None


def build_analogs_tao(name, lon, verbose=False):
    """D20 буя по дням года каждого сильного события (у TAO история с 1990-х: 1997, 2015, 2023)."""
    p = CACHE / f"analogs_{name}.json"
    cl = _load(p, {})
    for y in ANALOG_YEARS:
        if str(y) in cl or y < 1990:
            continue
        try:
            rows = _tao_rows(lon, f"{y}-01-01", f"{y}-12-31")
        except Exception as e:                                   # noqa: BLE001
            if verbose:
                print(f"  {name} {y}: {str(e)[:80]}")
            continue
        arr = [None] * 366
        for dt, prof in rows.items():
            pr = _profile(prof)
            if pr is not None:
                arr[_doy(date.fromisoformat(dt))] = d20(pr)
        if any(v is not None for v in arr):
            cl[str(y)] = arr
        if verbose:
            print(f"  {name} {y}: D20 на {sum(1 for v in arr if v is not None)} днях")
    _save(p, cl)
    return cl


def build_clim_tao(name, lon, verbose=False):
    p = CACHE / f"clim_{name}.json"
    cl = _load(p, {})
    if cl.get("clim"):
        return cl
    sums = np.zeros((366, len(DEPTHS)))
    cnts = np.zeros((366, len(DEPTHS)))
    for y in range(CLIM_YEARS[0], CLIM_YEARS[1] + 1):
        t0 = time.time()
        try:
            rows = _tao_rows(lon, f"{y}-01-01", f"{y}-12-31")
        except Exception as e:                                   # noqa: BLE001
            if verbose:
                print(f"  {name} {y}: {str(e)[:80]}")
            continue
        for dt, prof in rows.items():
            pr = _profile(prof)
            if pr is None:
                continue
            i = _doy(date.fromisoformat(dt))
            ok = np.isfinite(pr)
            sums[i, ok] += pr[ok]
            cnts[i, ok] += 1
        if verbose:
            print(f"  {name} {y}: {len(rows)} дней, {time.time() - t0:.0f} с")
    if cnts.max() == 0:
        return cl
    mean = np.where(cnts > 0, sums / np.maximum(cnts, 1), np.nan)
    # 31-дневное круговое сглаживание по дню года — буи с пропусками, иначе шумно
    k = 31
    ext = np.concatenate([mean[-k:], mean, mean[:k]], axis=0)
    sm = np.full_like(mean, np.nan)
    for i in range(366):
        blk = ext[i:i + k]
        with np.errstate(all="ignore"):
            sm[i] = np.nanmean(blk, axis=0)
    cl = {"depths": DEPTHS, "clim": [[None if not np.isfinite(v) else round(float(v), 3) for v in row] for row in sm],
          "n_days": int((cnts.sum(axis=1) > 0).sum()), "years": list(CLIM_YEARS), "smooth_days": k,
          "built": datetime.now().strftime("%Y-%m-%d %H:%M")}
    _save(p, cl)
    return cl


def tao(today=None, verbose=False):
    """Все станции: свежие профили, аномалии, D20, разрез."""
    today = today or date.today()
    t0 = (today - timedelta(days=RECENT_DAYS)).isoformat()
    st_out, section = [], {"lons": [], "labels": [], "anom": [], "temp": []}
    for name, lon in STATIONS:
        cl = _load(CACHE / f"clim_{name}.json", {})
        try:
            rows = _tao_rows(lon, t0)
        except Exception as e:                                   # noqa: BLE001
            st_out.append({"name": name, "lon": lon, "label": lon_label(lon), "error": str(e)[:120]})
            continue
        days = sorted(rows)
        profs = {d: _profile(rows[d]) for d in days}
        profs = {d: p for d, p in profs.items() if p is not None}
        if not profs:
            st_out.append({"name": name, "lon": lon, "label": lon_label(lon), "error": "no profiles in the window"})
            continue
        days = sorted(profs)
        last = days[-1]
        # последние пять дней — среднее, буй шумит по дням
        recent = [profs[d] for d in days[-5:]]
        with np.errstate(all="ignore"):
            pr = np.nanmean(np.array(recent), axis=0)
        clim = cl.get("clim")
        an = None
        if clim:
            c = np.array([[np.nan if v is None else v for v in row] for row in clim], float)
            idx = [_doy(date.fromisoformat(d)) for d in days[-5:]]
            with np.errstate(all="ignore"):
                cm = np.nanmean(c[idx], axis=0)
            an = pr - cm
        # D20 сейчас и 30 дней назад
        d_now = d20(pr)
        back = [d for d in days if d <= (date.fromisoformat(last) - timedelta(days=30)).isoformat()]
        d_back = d20(profs[back[-1]]) if back else None
        # ход D20 по дням для графика
        d20_series = [(d, d20(profs[d])) for d in days]
        an_d20 = _load(CACHE / f"analogs_{name}.json", {})
        d20_an = {}
        for y, arr in an_d20.items():
            vals = [arr[_doy(date.fromisoformat(d))] for d in days]
            if any(v is not None for v in vals):
                d20_an[y] = vals
        rec = {"name": name, "lon": lon, "label": lon_label(lon), "last_date": last,
               "days_stale": (today - date.fromisoformat(last)).days,
               "depths": DEPTHS,
               "temp": [None if not np.isfinite(v) else round(float(v), 2) for v in pr],
               "anom": None if an is None else [None if not np.isfinite(v) else round(float(v), 2) for v in an],
               "d20": d_now, "d20_30d_ago": d_back,
               "d20_series": {"dates": [x[0] for x in d20_series], "values": [x[1] for x in d20_series], "analogs": d20_an},
               "has_clim": bool(clim)}
        if an is not None and np.isfinite(an).any():
            j = int(np.nanargmax(np.abs(np.where(np.isfinite(an), an, 0))))
            rec["max_anom"] = {"value": round(float(an[j]), 2), "depth": DEPTHS[j]}
            # и отдельно самый тёплый слой — что именно всплывает
            jw = int(np.nanargmax(np.where(np.isfinite(an), an, -99)))
            rec["warmest_anom"] = {"value": round(float(an[jw]), 2), "depth": DEPTHS[jw]}
        st_out.append(rec)
        section["lons"].append(lon); section["labels"].append(lon_label(lon))
        section["anom"].append(rec["anom"]); section["temp"].append(rec["temp"])
        if verbose:
            print(f"  {name}: до {last}, D20 {d_now} м (было {d_back}), max anom {rec.get('warmest_anom')}")
    good = [s for s in st_out if s.get("anom")]
    out = {"stations": st_out, "section": section, "depths": DEPTHS,
           "n_live": len([s for s in st_out if not s.get("error")]),
           "source": "TAO/TRITON moorings (NOAA PMEL) via CoastWatch ERDDAP, daily temperature by depth",
           "clim": f"own {CLIM_YEARS[0]}–{CLIM_YEARS[1]} climatology per mooring, by day of year and depth, 31-day smoothing",
           "note": ("Each mooring reports temperature at a dozen depths every day. The anomaly is against "
                    "that mooring's own thirty-year record for the same days of the year, so gaps in the "
                    "record widen the uncertainty but do not bias it. The 20 °C isotherm marks the "
                    "thermocline: deeper in the east means the warm layer has arrived there.")}
    if good:
        best = max(good, key=lambda s: (s.get("warmest_anom") or {}).get("value") or -99)
        out["warmest"] = {"station": best["label"], **best["warmest_anom"], "date": best["last_date"]}
        east = [s for s in good if s["lon"] >= 235 and s.get("d20") is not None]
        west = [s for s in good if s["lon"] <= 190 and s.get("d20") is not None]
        out["d20_east"] = round(float(np.mean([s["d20"] for s in east])), 1) if east else None
        out["d20_west"] = round(float(np.mean([s["d20"] for s in west])), 1) if west else None
        out["last_date"] = max(s["last_date"] for s in good)
    return out


# ------------------------------------------------------------------ GODAS
def _godas_open(y):
    import netCDF4
    return netCDF4.Dataset(GODAS.format(y=y))


def _godas_index(ds):
    lat = np.array(ds["lat"][:], float); lon = np.array(ds["lon"][:], float)
    li = np.where(np.abs(lat) <= GODAS_LAT + 1e-6)[0]
    oi = np.where((lon >= GODAS_LON[0]) & (lon <= GODAS_LON[1]))[0]
    return li, oi, lat[li], lon[oi], np.array(ds["level"][:GODAS_LEVELS], float)


def _godas_year(y):
    """Разрез по месяцам года: (месяцы, уровни, долготы) в °C — среднее по ±2° широты."""
    ds = _godas_open(y)
    try:
        li, oi, lat, lon, lev = _godas_index(ds)
        v = ds["pottmp"][:, :GODAS_LEVELS, li[0]:li[-1] + 1, oi[0]:oi[-1] + 1]
        arr = np.ma.filled(np.ma.masked_invalid(v), np.nan).astype(float) - 273.15
        with np.errstate(all="ignore"):
            sec = np.nanmean(arr, axis=2)                     # (t, lev, lon)
        tm = ds["time"]
        import netCDF4
        months = [x.month for x in netCDF4.num2date(tm[:], tm.units)]
    finally:
        ds.close()
    return months, lev, lon, sec


def build_clim_godas(verbose=False):
    p = CACHE / "clim_godas.json"
    cl = _load(p, {})
    if cl.get("clim"):
        return cl
    sums = cnts = None
    lev = lon = None
    for y in range(CLIM_YEARS[0], CLIM_YEARS[1] + 1):
        t0 = time.time()
        try:
            months, lev, lon, sec = _godas_year(y)
        except Exception as e:                                   # noqa: BLE001
            if verbose:
                print(f"  GODAS {y}: {str(e)[:80]}")
            continue
        if sums is None:
            sums = np.zeros((12,) + sec.shape[1:]); cnts = np.zeros((12,) + sec.shape[1:])
        for k, m in enumerate(months):
            ok = np.isfinite(sec[k])
            sums[m - 1][ok] += sec[k][ok]; cnts[m - 1][ok] += 1
        if verbose:
            print(f"  GODAS {y}: {len(months)} мес, {time.time() - t0:.0f} с")
    if sums is None:
        return cl
    mean = np.where(cnts > 0, sums / np.maximum(cnts, 1), np.nan)
    cl = {"levels": [float(x) for x in lev], "lons": [float(x) for x in lon],
          "clim": [[[None if not np.isfinite(v) else round(float(v), 3) for v in row] for row in mm] for mm in mean],
          "years": list(CLIM_YEARS), "built": datetime.now().strftime("%Y-%m-%d %H:%M")}
    _save(p, cl)
    return cl


ANALOG_YEARS = (1982, 1997, 2015, 2023)


def build_analogs_godas(verbose=False):
    """Индекс тепла 0–300 м (180–100°W) по месяцам года каждого сильного события — один раз."""
    p = CACHE / "analogs_godas.json"
    cl = _load(p, {})
    clim = _load(CACHE / "clim_godas.json", {})
    if not clim.get("clim"):
        return cl
    C = np.array([[[np.nan if v is None else v for v in row] for row in mm] for mm in clim["clim"]], float)
    lev = np.array(clim["levels"]); lon = np.array(clim["lons"])
    thick = np.diff(np.concatenate([[0.0], (lev[:-1] + lev[1:]) / 2, [lev[-1] + (lev[-1] - lev[-2]) / 2]]))
    band = (lon >= 180) & (lon <= 260)
    for y in ANALOG_YEARS:
        if str(y) in cl:
            continue
        try:
            months, lv, ln, sec = _godas_year(y)
        except Exception as e:                                   # noqa: BLE001
            if verbose:
                print(f"  GODAS {y}: {str(e)[:80]}")
            continue
        hc = {}
        for k, m in enumerate(months):
            a = sec[k] - C[m - 1]
            col = a[:, band]
            with np.errstate(all="ignore"):
                w = np.where(np.isfinite(col), thick[:, None], 0.0)
                v = np.nansum(np.where(np.isfinite(col), col, 0.0) * w) / max(w.sum(), 1e-9)
            hc[f"{m:02d}"] = round(float(v), 3)
        cl[str(y)] = hc
        if verbose:
            print(f"  GODAS {y}: {len(hc)} мес")
    _save(p, cl)
    return cl


def _d20_by_lon(sec, lev):
    out = []
    for j in range(sec.shape[1]):
        col = sec[:, j]
        d = None
        for i in range(1, len(lev)):
            a, b = col[i - 1], col[i]
            if np.isfinite(a) and np.isfinite(b) and a >= 20 > b:
                d = float(lev[i - 1] + (a - 20) / (a - b) * (lev[i] - lev[i - 1]))
                break
        out.append(None if d is None else round(d, 1))
    return out


def godas(today=None, verbose=False):
    """Последний месяц реанализа: аномалия разреза, её максимум, индекс теплосодержания."""
    today = today or date.today()
    cl = _load(CACHE / "clim_godas.json", {})
    years, months_all, secs = [], [], []
    for y in (today.year - 1, today.year):
        try:
            months, lev, lon, sec = _godas_year(y)
        except Exception as e:                                   # noqa: BLE001
            if verbose:
                print(f"  GODAS {y}: {str(e)[:80]}")
            continue
        for k, m in enumerate(months):
            years.append(y); months_all.append(m); secs.append(sec[k])
    if not secs:
        return {"error": "GODAS did not answer"}
    lev = np.array(lev); lon = np.array(lon)
    clim = None
    if cl.get("clim"):
        clim = np.array([[[np.nan if v is None else v for v in row] for row in mm] for mm in cl["clim"]], float)
    last = secs[-1]; ym = f"{years[-1]}-{months_all[-1]:02d}"
    out = {"month": ym, "levels": [float(x) for x in lev], "lons": [float(x) for x in lon],
           "labels": [lon_label(x) for x in lon],
           "temp": [[None if not np.isfinite(v) else round(float(v), 2) for v in row] for row in last],
           "d20": _d20_by_lon(last, lev), "has_clim": clim is not None,
           "source": "GODAS ocean reanalysis (NCEP) via NOAA PSL OPeNDAP, monthly, potential temperature",
           "clim": f"own {CLIM_YEARS[0]}–{CLIM_YEARS[1]} monthly climatology on the same grid",
           "note": ("A reanalysis is a model that assimilates the moorings, Argo floats and satellites into "
                    "one continuous field. It lags about six weeks and smooths the extremes; the moorings "
                    "above are the raw measurement, this is the filled-in picture between them.")}
    if clim is not None:
        an = last - clim[months_all[-1] - 1]
        out["anom"] = [[None if not np.isfinite(v) else round(float(v), 2) for v in row] for row in an]
        if np.isfinite(an).any():
            i, j = np.unravel_index(int(np.nanargmax(np.where(np.isfinite(an), an, -99))), an.shape)
            out["max_anom"] = {"value": round(float(an[i, j]), 2), "depth": float(lev[i]), "lon": float(lon[j]),
                               "label": lon_label(float(lon[j]))}
        out["d20_clim"] = _d20_by_lon(clim[months_all[-1] - 1], lev)
        # индекс теплосодержания 0–300 м, 180–100°W: среднее аномалии по глубине (вес — толщина слоя)
        thick = np.diff(np.concatenate([[0.0], (lev[:-1] + lev[1:]) / 2, [lev[-1] + (lev[-1] - lev[-2]) / 2]]))
        band = (lon >= 180) & (lon <= 260)
        hc = []
        for k in range(len(secs)):
            a = secs[k] - clim[months_all[k] - 1]
            col = a[:, band]
            with np.errstate(all="ignore"):
                w = np.where(np.isfinite(col), thick[:, None], 0.0)
                v = np.nansum(np.where(np.isfinite(col), col, 0.0) * w) / max(w.sum(), 1e-9)
            hc.append(round(float(v), 3))
        an = _load(CACHE / "analogs_godas.json", {})
        mm_last = f"{months_all[-1]:02d}"
        out["heat_content"] = {"months": [f"{y}-{m:02d}" for y, m in zip(years, months_all)], "values": hc,
                               "unit": "°C", "band": "0–300 m, 180–100°W",
                               "levels": {y: v.get(mm_last) for y, v in an.items() if v.get(mm_last) is not None},
                               "note": "mean temperature anomaly of the upper 300 m across the central and eastern equatorial Pacific — the CPC upper-ocean heat content index, recomputed on our climatology"}
    return out


def risks(SUB):
    """Правила по глубине — в формате air.risks: (заголовок, уровень, горизонт, что видно,
    что значит, за чем следить, ряд, вид, имя)."""
    out = []
    t = (SUB or {}).get("tao") or {}
    w = t.get("warmest") or {}
    if w.get("value") is not None and w["value"] >= 3.0:
        lvl = 5 if w["value"] >= 8 else (4 if w["value"] >= 5 else 3)
        de, dw = t.get("d20_east"), t.get("d20_west")
        out.append((
            f"Water {w['value']:+.1f} °C above normal is sitting at {w['depth']} m under {w['station']}", lvl, "1–3 months",
            f"TAO mooring {w['station']}, five-day mean to {w.get('date')}, against the mooring's own 1991–2020 record. "
            f"The 20 °C isotherm is at {dw} m in the west and {de} m in the east"
            + (" — deeper in the east than in the west, the reversed slope of a mature event." if de and dw and de > dw else "."),
            "This is the heat that has not surfaced yet. It is measured directly, every day, and it is what makes "
            "'the event has room to grow' a statement about the present rather than about the past events.",
            "the warm anomaly moving east along the moorings and rising toward the surface; the east D20 shallowing again would mean the wave has passed",
            {"name": f"20 °C isotherm depth, {w['station']}", "unit": "m", "step": "day",
             "dates": next((s["d20_series"]["dates"] for s in t.get("stations", []) if s.get("label") == w["station"]), None),
             "values": next((s["d20_series"]["values"] for s in t.get("stations", []) if s.get("label") == w["station"]), None),
             "analogs": next((s["d20_series"].get("analogs") or {} for s in t.get("stations", []) if s.get("label") == w["station"]), {})},
            "climate", "subsurface_warm"))
    g = (SUB or {}).get("godas") or {}
    hc = (g.get("heat_content") or {}).get("values") or []
    if hc and hc[-1] >= 1.0:
        out.append((
            f"The upper 300 m of the central and eastern Pacific hold {hc[-1]:+.2f} °C of extra heat", 4, "1–3 months",
            f"GODAS reanalysis, {g.get('month')}: mean temperature anomaly of 0–300 m across 180–100°W, our climatology; "
            f"the reanalysis' warmest point is {(g.get('max_anom') or {}).get('value')} °C at {(g.get('max_anom') or {}).get('depth')} m, {(g.get('max_anom') or {}).get('label')}.",
            "The CPC calls this the upper-ocean heat content index and watches it as the leading sign of where the "
            "surface goes next. A whole degree across that band is a large charge.",
            "the index in the next monthly GODAS; the moorings above show it a month earlier",
            {"name": "Upper-ocean heat content, 0–300 m, 180–100°W", "unit": "°C", "step": "month",
             "dates": (g.get("heat_content") or {}).get("months"), "values": hc,
             "levels": (g.get("heat_content") or {}).get("levels") or {}},
            "climate", "heat_content_300"))
    return out


if __name__ == "__main__":
    import sys
    if "--clim" in sys.argv:
        for nm, ln in STATIONS:
            print("климатология TAO", nm)
            build_clim_tao(nm, ln, verbose=True)
            build_analogs_tao(nm, ln, verbose=True)
        print("климатология GODAS")
        build_clim_godas(verbose=True)
        build_analogs_godas(verbose=True)
        print("готово")
    else:
        t = tao(verbose=True)
        print("буи живы:", t["n_live"], "| теплее всего:", t.get("warmest"), "| D20 запад/восток:", t.get("d20_west"), t.get("d20_east"))
        g = godas(verbose=True)
        print("GODAS:", g.get("month"), "| max anom:", g.get("max_anom"), "| HC:", (g.get("heat_content") or {}).get("values", [])[-3:])
