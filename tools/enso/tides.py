# -*- coding: utf-8 -*-
"""Приливомеры вдоль пути прибрежной волны Кельвина: от Перу до штата Вашингтон (владелец 29.09).

Волна Кельвина, дойдя по экватору до Южной Америки, расходится вдоль берега на север и на юг и несёт с
собой поднятый уровень моря и тёплую воду (статья Guardian 28.09: волна у Калифорнии, до 30 см на месяцы).
Её прямой след — уровень моря на приливомерах; ни в одном другом нашем ряду его нет.

История — UHSLC, Гавайский университет (ERDDAP, без регистрации): суточный ряд `global_daily_fast`
(исследовательские данные до даты last_rq_date, дальше быстрые; сейчас по конец июля 2026). Свежие дни —
живые данные: NOAA CO-OPS у станций США (6-минутный уровень), IOC Sea Level Station Monitoring Facility
у остальных (минутные сырые данные). Живые ряды приводятся к суткам фильтром Годена (скользящие средние
24-24-25 часов: убирают приливы) и выравниваются на UHSLC медианой разности по общим дням.

Аномалия — от нормы самой станции: линейный тренд плюс годовой и полугодовой ход, подогнанные по 1991–2020.
Сантиметры. Прошлые события (1982, 1997, 2015, 2023) — те же календарные дни той же моделью.

    python tides.py              # история из кэша (быстрая часть обновляется) + живые хвосты → tides.json
    python tides.py --refresh    # перекачать историю UHSLC целиком
"""
import csv
import io
import json
import math
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import safeio                                                     # noqa: E402

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"
CACHE = ROOT / "tides"
OUT = ROOT / "tides.json"
UA = "Mozilla/5.0 (bridge42worlds El Nino panel)"
UH = "https://uhslc.soest.hawaii.edu/erddap/tabledap/global_daily_fast.csv?time,sea_level&uhslc_id={id}&time%3E={t0}"
COOPS = ("https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product={product}&station={st}&begin_date={b}"
         "&end_date={e}&datum={datum}&units=metric&time_zone=gmt&format=json&application=bridge42worlds{extra}")
IOC = "https://www.ioc-sealevelmonitoring.org/service.php?query=data&code={code}&timestart={t0}&timestop={t1}&format=json"
IOC_SENSORS = ("rad", "ra2", "ras", "prs", "flt", "enc", "pwl", "aqu", "bub", "pr2", "ra3")

BASE = (1991, 2020)
EVENTS = (1982, 1997, 2015, 2023)
WINDOW_FROM = "2026-05-01"          # начало окна на панели (картинка «широта против времени»)
LIVE_FROM = "2026-06-01"            # с какого дня берём живые данные: июнь–июль — перекрытие с UHSLC

# с юга на север вдоль берега; Галапагосы — точка на самом экваторе, откуда волна приходит к берегу
STATIONS = [
    ("callao", "Callao", "Peru", -12.07, -77.17, 93, ("ioc", "call")),
    ("talara", "Talara", "Peru", -4.58, -81.28, 92, ("ioc", "tala2")),
    ("lalibertad", "La Libertad", "Ecuador", -2.22, -80.91, 91, ("ioc", "lali")),
    ("baltra", "Baltra, Galápagos", "Ecuador", -0.43, -90.28, 3, ("ioc", "balt")),
    ("quepos", "Quepos", "Costa Rica", 9.43, -84.17, 87, ("ioc", "quepo")),
    ("acajutla", "Acajutla", "El Salvador", 13.57, -89.84, 82, ("ioc", "acaj")),
    ("lajolla", "La Jolla", "California", 32.87, -117.26, 554, ("coops", "9410230")),
    ("sanfrancisco", "San Francisco", "California", 37.81, -122.47, 551, ("coops", "9414290")),
    ("crescent", "Crescent City", "California", 41.75, -124.18, 556, ("coops", "9419750")),
    ("southbeach", "South Beach", "Oregon", 44.63, -124.04, 592, ("coops", "9435380")),
    ("neahbay", "Neah Bay", "Washington", 48.37, -124.60, 558, ("coops", "9443090")),
]
CALIFORNIA = ("lajolla", "vandenberg", "sanfrancisco", "crescent")
KING_TIDE_STATIONS = (("lajolla", "9410230"), ("sanfrancisco", "9414290"))


def _get(url, timeout=120, tries=3):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:                                   # noqa: BLE001
            last = e
            time.sleep(4 + 8 * k)
    raise RuntimeError(str(last)[:160])


def _dec_year(d):
    y = d.year
    n = 366 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 365
    return y + (d.timetuple().tm_yday - 0.5) / n


# ---------------------------------------------------------------- история UHSLC
def uh_daily(uid, refresh=False):
    """{дата ISO: мм} за 1980 — сегодня. Кэш на диске; быстрая часть (последние два года) перекачивается."""
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"uh_{uid}.json"
    have = {}
    if p.exists() and not refresh:
        try:
            have = json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                        # noqa: BLE001
            have = {}
    t0 = "1980-01-01" if not have else (date.today() - timedelta(days=730)).isoformat()
    raw = _get(UH.format(id=uid, t0=t0), timeout=240).decode("utf-8", "replace")
    rows = list(csv.reader(io.StringIO(raw)))
    got = 0
    for r in rows[2:]:
        if len(r) < 2 or not r[1] or r[1].lower() == "nan":
            continue
        try:
            v = float(r[1])
        except ValueError:
            continue
        if v < -9000:
            continue
        have[r[0][:10]] = v
        got += 1
    safeio.write_text(p, json.dumps(have))
    return have


def fit_normal(series):
    """Норма станции по 1991–2020: тренд + годовой и полугодовой ход. Если в базе меньше десяти лет —
    по всем годам станции (не меньше пяти) с пометкой short_base: у Кепоса, Акахутлы, Акапулько и
    Ванденберга ряд начинается после 2010 года (29.09)."""
    ts, vs = [], []
    for d, v in series.items():
        y = int(d[:4])
        if BASE[0] <= y <= BASE[1]:
            ts.append(_dec_year(date.fromisoformat(d)))
            vs.append(v)
    short = None
    if len(ts) < 3650:
        ts = [_dec_year(date.fromisoformat(d)) for d in series]
        vs = list(series.values())
        if len(ts) < 1825:
            return None
        yrs = sorted({int(d[:4]) for d in series})
        short = f"{yrs[0]}–{yrs[-1]}"
    t = np.array(ts)
    X = np.column_stack([np.ones_like(t), t - 2006, np.cos(2 * np.pi * t), np.sin(2 * np.pi * t),
                         np.cos(4 * np.pi * t), np.sin(4 * np.pi * t)])
    coef, *_ = np.linalg.lstsq(X, np.array(vs), rcond=None)
    years = len({int(d[:4]) for d in series if BASE[0] <= int(d[:4]) <= BASE[1]})
    return {"coef": [float(c) for c in coef], "n_days": len(ts), "years": years, "short_base": short}


def normal_at(nm, d):
    t = _dec_year(d)
    c = nm["coef"]
    return (c[0] + c[1] * (t - 2006) + c[2] * math.cos(2 * math.pi * t) + c[3] * math.sin(2 * math.pi * t)
            + c[4] * math.cos(4 * math.pi * t) + c[5] * math.sin(4 * math.pi * t))


# ---------------------------------------------------------------- живые данные → сутки
def godin_daily(hours):
    """{час ISO 'YYYY-MM-DDTHH': мм} → {день: мм}: фильтр Годена 24-24-25 ч, значение на 12:00 UTC.
    Дыры до шести часов заполняются линейно, длиннее — день пропускается."""
    if not hours:
        return {}
    keys = sorted(hours)
    t0 = datetime.strptime(keys[0], "%Y-%m-%dT%H")
    t1 = datetime.strptime(keys[-1], "%Y-%m-%dT%H")
    n = int((t1 - t0).total_seconds() // 3600) + 1
    h = np.full(n, np.nan)
    for k, v in hours.items():
        i = int((datetime.strptime(k, "%Y-%m-%dT%H") - t0).total_seconds() // 3600)
        h[i] = v
    ok = np.isfinite(h)
    idx = np.arange(n)
    if ok.sum() < 72:
        return {}
    gaps = np.interp(idx, idx[ok], h[ok])
    run, i = 0, 0
    fill = h.copy()
    while i < n:                                    # короткие дыры — линейно, длинные — оставляем пустыми
        if ok[i]:
            i += 1
            continue
        j = i
        while j < n and not ok[j]:
            j += 1
        if j - i <= 6 and i > 0 and j < n:
            fill[i:j] = gaps[i:j]
        i = j

    def ma(x, w):
        m = np.isfinite(x)
        c = np.convolve(np.where(m, x, 0.0), np.ones(w), "same")
        k = np.convolve(m.astype(float), np.ones(w), "same")
        out = c / np.maximum(k, 1)
        out[k < w] = np.nan
        return out

    f = ma(ma(ma(fill, 24), 24), 25)
    days = {}
    for i in range(n):
        t = t0 + timedelta(hours=i)
        if t.hour == 12 and np.isfinite(f[i]):
            days[t.date().isoformat()] = float(f[i])
    return days


def coops_hours(st, d0, d1):
    """6-минутный уровень NOAA CO-OPS (м, датум MSL) → часовые средние в мм."""
    acc = {}
    a = date.fromisoformat(d0)
    end = date.fromisoformat(d1)
    while a <= end:
        b = min(a + timedelta(days=30), end)
        url = COOPS.format(product="water_level", st=st, b=a.strftime("%Y%m%d"), e=b.strftime("%Y%m%d"), datum="MSL", extra="")
        try:
            d = json.loads(_get(url, timeout=120).decode("utf-8"))
        except Exception:                                        # noqa: BLE001
            d = {}
        for r in d.get("data") or []:
            try:
                v = float(r["v"])
            except (TypeError, ValueError, KeyError):
                continue
            k = r["t"][:13].replace(" ", "T")
            acc.setdefault(k, []).append(v * 1000.0)
        a = b + timedelta(days=1)
    return {k: float(np.mean(v)) for k, v in acc.items() if len(v) >= 6}


def ioc_hours(code, d0, d1):
    """Сырые минутные данные IOC → часовые средние из 5-минутных медиан (медиана гасит выбросы), мм.
    Датчик — тот, у которого больше всего отсчётов в окне (радар, давление, поплавок…)."""
    raw = []
    a = date.fromisoformat(d0)
    end = date.fromisoformat(d1)
    while a <= end:
        b = min(a + timedelta(days=29), end)
        try:
            raw += json.loads(_get(IOC.format(code=code, t0=a.isoformat(), t1=(b + timedelta(days=1)).isoformat()), timeout=180).decode("utf-8"))
        except Exception:                                        # noqa: BLE001
            pass
        a = b + timedelta(days=1)
    by = {}
    for r in raw:
        s = r.get("sensor")
        if s in IOC_SENSORS and r.get("slevel") is not None:
            by.setdefault(s, []).append(r)
    if not by:
        return {}, None
    sensor = max(by, key=lambda s: len(by[s]))
    five = {}
    for r in by[sensor]:
        try:
            v = float(r["slevel"]) * 1000.0
            t = datetime.strptime(r["stime"][:16], "%Y-%m-%d %H:%M")
        except (TypeError, ValueError):
            continue
        k = t.strftime("%Y-%m-%dT%H") + f"{t.minute // 5:02d}"
        five.setdefault(k, []).append(v)
    hrs = {}
    for k, v in five.items():
        hrs.setdefault(k[:13], []).append(float(np.median(v)))
    return {k: float(np.mean(v)) for k, v in hrs.items() if len(v) >= 6}, sensor


def live_hours(live, d0, d1):
    """Часовые живые данные с кэшем на диске: качается только хвост от последнего дня кэша минус трое суток.
    Возвращает (часы, датчик)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"live_{live[0]}_{live[1]}.json"
    have, sensor = {}, None
    if p.exists():
        try:
            c = json.loads(p.read_text(encoding="utf-8"))
            have, sensor = c.get("hours") or {}, c.get("sensor")
        except Exception:                                        # noqa: BLE001
            have = {}
    need = [(d0, d1)]
    if have:
        first = min(have)[:10]
        last = max(have)[:10]
        need = []
        if d0 < first:
            need.append((d0, (date.fromisoformat(first) - timedelta(days=1)).isoformat()))
        tail0 = max(d0, (date.fromisoformat(last) - timedelta(days=3)).isoformat())
        if tail0 <= d1:
            need.append((tail0, d1))
    for a, b in need:
        if live[0] == "coops":
            hrs, sn = coops_hours(live[1], a, b), "water level, 6 min"
        else:
            hrs, sn = ioc_hours(live[1], a, b)
        if hrs and (sensor is None or sn == sensor):
            have.update(hrs)
            sensor = sensor or sn
    if have:
        safeio.write_text(p, json.dumps({"sensor": sensor, "hours": have}))
    return {k: v for k, v in have.items() if d0 <= k[:10] <= d1}, sensor


# ---------------------------------------------------------------- сборка
def station(rec, refresh=False, verbose=True):
    key, name, country, lat, lon, uid, live = rec
    out = {"key": key, "name": name, "country": country, "lat": lat, "lon": lon, "uh_id": uid, "error": ""}
    try:
        hist = uh_daily(uid, refresh=refresh)
    except Exception as e:                                       # noqa: BLE001
        out["error"] = f"UHSLC: {str(e)[:120]}"
        hist = {}
    nm = fit_normal(hist) if hist else None
    if not nm:
        out["error"] = out["error"] or "not enough 1991–2020 data for a normal"
        return out
    out["trend_mm_yr"] = round(nm["coef"][1], 2)
    out["base_years"] = nm["years"]
    if nm.get("short_base"):
        out["short_base"] = nm["short_base"]      # норма не 1991–2020, а по годам станции — подпись на панели
    uh_last = max(hist) if hist else None
    out["uh_last"] = uh_last
    # живой хвост
    today = date.today().isoformat()
    lv = {}
    try:
        # история UHSLC кончилась раньше июня — живые данные берутся и за два месяца до её конца: там сдвиг
        start = LIVE_FROM if (uh_last or "") >= LIVE_FROM else min(LIVE_FROM, (date.fromisoformat(uh_last) - timedelta(days=60)).isoformat())
        hrs, sensor = live_hours(live, start, today)
        daily = godin_daily(hrs)
        common = [d for d in daily if d in hist]
        info = {"source": "NOAA CO-OPS" if live[0] == "coops" else "IOC SLSMF", "code": live[1], "sensor": sensor,
                "overlap_days": len(common), "last": max(daily) if daily else None}
        if len(common) >= 15:
            off = float(np.median([daily[d] - hist[d] for d in common]))
            spread = float(np.std([daily[d] - hist[d] - off for d in common]))
            info["offset_mm"] = round(off, 1)
            info["fit_sd_mm"] = round(spread, 1)
            if spread <= 40:                         # сдвиг датума устойчив — хвост годен
                lv = {d: v - off for d, v in daily.items()}
            else:
                info["rejected"] = "the live series does not follow UHSLC on the common days"
        else:
            info["rejected"] = "too few common days with UHSLC to align the live series"
        out["live"] = info
    except Exception as e:                                       # noqa: BLE001
        out["live"] = {"error": str(e)[:160]}
    # ряд окна: UHSLC, где есть; дальше живой
    d0 = date.fromisoformat(WINDOW_FROM)
    d1 = date.today() - timedelta(days=1)
    dates, anom, src = [], [], []
    d = d0
    while d <= d1:
        k = d.isoformat()
        v, s = (hist[k], "u") if k in hist else ((lv[k], "l") if k in lv else (None, "-"))
        dates.append(k)
        anom.append(None if v is None else round((v - normal_at(nm, d)) / 10.0, 1))
        src.append(s)
        d += timedelta(days=1)
    out["dates"], out["anom"], out["src"] = dates, anom, "".join(src)
    vals = [(k, a) for k, a in zip(dates, anom) if a is not None]
    out["last_date"] = vals[-1][0] if vals else None
    last = date.fromisoformat(out["last_date"]) if out["last_date"] else None

    def mean_to(a_list, n):
        v = [a for a in a_list[-n:] if a is not None]
        return round(float(np.mean(v)), 1) if len(v) >= n * 0.5 else None

    if last:
        i = dates.index(out["last_date"]) + 1
        out["mean7"] = mean_to(anom[:i], 7)
        out["mean30"] = mean_to(anom[:i], 30)
    # прошлые события: те же календарные дни
    an, an30 = {}, {}
    for y in EVENTS:
        arr = []
        for k in dates:
            try:
                dd = date(y, int(k[5:7]), int(k[8:10]))
            except ValueError:
                arr.append(None)
                continue
            v = hist.get(dd.isoformat())
            arr.append(None if v is None else round((v - normal_at(nm, dd)) / 10.0, 1))
        if sum(a is not None for a in arr) >= len(arr) * 0.5:
            an[str(y)] = arr
            if last:
                i = dates.index(out["last_date"]) + 1
                an30[str(y)] = mean_to(arr[:i], 30)
    out["analogs"], out["analog_mean30"] = an, an30
    if verbose:
        lvs = out.get("live") or {}
        print(f"  {name:22s} UHSLC до {uh_last}, тренд {out['trend_mm_yr']} мм/год, живые {lvs.get('source', '—')} "
              f"{lvs.get('code', '')} до {lvs.get('last')}, общих дней {lvs.get('overlap_days')}, "
              f"сдвиг {lvs.get('offset_mm')} ± {lvs.get('fit_sd_mm')} мм{(' — ' + lvs['rejected']) if lvs.get('rejected') else ''}; "
              f"последний день {out['last_date']}, 7 сут {out.get('mean7')} см, 30 сут {out.get('mean30')} см, "
              f"1997 {an30.get('1997')}, 2015 {an30.get('2015')}", flush=True)
    return out


def king_tides():
    """Самые высокие приливы октября–декабря над средним высоким уровнем (MHHW): прогноз NOAA."""
    out = {}
    y = date.today().year
    for key, st in KING_TIDE_STATIONS:
        url = COOPS.format(product="predictions", st=st, b=f"{y}1001", e=f"{y}1231", datum="MHHW", extra="&interval=hilo")
        try:
            d = json.loads(_get(url).decode("utf-8"))
        except Exception:                                        # noqa: BLE001
            continue
        hi = [p for p in d.get("predictions") or [] if p.get("type") == "H"]
        hi.sort(key=lambda p: -float(p["v"]))
        top, seen = [], set()
        for p in hi:
            day = p["t"][:10]
            if day in seen:
                continue
            seen.add(day)
            top.append({"t": p["t"], "cm": round(float(p["v"]) * 100)})
            if len(top) >= 6:
                break
        out[key] = sorted(top, key=lambda p: p["t"])
    return out


def build(refresh=False, verbose=True):
    t0 = time.time()
    st = []
    for rec in STATIONS:
        try:
            st.append(station(rec, refresh=refresh, verbose=verbose))
        except Exception as e:                                   # noqa: BLE001
            st.append({"key": rec[0], "name": rec[1], "country": rec[2], "lat": rec[3], "lon": rec[4], "error": str(e)[:160]})
    ca = [s for s in st if s.get("key") in CALIFORNIA and s.get("mean30") is not None]
    cal = None
    if ca:
        cal = {"stations": [s["name"] for s in ca], "mean30": round(float(np.mean([s["mean30"] for s in ca])), 1),
               "last_date": min(s["last_date"] for s in ca),
               "analog_mean30": {y: round(float(np.mean([s["analog_mean30"][y] for s in ca if s.get("analog_mean30", {}).get(y) is not None])), 1)
                                 for y in ("1997", "2015") if any(s.get("analog_mean30", {}).get(y) is not None for s in ca)}}
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "window_from": WINDOW_FROM, "stations": st,
           "california": cal, "king_tides": king_tides(), "secs": round(time.time() - t0),
           "sources": ["University of Hawaii Sea Level Center, daily fast-delivery series (ERDDAP), for the history and the normal",
                       "NOAA CO-OPS, 6-minute water level, for the United States gauges' latest days",
                       "IOC Sea Level Station Monitoring Facility (VLIZ), raw minute data, for the other gauges' latest days",
                       "NOAA CO-OPS tide predictions (high and low waters over MHHW) for the highest tides of the season"],
           "method": "Daily sea level against each gauge's own 1991–2020 normal: a linear trend plus the yearly and "
                     "half-yearly cycle fitted to the gauge's record, so the long rise of the sea is taken out. Live data "
                     "are hourly means brought to days with a Godin filter (24-24-25 hours, removes the tides) and aligned "
                     "to the Hawaii series by the median difference on the days both cover. Centimetres.",
           "note": "A Kelvin wave that reaches South America along the equator turns along the coast and runs north and "
                   "south, lifting the whole sea by several centimetres for weeks to months. The gauges from Peru to "
                   "Washington show it as a band that moves north with time."}
    safeio.write_text(OUT, json.dumps(doc, ensure_ascii=False, allow_nan=False))
    ok = sum(1 for s in st if s.get("dates"))
    print(f"tides.json: станций {ok} из {len(st)}, Калифорния 30 сут {cal and cal.get('mean30')} см, {doc['secs']} с")
    return doc


if __name__ == "__main__":
    build(refresh="--refresh" in sys.argv)
