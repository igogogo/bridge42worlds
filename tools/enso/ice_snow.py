# -*- coding: utf-8 -*-
"""Снег и ледники: две длинные записи для раздела «Long term».

Владелец 10.09: «есть данные по альбедо где-то, может, или по уровню ледников… берём в
основном то, что касается данных; лёгкие — исторично». Открытого ряда «альбедо планеты» нет:
CERES отдают только по учётной записи NASA Earthdata. Ближайшее, что лежит открыто и в один
файл, — площадь снежного покрова северного полушария: снег и есть главный сезонный
переключатель отражательной способности суши, и ряд идёт с 1966 года.

  · СНЕГ — Rutgers Global Snow Lab: месячная и недельная площадь снежного покрова, км²,
    северное полушарие целиком, Евразия и Северная Америка по отдельности, с ноября 1966.
    Файл текстовый, три колонки: год, месяц (или неделя года), площадь.
  · ЛЕДНИКИ — WGMS Fluctuations of Glaciers: годовой баланс массы каждого измеренного
    ледника, миллиметры водного эквивалента. Считаем годовое среднее по всем ледникам с
    измерением и накопленную сумму — это и есть «уровень ледников» в том смысле, в каком
    его меряют: сколько воды ледник потерял или набрал за год. Архив 36 МБ, годовой, поэтому
    качается ОДИН РАЗ и кладётся в raw; повторно только по ключу --refetch.

Ловушки:
  · снег меряется по площади, а не по толщине: тёплая зима с тем же покрытием даст ту же
    площадь при меньшем запасе воды;
  · у ледников последний год всегда неполный (в архиве 2024-го три записи против 175 в
    2021-м) — годы с числом измерений меньше 30 помечаем как предварительные и в тренд
    не берём;
  · баланс в WGMS хранится в мм в. э. и у отдельных ледников бывает грубым: берём медиану,
    а не среднее, и печатаем, сколько ледников вошло в год.

    python tools/enso/ice_snow.py            обновить снег, ледники из кэша
    python tools/enso/ice_snow.py --refetch  перекачать архив ледников (раз в год)
"""
import argparse
import csv
import io
import json
import statistics
import sys
import time
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "enso" / "raw"
OUT = ROOT / "data" / "enso" / "ice-snow.json"
WGMS_ZIP = RAW / "wgms-fog-2024-01.zip"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UA = {"User-Agent": "bridge42worlds-panel/1.0 (research; bridge42worlds@gmail.com)"}
SNOW = {
    "nh_month": ("https://climate.rutgers.edu/snowcover/files/moncov.nhland.txt", "Northern Hemisphere land, monthly"),
    "eurasia_month": ("https://climate.rutgers.edu/snowcover/files/moncov.eurasia.txt", "Eurasia, monthly"),
    "namerica_month": ("https://climate.rutgers.edu/snowcover/files/moncov.namgnld.txt", "North America and Greenland, monthly"),
    "nh_week": ("https://climate.rutgers.edu/snowcover/files/wkcov.nhland.txt", "Northern Hemisphere land, weekly"),
}
WGMS_URL = "https://wgms.ch/downloads/DOI-WGMS-FoG-2024-01.zip"
MIN_GLACIERS = 30            # год с меньшим числом измерений считаем предварительным


def get(url, timeout=180, tries=3):
    last = None
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as e:                                   # noqa: BLE001
            last = e
            time.sleep(4 + 4 * k)
    raise last


def snow_series(txt):
    """Три колонки «год, период, км²» → {год: {период: км²}} и месячные аномалии."""
    by_year, flat = {}, []
    for line in txt.splitlines():
        p = line.split()
        if len(p) != 3:
            continue
        try:
            y, m, v = int(p[0]), int(p[1]), float(p[2])
        except ValueError:
            continue
        if v <= 0:
            continue
        by_year.setdefault(y, {})[m] = round(v / 1e6, 3)          # млн км²
        flat.append((y, m, v / 1e6))
    return by_year, flat


def snow_stats(flat, base=(1991, 2020)):
    """Норма по периоду и аномалия последнего значения; плюс годовой ход последних лет."""
    norm = {}
    for y, m, v in flat:
        if base[0] <= y <= base[1]:
            norm.setdefault(m, []).append(v)
    norm = {m: round(statistics.mean(v), 3) for m, v in norm.items() if len(v) >= 10}
    last = flat[-1] if flat else None
    out = {"base": list(base), "norm": norm}
    if last:
        y, m, v = last
        out["last"] = {"year": y, "period": m, "value": round(v, 3),
                       "anom": round(v - norm[m], 3) if m in norm else None}
        same = sorted([(vv, yy) for yy, mm, vv in flat if mm == m], reverse=True)
        out["last"]["rank_high"] = [yy for _, yy in same].index(y) + 1
        out["last"]["of"] = len(same)
    # годовое среднее по 12 месяцам — общий ход
    ann = {}
    for y, m, v in flat:
        ann.setdefault(y, []).append(v)
    out["annual"] = {str(y): round(statistics.mean(v), 3) for y, v in sorted(ann.items()) if len(v) >= 11}
    return out


def glaciers(zip_path):
    """Годовой баланс массы: медиана по ледникам, число ледников, накопленная сумма."""
    z = zipfile.ZipFile(zip_path)
    with z.open("data/mass_balance.csv") as f:
        rd = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8", errors="replace"))
        by_year = {}
        for r in rd:
            # только строки за ледник целиком: у полос высот заданы границы
            lb, ub = (r.get("LOWER_BOUND") or "").strip(), (r.get("UPPER_BOUND") or "").strip()
            if lb not in ("9999", "") or ub not in ("9999", ""):
                continue
            try:
                y = int(r["YEAR"]); b = float(r["ANNUAL_BALANCE"])
            except (TypeError, ValueError, KeyError):
                continue
            if abs(b) > 12000:                                    # мусорные значения
                continue
            by_year.setdefault(y, []).append(b)
    years = sorted(by_year)
    out, cum = {}, 0.0
    for y in years:
        v = by_year[y]
        med = statistics.median(v)
        prelim = len(v) < MIN_GLACIERS
        if not prelim:
            cum += med
        out[str(y)] = {"median": round(med, 1), "n": len(v), "cum": round(cum, 1), "prelim": prelim}
    return out, years


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refetch", action="store_true", help="перекачать архив ледников (36 МБ, раз в год)")
    a = ap.parse_args()
    t0 = time.time()
    RAW.mkdir(parents=True, exist_ok=True)
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "snow": {}, "glaciers": {}, "errors": [],
           "sources": [
               {"key": "snow", "label": "Rutgers Global Snow Lab, Northern Hemisphere snow cover extent since 1966",
                "url": SNOW["nh_month"][0], "page": "https://climate.rutgers.edu/snowcover/"},
               {"key": "glaciers", "label": "WGMS Fluctuations of Glaciers, annual mass balance",
                "url": WGMS_URL, "page": "https://wgms.ch/data_databaseversions/"},
           ]}
    for key, (url, label) in SNOW.items():
        try:
            txt = get(url, timeout=90).decode("utf-8", "replace")
            by_year, flat = snow_series(txt)
            st = snow_stats(flat)
            st["label"] = label
            st["years"] = {str(y): v for y, v in sorted(by_year.items())}
            doc["snow"][key] = st
            print(f"  snow {key:15s} {len(flat)} points, {min(by_year)}–{max(by_year)}, "
                  f"last {st.get('last', {}).get('value')} млн км², anom {st.get('last', {}).get('anom')}")
        except Exception as e:                                   # noqa: BLE001
            doc["errors"].append(f"snow {key}: {str(e)[:100]}")
            print(f"  snow {key:15s} ERR {str(e)[:80]}")
    if a.refetch or not WGMS_ZIP.exists():
        try:
            print("  glaciers: fetching the archive (36 MB, once a year)…")
            WGMS_ZIP.write_bytes(get(WGMS_URL, timeout=900))
        except Exception as e:                                   # noqa: BLE001
            doc["errors"].append(f"glaciers fetch: {str(e)[:100]}")
    if WGMS_ZIP.exists():
        try:
            g, years = glaciers(WGMS_ZIP)
            doc["glaciers"] = {"label": "Annual mass balance, median over the measured glaciers, mm water equivalent",
                               "years": g, "first": years[0], "last": years[-1],
                               "min_glaciers": MIN_GLACIERS,
                               "note": "A negative balance means the glacier lost water over the year. The cumulative "
                                       "line adds the yearly medians and skips preliminary years."}
            solid = [y for y, v in g.items() if not v["prelim"]]
            print(f"  glaciers        {len(g)} years {years[0]}–{years[-1]}, last solid {max(solid)}: "
                  f"{g[max(solid)]['median']} mm w.e. from {g[max(solid)]['n']} glaciers, cumulative {g[max(solid)]['cum']}")
        except Exception as e:                                   # noqa: BLE001
            doc["errors"].append(f"glaciers parse: {str(e)[:100]}")
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"ice-snow.json: {OUT.stat().st_size // 1024} KB, {time.time() - t0:.0f} s"
          + (f", errors: {len(doc['errors'])}" if doc["errors"] else ""))
    try:
        import ops as OPSLOG
        OPSLOG.record_run("ice_snow", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          "partial" if doc["errors"] else "ok",
                          note=f"snow {len(doc['snow'])} series, glaciers {len(doc.get('glaciers', {}).get('years', {}))} years")
    except Exception:                                            # noqa: BLE001
        pass


if __name__ == "__main__":
    main()
