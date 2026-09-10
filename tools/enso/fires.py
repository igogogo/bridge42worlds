# -*- coding: utf-8 -*-
"""Активные пожары со спутников: суточный счёт по регионам, накопление ряда.

Владелец 10.09: «поищи по площади лесных пожаров, по состоянию биосферы в целом» и «берём в
основном то, что касается данных; лёгкие — исторично, подробные — за 25–26 годы». Площадь
выгоревшего в открытом виде не отдают ни EFFIS, ни Global Forest Watch (нужен ключ). А вот
активные очаги NASA FIRMS лежат открыто: глобальный CSV за последние сутки по трём приборам,
с координатами и мощностью излучения (FRP). Из них считается то, что и нужно панели: сколько
очагов и сколько мощности сегодня в каждом крупном пожарном регионе — и как это меняется день
ото дня. Ряд копится с первого запуска (подробное — за 2026), истории у открытого канала нет.

Почему это про Эль-Ниньо. Пожарные сезоны Индонезии, Амазонии и Австралии — классический
след события: засуха над Приморским континентом и на севере Амазонии приходит вместе с тёплым
востоком Пацифики. Сравнивать регион надо с его собственным ходом по дням, а не регионы между
собой: в Африке очагов всегда больше всех, это саванные палы, а не бедствие.

Ловушки, заложенные сразу:
  · очаг ≠ площадь: FRP это мощность излучения, а не гектары; в подписи так и сказано;
  · облачность и полоса обзора пропускают часть очагов — суточные числа шумные, сравнение
    ведём по скользящему среднему за 7 суток;
  · MODIS (Aqua/Terra) и VIIRS (SNPP, NOAA-20) видят по-разному: считаем раздельно, вместе
    не складываем.

    python tools/enso/fires.py            снять сутки и дописать ряд
    python tools/enso/fires.py --plan     показать регионы и не ходить в сеть
"""
import argparse
import csv
import io
import json
import sys
import time
import urllib.request
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "enso" / "raw" / "fires"
OUT = ROOT / "data" / "enso" / "fires.json"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UA = {"User-Agent": "bridge42worlds-panel/1.0 (research; bridge42worlds@gmail.com)"}
SATS = {
    "viirs_snpp": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_24h.csv",
    "viirs_n20": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_24h.csv",
    "modis": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_24h.csv",
}
# Регионы, у которых пожарный сезон завязан на Эль-Ниньо, плюс крупные для фона.
# (юг, север, запад, восток) в градусах; долгота −180…180.
REGIONS = [
    ("amazon", "Amazon basin", -18, 6, -75, -45),
    ("cerrado", "Cerrado and southern Brazil", -33, -18, -60, -40),
    ("maritime", "Maritime Continent (Indonesia, Borneo, PNG)", -11, 8, 95, 152),
    ("mainland_sea", "Mainland Southeast Asia", 8, 29, 92, 110),
    ("australia", "Australia", -44, -10, 112, 154),
    ("central_africa", "Central Africa", -15, 8, 8, 42),
    ("west_africa", "West Africa (Sahel)", 4, 16, -18, 8),
    ("siberia", "Siberia and the Russian Far East", 50, 73, 60, 180),
    ("north_america", "North America west", 30, 65, -170, -100),
    ("mediterranean", "Mediterranean", 30, 47, -10, 42),
    ("india", "India and Pakistan", 6, 35, 68, 92),
    ("central_america", "Central America and Mexico", 7, 32, -118, -77),
]


def get(url, tries=3):
    last = None
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
                return r.read()
        except Exception as e:                                   # noqa: BLE001
            last = e
            time.sleep(5 + 5 * k)
    raise last


def parse(body):
    """CSV FIRMS → список (lat, lon, frp, acq_date, confidence, daynight)."""
    rows = []
    rd = csv.DictReader(io.StringIO(body.decode("utf-8", "replace")))
    for r in rd:
        try:
            lat = float(r["latitude"]); lon = float(r["longitude"])
            frp = float(r.get("frp") or 0)
        except (TypeError, ValueError, KeyError):
            continue
        rows.append((lat, lon, frp, r.get("acq_date") or "", (r.get("confidence") or ""), r.get("daynight") or ""))
    return rows


def in_region(lat, lon, reg):
    _, _, s, n, w, e = reg
    if not (s <= lat <= n):
        return False
    if w <= e:
        return w <= lon <= e
    return lon >= w or lon <= e                                   # регион через 180-й меридиан


def aggregate(rows):
    """Счёт очагов и сумма мощности по регионам; отдельно — сильные очаги (FRP ≥ 100 МВт)."""
    out = {}
    for reg in REGIONS:
        out[reg[0]] = {"n": 0, "frp": 0.0, "strong": 0}
    total = {"n": 0, "frp": 0.0, "strong": 0}
    for lat, lon, frp, _d, _c, _dn in rows:
        total["n"] += 1
        total["frp"] += frp
        if frp >= 100:
            total["strong"] += 1
        for reg in REGIONS:
            if in_region(lat, lon, reg):
                b = out[reg[0]]
                b["n"] += 1
                b["frp"] += frp
                if frp >= 100:
                    b["strong"] += 1
    for b in list(out.values()) + [total]:
        b["frp"] = round(b["frp"], 1)
    return out, total


def thin_points(rows, keep=1400):
    """Точки для глобуса: самые мощные очаги, чтобы шар не тонул в саванных палах."""
    strong = sorted(rows, key=lambda r: -r[2])[:keep]
    return [[round(r[0], 2), round(r[1], 2), round(r[2])] for r in strong]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    a = ap.parse_args()
    if a.plan:
        for r in REGIONS:
            print(f"  {r[0]:16s} {r[1]:44s} lat {r[2]:>4}…{r[3]:<4} lon {r[4]:>5}…{r[5]}")
        print(f"{len(REGIONS)} regions · {len(SATS)} instruments")
        return
    RAW.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    today = date.today().isoformat()
    doc = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {
        "regions": [{"id": r[0], "name": r[1], "box": [r[2], r[3], r[4], r[5]]} for r in REGIONS],
        "series": {}, "points": {}, "note": "", "sources": {},
    }
    doc["regions"] = [{"id": r[0], "name": r[1], "box": [r[2], r[3], r[4], r[5]]} for r in REGIONS]
    got, errs = {}, []
    for sat, url in SATS.items():
        try:
            body = get(url)
            rows = parse(body)
            reg, total = aggregate(rows)
            got[sat] = {"regions": reg, "total": total, "n_rows": len(rows)}
            if sat == "viirs_snpp":
                doc["points"] = {"date": today, "instrument": sat, "items": thin_points(rows)}
            doc.setdefault("series", {}).setdefault(sat, {})[today] = {
                "total": total, "regions": {k: v["n"] for k, v in reg.items()},
                "frp": {k: v["frp"] for k, v in reg.items()},
            }
            print(f"  {sat:11s} {len(rows):>7} hotspots · strongest region "
                  f"{max(reg.items(), key=lambda kv: kv[1]['n'])[0]}")
        except Exception as e:                                   # noqa: BLE001
            errs.append(f"{sat}: {str(e)[:90]}")
            print(f"  {sat:11s} ERR {str(e)[:80]}")
    # ряд держим за два года: подробное это 2025–2026, старше открытый канал и не отдаёт
    for sat, days in doc.get("series", {}).items():
        for d in sorted(days)[:-800]:
            days.pop(d, None)
    doc["built"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    doc["last_date"] = today
    doc["errors"] = errs
    doc["sources"] = {k: v for k, v in SATS.items()}
    doc["note"] = ("Active fire detections from NASA FIRMS, the open 24-hour global files of three "
                   "instruments. A detection is not an area burnt: FRP is radiative power in megawatts. "
                   "Cloud and swath gaps make single days noisy - read the seven-day mean. Compare a "
                   "region with its own course, not regions with each other: African savannah burning "
                   "is a yearly practice, not a disaster.")
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    days = len(next(iter(doc.get("series", {}).values()), {}))
    print(f"fires.json: {days} day(s), {OUT.stat().st_size // 1024} KB, {time.time() - t0:.0f} s"
          + (f", errors: {len(errs)}" if errs else ""))
    try:
        import ops as OPSLOG
        OPSLOG.record_run("fires", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          "partial" if errs else "ok",
                          note=f"{days} days, {sum(g['n_rows'] for g in got.values())} hotspots" + ("; " + "; ".join(errs) if errs else ""))
    except Exception:                                            # noqa: BLE001
        pass


if __name__ == "__main__":
    main()
