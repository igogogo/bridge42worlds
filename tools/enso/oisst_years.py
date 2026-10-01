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
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio                      # noqa: E402
from oisst import BOXES, grid_index, NEXT_DAYS   # noqa: E402

CACHE = ROOT / "data" / "enso" / "oisst"
NCSS = ("https://psl.noaa.gov/thredds/ncss/grid/Datasets/noaa.oisst.v2.highres/sst.day.mean.{y}.nc"
        "?var=sst&north={north}&south={south}&west={west}&east={east}&horizStride={stride}"
        "&time_start={t0}T00:00:00Z&time_end={t1}T23:59:59Z&accept=netcdf")
STRIDE = 4
# ПЛАШКИ (29.09): четыре зоны Niño режутся одной плашкой Пацифики, каждый бокс вне её — своей, по
# границам бокса (так же получил годы Залив, у которого ERDDAP отдавал годы с дырами).
PACIFIC = ("nino4", "nino34", "nino3", "nino12")
# боксы у Калифорнии — одной плашкой на три (запросов втрое меньше: сервер тратит минуту на любой запрос)
GROUPS = {"calif": ("baja", "socal", "ncal")}


def slabs():
    out = {"pacific": {"north": 5, "south": -10, "west": 160, "east": 280, "stride": STRIDE, "boxes": list(PACIFIC)}}
    grouped = set()
    for g, keys in GROUPS.items():
        ks = [k for k in keys if k in BOXES]
        if not ks:
            continue
        grouped |= set(ks)
        out[g] = {"north": max(BOXES[k]["lat"][1] for k in ks), "south": min(BOXES[k]["lat"][0] for k in ks),
                  "west": min((BOXES[k]["lon"][0][0] + 360) % 360 for k in ks), "east": max((BOXES[k]["lon"][0][1] + 360) % 360 for k in ks),
                  "stride": min(BOXES[k].get("stride", STRIDE) for k in ks), "boxes": ks}
    for k, b in BOXES.items():
        if b.get("tail_only") or k in PACIFIC or k in grouped:
            continue
        lo, hi = b["lon"][0]
        out[k] = {"north": b["lat"][1], "south": b["lat"][0], "west": (lo + 360) % 360, "east": (hi + 360) % 360 or 360,
                  "stride": b.get("stride", STRIDE), "boxes": [k]}
    return out
YEARS = range(1982, datetime.now().year)
BOX_KEYS = tuple(k for k, b in BOXES.items() if not b.get("tail_only"))
QUARTERS = ((1, 1, 3, 31), (4, 1, 6, 30), (7, 1, 9, 30), (10, 1, 12, 31))
UA = "Mozilla/5.0 (bridge42worlds El Nino panel)"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _lon360(x):
    return x + 360.0 if x < 0 else x


def _fetch(y, t0, t1, tries=3, slab=None):
    import netCDF4
    sl = slab or slabs()["pacific"]
    url = NCSS.format(y=y, stride=sl["stride"], t0=t0, t1=t1, north=sl["north"], south=sl["south"], west=sl["west"], east=sl["east"])
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
    lon = np.mod(lon, 360.0)      # PSL отдаёт 360–397 для запроса от нуля градусов (Средиземное, 29.09)
    for lo, hi in b["lon"]:
        lo3, hi3 = _lon360(lo), _lon360(hi)
        m_lon |= (lon >= lo3 - 1e-6) & (lon <= hi3 + 1e-6)
    return m_lat, m_lon


def year_means(y, verbose=True, until=None, slab=None, keys=None, since=None):
    """{бокс: {дата: SST}} за год — четыре запроса по кварталам, из каждого все боксы плашки.
    until — последняя дата (текущий год: до вчера), кварталы позже неё не запрашиваются;
    since — первая нужная дата (ежедневный хвост), кварталы раньше неё не запрашиваются."""
    keys = keys or BOX_KEYS
    out = {b: {} for b in keys}
    # плашка Пацифики велика — по кварталам; плашка одного бокса мала — одним запросом на год (29.09)
    parts = QUARTERS   # целый год одним запросом PSL отдаёт 502 (проверено 29.09), поэтому всегда кварталы
    for (m0, d0, m1, d1) in parts:
        t = time.time()
        q0, q1 = date(y, m0, d0), date(y, m1, d1)
        if until is not None:
            if q0 > until:
                break
            q1 = min(q1, until)
        if since is not None:
            if q1 < since:
                continue
            q0 = max(q0, since)
        days, lat, lon, sst = _fetch(y, q0.isoformat(), q1.isoformat(), slab=slab)
        for b in keys:
            ml, mo = _box_mask(b, lat, lon)
            sub = sst[:, ml][:, :, mo]
            with np.errstate(all="ignore"):
                mean = np.nanmean(np.nanmean(sub, axis=2), axis=1)
            for d, v in zip(days, mean):
                if np.isfinite(v):
                    out[b][d] = float(v)
        if verbose:
            print(f"    {y} {'Q' + str(QUARTERS.index((m0, d0, m1, d1)) + 1) if (m0, d0, m1, d1) in QUARTERS else 'year'}: {len(days)} дней, {time.time() - t:.0f} с", flush=True)
    return out


def _load(box):
    p = CACHE / f"years_{box}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"box": box, "years": {}, "next": {}}


def _save(box, doc):
    doc["built"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    doc["source"] = "NOAA OISST v2.1 daily 0.25°, PSL THREDDS NetCDF subset: one slab 10°S–5°N × 160°E–80°W for the Niño zones, a slab per box elsewhere"
    doc["stride"] = STRIDE; doc["title"] = BOXES[box]["title"]; doc["next_days"] = NEXT_DAYS
    safeio.write_text(CACHE / f"years_{box}.json", json.dumps(doc, ensure_ascii=False))


def build(years=YEARS, verbose=True, current=False, only=None):
    """current=True — только текущий год до вчера: частичный, перезаписывается при каждом вызове
    (29.09: линия этого года у зон кроме Niño 3.4 была 120-дневным хвостом бокса)."""
    t0 = time.time()
    docs = {b: _load(b) for b in BOX_KEYS}
    cy = datetime.now().year
    if current:
        years = [cy]
    for sname, sl in slabs().items():
      if only and sname not in only:
          continue
      keys = [k for k in sl["boxes"] if k in BOX_KEYS]
      if current and not only:
          # ТЕКУЩИЙ ГОД — ТОЛЬКО БОКСАМ С НОРМОЙ (29.09): новые моря ещё докачивают годы нормы, и ежедневный
          # прогон не должен занимать для них сервер PSL (он пускает три запроса и тратит минуту на каждый)
          def _has_norm(b):
              try:
                  return bool(json.loads((CACHE / f"clim_{b}.json").read_text(encoding="utf-8")).get("complete"))
              except Exception:                                  # noqa: BLE001
                  return False
          if not all(_has_norm(b) for b in keys):
              print(f"  {sname}: норма ещё не собрана — текущий год не берём", flush=True)
              continue
      for y in years:
        if y != cy and all(str(y) in docs[b]["years"] for b in keys):
            continue
        try:
            # ХВОСТ ВМЕСТО ГОДА (01.10): если текущий год уже лежит у всех боксов плашки, берём только
            # последние 45 дней (переход предварительных данных в окончательные) и вливаем в лежащий массив
            tail = current and y == cy and all(str(y) in docs[b]["years"] for b in keys)
            means = year_means(y, verbose, until=(date.today() - timedelta(days=1)) if y == cy else None, slab=sl, keys=keys,
                               since=(date.today() - timedelta(days=45)) if tail else None)
        except Exception as e:                                   # noqa: BLE001
            print(f"  {sname} {y}: НЕ ВЗЯТ: {str(e)[:120]}", flush=True)
            continue
        for b in keys:
            arr = list(docs[b]["years"][str(y)]) if (tail and len(docs[b]["years"].get(str(y)) or []) == 366) else [None] * 366
            for d, v in means[b].items():
                arr[grid_index(date.fromisoformat(d))] = round(v, 3)
            docs[b]["years"][str(y)] = arr
            # продолжение прошлого года — первые 120 клеток этого
            prev = str(y - 1)
            if prev in docs[b]["years"] and prev not in docs[b]["next"]:
                docs[b]["next"][prev] = arr[:NEXT_DAYS]
            _save(b, docs[b])
        print(f"  {sname} {y}: готов, {sum(v is not None for v in docs[keys[0]]['years'][str(y)])} дней у {keys[0]}; всего {time.time() - t0:.0f} с", flush=True)
    for b in BOX_KEYS:
        print(f"{b}: годов {len(docs[b]['years'])}, продолжений {len(docs[b]['next'])}")
    print(f"готово, {time.time() - t0:.0f} с")


def main():
    only = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--slab=")]
    # --clim-years: сначала годы нормы 1991–2020 и четыре аналога (около 190 с на год плашки, 29.09),
    # остальные годы — потом обычным запуском
    yrs = (list(range(1991, 2021)) + [1982, 1997, 2015, 2023]) if "--clim-years" in sys.argv else YEARS
    lst = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--years=")]
    if lst:                                   # явный список лет: --years=1982,1983,1997
        yrs = [int(x) for x in lst[0].split(",") if x.strip()]
    build(years=sorted(set(yrs)), current="--current" in sys.argv, only=only or None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
