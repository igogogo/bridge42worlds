# -*- coding: utf-8 -*-
"""Водяной пар над тропиками и нашими боксами: ERA5 через Open-Meteo, суточно с 1991 года.

Владелец 18.09 (Guardian о C3S: 27,35 кг/м² в августе — рекорд ERA5 с 1979, прежний июль 2024;
«тропические океаны и Эль-Ниньо — главный вклад»). Глобальный ряд ERA5 лежит в CDS за
регистрацией; здесь — тот же ERA5 через Open-Meteo (без ключа), поле
total_column_integrated_water_vapour, почасово по точкам. Глобальное среднее из точек мы НЕ
подделываем: считаем то, что честно даёт редкая сетка — тропический пояс 20°S–20°N (5 широт ×
12 долгот, вес cos φ) и наши боксы (Niño 1+2, 3, 3.4, 4, тёплый бассейн) по 3×5 точкам.
Цифру C3S панель цитирует как «reported», не как своё измерение.

Забор одноразовый по годам в data/enso/raw/vapour/<год>.json (суточные средние по точкам,
компактно); потом дописываются только новые сутки. Один вызов = все точки одного года
(~13 МБ, полминуты); весь пояс с 1991-го — около 40 вызовов.
"""
import json
import math
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio   # noqa: E402
OUT = ROOT / "data" / "enso" / "vapour.json"
RAW = ROOT / "data" / "enso" / "raw" / "vapour"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = "https://archive-api.open-meteo.com/v1/archive"
UA = {"User-Agent": "bridge42worlds-panel/1.0 (research; bridge42worlds@gmail.com)"}
FIRST_YEAR = 1991
CLIM = (1991, 2020)
ANALOGS = (1997, 2015, 2023)
VAR = "total_column_integrated_water_vapour"

# регионы: (ключ, имя, широты, долготы, «почему»)
REGIONS = {
    "tropics": ("Tropics 20°S–20°N", [-20, -10, 0, 10, 20], list(range(-180, 180, 30)),
                "the belt C3S names as the source of the record: warm oceans evaporate, the air holds it"),
    "nino34": ("Niño 3.4", [-4, 0, 4], [-165, -155, -145, -135, -125], "the box the event is measured in"),
    "nino3": ("Niño 3", [-4, 0, 4], [-145, -130, -115, -100, -95], "the eastern box, where the warm water surfaces"),
    "nino4": ("Niño 4", [-4, 0, 4], [160, 170, 180, -170, -160], "the western box, the warm pool's edge"),
    "nino12": ("Niño 1+2", [-8, -5, -2], [-90, -87, -84, -82, -81], "the coast of Peru"),
    "warmpool": ("Warm pool", [-4, 0, 4], [130, 140, 150, 160, 170], "where convection lives in a normal year"),
}
C3S = {"value": 27.35, "unit": "kg/m²", "month": "2026-08", "previous": {"value": 27.31, "month": "2024-07"},
       "since": 1979, "source": "Copernicus Climate Change Service, ERA5, as reported 18 September 2026",
       "quote": "the highest global monthly mean column water vapour on the ERA5 record"}


def points(reg):
    _, lats, lons, _ = REGIONS[reg]
    out = []
    for la in lats:
        for lo in lons:
            out.append((la, lo))
    return out


def get(lat_list, lon_list, y0, y1, tries=3):
    q = (f"latitude={','.join(map(str, lat_list))}&longitude={','.join(map(str, lon_list))}"
         f"&start_date={y0}&end_date={y1}&hourly={VAR}")
    last = None
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(API + "?" + q, headers=UA), timeout=300) as r:
                d = json.loads(r.read().decode("utf-8"))
                return d if isinstance(d, list) else [d]
        except Exception as e:                                   # noqa: BLE001
            last = e
            # 429 — исчерпана квота Open-Meteo на тяжёлые почасовые запросы (18.09: забор встал на
            # 2004-м после 13 лет). Ждём долго; если не отпустило — год остаётся на следующий прогон.
            time.sleep(120 + 120 * k if "429" in str(e) else 10 + 10 * k)
    raise last


def daily_means(p):
    """Суточные средние из почасового ряда одной точки: {дата: кг/м²}."""
    hs, vs = p["hourly"]["time"], p["hourly"][VAR]
    acc = {}
    for t, v in zip(hs, vs):
        if v is None:
            continue
        d = t[:10]
        a = acc.setdefault(d, [0.0, 0])
        a[0] += v; a[1] += 1
    return {d: round(a[0] / a[1], 2) for d, a in acc.items() if a[1] >= 12}


def fetch_year(year, end=None):
    """Все точки всех регионов за год одним-двумя вызовами; пишет raw/vapour/<год>.json."""
    RAW.mkdir(parents=True, exist_ok=True)
    f = RAW / f"{year}.json"
    y0 = f"{year}-01-01"
    y1 = end or f"{year}-12-31"
    allpts = []
    for reg in REGIONS:
        for la, lo in points(reg):
            if (la, lo) not in allpts:
                allpts.append((la, lo))
    out = {"year": year, "to": y1, "points": {}}
    # не больше 40 точек за вызов, чтобы ответ не переваливал за десяток мегабайт
    for i in range(0, len(allpts), 40):
        chunk = allpts[i:i + 40]
        res = get([p[0] for p in chunk], [p[1] for p in chunk], y0, y1)
        for (la, lo), p in zip(chunk, res):
            out["points"][f"{la},{lo}"] = daily_means(p)
        time.sleep(2)
    safeio.write_text(f, json.dumps(out, separators=(",", ":")))
    return out


MAX_NEW_YEARS = 4          # сколько недостающих лет добирать за один прогон: квота Open-Meteo дневная


def load_years(today, max_new=MAX_NEW_YEARS):
    """Годы с диска; недостающие — с сети, но В ПОРЯДКЕ НУЖНОСТИ: сначала текущий год (без него
    сцены нет), потом аналоги (1997, 2015, 2023), потом климатология с самых свежих лет назад.
    За прогон добираем не больше max_new лет: квота Open-Meteo дневная, и лучше сцена с частичной
    климатологией сегодня, чем полная через неделю (18.09)."""
    years = {}
    order = [today.year] + [y for y in ANALOGS if y != today.year] + [y for y in range(today.year - 1, FIRST_YEAR - 1, -1) if y not in ANALOGS]
    fetched = 0
    for y in order:
        f = RAW / f"{y}.json"
        d = json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
        want_to = (today - timedelta(days=6)).isoformat() if y == today.year else f"{y}-12-31"
        need = d is None or (y == today.year and (d.get("to") or "") < want_to)
        if need and fetched < max_new:
            print(f"  vapour {y}: fetching…", flush=True)
            try:
                d = fetch_year(y, want_to if y == today.year else None)
                fetched += 1
            except Exception as e:                               # noqa: BLE001
                print(f"  vapour {y}: not fetched ({str(e)[:60]}); left for the next run", flush=True)
                if "429" in str(e):
                    break                                        # квота кончилась — дальше бессмысленно
                d = None
        if d:
            years[y] = d
    return years


def region_series(years, reg):
    """Суточный ряд региона: среднее по точкам с весом cos φ."""
    pts = points(reg)
    ser = {}
    for y, d in years.items():
        P = d["points"]
        dates = set()
        for la, lo in pts:
            dates |= set((P.get(f"{la},{lo}") or {}).keys())
        for dt in sorted(dates):
            num = den = 0.0
            for la, lo in pts:
                v = (P.get(f"{la},{lo}") or {}).get(dt)
                if v is None:
                    continue
                w = math.cos(math.radians(la))
                num += w * v; den += w
            if den > 0:
                ser[dt] = round(num / den, 2)
    return ser


def _q(s, p):
    s = sorted(s)
    if not s:
        return None
    k = (len(s) - 1) * p
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def summarise(reg, ser, today):
    name, lats, lons, why = REGIONS[reg]
    dates = sorted(ser)
    if not dates:
        return None
    last_dt = dates[-1]
    by_doy = {}
    for dt in dates:
        d = date.fromisoformat(dt)
        if CLIM[0] <= d.year <= CLIM[1]:
            by_doy.setdefault(d.timetuple().tm_yday, []).append(ser[dt])
    clim = {}
    for doy in range(1, 367):
        pool = []
        for k in range(-7, 8):
            pool += by_doy.get(((doy - 1 + k) % 366) + 1, [])
        if len(pool) >= 20:
            clim[doy] = _q(pool, .5)
    # 30-суточное среднее против того же окна каждого года (ранг среди всех лет)
    ld = date.fromisoformat(last_dt)
    def win_mean(end):
        w = [ser[dt] for dt in dates if end - timedelta(days=29) <= date.fromisoformat(dt) <= end]
        return sum(w) / len(w) if len(w) >= 25 else None
    m30 = win_mean(ld)
    yrs = {}
    for y in range(FIRST_YEAR, ld.year):
        try:
            v = win_mean(date(y, ld.month, min(ld.day, 28)))
        except ValueError:
            v = None
        if v is not None:
            yrs[str(y)] = round(v, 2)
    rank = 1 + sum(1 for v in yrs.values() if v > m30) if m30 is not None else None
    # ряд текущего года и аналогов по дню года
    def year_series(y):
        return [[dt[5:], ser[dt]] for dt in dates if dt.startswith(str(y))]
    # аномалия последнего дня и 30 суток против климатологии
    anom_last = round(ser[last_dt] - clim[ld.timetuple().tm_yday], 2) if ld.timetuple().tm_yday in clim else None
    clim30 = [clim.get(((ld - timedelta(days=i)).timetuple().tm_yday)) for i in range(30)]
    clim30 = [c for c in clim30 if c is not None]
    anom30 = round(m30 - sum(clim30) / len(clim30), 2) if m30 is not None and clim30 else None
    clim_have = sorted({date.fromisoformat(dt).year for dt in dates if CLIM[0] <= date.fromisoformat(dt).year <= CLIM[1]})
    return {"key": reg, "name": name, "why": why, "n_points": len(lats) * len(lons),
            "clim_years_have": clim_have, "clim_complete": len(clim_have) >= (CLIM[1] - CLIM[0] + 1),
            "last": {"date": last_dt, "value": ser[last_dt], "anom": anom_last},
            "mean30": {"value": round(m30, 2) if m30 is not None else None, "anom": anom30, "rank": rank, "of": len(yrs) + 1,
                       "record": rank == 1, "by_year": yrs},
            "clim": [round(clim[d], 2) if d in clim else None for d in range(1, 367)],
            "this_year": year_series(ld.year),
            "analogs": {str(y): year_series(y) for y in ANALOGS},
            "years_max": {str(y): round(max(v), 2) for y in range(FIRST_YEAR, ld.year + 1)
                          for v in [[ser[dt] for dt in dates if dt.startswith(str(y))]] if v}}   # годы с пропуском ещё не скачаны


def main():
    t0 = time.time()
    today = date.today()
    years = load_years(today, max_new=0 if "--no-fetch" in sys.argv else MAX_NEW_YEARS)
    if today.year not in years:
        # без текущего года сцены нет: пишем честную заглушку, панель прячет вкладку, проверки видят файл
        doc = {"built": None, "pending": True, "years_have": sorted(years), "first_year": FIRST_YEAR,
               "note": "the current year has not been fetched yet (Open-Meteo daily quota); the daily run retries"}
        safeio.write_text(OUT, json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
        print(f"vapour.json: pending, {len(years)} years on disk, current year missing")
        return 0
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "first_year": FIRST_YEAR, "clim_years": list(CLIM),
           "analog_years": list(ANALOGS), "c3s": C3S, "items": [],
           "source": {"label": "ERA5 total column water vapour via the Open-Meteo archive API, hourly points averaged to days",
                      "page": "https://open-meteo.com/en/docs/historical-weather-api"},
           "note": ("Column water vapour, kg per square metre of the whole air column, from ERA5 through Open-Meteo. "
                    "Not a global mean: a sparse grid cannot give one honestly, so the panel shows the tropical belt "
                    "20°S–20°N on a 10° by 30° grid weighted by cos(latitude), and the Niño boxes on 3 by 5 points. "
                    "The global record is quoted from C3S, as reported. Climatology 1991–2020, ±7 days.")}
    for reg in REGIONS:
        s = summarise(reg, region_series(years, reg), today)
        if s:
            doc["items"].append(s)
            print(f"  {s['name']:20s} last {s['last']['value']:5.1f} ({s['last']['anom']:+.1f}) on {s['last']['date']}; "
                  f"30-day {s['mean30']['value']:5.1f} ({s['mean30']['anom']:+.1f}) rank {s['mean30']['rank']}/{s['mean30']['of']}")
    safeio.write_text(OUT, json.dumps(doc, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
    print(f"vapour.json: {len(doc['items'])} regions, {OUT.stat().st_size // 1024} KB, {time.time() - t0:.0f} s")
    try:
        import ops as OPSLOG
        OPSLOG.record_run("vapour", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ok",
                          note=f"{len(doc['items'])} regions to {doc['items'][0]['last']['date'] if doc['items'] else '?'}")
    except Exception:                                            # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
