# -*- coding: utf-8 -*-
"""Факт по городам за всю историю — одним прибитым набором (era5).

Зачем отдельный скрипт. Ежедневный сбор (`cities.fetch_actuals`) ходит на 16 суток назад и ровно
на них: этого хватает, чтобы догонять факт, и совсем не хватает, чтобы перебрать историю. А
перебрать её понадобилось: сторож подмены набора 15.09 показал, что факт склеен из двух источников
(сдвиг эпох +0,63 °C), потому что ключ `models` не был прибит. Ошибка мною же и допущена: снёс
накопленный факт, надеясь, что обычный сбор его наберёт, — он не набирает, он держит окно.

Здесь окно во всю историю: от первого выпуска прогнозов до позавчера, кусками по DAYS суток, все
города одним запросом на кусок. Пишет в тот же `raw/cities/actuals.json`, сливая с тем, что есть.

    python tools/enso/cities_actuals_refill.py              вся история
    python tools/enso/cities_actuals_refill.py --from 2025-06-01
"""
import argparse
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cities as C                                              # noqa: E402

DAYS = 90                        # кусок истории на один запрос
PAUSE = 2.0

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def first_forecast_day():
    """С какого дня вообще есть прогнозы: раньше факт не с чем сравнивать."""
    days = set()
    for p in (C.FORECASTS, C.ARCHIVE):
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except Exception:                                    # noqa: BLE001
                continue
            # у записи прогноза сами цели лежат списком в `dates`, а `issued` — день выпуска
            for d in (r.get("dates") or []):
                if isinstance(d, str) and len(d) == 10:
                    days.add(d)
            if isinstance(r.get("issued"), str) and len(r["issued"]) == 10:
                days.add(r["issued"])
    return min(days) if days else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="d0", help="с какой даты (по умолчанию — первый день прогнозов)")
    ap.add_argument("--pause", type=float, default=PAUSE)
    a = ap.parse_args()
    t0 = time.time()
    store = {}
    if C.ACTUALS.exists():
        try:
            store = json.loads(C.ACTUALS.read_text(encoding="utf-8"))
        except Exception:                                        # noqa: BLE001
            store = {}
    have = sum(len(v) for v in store.values())
    d0 = a.d0 or first_forecast_day()
    if not d0:
        sys.exit("не нашёл ни одного дня прогнозов — нечего сверять")
    start, end = date.fromisoformat(d0), date.today() - timedelta(days=1)
    print(f"факт нужен с {start} по {end}; в складе уже {have} город-дней")
    cur, got = start, 0
    while cur <= end:
        to = min(cur + timedelta(days=DAYS - 1), end)
        # fetch_actuals(today, back) берёт окно [today−back, today−1]: подставляем свои концы
        try:
            part = C.fetch_actuals(to + timedelta(days=1), back=(to - cur).days + 1)
        except Exception as e:                                   # noqa: BLE001
            print(f"  {cur}…{to}: {str(e)[:90]}")
            cur = to + timedelta(days=1); time.sleep(a.pause * 3); continue
        n = 0
        for city, days in part.items():
            for day, rec in days.items():
                if start.isoformat() <= day <= end.isoformat():
                    store.setdefault(city, {})[day] = rec; n += 1
        got += n
        print(f"  {cur}…{to}: +{n} город-дней, всего {sum(len(v) for v in store.values())}", flush=True)
        C.ACTUALS.write_text(json.dumps(store, ensure_ascii=False), encoding="utf-8")
        cur = to + timedelta(days=1)
        time.sleep(a.pause)
    total = sum(len(v) for v in store.values())
    print(f"готово: +{got}, теперь {total} город-дней у {len(store)} городов, {time.time() - t0:.0f} с")


if __name__ == "__main__":
    main()
