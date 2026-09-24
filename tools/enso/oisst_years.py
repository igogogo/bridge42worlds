# -*- coding: utf-8 -*-
"""БОКСЫ OISST ПО ВСЕМ ГОДАМ (владелец 24.09: «зоны Niño 3, 1+2 и 4 по всем годам — сделай»).

ERDDAP coastwatch лежит, поэтому источник — те же суточные поля NOAA OISST v2.1 (0,25°) с PSL,
через NetCDF Subset Service THREDDS (OPeNDAP там же отдаёт 60 суток за 19 с и падает на годе,
NCSS — квартал за ~28 с). Один запрос на квартал берёт ОДИН пласт 10°S–5°N × 160°E–80°W с шагом
4 ячейки, и из него считаются сразу четыре бокса Niño (границы — те же, что в oisst.py). Итог:
data/enso/oisst/years_<box>.json — абсолютная SST по дню года за 1982–2025 на 366-дневной
сетке плюс первые 120 суток следующего года (из следующего года же); аномалию к норме
1991–2020 панель считает сама из clim_<box>.json.doy, как и у четырёх аналогов.
Оговорка: у Niño 1+2 климатология строилась с шагом 2, здесь шаг 4 — расхождение среднего по
боксу в сотые градуса, оно меньше суточного шума. Докачка инкрементальная, по годам.
"""
import calendar
import json
import sys
import time
import urllib.request
from datetime import date, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio                      # noqa: E402
from oisst import BOXES, grid_index, NEXT_DAYS   # noqa: E402

CACHE = ROOT / "data" / "enso" / "oisst"
NCSS = ("https://psl.noaa.gov/thredds/ncss/grid/Datasets/noaa.oisst.v2.highres/sst.day.mean.{y}.nc"
        "?var=sst&north=5&south=-10&west=160&east=280&horizStride={stride}"
        "&time_start={t0}T00:00:00Z&time_end={t1}T23:59:59Z&accept=netcdf")
STRIDE = 4
YEARS = range(1982, datetime.now().year)
BOX_KEYS = ("nino4", "nino34", "nino3", "nino12")
QUARTERS = ((1, 1, 3, 31), (4, 1, 6, 30), (7, 1, 9, 30), (10, 1, 12, 31))
UA = "Mozilla/5.0 (bridge42worlds El Nino panel)"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _lon360(x):
    return x + 360.0 if x < 0 else x


def _fetch(y, t0, t1, tries=3):
    import netCDF4
    url = NCSS.format(y=y, stride=STRIDE, t0=t0, t1=t1)
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=240) as r:
                data = r.read()
            if not data.startswith(b"CDF") and not data.startswith(b"\x89HDF"):
                raise RuntimeError("not netcdf: " + data[:60].decode("latin-1"))
            ds = netCDF4.Dataset("inmem.nc", memory=data)
            try:
                lat = np.array(ds["lat"][:], float); lon = np.array(ds["lon"][:], float)
                tm = ds["time"]
                days = [x.strftime("%Y-%m-%d") for x in netCDF4.num2date(tm[:], tm.units)]
                sst = np.ma.filled(np.ma.masked_invalid(ds["sst"][:]), np.nan).astype(float)
                if sst.ndim == 4:
                    sst = sst[:, 0]
            finally:
                ds.close()
            return days, lat, lon, sst
        except Exception as e:                                   # noqa: BLE001
            last = e
            time.sleep(5 + 10 * k)
    raise RuntimeError(str(last)[:120])


def _box_mask(box, lat, lon):
    b = BOXES[box]
    m_lat = (lat >= b["lat"][0] - 1e-6) & (lat <= b["lat"][1] + 1e-6)
    m_lon = np.zeros(len(lon), bool)
    for lo, hi in b["lon"]:
        lo3, hi3 = _lon360(lo), _lon360(hi)
        m_lon |= (lon >= lo3 - 1e-6) & (lon <= hi3 + 1e-6)
    return m_lat, m_lon


def year_means(y, verbose=True):
    """{бокс: {дата: SST}} за год — четыре запроса по кварталам, из каждого все боксы."""
    out = {b: {} for b in BOX_KEYS}
    for (m0, d0, m1, d1) in QUARTERS:
        t = time.time()
        days, lat, lon, sst = _fetch(y, f"{y}-{m0:02d}-{d0:02d}", f"{y}-{m1:02d}-{d1:02d}")
        for b in BOX_KEYS:
            ml, mo = _box_mask(b, lat, lon)
            sub = sst[:, ml][:, :, mo]
            with np.errstate(all="ignore"):
                mean = np.nanmean(np.nanmean(sub, axis=2), axis=1)
            for d, v in zip(days, mean):
                if np.isfinite(v):
                    out[b][d] = float(v)
        if verbose:
            print(f"    {y} Q{QUARTERS.index((m0, d0, m1, d1)) + 1}: {len(days)} дней, {time.time() - t:.0f} с", flush=True)
    return out


def _load(box):
    p = CACHE / f"years_{box}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"box": box, "years": {}, "next": {}}


def _save(box, doc):
    doc["built"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    doc["source"] = "NOAA OISST v2.1 daily 0.25°, PSL THREDDS NetCDF subset, one slab 10°S–5°N × 160°E–80°W, stride 4"
    doc["stride"] = STRIDE; doc["title"] = BOXES[box]["title"]; doc["next_days"] = NEXT_DAYS
    safeio.write_text(CACHE / f"years_{box}.json", json.dumps(doc, ensure_ascii=False))


def build(years=YEARS, verbose=True):
    t0 = time.time()
    docs = {b: _load(b) for b in BOX_KEYS}
    for y in years:
        if all(str(y) in docs[b]["years"] for b in BOX_KEYS):
            continue
        try:
            means = year_means(y, verbose)
        except Exception as e:                                   # noqa: BLE001
            print(f"  {y}: НЕ ВЗЯТ: {str(e)[:120]}", flush=True)
            continue
        for b in BOX_KEYS:
            arr = [None] * 366
            for d, v in means[b].items():
                arr[grid_index(date.fromisoformat(d))] = round(v, 3)
            docs[b]["years"][str(y)] = arr
            # продолжение прошлого года — первые 120 клеток этого
            prev = str(y - 1)
            if prev in docs[b]["years"] and prev not in docs[b]["next"]:
                docs[b]["next"][prev] = arr[:NEXT_DAYS]
            _save(b, docs[b])
        print(f"  {y}: готов, {sum(v is not None for v in docs['nino34']['years'][str(y)])} дней у Niño 3.4; всего {time.time() - t0:.0f} с", flush=True)
    for b in BOX_KEYS:
        print(f"{b}: годов {len(docs[b]['years'])}, продолжений {len(docs[b]['next'])}")
    print(f"готово, {time.time() - t0:.0f} с")


def main():
    build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
