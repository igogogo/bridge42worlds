# -*- coding: utf-8 -*-
"""Ветер по дням: западные всплески над западной Пацификой.

ЗАЧЕМ. Эль-Ниньо толкают западные ветровые всплески (WWB): несколько дней западного ветра
над тёплым бассейном запускают волну Кельвина, и через два-три месяца тёплая вода
всплывает у Америки. Месячные индексы CPC (wpac850 и другие) сглаживают всплеск в ноль:
экспертиза 04.09 (п. 3.4) требует недельный и суточный шаг и сам детектор.

ОТКУДА. Реанализы NCEP на PSL в сентябре 2026 стоят на марте (проверено), поэтому суточный
ряд берём из ERA5 через Open-Meteo (архивный API, без ключа, до вчерашнего дня): скорость и
направление ветра на 10 м по часам в шести точках экватора 130°E…180°, из них — среднесуточная
зональная компонента. Климатология 1991–2020 и разброс — по тем же точкам и тем же часам,
строятся один раз. Буи TAO на 165°E и 170°W дают прямой замер ветра для сверки.

ПОРОГ. Всплеск — среднее по точкам западная аномалия не ниже двух сигм суточной аномалии
пять дней подряд и дольше. На 850 гПа в литературе берут 5–7 м/с; у поверхности ветер
слабее, и две сигмы (около 3–4 м/с) — тот же критерий в тех же единицах.
"""
import json
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"
CACHE = ROOT / "wind"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
ARCH = "https://archive-api.open-meteo.com/v1/archive"
POINTS = [(0.0, 130.0), (0.0, 140.0), (0.0, 150.0), (0.0, 160.0), (0.0, 170.0), (0.0, 180.0)]
CLIM_YEARS = (1991, 2020)
RECENT_DAYS = 120
MIN_RUN = 5
SIGMAS = 2.0
TAO_W = "https://coastwatch.pfeg.noaa.gov/erddap/tabledap/pmelTaoDyW.csv"
TAO_STATIONS = [("0n165e", 165), ("0n170w", 190)]


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


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))


def _daily_u(lat, lon, t0, t1):
    """Среднесуточная зональная компонента ветра на 10 м, м/с: {дата: u}. Восток — плюс."""
    d = _get(f"{ARCH}?latitude={lat}&longitude={lon}&start_date={t0}&end_date={t1}"
             "&hourly=wind_speed_10m,wind_direction_10m&wind_speed_unit=ms&timezone=UTC")
    h = d.get("hourly") or {}
    times, sp, dr = h.get("time") or [], h.get("wind_speed_10m") or [], h.get("wind_direction_10m") or []
    acc = {}
    for t, s, a in zip(times, sp, dr):
        if s is None or a is None:
            continue
        u = -s * np.sin(np.deg2rad(a))          # направление «откуда»: ветер с запада даёт u > 0
        acc.setdefault(t[:10], []).append(u)
    return {k: round(float(np.mean(v)), 3) for k, v in acc.items() if len(v) >= 12}


def build_clim(verbose=False):
    """Климатология и сигма по дню года для среднего по точкам — один раз, по пять лет за запрос."""
    p = CACHE / "clim_era5.json"
    cl = _load(p, {})
    if cl.get("doy"):
        return cl
    per_day = {}
    for lat, lon in POINTS:
        for y0 in range(CLIM_YEARS[0], CLIM_YEARS[1] + 1, 5):
            y1 = min(y0 + 4, CLIM_YEARS[1])
            t0 = time.time()
            try:
                u = _daily_u(lat, lon, f"{y0}-01-01", f"{y1}-12-31")
            except Exception as e:                               # noqa: BLE001
                if verbose:
                    print(f"  {lat},{lon} {y0}-{y1}: {str(e)[:80]}")
                continue
            for k, v in u.items():
                per_day.setdefault(k, []).append(v)
            if verbose:
                print(f"  {lon}°E {y0}-{y1}: {len(u)} дней, {time.time() - t0:.0f} с")
    if not per_day:
        return cl
    # среднее по точкам на каждый день, потом по дню года; сигма — разброс суточных аномалий
    daily = {k: float(np.mean(v)) for k, v in per_day.items() if len(v) >= len(POINTS) - 1}
    sums, cnts = np.zeros(366), np.zeros(366)
    for k, v in daily.items():
        i = _doy(date.fromisoformat(k)); sums[i] += v; cnts[i] += 1
    mean = np.where(cnts > 0, sums / np.maximum(cnts, 1), np.nan)
    if not np.isfinite(mean[59]):
        mean[59] = np.nanmean([mean[58], mean[60]])
    kk = 31
    ext = np.concatenate([mean[-kk:], mean, mean[:kk]])
    sm = np.array([np.nanmean(ext[i:i + kk]) for i in range(366)])
    an = [v - sm[_doy(date.fromisoformat(k))] for k, v in daily.items()]
    cl = {"doy": [round(float(v), 3) for v in sm], "sigma": round(float(np.std(an)), 3),
          "n_days": len(daily), "years": list(CLIM_YEARS), "smooth_days": kk,
          "points": POINTS, "built": datetime.now().strftime("%Y-%m-%d %H:%M"),
          "source": "ERA5 10 m wind via Open-Meteo archive, hourly, six equatorial points 130°E–180°"}
    _save(p, cl)
    return cl


ANALOG_YEARS = (1982, 1997, 2015, 2023)


def build_analogs(verbose=False):
    """Среднесуточная зональная компонента по шести точкам за ВЕСЬ год каждого сильного события:
    один раз, в кэш; дальше режется по дню года под текущее окно."""
    p = CACHE / "analogs_era5.json"
    cl = _load(p, {})
    for y in ANALOG_YEARS:
        if str(y) in cl:
            continue
        per_day = {}
        for lat, lon in POINTS:
            try:
                u = _daily_u(lat, lon, f"{y}-01-01", f"{y}-12-31")
            except Exception as e:                               # noqa: BLE001
                if verbose:
                    print(f"  {y} {lon}: {str(e)[:80]}")
                continue
            for k, v in u.items():
                per_day.setdefault(k, []).append(v)
        arr = [None] * 366
        for k, v in per_day.items():
            if len(v) >= len(POINTS) - 1:
                arr[_doy(date.fromisoformat(k))] = round(float(np.mean(v)), 3)
        if any(v is not None for v in arr):
            cl[str(y)] = arr
        if verbose:
            print(f"  ветер {y}: {sum(1 for v in arr if v is not None)} дней")
    _save(p, cl)
    return cl


def analog_window(days, doy_clim):
    """Аномалии годов-аналогов на те же дни календаря, что и окно панели."""
    cl = _load(CACHE / "analogs_era5.json", {})
    out = {}
    for y, arr in cl.items():
        vals = []
        for d in days:
            i = _doy(d)
            v = arr[i] if i < len(arr) else None
            vals.append(None if v is None or not doy_clim else round(v - doy_clim[i], 2))
        if any(v is not None for v in vals):
            out[y] = vals
    return out


def events(dates, anom, thr):
    out, run = [], []
    for d, a in zip(dates, anom):
        if a is not None and a >= thr:
            run.append((d, a))
        else:
            if len(run) >= MIN_RUN:
                out.append({"start": run[0][0], "end": run[-1][0], "days": len(run),
                            "peak": round(max(x[1] for x in run), 2)})
            run = []
    if len(run) >= MIN_RUN:
        out.append({"start": run[0][0], "end": run[-1][0], "days": len(run),
                    "peak": round(max(x[1] for x in run), 2), "ongoing": True})
    return out


def era5(today=None, verbose=False):
    today = today or date.today()
    cl = _load(CACHE / "clim_era5.json", {})
    p = CACHE / "era5_recent.json"
    store = _load(p, {"u": {}})
    t0 = (today - timedelta(days=RECENT_DAYS)).isoformat()
    t1 = (today - timedelta(days=1)).isoformat()
    per_day, err = {}, ""
    for lat, lon in POINTS:
        try:
            u = _daily_u(lat, lon, t0, t1)
        except Exception as e:                                   # noqa: BLE001
            err = str(e)[:120]
            continue
        for k, v in u.items():
            per_day.setdefault(k, []).append(v)
    fresh = {k: round(float(np.mean(v)), 3) for k, v in per_day.items() if len(v) >= len(POINTS) - 1}
    if fresh:
        store["u"].update(fresh)
        store["u"] = dict(sorted(store["u"].items())[-(RECENT_DAYS + 30):])
        store["fetched"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        _save(p, store)
    u = store.get("u") or {}
    if not u:
        return {"error": err or "no wind data"}
    last = date.fromisoformat(max(u))
    days = [last - timedelta(days=i) for i in range(RECENT_DAYS - 1, -1, -1)]
    dates = [d.isoformat() for d in days]
    vals = [u.get(d) for d in dates]
    doy = cl.get("doy") or []
    anom = [None if v is None or not doy else round(v - doy[_doy(d)], 3) for v, d in zip(vals, days)]
    sig = cl.get("sigma")
    thr = round(SIGMAS * sig, 2) if sig else None
    ev = events(dates, anom, thr) if thr else []
    analogs = analog_window(days, doy) if doy else {}
    out = {"dates": dates, "u": vals, "anom": anom, "sigma": sig, "threshold": thr, "analogs": analogs,
           "last_date": last.isoformat(), "days_stale": (today - last).days, "has_clim": bool(doy),
           "events": ev, "active": bool(ev and ev[-1].get("ongoing")),
           "days_since_last": None if not ev else (last - date.fromisoformat(ev[-1]["end"])).days,
           "mean7": round(float(np.mean([a for a in anom[-7:] if a is not None])), 2) if any(a is not None for a in anom[-7:]) else None,
           "points": POINTS, "error": err,
           "source": "ERA5 10 m wind via Open-Meteo archive (hourly → daily zonal mean), six equatorial points 130°E–180°",
           "clim": f"own {CLIM_YEARS[0]}–{CLIM_YEARS[1]} climatology by day of year, 31-day smoothing; σ of the daily anomaly {sig}",
           "note": ("Westerly is positive. A burst is a westerly anomaly of two sigma or more for five days "
                    "or longer, averaged over the six points: that is what launches a Kelvin wave, and its "
                    "warm water reaches the American coast two to three months later. Reanalysis winds at "
                    "850 hPa would be the textbook choice, but NCEP's daily files are frozen at March 2026; "
                    "the 10 m ERA5 wind carries the same bursts at about half the amplitude.")}
    if verbose:
        print(f"  ERA5: до {last}, 7 дней {out['mean7']}, порог {thr}, всплесков {len(ev)}, активен {out['active']}")
    return out


# ------------------------------------------------------------------ TAO winds, для сверки
def _tao_u(lon, t0, t1=None):
    # Tomcat за ERDDAP отвергает сырые «>» и «<» в строке запроса (400 без текста): кодируем.
    q = f"{TAO_W}?time,WU_422&longitude={lon}&latitude=0&time%3E%3D{t0}" + (f"&time%3C%3D{t1}" if t1 else "")
    req = urllib.request.Request(q, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        txt = r.read().decode("utf-8", "replace")
    out = {}
    for ln in txt.splitlines()[2:]:
        p = ln.split(",")
        try:
            v = float(p[1])
        except (ValueError, IndexError):
            continue
        if np.isfinite(v):
            out[p[0][:10]] = round(v, 3)
    return out


def build_clim_tao(verbose=False):
    p = CACHE / "clim_tao.json"
    cl = _load(p, {})
    for name, lon in TAO_STATIONS:
        if cl.get(name):
            continue
        sums, cnts = np.zeros(366), np.zeros(366)
        for y in range(CLIM_YEARS[0], CLIM_YEARS[1] + 1):
            try:
                u = _tao_u(lon, f"{y}-01-01", f"{y}-12-31")
            except Exception as e:                               # noqa: BLE001
                if verbose:
                    print(f"  {name} {y}: {str(e)[:80]}")
                continue
            for k, v in u.items():
                i = _doy(date.fromisoformat(k)); sums[i] += v; cnts[i] += 1
        if cnts.max() == 0:
            continue
        mean = np.where(cnts > 0, sums / np.maximum(cnts, 1), np.nan)
        kk = 31
        ext = np.concatenate([mean[-kk:], mean, mean[:kk]])
        sm = [None if not np.isfinite(v) else round(float(v), 3) for v in
              (np.nanmean(ext[i:i + kk]) for i in range(366))]
        cl[name] = {"doy": sm, "n_days": int((cnts > 0).sum()), "years": list(CLIM_YEARS)}
        if verbose:
            print(f"  {name}: климатология из {int(cnts.sum())} дней")
    _save(p, cl)
    return cl


def tao(today=None, verbose=False):
    today = today or date.today()
    cl = _load(CACHE / "clim_tao.json", {})
    out = {}
    t0 = (today - timedelta(days=RECENT_DAYS)).isoformat()
    for name, lon in TAO_STATIONS:
        try:
            u = _tao_u(lon, t0)
        except Exception as e:                                   # noqa: BLE001
            out[name] = {"error": str(e)[:120]}
            continue
        if not u:
            out[name] = {"error": "no data in the window"}
            continue
        dates = sorted(u)
        doy = (cl.get(name) or {}).get("doy") or []
        anom = [None if not doy or doy[_doy(date.fromisoformat(d))] is None else round(u[d] - doy[_doy(date.fromisoformat(d))], 2) for d in dates]
        out[name] = {"lon": lon, "dates": dates, "u": [u[d] for d in dates], "anom": anom,
                     "last_date": dates[-1], "days_stale": (today - date.fromisoformat(dates[-1])).days,
                     "mean7": round(float(np.mean([a for a in anom[-7:] if a is not None])), 2) if any(a is not None for a in anom[-7:]) else None}
        if verbose:
            print(f"  TAO {name}: до {dates[-1]}, 7 дней аномалия {out[name]['mean7']}")
    return out


def build(today=None, verbose=False):
    return {"era5": era5(today, verbose), "tao": tao(today, verbose),
            "note": "ERA5 is the field, the moorings are the check: two independent measures of the same wind."}


def risks(WIND):
    """Правила по ветру — в формате air.risks."""
    out = []
    e = (WIND or {}).get("era5") or {}
    if e.get("error") or not e.get("dates"):
        return out
    ev = e.get("events") or []
    if e.get("active"):
        last = ev[-1]
        out.append((
            "A westerly wind burst is under way over the western Pacific", 4, "2–3 months",
            f"Since {last['start']}: {last['days']} days at or above the threshold of {e.get('threshold')} m/s, "
            f"peak anomaly {last['peak']} m/s (ERA5 10 m wind, six points 130°E–180°).",
            "The trade winds have given way for a week or more. Each burst pushes warm water down and east; the "
            "Kelvin wave it launches reaches the American coast in two to three months and lifts the event another step.",
            "the burst ending; the eastern moorings' 20 °C isotherm deepening two to three months from now",
            {"name": "Westerly wind anomaly, 130°E–180°, daily", "unit": "m/s", "step": "day",
             "dates": e["dates"], "values": e["anom"], "analogs": e.get("analogs") or {}},
            "climate", "wwb_active"))
    elif ev:
        last = ev[-1]
        since = e.get("days_since_last")
        out.append((
            f"{len(ev)} westerly wind bursts in the last 120 days, the latest {since} days ago", 3, "2–3 months",
            "; ".join(f"{x['start']} to {x['end']} ({x['days']} d, peak {x['peak']} m/s)" for x in ev) +
            f". Threshold {e.get('threshold')} m/s = two sigma of the daily anomaly. Last week: {e.get('mean7')} m/s.",
            "Bursts are how an El Niño is fed: the warm water each one sends east surfaces off South America two to "
            "three months later. The bursts of the last four months are the ones arriving now and through the autumn.",
            "a new run of five days above the threshold; the MJO entering phases 6–8 makes one more likely",
            {"name": "Westerly wind anomaly, 130°E–180°, daily", "unit": "m/s", "step": "day",
             "dates": e["dates"], "values": e["anom"], "analogs": e.get("analogs") or {}},
            "climate", "wwb_recent"))
    return out


if __name__ == "__main__":
    import sys
    if "--clim" in sys.argv:
        build_clim(verbose=True)
        build_clim_tao(verbose=True)
        build_analogs(verbose=True)
        print("готово")
    else:
        b = build(verbose=True)
        e = b["era5"]
        print("события:", e.get("events"))
