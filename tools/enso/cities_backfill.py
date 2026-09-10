# -*- coding: utf-8 -*-
"""Докачка прошлых прогнозов по городам: с января 2025 по вчера, три модели, семь горизонтов.

Владелец 10.09: «возьми с января; если данных не так много, подключим другие годы — наши
важные, когда Эль-Ниньо, и по годам выборочно спокойные с момента старта наблюдений; тогда
будет полное сравнение динамики ошибочности моделей».

Что оказалось доступно (проверено 10.09 на Open-Meteo Previous Runs API): все три модели
(ECMWF IFS, GFS, ICON) с горизонтами 1–7 суток и всеми параметрами — с января 2025. За 2023–2024
у ECMWF и ICON пусто, у GFS есть только температура; архивных прогнозов за 1997 и 2015 нет
нигде — тогдашние выпуски не хранились публично. Значит, честное сравнение: спокойный 2025
против событийного 2026, те же города, модели и параметры.

Предыдущие выпуски отдаются только часовыми рядами (`temperature_2m_previous_day5` и т. п.),
суточные величины считаем сами: max/min температуры, сумма осадков, max ветра, средние
влажность/облачность/давление — ровно так, как их считает суточный прогноз, чтобы ошибки
за прошлое и за сегодня лежали на одной шкале.

Запросов много (50 городов × 3 модели × ~20 месяцев ≈ 3000), поэтому инструмент возобновляемый:
состояние в data/enso/raw/cities/backfill-state.json, строки — в forecasts-archive.jsonl в том
же формате, что суточный сбор. Останов в любой момент, повторный запуск продолжит.

    python tools/enso/cities_backfill.py --from 2025-01-01          докачать
    python tools/enso/cities_backfill.py --from 2025-01-01 --dry    только план
"""
import argparse
import json
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cities import CITIES, MODELS, RAW, get  # noqa: E402

ARCHIVE = RAW / "forecasts-archive.jsonl"
STATE = RAW / "backfill-state.json"
HOURLY = ["temperature_2m", "precipitation", "wind_speed_10m", "relative_humidity_2m", "cloud_cover", "pressure_msl"]
LEADS = range(1, 8)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def month_spans(start, end):
    cur = start
    while cur <= end:
        nxt = (cur.replace(day=28) + timedelta(days=4)).replace(day=1)
        yield cur, min(nxt - timedelta(days=1), end)
        cur = nxt


def daily_from_hourly(times, cols):
    """Часовые ряды одного горизонта → суточные величины по дням (UTC)."""
    days = {}
    for i, t in enumerate(times):
        d = t[:10]
        b = days.setdefault(d, {"t": [], "p": [], "w": [], "h": [], "c": [], "pr": []})
        for key, col in (("t", "temperature_2m"), ("p", "precipitation"), ("w", "wind_speed_10m"),
                         ("h", "relative_humidity_2m"), ("c", "cloud_cover"), ("pr", "pressure_msl")):
            v = cols.get(col)
            if v is not None and i < len(v) and v[i] is not None:
                b[key].append(v[i])
    out = {}
    for d, b in days.items():
        if len(b["t"]) < 20:                       # неполные сутки не считаем
            continue
        rec = {"temperature_2m_max": round(max(b["t"]), 1), "temperature_2m_min": round(min(b["t"]), 1)}
        if b["p"]:
            rec["precipitation_sum"] = round(sum(b["p"]), 1)
        if b["w"]:
            rec["wind_speed_10m_max"] = round(max(b["w"]), 1)
        if b["h"]:
            rec["relative_humidity_2m_mean"] = round(sum(b["h"]) / len(b["h"]))
        if b["c"]:
            rec["cloud_cover_mean"] = round(sum(b["c"]) / len(b["c"]))
        if b["pr"]:
            rec["pressure_msl_mean"] = round(sum(b["pr"]) / len(b["pr"]), 1)
        out[d] = rec
    return out


def fetch_city_month(city, model, d0, d1):
    hv = ",".join(f"{v}_previous_day{L}" for L in LEADS for v in HOURLY)
    url = (f"https://previous-runs-api.open-meteo.com/v1/forecast?latitude={city[2]}&longitude={city[3]}"
           f"&start_date={d0.isoformat()}&end_date={d1.isoformat()}&hourly={hv}&models={model}&timezone=UTC")
    r = get(url)
    h = r.get("hourly") or {}
    times = h.get("time") or []
    rows = []
    for L in LEADS:
        cols = {v: h.get(f"{v}_previous_day{L}") for v in HOURLY}
        if not any(cols.values()):
            continue
        daily = daily_from_hourly(times, cols)
        # каждая целевая дата → отдельный «выпуск» за L суток до неё: тот же формат, что у суточного сбора
        for tgt, rec in daily.items():
            issued = (date.fromisoformat(tgt) - timedelta(days=L)).isoformat()
            rows.append({"issued": issued, "city": city[0], "model": model, "dates": [tgt],
                         "values": {k: [v] for k, v in rec.items()}, "lead": L, "source": "previous-runs"})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default="2025-01-01")
    ap.add_argument("--to", dest="end", default=(date.today() - timedelta(days=1)).isoformat())
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--pause", type=float, default=2.0, help="секунд между запросами")
    a = ap.parse_args()
    start, end = date.fromisoformat(a.start), date.fromisoformat(a.end)
    RAW.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"done": []}
    done = set(state["done"])
    jobs = [(c, m, d0, d1) for d0, d1 in month_spans(start, end) for c in CITIES for m in MODELS]
    todo = [j for j in jobs if f"{j[0][0]}|{j[1]}|{j[2].isoformat()}" not in done]
    print(f"jobs {len(jobs)}, done {len(jobs) - len(todo)}, to do {len(todo)}")
    if a.dry:
        return
    t0 = time.time()
    # факты за весь промежуток — один запрос на пачку городов, дёшево
    if not state.get("actuals_from") or state["actuals_from"] > a.start:
        from cities import ACTUALS, BATCH, PARAMS
        acts = json.loads(ACTUALS.read_text(encoding="utf-8")) if ACTUALS.exists() else {}
        n_act = 0
        for i in range(0, len(CITIES), 5):
            chunk = CITIES[i:i + 5]
            url = ("https://archive-api.open-meteo.com/v1/archive?latitude=" + ",".join(str(c[2]) for c in chunk)
                   + "&longitude=" + ",".join(str(c[3]) for c in chunk)
                   + f"&start_date={a.start}&end_date={a.end}&daily=" + ",".join(PARAMS) + "&timezone=UTC")
            res = get(url)
            if isinstance(res, dict):
                res = [res]
            for c, loc in zip(chunk, res):
                d = loc.get("daily") or {}
                for k, day in enumerate(d.get("time") or []):
                    rec = {p: d[p][k] for p in PARAMS if d.get(p) and k < len(d[p]) and d[p][k] is not None}
                    if rec and day not in acts.get(c[0], {}):
                        acts.setdefault(c[0], {})[day] = rec
                        n_act += 1
            time.sleep(a.pause)
        ACTUALS.write_text(json.dumps(acts, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        state["actuals_from"] = a.start
        STATE.write_text(json.dumps(state), encoding="utf-8")
        print(f"actuals: +{n_act} city-days from {a.start}")
    n_rows = 0
    with ARCHIVE.open("a", encoding="utf-8") as fh:
        for k, (c, m, d0, d1) in enumerate(todo, 1):
            key = f"{c[0]}|{m}|{d0.isoformat()}"
            try:
                rows = fetch_city_month(c, m, d0, d1)
            except Exception as e:                               # noqa: BLE001
                print(f"  ! {key}: {str(e)[:80]} — stop; rerun to continue")
                break
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
            n_rows += len(rows)
            done.add(key)
            state["done"] = sorted(done)
            STATE.write_text(json.dumps(state), encoding="utf-8")
            if k % 25 == 0:
                print(f"  {k}/{len(todo)} · rows {n_rows} · {time.time() - t0:.0f} s")
            time.sleep(a.pause)
    print(f"backfill: +{n_rows} rows, {len(done)}/{len(jobs)} jobs done, {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
