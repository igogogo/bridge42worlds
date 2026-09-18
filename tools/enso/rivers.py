# -*- coding: utf-8 -*-
"""Реки, завязанные на Эль-Ниньо: суточный расход GloFAS против его же климатологии.

Владелец 18.09 (Guardian о докладе WMO «State of Global Water Resources 2025»: 36 % площади
бассейнов ниже нормы, только треть рек в норме): «можем ли мы эти данные начать подкручивать».
Доклад WMO годовой и модельный (13 гидрологических моделей). Живой эквивалент той же природы —
GloFAS (Copernicus), отдаётся через Open-Meteo Flood API без ключа: суточный расход по любой
точке с 2000 года. Это МОДЕЛЬНЫЙ расход, не гидропост, и панель так и подписывает.

Что считаем по каждой реке: климатология по дню года (медиана, p10/p25/p75/p90 в окне ±7 суток,
2000–2020), сегодняшний расход и его процентиль, среднее за 30 суток и его процентиль, ряды
за последние два года и тот же календарь в 2015-м и 2023-м (1982/1997 у GloFAS нет — ряд с
2000 года). Итог для доски: сколько из наших рек ниже p25 и выше p75 по 30-суточному среднему.

РУСЛОВАЯ ЯЧЕЙКА. Сетка GloFAS 0,05°; точка гидропоста почти всегда попадает в сухую ячейку
рядом с руслом (Обидус: 0,1 м³/с против 78 000 в соседней). Ищем максимум в окне 5×5 вокруг
заявленной точки один раз и запоминаем в rivers-cells.json.
"""
import json
import statistics
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio   # noqa: E402
OUT = ROOT / "data" / "enso" / "rivers.json"
CELLS = ROOT / "data" / "enso" / "raw" / "rivers-cells.json"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = "https://flood-api.open-meteo.com/v1/flood"
UA = {"User-Agent": "bridge42worlds-panel/1.0 (research; bridge42worlds@gmail.com)"}
CLIM = (2000, 2020)
ANALOGS = (2015, 2023)

# (ключ, имя, точка у гидропоста, за что эта река отвечает у Эль-Ниньо)
RIVERS = [
    ("amazon", "Amazon at Óbidos", -1.92, -55.50, "the largest river on Earth; El Niño dries the basin's north and east"),
    ("parana", "Paraná at Corrientes", -27.47, -58.85, "south-east South America is wetter in El Niño; floods 1982–83, 1997–98, 2015–16"),
    ("magdalena", "Magdalena, Colombia", 9.25, -74.90, "northern Colombia dries in El Niño"),
    ("orinoco", "Orinoco at Ciudad Bolívar", 8.15, -63.55, "the Venezuelan llanos dry in El Niño"),
    ("mississippi", "Mississippi at Vicksburg", 32.32, -90.91, "the southern United States is wetter in El Niño winters"),
    ("nile", "Blue Nile at Khartoum", 15.60, 32.55, "the Ethiopian highland rains weaken in El Niño"),
    ("zambezi", "Zambezi at Tete", -16.15, 33.58, "southern Africa dries in El Niño"),
    ("congo", "Congo at Kinshasa", -4.30, 15.30, "central Africa, a weak and mixed signal"),
    ("mekong", "Mekong at Phnom Penh", 11.56, 104.93, "Indochina dries in El Niño; the Tonlé Sap flood pulse shrinks"),
    ("ganges", "Ganges at Farakka", 24.80, 87.93, "the Indian monsoon weakens in El Niño"),
    ("indus", "Indus at Sukkur", 27.70, 68.85, "the Pakistan monsoon weakens in El Niño"),
    ("yangtze", "Yangtze at Datong", 30.77, 117.62, "the Yangtze floods in the summer after an El Niño (1998, 2016)"),
    ("murray", "Murray at Wentworth", -34.10, 141.90, "south-east Australia dries in El Niño"),
    ("orange", "Orange at Upington", -28.45, 21.25, "southern Africa dries in El Niño"),
]


def get(params, tries=3):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    last = None
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(API + "?" + q, headers=UA), timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:                                   # noqa: BLE001
            last = e
            # 429 у Open-Meteo — минутный лимит; ждём дольше, чем при обычной осечке (18.09: Ганг и Инд отвалились)
            time.sleep(25 + 20 * k if "429" in str(e) else 3 + 3 * k)
    raise last


def find_cell(lat, lon):
    """Русловая ячейка: максимум сегодняшнего расхода в окне 11×11 по 0,05° (±0,25°): при 5×5
    Магдалена попала в ручей на 2 м³/с."""
    lats, lons = [], []
    for i in range(-5, 6):
        for j in range(-5, 6):
            lats.append(round(lat + 0.05 * i, 3)); lons.append(round(lon + 0.05 * j, 3))
    d = get({"latitude": ",".join(map(str, lats)), "longitude": ",".join(map(str, lons)),
             "daily": "river_discharge", "past_days": "3", "forecast_days": "1"})
    d = d if isinstance(d, list) else [d]
    best = None
    for p in d:
        vals = [v for v in (p.get("daily") or {}).get("river_discharge") or [] if v is not None]
        if not vals:
            continue
        m = max(vals)
        if best is None or m > best[0]:
            best = (m, p["latitude"], p["longitude"])
    return best


def _pct(v, sample):
    s = sorted(sample)
    if not s:
        return None
    below = sum(1 for x in s if x < v)
    return round(100.0 * below / len(s), 1)


def _q(s, p):
    s = sorted(s)
    if not s:
        return None
    k = (len(s) - 1) * p
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def main():
    t0 = time.time()
    cells = json.loads(CELLS.read_text(encoding="utf-8")) if CELLS.exists() else {}
    today = date.today()
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "items": [], "errors": [],
           "clim_years": list(CLIM), "analog_years": list(ANALOGS),
           "source": {"label": "GloFAS v4 river discharge (Copernicus Emergency Management Service) via the Open-Meteo Flood API",
                      "page": "https://open-meteo.com/en/docs/flood-api", "since": "2000"},
           "wmo": {"report": "WMO State of Global Water Resources 2025 (published September 2026)", "as_reported":
                   "36 % of the global river-basin area had below- or much-below-normal flow in 2025, 21 % above; only about a third of rivers were in the normal range, the fewest since 1991; terrestrial water storage 42 % below normal; simulations from 13 global hydrological models",
                   "note": "reported by the WMO, not measured here; the annual report has no live feed, so the panel follows the same model family day by day instead"},
           "note": ("Modelled river discharge, not gauge readings: GloFAS runs a hydrological model on observed weather, "
                    "so the level is approximate and the anomaly against the model's own climatology is what to read. "
                    "The record starts in 2000, so 1982 and 1997 cannot be shown; 2015 and 2023 can.")}
    for key, name, lat, lon, why in RIVERS:
        try:
            c = cells.get(key)
            if not c:
                best = find_cell(lat, lon)
                if not best:
                    raise RuntimeError("no river cell found")
                c = {"lat": best[1], "lon": best[2], "today": best[0], "found": today.isoformat()}
                cells[key] = c
                safeio.write_text(CELLS, json.dumps(cells, ensure_ascii=False, indent=1))
            d = get({"latitude": c["lat"], "longitude": c["lon"], "daily": "river_discharge",
                     "start_date": f"{CLIM[0]}-01-01", "end_date": today.isoformat()})
            dates = d["daily"]["time"]; vals = d["daily"]["river_discharge"]
            ser = [(dt, v) for dt, v in zip(dates, vals) if v is not None]
            if len(ser) < 3000:
                raise RuntimeError(f"only {len(ser)} days")
            by_doy = {}
            for dt, v in ser:
                dd = date.fromisoformat(dt)
                if CLIM[0] <= dd.year <= CLIM[1]:
                    by_doy.setdefault(dd.timetuple().tm_yday, []).append(v)
            clim = {}
            for doy in range(1, 367):
                pool = []
                for k in range(-7, 8):
                    pool += by_doy.get(((doy - 1 + k) % 366) + 1, [])
                if len(pool) >= 20:
                    clim[doy] = {"p10": _q(pool, .1), "p25": _q(pool, .25), "p50": _q(pool, .5), "p75": _q(pool, .75), "p90": _q(pool, .9), "pool": pool}
            last_dt, last_v = ser[-1]
            ldoy = date.fromisoformat(last_dt).timetuple().tm_yday
            last30 = [v for dt, v in ser[-30:]]
            m30 = sum(last30) / len(last30)
            # 30-суточное среднее против таких же 30-суточных средних по годам климатологии
            m30_pool = []
            for y in range(CLIM[0], CLIM[1] + 1):
                end = date(y, 1, 1) + timedelta(days=ldoy - 1)
                w = [v for dt, v in ser if end - timedelta(days=29) <= date.fromisoformat(dt) <= end]
                if len(w) >= 25:
                    m30_pool.append(sum(w) / len(w))
            cl = clim.get(ldoy) or {}
            two_years = [(dt, round(v)) for dt, v in ser if date.fromisoformat(dt) >= today - timedelta(days=730)]
            # тот же календарный отрезок в годах-аналогах: сдвиг на целые годы от первого дня ряда
            analogs = {}
            first_dt = date.fromisoformat(two_years[0][0])
            for y in ANALOGS:
                shift = first_dt.year - y
                a0 = date(first_dt.year - shift, first_dt.month, min(first_dt.day, 28))
                a1 = a0 + timedelta(days=len(two_years) - 1)
                analogs[str(y)] = [(dt, round(v)) for dt, v in ser if a0 <= date.fromisoformat(dt) <= a1]
            doc["items"].append({
                "key": key, "name": name, "why": why, "lat": c["lat"], "lon": c["lon"], "gauge_lat": lat, "gauge_lon": lon,
                "last": {"date": last_dt, "value": round(last_v), "pct": _pct(last_v, cl.get("pool") or []), "p50": round(cl.get("p50") or 0)},
                "mean30": {"value": round(m30), "pct": _pct(m30, m30_pool), "n_years": len(m30_pool),
                           "p50": round(_q(m30_pool, .5)) if m30_pool else None},
                "clim": {"doy": list(range(1, 367)), "p10": [round(clim[d]["p10"]) if d in clim else None for d in range(1, 367)],
                         "p50": [round(clim[d]["p50"]) if d in clim else None for d in range(1, 367)],
                         "p90": [round(clim[d]["p90"]) if d in clim else None for d in range(1, 367)]},
                "series": two_years, "analogs": analogs,
                "record_low_30d": bool(m30_pool) and m30 < min(m30_pool), "record_high_30d": bool(m30_pool) and m30 > max(m30_pool),
            })
            p = doc["items"][-1]
            print(f"  {name:26s} {p['last']['value']:>9,} m³/s on {last_dt}  today p{p['last']['pct']:.0f}  30-day p{p['mean30']['pct']:.0f}"
                  + ("  RECORD LOW 30 d" if p["record_low_30d"] else "") + ("  RECORD HIGH 30 d" if p["record_high_30d"] else ""))
            time.sleep(2.5)   # минутный лимит Open-Meteo
        except Exception as e:                                   # noqa: BLE001
            doc["errors"].append(f"{key}: {str(e)[:120]}")
            print(f"  {name:26s} ERR {str(e)[:90]}")
    ok = [p for p in doc["items"] if p["mean30"]["pct"] is not None]
    doc["board"] = {"n": len(ok), "below_p25": sum(1 for p in ok if p["mean30"]["pct"] < 25), "above_p75": sum(1 for p in ok if p["mean30"]["pct"] > 75),
                    "record_low": [p["key"] for p in ok if p["record_low_30d"]], "record_high": [p["key"] for p in ok if p["record_high_30d"]],
                    "as_of": max((p["last"]["date"] for p in ok), default=None)}
    safeio.write_text(OUT, json.dumps(doc, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
    print(f"rivers.json: {len(doc['items'])} rivers, board {doc['board']}, {OUT.stat().st_size // 1024} KB, {time.time() - t0:.0f} s"
          + (f", errors: {len(doc['errors'])}" if doc["errors"] else ""))
    try:
        import ops as OPSLOG
        OPSLOG.record_run("rivers", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "partial" if doc["errors"] else "ok",
                          note=f"{len(doc['items'])} rivers; {doc['board']['below_p25']} below p25, {doc['board']['above_p75']} above p75"
                          + ("; " + "; ".join(doc["errors"]) if doc["errors"] else ""))
    except Exception:                                            # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
