# -*- coding: utf-8 -*-
"""Кувейт и Залив: что событие значит здесь, а не «в мире вообще».

ЗАЧЕМ. Панель читает инженерный факультет в Кувейте (аудитория проекта), а региональная
строка «Gulf and Arabian Peninsula» в справочнике — общие слова. Экспертиза 04.09 (п. 3.8)
просит вкладку с замерами по месту: море у берега, температура и дожди по точке, зимняя
телесвязь с источниками, и цепочка импорта еды — пшеница и рис, с прецедентами.

ЧТО ЗДЕСЬ ЖИВОЕ, А ЧТО СПРАВОЧНОЕ. Живое: SST Залива из OISST (oisst.py, бокс 24–30°N,
48–56°E), температура и осадки Кувейта из ERA5 по точке 29.37°N 47.98°E (Open-Meteo, без
ключа, до вчерашнего дня, климатология 1991–2020 своя), цены пшеницы и риса из Pink Sheet.
Справочное: телесвязь зимы (три работы и одно событие, с источниками), доли импорта и
прецеденты 2023 года. Справочное подписано как справочное и с датой.
"""
import json
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"
CACHE = ROOT / "gulf"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
ARCH = "https://archive-api.open-meteo.com/v1/archive"
LAT, LON = 29.37, 47.98
CLIM_YEARS = (1991, 2020)
HOT = 45.0                     # порог «очень жаркого дня» для Кувейта, °C
SEA_STRESS = 35.0              # порог стресса для опреснения и рыболовства, °C

# ── Справочник. Числа взяты из экспертизы 04.09 с её источниками; не измеряются нами.
WINTER = {
    "claim": ("In an El Niño winter the storm track over the Gulf and Iran is stronger and the storms are "
              "wetter; the risk is a wet winter with flash floods, not a forecast of one."),
    "refs": [
        {"what": "El Niño winters strengthen the storm track and storm intensity over the Gulf and Iran",
         "src": "Impact of ENSO on extreme precipitation in Southwest Asia (2024)", "url": "https://www.sciencedirect.com/"},
        {"what": "ENSO and the Indian Ocean Dipole act together on sub-seasonal rainfall in the Middle East",
         "src": "Hochman et al., Quarterly Journal of the Royal Meteorological Society (2025)", "url": "https://rmets.onlinelibrary.wiley.com/journal/1477870x"},
        {"what": "The April 2024 floods in the UAE were linked in part to El Niño",
         "src": "World Weather Attribution; CBC", "url": "https://www.worldweatherattribution.org/"},
    ],
    "forecasts": [
        {"name": "IRI seasonal climate forecasts (Middle East maps)", "url": "https://iri.columbia.edu/our-expertise/climate/forecasts/seasonal-climate-forecasts/", "note": "free, monthly, around the 15th"},
        {"name": "Copernicus C3S multi-system seasonal forecast", "url": "https://climate.copernicus.eu/charts/packages/c3s_seasonal/", "note": "free with registration"},
        {"name": "NOAA CPC ENSO outlook", "url": "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/", "note": "second Thursday of the month"},
    ],
}
IMPORTS = {
    "as_of": "2026-09-04",
    "rows": [
        {"item": "Wheat", "fact": "Kuwait imports all of its wheat; Australia supplied 83 % of the import value in 2024",
         "src": "IndexBox, 2024 trade data", "commodity": "wheat"},
        {"item": "Rice", "fact": "Rice comes mainly from India: about $267 million in 2025",
         "src": "Trading Economics, 2025", "commodity": "rice"},
    ],
    "precedents": [
        {"when": "July 2023", "what": "India banned exports of non-basmati rice; exports fell 93 % over August–November, and the price of Thai rice rose 22 %",
         "src": "IFPRI; USDA FAS"},
        {"when": "Harvest 2023/24", "what": "Australia's wheat harvest came in at 25.5 million tonnes against the record 40.5 the year before, a fall of 36 %",
         "src": "ABARES; USDA"},
    ],
    "watch": [
        {"name": "FAO All Rice Price Index", "url": "https://www.fao.org/markets-and-trade/commodities/rice/fao-rice-price-update/en/", "cadence": "monthly"},
        {"name": "ABARES Australian crop report", "url": "https://www.agriculture.gov.au/abares/research-topics/agricultural-outlook/australian-crop-report", "cadence": "quarterly: March, June, September, December"},
        {"name": "AMIS Market Monitor", "url": "https://www.amis-outlook.org/amis-monitoring/monthly-report", "cadence": "monthly, first Thursday"},
        {"name": "USDA WASDE", "url": "https://www.usda.gov/oce/commodity/wasde", "cadence": "monthly, around the 10th"},
    ],
}


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


# ------------------------------------------------------------------ Кувейт, ERA5
def build_clim(verbose=False):
    """Климатология точки по дню года: tmax, tmin, осадки; плюс сколько дней ≥45 °C и сколько
    дождя за сезон бывает в среднем за год. Один запрос на тридцать лет."""
    p = CACHE / "clim_kuwait.json"
    cl = _load(p, {})
    if cl.get("tmax"):
        return cl
    d = _get(f"{ARCH}?latitude={LAT}&longitude={LON}&start_date={CLIM_YEARS[0]}-01-01&end_date={CLIM_YEARS[1]}-12-31"
             "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=UTC")
    dd = d.get("daily") or {}
    times, tx, tn, pr = dd.get("time") or [], dd.get("temperature_2m_max") or [], dd.get("temperature_2m_min") or [], dd.get("precipitation_sum") or []
    sums = {k: np.zeros(366) for k in ("tmax", "tmin", "prec")}
    cnts = np.zeros(366)
    hot_by_year, rain_by_season = {}, {}
    for t, a, b, c in zip(times, tx, tn, pr):
        if a is None or b is None:
            continue
        dt = date.fromisoformat(t); i = _doy(dt)
        sums["tmax"][i] += a; sums["tmin"][i] += b; sums["prec"][i] += (c or 0.0); cnts[i] += 1
        if a >= HOT:
            hot_by_year[dt.year] = hot_by_year.get(dt.year, 0) + 1
        # сезон дождей считаем от 1 сентября
        sy = dt.year if dt.month >= 9 else dt.year - 1
        rain_by_season[sy] = rain_by_season.get(sy, 0.0) + (c or 0.0)
    def sm(arr, k):
        m = np.where(cnts > 0, arr / np.maximum(cnts, 1), np.nan)
        if not np.isfinite(m[59]):
            m[59] = np.nanmean([m[58], m[60]])
        ext = np.concatenate([m[-k:], m, m[:k]])
        return [round(float(np.nanmean(ext[i:i + k])), 3) for i in range(366)]
    years = range(CLIM_YEARS[0], CLIM_YEARS[1] + 1)
    cl = {"tmax": sm(sums["tmax"], 15), "tmin": sm(sums["tmin"], 15), "prec": sm(sums["prec"], 31),
          "hot_days_per_year": round(float(np.mean([hot_by_year.get(y, 0) for y in years])), 1),
          "rain_per_season": round(float(np.mean([rain_by_season.get(y, 0.0) for y in years if y >= CLIM_YEARS[0]])), 1),
          "years": list(CLIM_YEARS), "built": datetime.now().strftime("%Y-%m-%d %H:%M"),
          "source": "ERA5 via Open-Meteo archive, daily, point 29.37°N 47.98°E"}
    _save(p, cl)
    if verbose:
        print(f"  Кувейт: климатология построена, дней ≥{HOT:g}° в год {cl['hot_days_per_year']}, дождь за сезон {cl['rain_per_season']} мм")
    return cl


ANALOG_YEARS = (1982, 1997, 2015, 2023)


def build_analogs(verbose=False):
    p = CACHE / "analogs_kuwait.json"
    cl = _load(p, {})
    for y in ANALOG_YEARS:
        if str(y) in cl:
            continue
        try:
            d = _get(f"{ARCH}?latitude={LAT}&longitude={LON}&start_date={y}-01-01&end_date={y}-12-31"
                     "&daily=temperature_2m_max&timezone=UTC")
        except Exception as e:                                   # noqa: BLE001
            if verbose:
                print(f"  Кувейт {y}: {str(e)[:80]}")
            continue
        dd = d.get("daily") or {}
        arr = [None] * 366
        for t, v in zip(dd.get("time") or [], dd.get("temperature_2m_max") or []):
            if v is not None:
                arr[_doy(date.fromisoformat(t))] = round(v, 1)
        cl[str(y)] = arr
        if verbose:
            print(f"  Кувейт {y}: {sum(1 for v in arr if v is not None)} дней")
    _save(p, cl)
    return cl


def kuwait(raw, today=None):
    """Текущий год по точке против климатологии."""
    today = today or date.today()
    cl = _load(CACHE / "clim_kuwait.json", {})
    dd = (raw or {}).get("daily") or {}
    times = dd.get("time") or []
    if not times:
        return {"error": "no ERA5 data for Kuwait"}
    tx, tn, pr = dd.get("temperature_2m_max") or [], dd.get("temperature_2m_min") or [], dd.get("precipitation_sum") or []
    rows = [(date.fromisoformat(t), a, b, c) for t, a, b, c in zip(times, tx, tn, pr) if a is not None]
    if not rows:
        return {"error": "ERA5 rows are empty"}
    last = rows[-1][0]
    ctx, cpr = cl.get("tmax") or [], cl.get("prec") or []
    tail = rows[-120:]
    out = {"last_date": last.isoformat(), "days_stale": (today - last).days,
           "dates": [r[0].isoformat() for r in tail], "tmax": [round(r[1], 1) for r in tail],
           "tmin": [round(r[2], 1) for r in tail],
           "tmax_anom": [round(r[1] - ctx[_doy(r[0])], 2) if ctx else None for r in tail],
           "tmax_clim": [round(ctx[_doy(r[0])], 1) if ctx else None for r in tail],
           "has_clim": bool(ctx), "point": [LAT, LON],
           "source": "ERA5 via Open-Meteo archive (free, no key), daily, one to three days behind",
           "clim": f"own {CLIM_YEARS[0]}–{CLIM_YEARS[1]} climatology for the same point"}
    if ctx:
        a30 = [r[1] - ctx[_doy(r[0])] for r in rows[-30:]]
        out["tmax_anom_30d"] = round(float(np.mean(a30)), 2)
        # прошлые сильные события на те же дни: аномалия максимума от той же нормы
        an = _load(CACHE / "analogs_kuwait.json", {})
        out["tmax_anom_analogs"] = {}
        for y, arr in an.items():
            vals = [None if arr[_doy(r[0])] is None else round(arr[_doy(r[0])] - ctx[_doy(r[0])], 2) for r in tail]
            if any(v is not None for v in vals):
                out["tmax_anom_analogs"][y] = vals
    hottest = max(rows, key=lambda r: r[1])
    out["hottest"] = {"value": round(hottest[1], 1), "date": hottest[0].isoformat()}
    out["hot_days"] = sum(1 for r in rows if r[1] >= HOT)
    out["hot_days_normal"] = cl.get("hot_days_per_year")
    # дождь: текущий сезон (с 1 сентября) и прошлый календарный кусок года
    s0 = date(last.year if last.month >= 9 else last.year - 1, 9, 1)
    season = [r for r in rows if r[0] >= s0]
    out["rain_season_mm"] = round(float(sum((r[3] or 0.0) for r in season)), 1)
    out["rain_season_from"] = s0.isoformat()
    if cpr:
        out["rain_season_normal_todate_mm"] = round(float(sum(cpr[_doy(r[0])] for r in season)), 1)
    out["rain_season_normal_mm"] = cl.get("rain_per_season")
    ytd = [r for r in rows if r[0].year == last.year]
    out["rain_ytd_mm"] = round(float(sum((r[3] or 0.0) for r in ytd)), 1)
    if cpr:
        out["rain_ytd_normal_mm"] = round(float(sum(cpr[_doy(r[0])] for r in ytd)), 1)
    wet = [r for r in rows if (r[3] or 0) >= 1.0]
    out["last_rain"] = {"date": wet[-1][0].isoformat(), "mm": round(wet[-1][3], 1)} if wet else None
    return out


# ------------------------------------------------------------------ сборка
def build(sea, kuwait_raw, pink, onset=None, today=None):
    today = today or date.today()
    out = {"sea": sea or {}, "kuwait": kuwait(kuwait_raw, today), "winter": WINTER,
           "imports": dict(IMPORTS), "as_of": today.isoformat(),
           "note": ("Measured here: the sea off the coast, the weather at one point in Kuwait, and the prices "
                    "of the two grains the country imports. Quoted, not measured: the winter teleconnection and "
                    "the import shares — every quoted line carries its source and date.")}
    if sea:
        s = sea
        out["sea"] = dict(s, stress=SEA_STRESS,
                          note=("The box 24–30°N, 48–56°E of the same NOAA grid; the anomaly is against the box's own "
                                f"1991–2020 climatology. Above {SEA_STRESS:g} °C desalination intakes and fisheries are "
                                "under stress; the count is of days in the last 120."))
    # живые цены: пшеница и рис из Pink Sheet, от начала события
    prices = []
    for key, name in (("wheat", "Wheat, US HRW"), ("rice", "Rice, Thai 5%")):
        rec = (pink or {}).get(key)
        if not rec or not rec.get("series"):
            continue
        ser = rec["series"]; months = sorted(ser)
        last = months[-1]
        base = ser.get(onset) if onset else None
        prices.append({"key": key, "name": rec.get("name") or name, "unit": rec.get("unit"),
                       "date": last, "value": ser[last],
                       "since_onset_pct": round(100 * (ser[last] / base - 1), 1) if base else None,
                       "onset": onset,
                       "months": months[-36:], "values": [ser[m] for m in months[-36:]]})
    out["prices"] = prices
    return out


def risks(G):
    """Правила по Заливу — в том же формате, что у air.risks."""
    out = []
    sea = (G or {}).get("sea") or {}
    if sea.get("days_over_35") and sea["days_over_35"] >= 10:
        out.append((
            f"The Gulf has spent {sea['days_over_35']} of the last 120 days above {SEA_STRESS:g} °C", 3, "now",
            f"Persian Gulf box SST peaked at {sea.get('max_sst')} °C on {sea.get('max_sst_date')}; anomaly now "
            f"{sea.get('last_anom'):+.2f} °C against the box's own 1991–2020 climatology.",
            "Water this warm stresses desalination intakes, coral and fisheries; the Gulf is shallow and heats fast, "
            "and an El Niño summer does not cool it. This is measured at the coast, not inferred from the Pacific.",
            "the box anomaly after the summer peak; the number of days above the threshold",
            {"name": "Persian Gulf SST, daily", "unit": "°C", "step": "day", "dates": sea.get("dates"),
             "values": sea.get("anom"), "analogs": sea.get("analogs") or {}},
            "climate", "gulf_sea_stress"))
    k = (G or {}).get("kuwait") or {}
    if k.get("tmax_anom_30d") is not None and k["tmax_anom_30d"] >= 1.5:
        out.append((
            f"Kuwait: the last 30 days ran {k['tmax_anom_30d']:+.1f} °C above the normal daily maximum", 2, "now",
            f"ERA5 at 29.37°N 47.98°E to {k.get('last_date')}; hottest day this year {k['hottest']['value']} °C on "
            f"{k['hottest']['date']}; {k.get('hot_days')} days at or above {HOT:g} °C against a normal {k.get('hot_days_normal')}.",
            "A hot late summer is not by itself an El Niño signal for Kuwait — the local link runs through winter "
            "rain, not summer heat — but it sets the load on power and water going into the season.",
            "the first rains from November; the winter storm count",
            {"name": "Kuwait daily maximum, anomaly", "unit": "°C", "step": "day", "dates": k.get("dates"),
             "values": k.get("tmax_anom"), "analogs": k.get("tmax_anom_analogs") or {}},
            "climate", "kuwait_heat"))
    return out


if __name__ == "__main__":
    build_clim(verbose=True)
    build_analogs(verbose=True)
    print("готово")
