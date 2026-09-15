# -*- coding: utf-8 -*-
"""Сторож подмены набора: не склеен ли ряд Open-Meteo из двух разных источников.

Поймано 14.09 на ледниках. Без ключа `models` архив Open-Meteo сам выбирает набор данных и на
свежих годах выбирает ДРУГОЙ. Та же точка, то же 15 июля:

    1995   умолчание  9.4    era5 10.0    era5_land  9.4
    2015   умолчание  2.2    era5  2.1    era5_land  2.2
    2025   умолчание  5.8    era5 14.4    era5_land 12.7

До середины 2010-х умолчание совпадает с era5_land, дальше расходится на семь градусов — как
если бы точка уехала на километр вверх. Беда в том, что ряд, склеенный из двух наборов, ломает
именно то, ради чего он собран: климатология берётся из старой эпохи, сегодняшний день из новой,
и разность между ними записывается в аномалию как погода.

Этот скрипт меряет разрыв там, где он может нам навредить: по настоящим точкам и настоящим
переменным каждого сборщика. Ничего не чинит и не пишет в данные — только числа на экран.

    python tools/enso/om_dataset_check.py            все пробы
    python tools/enso/om_dataset_check.py --only wind
    python tools/enso/om_dataset_check.py --json out.json

Как читать. Смотреть надо не на саму разность, а на то, МЕНЯЕТСЯ ли она между эпохами: ровный
сдвиг во всех годах климатология съедает, а вот сдвиг, который появился в последние годы,
садится прямо в аномалию. Последняя колонка и есть эта разница разностей.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ARCH = "https://archive-api.open-meteo.com/v1/archive"
OLD_YEARS = ["2005", "2012"]          # заведомо старая эпоха
NEW_YEARS = ["2023", "2025"]          # заведомо новая
WINDOW = ("-07-10", "-07-14")         # пять июльских суток: короткий запрос, квоту не жжёт

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


# имя, чей сборщик, точки, переменные, срез (daily|hourly), поле
# У каждой пробы — файл сборщика: прибитый ключ ищется в нём самом, а не в памяти автора.
COLLECTOR = {"wind": "wind.py", "boxes": "spectral.py", "precip": "precip.py",
             "gulf": "gulf.py", "kuwait": "sources.py", "cities": "cities.py"}


def pinned_model(probe):
    """Какой набор прибит у сборщика этой пробы. None — ключа нет, набор выбирает архив."""
    f = COLLECTOR.get(probe)
    if not f:
        return None
    try:
        src = (Path(__file__).resolve().parent / f).read_text(encoding="utf-8")
    except Exception:                                            # noqa: BLE001
        return None
    for m in ("era5_land", "era5"):
        if "models=" + m in src:
            return m
    return None


PROBES = [
    ("wind", "wind.py — на нём стоит тревога и риск 4-го уровня о западном прорыве",
     [(0.0, 130.0), (0.0, 150.0), (0.0, 170.0)], "wind_speed_10m", "hourly", "&wind_speed_unit=ms"),
    ("boxes", "spectral.py — шесть боксов суши на Dynamics (уже прибит, проба контрольная)",
     [(50.0, 12.5), (-11.0, -78.0)], "temperature_2m_mean", "daily", ""),
    ("precip", "precip.py — дожди по регионам против нормы с 1981",
     [(-8.0, 110.0), (-1.0, 37.0)], "precipitation_sum", "daily", ""),
    ("gulf", "gulf.py — воздух и море Залива",
     [(29.0, 48.5)], "temperature_2m_max", "daily", ""),
    ("kuwait", "sources.py — суточный ряд Кувейта",
     [(29.37, 47.98)], "temperature_2m_mean", "daily", ""),
    ("cities", "cities.py — ФАКТ, против которого меряется ошибка прогнозов",
     [(-12.05, -77.04), (51.51, -0.13)], "temperature_2m_max", "daily", ""),
]
MODELS = ["", "era5", "era5_land"]     # пусто = умолчание
# Прибиты (15.09): spectral (боксы), glaciers (era5_land), gulf, sources/Кувейт, cities —
# все на era5, кроме ледников: там era5_land, потому что 9 км против 31 и все точки на суше.
# Проба по-прежнему ходит без ключа: она сравнивает, а не собирает.


def _get(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "bridge42worlds enso"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = json.loads(e.read().decode("utf-8", "replace")).get("reason", "")
            except Exception:                                    # noqa: BLE001
                pass
            last = f"HTTP {e.code} {body}"[:120]
            if e.code == 429 and "Daily" in body:
                raise RuntimeError(last)                         # суточная квота: дальше бессмысленно
            time.sleep(6 * (i + 1))
        except Exception as e:                                   # noqa: BLE001
            last = str(e)[:120]
            time.sleep(6 * (i + 1))
    raise RuntimeError(last or "нет ответа")


def value(points, var, slice_, extra, year, model):
    """Среднее по точкам и суткам окна. None, если набор этих данных не отдаёт."""
    lats = ",".join(f"{p[0]:.3f}" for p in points)
    lons = ",".join(f"{p[1]:.3f}" for p in points)
    u = (f"{ARCH}?latitude={lats}&longitude={lons}&start_date={year}{WINDOW[0]}"
         f"&end_date={year}{WINDOW[1]}&timezone=UTC&{slice_}={var}{extra}"
         + (f"&models={model}" if model else ""))
    res = _get(u)
    if isinstance(res, dict):
        res = [res]
    vals = []
    for one in res:
        block = one.get(slice_) or {}
        vals += [v for v in (block.get(var) or []) if v is not None]
    return (sum(vals) / len(vals)) if vals else None


def run(only=None, pause=2.0):
    rows = []
    stopped = None
    for name, whose, points, var, slice_, extra in PROBES:
        if only and name != only:
            continue
        print(f"\n=== {name}: {whose}")
        print(f"    {len(points)} точек, {var}, {slice_}")
        got = {}
        try:
            for era, years in (("старые", OLD_YEARS), ("свежие", NEW_YEARS)):
                for y in years:
                    for m in MODELS:
                        got[(y, m)] = value(points, var, slice_, extra, y, m)
                        time.sleep(pause)
        except RuntimeError as e:
            stopped = str(e)
            print(f"    ОСТАНОВ: {stopped}")
            break
        head = "год   " + "".join(f"{(m or 'умолчание'):>12}" for m in MODELS) + "   умолч−era5"
        print("    " + head)
        gaps = {}
        for era, years in (("старые", OLD_YEARS), ("свежие", NEW_YEARS)):
            for y in years:
                d, e5 = got.get((y, "")), got.get((y, "era5"))
                gap = None if (d is None or e5 is None) else d - e5
                gaps.setdefault(era, []).append(gap)
                cells = "".join((f"{got[(y, m)]:>12.2f}" if got.get((y, m)) is not None else f"{'—':>12}") for m in MODELS)
                print(f"    {y}  {cells}   " + (f"{gap:+.2f}" if gap is not None else "—"))
        def avg(k):
            v = [g for g in gaps.get(k, []) if g is not None]
            return sum(v) / len(v) if v else None
        a_old, a_new = avg("старые"), avg("свежие")
        drift = None if (a_old is None or a_new is None) else a_new - a_old
        pin = pinned_model(name)
        # Разрыв меряется против УМОЛЧАНИЯ. Если сборщик умолчанием не пользуется, этот разрыв
        # ряду не грозит: он остаётся свойством архива, а не нашего файла.
        verdict = ("данных нет" if drift is None else
                   "РОВНО: склейка не мешает" if abs(drift) < 0.05 else
                   "СЛАБО: сдвиг мал, но есть" if abs(drift) < 0.3 else
                   "ЗНАЧИМО: свежие годы уехали против старых — ряд чинить")
        if pin and drift is not None:
            verdict = ("ключ прибит (models=" + pin + "), ряду подмена не грозит; "
                       + "сдвиг относится к умолчанию, которым мы не пользуемся")
        elif drift is not None and abs(drift) >= 0.05:
            verdict += " — и ключ НЕ ПРИБИТ"
        print(f"    разрыв старые {a_old if a_old is None else round(a_old, 2)} → "
              f"свежие {a_new if a_new is None else round(a_new, 2)}; сдвиг эпох "
              f"{drift if drift is None else round(drift, 2)} → {verdict}")
        rows.append({"probe": name, "whose": whose, "var": var, "gap_old": a_old, "gap_new": a_new,
                     "era_drift": drift, "verdict": verdict, "pinned": pin,
                     "values": {f"{y}|{m or 'default'}": v for (y, m), v in got.items()}})
    return rows, stopped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="одна проба по имени")
    ap.add_argument("--pause", type=float, default=2.0)
    ap.add_argument("--json", help="куда сложить числа")
    a = ap.parse_args()
    rows, stopped = run(a.only, a.pause)
    if a.json and rows:
        Path(a.json).write_text(json.dumps({"probes": rows, "stopped": stopped}, ensure_ascii=False, indent=1),
                                encoding="utf-8")
        print(f"\nчисла сложены в {a.json}")
    if stopped:
        print(f"\nпроба не закончена: {stopped}")
        sys.exit(2)


if __name__ == "__main__":
    main()
