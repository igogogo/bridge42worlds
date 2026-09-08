# -*- coding: utf-8 -*-
"""Раздел истории измерений («Long record»): парниковые газы, морской лёд, глобальная температура,
уровень моря и спагетти по годам для наших суточных рядов.

Владелец 06.09: «отдельный раздел, у него другая цель — показать динамику за историю измерений,
как на climatereanalyzer, графики с множеством линий». Это фон, на котором идёт событие, не само
событие: медленные ряды, обновление раз в день из ежедневной обёртки, без модели.

Источники, все без регистрации: NOAA GML (CO2 Мауна-Лоа, CH4 и N2O глобальные), NSIDC Sea Ice
Index v4 (площадь льда по дням с 1978), Met Office HadCRUT5 (годовые аномалии с 1850; GISTEMP с
этой машины не открывается), NOAA STAR (уровень моря по альтиметрии с 1993), climatereanalyzer
(наши же суточные ряды ERA5 и OISST, уже лежат в last_good).

    python planet.py          # обновить data/enso/planet.json (кэш data/enso/planet/)

Подписи — правилами: последнее значение, изменение за год, место среди всех лет на ту же дату.
"""
import io
import json
import re
import sys
import time
import urllib.request
from datetime import date, datetime
from pathlib import Path

import numpy as np

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[1] / "data" / "enso"
CACHE = ROOT / "planet"
OUT = ROOT / "planet.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
ELNINO_YEARS = [1982, 1997, 2015, 2023, 2026]
CLIM = (1981, 2010)

SOURCES = {
    "co2": ("https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.txt",
            "NOAA GML, Mauna Loa CO2, monthly mean", "https://gml.noaa.gov/ccgg/trends/"),
    "co2_gr": ("https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_gr_mlo.txt",
               "NOAA GML, Mauna Loa CO2, annual growth", "https://gml.noaa.gov/ccgg/trends/gr.html"),
    "ch4": ("https://gml.noaa.gov/webdata/ccgg/trends/ch4/ch4_mm_gl.txt",
            "NOAA GML, global CH4, monthly mean", "https://gml.noaa.gov/ccgg/trends_ch4/"),
    "n2o": ("https://gml.noaa.gov/webdata/ccgg/trends/n2o/n2o_mm_gl.txt",
            "NOAA GML, global N2O, monthly mean", "https://gml.noaa.gov/ccgg/trends_n2o/"),
    "ice_n": ("https://noaadata.apps.nsidc.org/NOAA/G02135/north/daily/data/N_seaice_extent_daily_v4.0.csv",
              "NSIDC Sea Ice Index v4, Arctic daily extent", "https://nsidc.org/data/seaice_index"),
    "ice_s": ("https://noaadata.apps.nsidc.org/NOAA/G02135/south/daily/data/S_seaice_extent_daily_v4.0.csv",
              "NSIDC Sea Ice Index v4, Antarctic daily extent", "https://nsidc.org/data/seaice_index"),
    "hadcrut": ("https://www.metoffice.gov.uk/hadobs/hadcrut5/data/HadCRUT.5.0.2.0/analysis/diagnostics/"
                "HadCRUT.5.0.2.0.analysis.summary_series.global.annual.csv",
                "Met Office HadCRUT5, global annual anomaly against 1961–1990", "https://www.metoffice.gov.uk/hadobs/hadcrut5/"),
    # суша отдельно: тот же формат файла, что у HadCRUT5 (владелец 08.09). Суточного ряда по суше
    # у climatereanalyzer нет (проверено 08.09: land/ocean варианты t2 отдают 302), поэтому годовой.
    "crutem": ("https://www.metoffice.gov.uk/hadobs/crutem5/data/CRUTEM.5.0.2.0/diagnostics/"
               "CRUTEM.5.0.2.0.summary_series.global.annual.csv",
               "Met Office CRUTEM5, land air temperature, global annual anomaly against 1961–1990", "https://www.metoffice.gov.uk/hadobs/crutem5/"),
    "slr": ("https://www.star.nesdis.noaa.gov/socd/lsa/SeaLevelRise/slr/slr_sla_gbl_free_ref_90.csv",
            "NOAA STAR, global mean sea level from satellite altimetry",
            "https://www.star.nesdis.noaa.gov/socd/lsa/SeaLevelRise/LSA_SLR_timeseries_global.php"),
}


def _doy(d):
    import calendar
    doy = d.timetuple().tm_yday - 1
    return doy if calendar.isleap(d.year) or doy < 59 else doy + 1


def _fetch(key):
    """Свежая копия или последняя удачная; (текст, fetched, fresh, error)."""
    url, _, _ = SOURCES[key]
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f"{key}.txt"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=90) as r:
            data = r.read()
        if len(data) < 500:
            raise ValueError("too short")
        p.write_bytes(data)
        return data.decode("utf-8", "replace"), datetime.now().strftime("%Y-%m-%d %H:%M"), True, ""
    except Exception as e:                                       # noqa: BLE001
        if p.exists():
            return (p.read_text(encoding="utf-8", errors="replace"),
                    datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M"), False, str(e)[:120])
        return None, None, False, str(e)[:120]


def _nums(line):
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", line)]


# ------------------------------------------------------------------ газы
def gml_monthly(txt, unit, trend_col=5):
    """NOAA GML: год месяц десятичный среднее … тренд …; -9.99 = нет данных.
    trend_col: 4 у CO2 (deseasonalized; колонка 5 там — число дней!), 5 у CH4/N2O (trend)."""
    months, vals, trend = [], [], []
    for ln in txt.splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        f = ln.split()
        if len(f) < 4 or not re.fullmatch(r"\d{4}", f[0]):
            continue
        try:
            y, m, avg = int(f[0]), int(f[1]), float(f[3])
        except ValueError:
            continue
        if avg < 0:
            continue
        months.append(f"{y}-{m:02d}"); vals.append(round(avg, 2))
        tr = None
        try:
            v = float(f[trend_col])
            if v > 0:
                tr = round(v, 2)
        except (ValueError, IndexError):
            pass
        trend.append(tr)
    out = {"months": months, "values": vals, "trend": trend, "unit": unit}
    if vals:
        last_i = len(vals) - 1
        yo = vals[last_i - 12] if last_i >= 12 else None
        mon = months[-1][5:]
        same = [(months[i], vals[i]) for i in range(len(vals)) if months[i][5:] == mon]
        rank = 1 + sum(1 for _, v in same if v > vals[-1])
        out["last"] = {"month": months[-1], "value": vals[-1], "year_ago": yo,
                       "change_year": round(vals[-1] - yo, 2) if yo is not None else None,
                       "rank_same_month": rank, "of": len(same), "record": vals[-1] >= max(v for _, v in same)}
    return out


def gml_growth(txt):
    years, vals = [], []
    for ln in txt.splitlines():
        if ln.startswith("#") or not ln.strip():
            continue
        f = _nums(ln)
        if len(f) >= 2 and 1950 <= f[0] <= 2100:
            years.append(int(f[0])); vals.append(round(f[1], 2))
    return {"years": years, "values": vals, "unit": "ppm per year"}


# ------------------------------------------------------------------ лёд
def nsidc_daily(txt):
    """CSV NSIDC: Year, Month, Day, Extent (10^6 km²), Missing, Source. → {год: [366]} с заделкой
    пропусков до двух дней (до 1988 спутник мерил через день)."""
    years = {}
    for ln in txt.splitlines():
        f = [x.strip() for x in ln.split(",")]
        if len(f) < 4 or not f[0].isdigit():
            continue
        try:
            d = date(int(f[0]), int(f[1]), int(f[2])); v = float(f[3])
        except ValueError:
            continue
        if v <= 0:
            continue
        years.setdefault(d.year, [None] * 366)[_doy(d)] = round(v, 3)
    out = {}
    for y, arr in years.items():
        a = np.array([np.nan if v is None else v for v in arr], float)
        idx = np.where(np.isfinite(a))[0]
        if len(idx) < 30:
            continue
        # линейная заделка коротких пропусков (≤ 2 дня) внутри измеренного
        for i in range(len(a)):
            if np.isnan(a[i]):
                lo = i - 1
                while lo >= 0 and np.isnan(a[lo]):
                    lo -= 1
                hi = i + 1
                while hi < len(a) and np.isnan(a[hi]):
                    hi += 1
                if lo >= 0 and hi < len(a) and hi - lo <= 3:
                    a[i] = a[lo] + (a[hi] - a[lo]) * (i - lo) / (hi - lo)
        out[str(y)] = [None if not np.isfinite(v) else round(float(v), 3) for v in a]
    return out


def _spaghetti_summary(years, clim_years, higher_is_worse):
    """Сводка для спагетти: последний день текущего года против медианы нормы и всех лет."""
    ys = sorted(int(y) for y in years)
    cur = ys[-1]
    arr = years[str(cur)]
    last_i = max(i for i, v in enumerate(arr) if v is not None)
    grid = np.array([[np.nan if v is None else v for v in years[str(y)]] for y in ys], float)
    ci = [k for k, y in enumerate(ys) if clim_years[0] <= y <= clim_years[1]]
    med = np.nanmedian(grid[ci], axis=0) if ci else np.full(366, np.nan)
    same = [(y, years[str(y)][last_i]) for y in ys if years[str(y)][last_i] is not None]
    v = arr[last_i]
    lower = sum(1 for y, x in same if x < v)
    higher = sum(1 for y, x in same if x > v)
    rec = min(same, key=lambda t: t[1]) if higher_is_worse is False else max(same, key=lambda t: t[1])
    from datetime import timedelta
    d = date(cur, 1, 1) + timedelta(days=last_i if (cur % 4 == 0 and (cur % 100 != 0 or cur % 400 == 0)) or last_i < 59 else last_i - 1)
    return {"year": cur, "date": d.isoformat(), "value": v, "doy": last_i,
            "median_norm": None if not np.isfinite(med[last_i]) else round(float(med[last_i]), 3),
            "rank_low": lower + 1, "rank_high": higher + 1, "of": len(same),
            "extreme": {"year": rec[0], "value": rec[1]}}, [None if not np.isfinite(x) else round(float(x), 3) for x in med]


# ------------------------------------------------------------------ температура, уровень моря
def hadcrut_annual(txt):
    years, vals, lo, hi = [], [], [], []
    for ln in txt.splitlines():
        f = ln.split(",")
        if len(f) < 2 or not f[0].strip().isdigit():
            continue
        try:
            years.append(int(f[0])); vals.append(round(float(f[1]), 3))
            lo.append(round(float(f[2]), 3)); hi.append(round(float(f[3]), 3))
        except (ValueError, IndexError):
            vals.append(None); lo.append(None); hi.append(None)
    out = {"years": years, "values": vals, "low": lo, "high": hi, "unit": "°C", "baseline": "1961–1990"}
    if vals:
        order = sorted([(v, y) for v, y in zip(vals, years) if v is not None], reverse=True)
        rank = 1 + [y for _, y in order].index(years[-1])
        out["last"] = {"year": years[-1], "value": vals[-1], "rank": rank, "of": len(order),
                       "warmest": {"year": order[0][1], "value": order[0][0]}}
    return out


def slr_series(txt):
    """NOAA STAR: строки с десятичным годом и значением (мм). Берём первую пару чисел."""
    xs, ys = [], []
    for ln in txt.splitlines():
        if ln.startswith("#") or not ln.strip():
            continue
        f = _nums(ln)
        if len(f) >= 2 and 1990 <= f[0] <= 2100:
            xs.append(round(f[0], 4)); ys.append(round(f[1], 2))
    out = {"years": xs, "values": ys, "unit": "mm"}
    if len(xs) > 40:
        x = np.array(xs); y = np.array(ys)
        m = x >= x[-1] - 10
        rate = float(np.polyfit(x[m], y[m], 1)[0]) if m.sum() > 10 else None
        rate_all = float(np.polyfit(x, y, 1)[0])
        out["last"] = {"year": xs[-1], "value": ys[-1], "since_start": round(ys[-1] - ys[0], 1), "start": xs[0],
                       "rate_10y_mm_per_year": None if rate is None else round(rate, 2),
                       "rate_all_mm_per_year": round(rate_all, 2)}
    return out


def our_daily(key, label):
    """Наши суточные ряды из last_good: спагетти по годам + норма 1991–2020."""
    import sources as S
    p = S.LAST / f"{key}.json"
    if not p.exists():
        return None
    ds = S.read_cr_json(p)
    years = {str(y): [None if not np.isfinite(v) else round(float(v), 3) for v in arr] for y, arr in ds["years"].items()}
    clim = [None if not np.isfinite(v) else round(float(v), 3) for v in ds["clim"]] if ds.get("clim") is not None else None
    summ, _ = _spaghetti_summary(years, (1991, 2020), True)
    summ["label"] = label
    return {"label": label, "unit": "°C", "years": years, "clim": clim, "clim_years": [1991, 2020],
            "last": summ, "last_date": str(ds.get("last_date"))}


# ------------------------------------------------------------------ сборка
def build(verbose=True):
    t0 = time.time()
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "elnino_years": ELNINO_YEARS,
           "gases": {}, "ice": {}, "temperature": {}, "sea_level": None, "sources": [], "errors": []}
    got = {}
    for key in SOURCES:
        txt, fetched, fresh, err = _fetch(key)
        got[key] = txt
        doc["sources"].append({"key": key, "label": SOURCES[key][1], "url": SOURCES[key][0], "page": SOURCES[key][2],
                               "fetched": fetched, "fresh": fresh, "error": err})
        if verbose:
            print(f"  {'ok ' if fresh else 'OLD'} {key}: {len(txt) if txt else 0} bytes {err}")
    try:
        if got["co2"]:
            doc["gases"]["co2"] = gml_monthly(got["co2"], "ppm", trend_col=4)
            if got["co2_gr"]:
                doc["gases"]["co2"]["growth"] = gml_growth(got["co2_gr"])
        if got["ch4"]:
            doc["gases"]["ch4"] = gml_monthly(got["ch4"], "ppb")
        if got["n2o"]:
            doc["gases"]["n2o"] = gml_monthly(got["n2o"], "ppb")
    except Exception as e:                                       # noqa: BLE001
        doc["errors"].append(f"gases: {str(e)[:120]}")
    for key, name in (("ice_n", "north"), ("ice_s", "south")):
        try:
            if got[key]:
                years = nsidc_daily(got[key])
                summ, med = _spaghetti_summary(years, CLIM, False)
                doc["ice"][name] = {"label": ("Arctic" if name == "north" else "Antarctic") + " sea ice extent",
                                    "unit": "million km²", "years": years, "clim": med, "clim_years": list(CLIM), "last": summ}
        except Exception as e:                                   # noqa: BLE001
            doc["errors"].append(f"{key}: {str(e)[:120]}")
    try:
        if got["hadcrut"]:
            doc["temperature"]["hadcrut"] = hadcrut_annual(got["hadcrut"])
    except Exception as e:                                       # noqa: BLE001
        doc["errors"].append(f"hadcrut: {str(e)[:120]}")
    try:
        if got.get("crutem"):
            doc["temperature"]["crutem"] = hadcrut_annual(got["crutem"])
    except Exception as e:                                       # noqa: BLE001
        doc["errors"].append(f"crutem: {str(e)[:120]}")
    for key, label in (("t2_world", "Land+ocean, 2 m (ERA5)"), ("sst_world", "Ocean, 60°S–60°N (OISST)")):
        try:
            blk = our_daily(key, label)
            if blk:
                doc["temperature"][key] = blk
        except Exception as e:                                   # noqa: BLE001
            doc["errors"].append(f"{key}: {str(e)[:120]}")
    try:
        if got["slr"]:
            doc["sea_level"] = slr_series(got["slr"])
    except Exception as e:                                       # noqa: BLE001
        doc["errors"].append(f"slr: {str(e)[:120]}")
    for s in doc["sources"]:
        k = s["key"]
        rng = None
        if k in ("co2", "ch4", "n2o") and doc["gases"].get(k):
            m = doc["gases"][k]["months"]; rng = (m[0], m[-1])
        elif k == "co2_gr" and doc["gases"].get("co2", {}).get("growth"):
            g = doc["gases"]["co2"]["growth"]; rng = (str(g["years"][0]), str(g["years"][-1]))
        elif k in ("ice_n", "ice_s"):
            b = doc["ice"].get("north" if k == "ice_n" else "south")
            if b:
                ys = sorted(b["years"]); rng = (ys[0], b["last"]["date"])
        elif k in ("hadcrut", "crutem") and doc["temperature"].get(k):
            h = doc["temperature"][k]; rng = (str(h["years"][0]), str(h["years"][-1]))
        elif k == "slr" and doc["sea_level"]:
            sl = doc["sea_level"]; rng = (str(sl["years"][0]), str(sl["years"][-1]))
        s["data_from"], s["data_to"] = (rng or (None, None))
    doc["note"] = ("The long record is the background the event runs on, not the event: greenhouse gases, sea ice, "
                   "global temperature and sea level over the whole history of measurement. Updated daily by the light "
                   "run wrapper, no model; every caption is a rule over the series itself.")
    doc["secs"] = int(time.time() - t0)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    try:
        import ops as OPSLOG
        OPSLOG.record_run("planet", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          "ok" if not doc["errors"] else "partial", note=", ".join(doc["errors"])[:160],
                          stale=[s["key"] for s in doc["sources"] if not s["fresh"]])
    except Exception as e:                                       # noqa: BLE001
        print("  журнал прогонов не обновлён:", str(e)[:100])
    if verbose:
        print(f"planet.json: {OUT.stat().st_size // 1024} КБ, {doc['secs']} с; ошибок {len(doc['errors'])}", doc["errors"] or "")
    return doc


if __name__ == "__main__":
    build()
