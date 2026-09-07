# -*- coding: utf-8 -*-
"""Регионы суши на вкладке Dynamics «как у Niño 3.4» (владелец 07.09).

Ряды ERA5 по дням (2 м воздух) для точек суши лежат в складе спектрального сторожа
(data/enso/spectral/<ключ>.json, Open-Meteo, с 1981 года). Здесь они переводятся в ту же
366-дневную сетку, что у climatereanalyzer, с климатологией 1991–2020 (15-дневное сглаживание),
и прогоняются через watch.series_watch — тот же кирпич, что считает Niño 3.4, мировой SST и
воздух: 400 дней, полоса всех лет, рекорды, CUSUM, прогноз на 14 дней, 13 месяцев, аналоги.

Выход: data/enso/regions-daily.json {series: {land_<ключ>: <watch>}, built}. Запуск:
python regions_daily.py (в ежедневной обёртке после spectral.py, который дотягивает склад).
"""
import calendar
import json
import sys
import time
from datetime import date, datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import watch as WT                                              # noqa: E402
import spectral as SPX                                          # noqa: E402

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"
OUT = ROOT / "regions-daily.json"
CLIM = (1991, 2020)


def grid_index(d):
    doy = d.timetuple().tm_yday - 1
    return doy if calendar.isleap(d.year) or doy < 59 else doy + 1


def dataset(store):
    """{дата: значение} → {years: {год: 366}, clim, last_year, last_idx, last_date, last_n}."""
    years = {}
    for k, v in store.items():
        d = date.fromisoformat(k)
        years.setdefault(d.year, np.full(366, np.nan))[grid_index(d)] = float(v)
    cy = [y for y in range(CLIM[0], CLIM[1] + 1) if y in years]
    stack = np.array([years[y] for y in cy])
    clim = np.nanmean(stack, axis=0)
    # 29 февраля пусто в невисокосные годы: заполняем и сглаживаем циклично 15 днями
    clim = np.where(np.isfinite(clim), clim, np.nanmean(clim))
    pad = np.concatenate([clim[-7:], clim, clim[:7]])
    clim = np.convolve(pad, np.ones(15) / 15, mode="valid")
    y_last = max(years)
    fin = np.where(np.isfinite(years[y_last]))[0]
    last_idx = int(fin[-1])
    # индекс сетки → дата
    d0 = date(y_last, 1, 1)
    from datetime import timedelta
    last_date = d0 + timedelta(days=last_idx if calendar.isleap(y_last) or last_idx < 59 else last_idx - 1)
    return {"years": years, "clim": clim, "last_year": y_last, "last_n": int(len(fin)), "last_idx": last_idx, "last_date": last_date}


def build(verbose=True):
    t0 = time.time()
    out = {}
    for key, label, box, rid in SPX.REGIONS:
        p = SPX.RCACHE / f"{key}-box.json"
        if not p.exists():
            continue
        try:
            ds = dataset(json.load(open(p, encoding="utf-8")))
            w = WT.series_watch(ds, label + ", daily", analog_years=WT.ANALOGS)
            w["source"] = f"ERA5 via Open-Meteo archive, mean of a {SPX.GRID}×{SPX.GRID} grid inside the box, cos-latitude weights"
            w["box"] = list(box); w["region"] = rid
            out["land_" + key] = w
            if verbose:
                print(f"  {key:<8} to {w['last_date']}: last {w['last_value']:+.2f}, 30 d {w['level30']['anom']:+.2f} °C rank {w['level30']['rank_raw']}/{w['level30']['of']}, streak {w['records']['streak']}")
        except Exception as e:                                   # noqa: BLE001
            if verbose:
                print(f"  {key}: {str(e)[:120]}")
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "series": out,
           "note": ("Six land regions from ERA5 (box means of a 3×3 grid, via Open-Meteo), treated exactly like the "
                    "global series: anomaly against the 1991–2020 mean of the same calendar day, the band of all years "
                    "since 1981, records, CUSUM and a 14-day analogue forecast. Air over land swings more day to day "
                    "than the ocean boxes; the band is wider for that reason, not because the data are worse."),
           "secs": int(time.time() - t0)}
    OUT.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    if verbose:
        print(f"regions-daily.json: {len(out)} series, {doc['secs']} s")
    try:
        import ops as OPSLOG
        OPSLOG.record_run("regions-daily", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ok" if out else "partial", note=f"{len(out)} land points")
    except Exception:                                            # noqa: BLE001
        pass
    return doc


if __name__ == "__main__":
    build()
