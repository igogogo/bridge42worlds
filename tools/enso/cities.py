# -*- coding: utf-8 -*-
"""Прогнозы по 50 городам против факта: локальный сторож устойчивости моделей.

Владелец 10.09: «у нас есть недельный прогноз по 50 городам, обновляем его ежедневно и
смотрим, насколько ломаются метеорологические модели — это такой же фактор, только более
локальный, и он подходит под задачу понять, насколько система устойчива сейчас. Берём всё,
что есть: температуру, осадки, облачность, влажность, ветер — и по каждому параметру смотрим
устойчивость моделей».

Как это работает. Каждый день снимаем прогноз на 7 суток по трём моделям (ECMWF IFS, GFS,
ICON) для 50 городов и семи суточных параметров. Когда день наступает и в архиве появляется
факт (ERA5 через Open-Meteo, отстаёт на ~2 суток), каждый прогноз этого дня — за 1, 2 … 7
суток до него — сравнивается с фактом. Так у нас по каждому городу, модели, параметру и
горизонту копится ошибка, и главное — её ход во времени: растёт ли ошибка на 5–7 сутках там,
где Эль-Ниньо ломает привычные режимы.

Ловушки, заложенные заранее:
  · ошибка зависит от климата города — сравнивать надо с собственной нормой города, поэтому
    храним сырые пары и считаем норму по накопленному, а не сравниваем города между собой;
  · факт у Open-Meteo сеточный (ERA5), не станция — для «насколько ломаются модели» годится,
    для «какая погода была» нет; это написано в примечании файла;
  · первые сравнения появляются через ~3 суток после старта, устойчивая статистика — через
    месяц; до этого файл честно показывает «копим».

Сырьё лежит в data/enso/raw/cities/ (вне git, растёт ~150 КБ в сутки); панель читает
data/enso/cities.json (сводка, ~100 КБ).

    python tools/enso/cities.py            снять прогнозы, добрать факты, пересчитать сводку
    python tools/enso/cities.py --plan     показать список городов и не ходить в сеть
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "enso" / "raw" / "cities"
OUT = ROOT / "data" / "enso" / "cities.json"
FORECASTS = RAW / "forecasts.jsonl"
ARCHIVE = RAW / "forecasts-archive.jsonl"      # докачка прошлых выпусков (cities_backfill.py)
ACTUALS = RAW / "actuals.json"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 50 городов: перевес на тропики и оба берега Тихого океана — там сигнал ожидается первым.
CITIES = [
    ("lima", "Lima", -12.05, -77.04, "pacific-east"), ("guayaquil", "Guayaquil", -2.19, -79.89, "pacific-east"),
    ("quito", "Quito", -0.18, -78.47, "pacific-east"), ("bogota", "Bogotá", 4.71, -74.07, "tropics"),
    ("panama", "Panama City", 8.98, -79.52, "pacific-east"), ("sanjose", "San José", 9.93, -84.08, "pacific-east"),
    ("mexico", "Mexico City", 19.43, -99.13, "tropics"), ("losangeles", "Los Angeles", 34.05, -118.24, "pacific-east"),
    ("sanfrancisco", "San Francisco", 37.77, -122.42, "pacific-east"), ("seattle", "Seattle", 47.61, -122.33, "pacific-east"),
    ("vancouver", "Vancouver", 49.28, -123.12, "pacific-east"), ("honolulu", "Honolulu", 21.31, -157.86, "pacific-mid"),
    ("anchorage", "Anchorage", 61.22, -149.90, "pacific-north"), ("tokyo", "Tokyo", 35.68, 139.69, "pacific-west"),
    ("osaka", "Osaka", 34.69, 135.50, "pacific-west"), ("seoul", "Seoul", 37.57, 126.98, "pacific-west"),
    ("shanghai", "Shanghai", 31.23, 121.47, "pacific-west"), ("hongkong", "Hong Kong", 22.32, 114.17, "pacific-west"),
    ("taipei", "Taipei", 25.03, 121.57, "pacific-west"), ("manila", "Manila", 14.60, 120.98, "pacific-west"),
    ("jakarta", "Jakarta", -6.21, 106.85, "tropics"), ("singapore", "Singapore", 1.29, 103.85, "tropics"),
    ("kualalumpur", "Kuala Lumpur", 3.14, 101.69, "tropics"), ("bangkok", "Bangkok", 13.76, 100.50, "tropics"),
    ("hochiminh", "Ho Chi Minh City", 10.82, 106.63, "tropics"), ("darwin", "Darwin", -12.46, 130.84, "tropics"),
    ("sydney", "Sydney", -33.87, 151.21, "pacific-west"), ("brisbane", "Brisbane", -27.47, 153.03, "pacific-west"),
    ("auckland", "Auckland", -36.85, 174.76, "pacific-west"), ("suva", "Suva", -18.14, 178.44, "pacific-mid"),
    ("portmoresby", "Port Moresby", -9.44, 147.18, "tropics"), ("papeete", "Papeete", -17.54, -149.57, "pacific-mid"),
    ("santiago", "Santiago", -33.45, -70.67, "pacific-east"), ("buenosaires", "Buenos Aires", -34.60, -58.38, "atlantic"),
    ("saopaulo", "São Paulo", -23.55, -46.63, "atlantic"), ("rio", "Rio de Janeiro", -22.91, -43.17, "atlantic"),
    ("miami", "Miami", 25.76, -80.19, "atlantic"), ("houston", "Houston", 29.76, -95.37, "atlantic"),
    ("newyork", "New York", 40.71, -74.01, "atlantic"), ("london", "London", 51.51, -0.13, "europe"),
    ("madrid", "Madrid", 40.42, -3.70, "europe"), ("cairo", "Cairo", 30.04, 31.24, "africa"),
    ("nairobi", "Nairobi", -1.29, 36.82, "tropics"), ("lagos", "Lagos", 6.52, 3.38, "tropics"),
    ("johannesburg", "Johannesburg", -26.20, 28.05, "africa"), ("mumbai", "Mumbai", 19.08, 72.88, "tropics"),
    ("delhi", "Delhi", 28.61, 77.21, "asia"), ("dhaka", "Dhaka", 23.81, 90.41, "tropics"),
    ("kuwait", "Kuwait City", 29.37, 47.98, "gulf"), ("moscow", "Moscow", 55.76, 37.62, "europe"),
]
MODELS = ["ecmwf_ifs025", "gfs_seamless", "icon_seamless"]
PARAMS = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "wind_speed_10m_max",
          "relative_humidity_2m_mean", "cloud_cover_mean", "pressure_msl_mean"]
UNITS = {"temperature_2m_max": "°C", "temperature_2m_min": "°C", "precipitation_sum": "mm",
         "wind_speed_10m_max": "km/h", "relative_humidity_2m_mean": "%", "cloud_cover_mean": "%",
         "pressure_msl_mean": "hPa"}
LABELS = {"temperature_2m_max": "T max", "temperature_2m_min": "T min", "precipitation_sum": "rain",
          "wind_speed_10m_max": "wind max", "relative_humidity_2m_mean": "humidity",
          "cloud_cover_mean": "cloud", "pressure_msl_mean": "pressure"}
HORIZONS = 7
BATCH = 10            # городов в одном запросе: Open-Meteo принимает списки координат


def get(url, tries=6):
    """Open-Meteo считает «вызовы» с весом по объёму: длинный часовой запрос стоит десятков.
    На 429 ждём всерьёз (минута, потом больше), а не секунды — иначе докачка ложится на
    первом же месяце (10.09)."""
    last = None
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429:
                time.sleep(60 * (k + 1))
            else:
                time.sleep(3 + 3 * k)
        except Exception as e:                                   # noqa: BLE001
            last = e
            time.sleep(3 + 3 * k)
    raise last


def fetch_forecasts(today):
    """Прогноз на 7 суток по трём моделям, пачками по BATCH городов."""
    rows = []
    for i in range(0, len(CITIES), BATCH):
        chunk = CITIES[i:i + BATCH]
        url = ("https://api.open-meteo.com/v1/forecast?latitude=" + ",".join(str(c[2]) for c in chunk)
               + "&longitude=" + ",".join(str(c[3]) for c in chunk)
               + "&daily=" + ",".join(PARAMS) + "&models=" + ",".join(MODELS)
               + f"&forecast_days={HORIZONS}&timezone=UTC")
        res = get(url)
        if isinstance(res, dict):
            res = [res]
        for c, loc in zip(chunk, res):
            d = loc.get("daily") or {}
            times = d.get("time") or []
            for m in MODELS:
                vals = {}
                for p in PARAMS:
                    v = d.get(f"{p}_{m}")
                    if v is not None:
                        vals[p] = v
                if not vals:
                    continue
                rows.append({"issued": today.isoformat(), "city": c[0], "model": m, "dates": times, "values": vals})
    return rows


def fetch_actuals(today, back=16):
    """Факт из архива ERA5 за последние `back` суток (архив отстаёт на ~2 суток)."""
    start = (today - timedelta(days=back)).isoformat()
    end = (today - timedelta(days=1)).isoformat()
    out = {}
    for i in range(0, len(CITIES), BATCH):
        chunk = CITIES[i:i + BATCH]
        url = ("https://archive-api.open-meteo.com/v1/archive?latitude=" + ",".join(str(c[2]) for c in chunk)
               + "&longitude=" + ",".join(str(c[3]) for c in chunk)
               + f"&start_date={start}&end_date={end}&daily=" + ",".join(PARAMS) + "&timezone=UTC")
        res = get(url)
        if isinstance(res, dict):
            res = [res]
        for c, loc in zip(chunk, res):
            d = loc.get("daily") or {}
            for k, day in enumerate(d.get("time") or []):
                rec = {}
                for p in PARAMS:
                    v = (d.get(p) or [None])[k] if k < len(d.get(p) or []) else None
                    if v is not None:
                        rec[p] = v
                if rec:
                    out.setdefault(c[0], {})[day] = rec
    return out


def load_jsonl(p):
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def summarize(forecasts, actuals, today):
    """Пары прогноз–факт → ошибки по городу, модели, параметру, горизонту."""
    pairs = []                 # (city, model, param, horizon, issued, target, err)
    for f in forecasts:
        act = actuals.get(f["city"]) or {}
        for h, day in enumerate(f["dates"]):
            a = act.get(day)
            if not a:
                continue
            lead = f.get("lead") or (h + 1)          # у докачанных строк горизонт задан явно
            for p, series in f["values"].items():
                if h < len(series) and series[h] is not None and a.get(p) is not None:
                    pairs.append((f["city"], f["model"], p, lead, f["issued"], day, series[h] - a[p]))

    def stat(errs):
        n = len(errs)
        if not n:
            return None
        mae = sum(abs(e) for e in errs) / n
        bias = sum(errs) / n
        return {"n": n, "mae": round(mae, 2), "bias": round(bias, 2)}

    # по параметру × модели × горизонту (все города)
    by_pmh = {}
    for c, m, p, h, iss, tgt, e in pairs:
        by_pmh.setdefault(p, {}).setdefault(m, {}).setdefault(h, []).append(e)
    param_stats = {p: {m: {str(h): stat(v) for h, v in hs.items()} for m, hs in ms.items()} for p, ms in by_pmh.items()}

    # по городу: ошибка на горизонте 5 суток по каждому параметру (средняя по моделям)
    by_city = {}
    for c, m, p, h, iss, tgt, e in pairs:
        by_city.setdefault(c, {}).setdefault(p, {}).setdefault(h, []).append(e)
    city_stats = {}
    for c, ps in by_city.items():
        city_stats[c] = {p: {str(h): stat(v) for h, v in hs.items()} for p, hs in ps.items()}

    # ход ошибки во времени: по дате факта, горизонт 5, средняя по городам и моделям, по параметру
    by_day = {}
    for c, m, p, h, iss, tgt, e in pairs:
        if h == 5:
            by_day.setdefault(p, {}).setdefault(tgt, []).append(abs(e))
    daily = {p: {d: round(sum(v) / len(v), 3) for d, v in sorted(ds.items())} for p, ds in by_day.items()}

    # помесячно, горизонты 1/3/5/7, по параметру: это и есть «динамика ошибочности» по годам
    by_month = {}
    for c, m, p, h, iss, tgt, e in pairs:
        if h in (1, 3, 5, 7):
            by_month.setdefault(p, {}).setdefault(str(h), {}).setdefault(tgt[:7], []).append(abs(e))
    monthly = {p: {h: {mo: {"mae": round(sum(v) / len(v), 3), "n": len(v)} for mo, v in sorted(ms.items())}
                   for h, ms in hs.items()} for p, hs in by_month.items()}

    issues = sorted({f["issued"] for f in forecasts})
    return {
        "built": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "since": issues[0] if issues else today.isoformat(),
        "issues": len(issues),
        "cities": [{"id": c[0], "name": c[1], "lat": c[2], "lon": c[3], "group": c[4]} for c in CITIES],
        "models": MODELS, "params": PARAMS, "units": UNITS, "labels": LABELS, "horizons": HORIZONS,
        "pairs": len(pairs),
        "param_stats": param_stats,
        "city_stats": city_stats,
        "daily_h5": daily,
        "monthly": monthly,
        "note": ("Forecasts: Open-Meteo, three models, 7 days, taken every morning. Facts: ERA5 through the "
                 "Open-Meteo archive, gridded, about two days behind - good for how far the models miss, "
                 "not for what the weather was at a station. Errors are forecast minus fact; compare a city "
                 "with its own norm, not cities with each other."),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    a = ap.parse_args()
    today = date.today()
    if a.plan:
        for c in CITIES:
            print(f"  {c[0]:14s} {c[1]:18s} {c[2]:7.2f} {c[3]:8.2f} {c[4]}")
        print(f"{len(CITIES)} cities · {len(MODELS)} models · {len(PARAMS)} params · {HORIZONS} days")
        return
    RAW.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    forecasts = load_jsonl(FORECASTS)
    archive = load_jsonl(ARCHIVE)
    have_today = any(f["issued"] == today.isoformat() for f in forecasts)
    if not have_today:
        new = fetch_forecasts(today)
        with FORECASTS.open("a", encoding="utf-8") as fh:
            for r in new:
                fh.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
        forecasts += new
        print(f"forecasts: +{len(new)} rows for {today}")
    else:
        print("forecasts: already taken today")
    actuals = json.loads(ACTUALS.read_text(encoding="utf-8")) if ACTUALS.exists() else {}
    fresh = fetch_actuals(today)
    n_new = 0
    for c, days in fresh.items():
        for d, rec in days.items():
            if d not in actuals.get(c, {}):
                n_new += 1
            actuals.setdefault(c, {})[d] = rec
    ACTUALS.write_text(json.dumps(actuals, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    last_fact = max((d for days in actuals.values() for d in days), default="-")
    print(f"actuals: +{n_new} city-days, latest fact {last_fact}")
    summary = summarize(forecasts + archive, actuals, today)
    OUT.write_text(json.dumps(summary, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"cities.json: {summary['issues']} issue(s) since {summary['since']}, {summary['pairs']} forecast-fact pairs, "
          f"{OUT.stat().st_size // 1024} KB, {time.time() - t0:.0f} s")
    try:
        import ops as OPSLOG
        OPSLOG.record_run("cities", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ok",
                          note=f"{summary['issues']} issues, {summary['pairs']} pairs, facts to {last_fact}")
    except Exception:                                            # noqa: BLE001
        pass


if __name__ == "__main__":
    main()
