# -*- coding: utf-8 -*-
"""Облака на шаре: глобальное поле уходящего длинноволнового излучения (OLR).

Владелец 15.09: «на глобусе сверху показывать облака, полупрозрачный слой». Декоративную
картинку облаков брать нельзя — на этой панели каждый пиксель обязан быть измерением. Настоящее
измерение здесь есть, и оно же — главный герой всей темы.

ЧТО ЭТО. Спутник меряет, сколько тепла Земля отдаёт в космос в инфракрасном (NOAA Interpolated
OLR, сетка 2,5°, суточное, с 1974 года). Над ясным тёплым океаном уходит много — 280–300 Вт/м².
Там, где стоит высокая грозовая башня, излучает её ледяная вершина, а она холодная, и уходит
мало — 180–200 Вт/м². Поэтому НИЗКИЙ OLR это и есть глубокая облачность: то самое, что на
панели называется конвекцией и что при Эль-Ниньо переезжает на восток.

ПОЧЕМУ ИМЕННО ОН, А НЕ «ОБЛАЧНОСТЬ» КАКОГО-НИБУДЬ ПРОГНОЗА:
  · это замер, а не модель;
  · тот же ряд, по которому панель уже считает индекс конвекции у линии перемены дат;
  · рядом лежит климатология 1991–2020 — та же база, что у всех аномалий панели, поэтому
    «облачно против обычного» считается честно, а не на глаз.

Берём два поля на одну дату: само излучение (для картинки облаков) и его отклонение от нормы
этого дня года (для слоя «где облаков больше или меньше обычного»). Читаем через OPeNDAP
обычным текстом — netCDF-библиотека не нужна.

    python tools/enso/olr_grid.py            последний доступный день
    python tools/enso/olr_grid.py --stride 2 погрубее (2,5° × 2 = 5°), файл вчетверо легче
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"
OUT = ROOT / "olr-grid.json"
# ДЕЙСТВУЮЩИЙ РЯД, А НЕ АРХИВНЫЙ. Первым взял interp_OLR — он закончился 31.12.2022, и «облака
# сейчас» показывали позапрошлую эпоху. У PSL пять наборов OLR; живых два, оба доходят до
# позавчера. Берём климатическую запись CDR на сетке 1° (v2): вдвое подробнее CPC-смеси и с
# готовой климатологией 1991–2020 в том же каталоге.
BASE = "https://psl.noaa.gov/thredds/dodsC/Datasets/olr_cdr_day/"
DAILY = BASE + "olr.day.mean.v2.nc"
LTM = BASE + "olr.day.ltm.v2.1991-2020.nc"
GRID_DEG = 1.0
UA = {"User-Agent": "Mozilla/5.0 bridge42worlds enso"}
EPOCH = date(1800, 1, 1)                   # units: hours since 1800-01-01

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def _get(url, timeout=90, tries=3):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:                                   # noqa: BLE001
            last = e
            time.sleep(4 * (i + 1))
    raise RuntimeError(str(last)[:160])


def _dims(url):
    """Размеры сетки из .dds: сколько времени, широт и долгот."""
    d = _get(url + ".dds", timeout=60)
    n = {k: int(v) for k, v in re.findall(r"(\w+) = (\d+)", d)}
    return n


def _grid(url, var, ti, stride, nlat, nlon):
    """Один срез по времени как plain text: строки «[0][i], v, v, …»."""
    u = f"{url}.ascii?{var}[{ti}:1:{ti}][0:{stride}:{nlat - 1}][0:{stride}:{nlon - 1}]"
    txt = _get(u)
    rows = []
    for line in txt.splitlines():
        m = re.match(r"^\[0\]\[(\d+)\],\s*(.+)$", line.strip())
        if not m:
            continue
        vals = []
        for tok in m.group(2).split(","):
            tok = tok.strip()
            try:
                v = float(tok)
            except ValueError:
                v = float("nan")
            vals.append(None if (not np.isfinite(v) or v < -9000 or v > 9000) else round(v, 1))
        rows.append(vals)
    return rows


def _axis(url, var, stride, n):
    txt = _get(f"{url}.ascii?{var}[0:{stride}:{n - 1}]", timeout=60)
    nums = re.findall(r"-?\d+\.?\d*", txt.split(var, 1)[-1])
    return [float(x) for x in nums[1:]] if nums else []


def _last_time(url, ntime):
    """Дата последнего дня: читаем хвост оси времени."""
    txt = _get(f"{url}.ascii?time[{ntime - 1}:1:{ntime - 1}]", timeout=60)
    m = re.findall(r"(\d+\.?\d*)", txt.split("time", 1)[-1])
    hrs = float(m[-1]) if m else None
    return (EPOCH + timedelta(hours=hrs)) if hrs else None


def build(stride=2, verbose=True):
    t0 = time.time()
    nd = _dims(DAILY)
    ntime, nlat, nlon = nd["time"], nd["lat"], nd["lon"]
    ti = ntime - 1
    day = _last_time(DAILY, ntime)
    if verbose:
        print(f"суток в ряду {ntime}, сетка {nlat}×{nlon}, последний день {day}")
    rows = _grid(DAILY, "olr", ti, stride, nlat, nlon)
    lat = _axis(DAILY, "lat", stride, nlat)
    lon = _axis(DAILY, "lon", stride, nlon)
    # климатология того же дня года: у ltm 365 суток
    nl = _dims(LTM)
    doy = min(364, day.timetuple().tm_yday - 1) if day else 0
    ltm = _grid(LTM, "olr", doy, stride, nl["lat"], nl["lon"])
    anom = []
    for i, row in enumerate(rows):
        base = ltm[i] if i < len(ltm) else []
        anom.append([None if (v is None or i >= len(ltm) or j >= len(base) or base[j] is None)
                     else round(v - base[j], 1) for j, v in enumerate(row)])
    vv = [v for row in rows for v in row if v is not None]
    av = [v for row in anom for v in row if v is not None]
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "date": day.isoformat() if day else None,
           "lat0": lat[0] if lat else 90.0, "lon0": lon[0] if lon else 0.0,
           "step": GRID_DEG * stride, "nlat": len(rows), "nlon": len(rows[0]) if rows else 0,
           "olr": rows, "anom": anom,
           "range": {"min": min(vv) if vv else None, "max": max(vv) if vv else None,
                     "anom_min": min(av) if av else None, "anom_max": max(av) if av else None},
           "unit": "W/m²",
           "source": "NOAA OLR Climate Data Record v2 (PSL), daily 1° grid; climatology 1991–2020 from the same series",
           "note": ("Outgoing longwave radiation: how much heat the Earth sends back to space in the infrared. "
                    "Over clear warm ocean a lot escapes, around 280–300 W/m². Where a tall storm tower stands, "
                    "what radiates is its frozen top, and a cold top sends little — 180–200. So LOW values are deep "
                    "cloud, and the field is a direct measurement of where the storms are, not a model of clouds. "
                    "The anomaly is against the 1991–2020 mean of the same day of the year, the same base as every "
                    "other anomaly on this panel: negative means more deep cloud than usual on that date."),
           "secs": int(time.time() - t0)}
    OUT.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    if verbose:
        kb = OUT.stat().st_size / 1024
        print(f"olr-grid.json: {doc['nlat']}×{doc['nlon']} на {doc['date']}, {kb:.0f} КБ, {doc['secs']} с")
        print(f"  излучение {doc['range']['min']}…{doc['range']['max']} Вт/м², аномалия "
              f"{doc['range']['anom_min']}…{doc['range']['anom_max']}")
    try:
        import ops as OPSLOG
        OPSLOG.record_run("olr-grid", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ok" if vv else "fail",
                          note=f"{doc['nlat']}x{doc['nlon']} {doc['date']}")
    except Exception:                                            # noqa: BLE001
        pass
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stride", type=int, default=2, help="1 = 1°, 2 = 2°: на шаре 2° неотличимо, а файл вчетверо легче")
    a = ap.parse_args()
    build(a.stride)


if __name__ == "__main__":
    main()
