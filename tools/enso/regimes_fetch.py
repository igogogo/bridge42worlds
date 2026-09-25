# -*- coding: utf-8 -*-
"""РЕЖИМЫ ЦИРКУЛЯЦИИ, СЫРЬЁ: геопотенциал 500 гПа и приземное давление, Северное полушарие 20–90°N,
сетка 2,5°, сутки (владелец 25.09: «упорядоченность системы по давлению, застревание погоды»).

Два источника, потому что ни один не покрывает всё:
  · история 1948–2025 и начало 2026 — NCEP/NCAR Reanalysis 1 с PSL (OPeNDAP, 2,5°, hgt.<год>.nc
    уровень 500 гПа и slp.<год>.nc); файл 2026 года у PSL остановился на 17.03.2026;
  · дальше по вчерашний день — анализы GFS 00Z (f000) из открытого архива NOAA на AWS: по .idx
    берётся один блок HGT 500 mb и PRMSL из файла 0,5°, читается eccodes, прореживается до 2,5°.
Кэш: data/enso/regimes/<год>.npz (int16 в геопотенциальных метрах и в десятых гПа; NH 29 широт ×
144 долгот) — внутреннее, не выкладывается. Оба источника — анализы, не прогнозы; шов между
реанализом и GFS помечен в паспорте кэша, и слой метрик обязан его учитывать (сравнивать
внутри одного источника или проверить сдвиг на общих днях, когда PSL догонит).
"""
import io
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

CACHE = ROOT / "data" / "enso" / "regimes"
R1_HGT = "https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis/Dailies/pressure/hgt.{y}.nc"
R1_SLP = "https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis/Dailies/surface/slp.{y}.nc"
GFS = "https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{d}/00/atmos/gfs.t00z.pgrb2.0p50.f000"
LAT0, LAT1 = 20.0, 90.0          # Северное полушарие: там блокинги и «застывшая» погода умеренных широт
UA = "Mozilla/5.0 (bridge42worlds El Nino panel)"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _passport(y):
    p = CACHE / f"{y}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"year": y, "days": [], "src": []}


def _save(y, days, src, hgt, slp, lat, lon):
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CACHE / f"{y}.npz", hgt=np.round(hgt).astype(np.int16), slp=np.round(slp * 10).astype(np.int16),
                        lat=lat.astype(np.float32), lon=lon.astype(np.float32))
    safeio.write_text(CACHE / f"{y}.json", json.dumps({"year": y, "days": days, "src": src, "n": len(days),
                                                       "lat": [float(v) for v in lat], "lon": [float(v) for v in lon],
                                                       "hgt_unit": "gpm, int16", "slp_unit": "hPa ×10, int16",
                                                       "built": datetime.now().strftime("%Y-%m-%d %H:%M")}, ensure_ascii=False))


def load_year(y):
    """(days, src, hgt[t,lat,lon] м, slp[t,lat,lon] гПа, lat, lon) из кэша или None."""
    p = CACHE / f"{y}.npz"
    if not p.exists():
        return None
    z = np.load(p)
    ps = _passport(y)
    return ps["days"], ps["src"], z["hgt"].astype(float), z["slp"].astype(float) / 10.0, z["lat"], z["lon"]


# ------------------------------------------------------------------ NCEP R1
def fetch_r1_year(y, verbose=True):
    import netCDF4
    t0 = time.time()
    ds = netCDF4.Dataset(R1_HGT.format(y=y))
    try:
        lat = np.array(ds["lat"][:], float); lon = np.array(ds["lon"][:], float)
        li = np.where((lat >= LAT0 - 1e-6) & (lat <= LAT1 + 1e-6))[0]
        lev = list(np.array(ds["level"][:], float)).index(500.0)
        tm = ds["time"]; n = len(tm)
        days = [x.strftime("%Y-%m-%d") for x in netCDF4.num2date(tm[:], tm.units)]
        hgt = np.empty((n, len(li), len(lon)), float)
        for a in range(0, n, 92):                                # четвертями: годовой запрос PSL режет
            b = min(n, a + 92)
            hgt[a:b] = np.ma.filled(np.ma.masked_invalid(ds["hgt"][a:b, lev, li[0]:li[-1] + 1, :]), np.nan)
    finally:
        ds.close()
    ds = netCDF4.Dataset(R1_SLP.format(y=y))
    try:
        tm = ds["time"]; n2 = len(tm)
        slp = np.empty((n2, len(li), len(lon)), float)
        for a in range(0, n2, 92):
            b = min(n2, a + 92)
            slp[a:b] = np.ma.filled(np.ma.masked_invalid(ds["slp"][a:b, li[0]:li[-1] + 1, :]), np.nan)
    finally:
        ds.close()
    n = min(n, n2)
    if verbose:
        print(f"  R1 {y}: {n} суток, {time.time() - t0:.0f} с", flush=True)
    return days[:n], ["ncep_r1"] * n, hgt[:n], slp[:n], lat[li], lon


# ------------------------------------------------------------------ GFS analysis (AWS)
def _gfs_field(d, name_re):
    """Один блок GRIB2 по .idx (байтовый диапазон), декод eccodes → (lat, lon, values 2D)."""
    import re
    import eccodes
    base = GFS.format(d=d.strftime("%Y%m%d"))
    idx = urllib.request.urlopen(urllib.request.Request(base + ".idx", headers={"User-Agent": UA}), timeout=60).read().decode("utf-8", "replace").splitlines()
    rows = [l.split(":") for l in idx]
    k = next(i for i, r in enumerate(rows) if re.search(name_re, ":" + ":".join(r[3:])))
    start = int(rows[k][1]); end = int(rows[k + 1][1]) - 1 if k + 1 < len(rows) else ""
    req = urllib.request.Request(base, headers={"User-Agent": UA, "Range": f"bytes={start}-{end}"})
    data = urllib.request.urlopen(req, timeout=120).read()
    h = eccodes.codes_new_from_message(data)
    try:
        ni, nj = eccodes.codes_get(h, "Ni"), eccodes.codes_get(h, "Nj")
        vals = np.array(eccodes.codes_get_values(h), float).reshape(nj, ni)
        la0, la1 = eccodes.codes_get(h, "latitudeOfFirstGridPointInDegrees"), eccodes.codes_get(h, "latitudeOfLastGridPointInDegrees")
        lo0 = eccodes.codes_get(h, "longitudeOfFirstGridPointInDegrees")
        dlat, dlon = eccodes.codes_get(h, "jDirectionIncrementInDegrees"), eccodes.codes_get(h, "iDirectionIncrementInDegrees")
    finally:
        eccodes.codes_release(h)
    lat = np.linspace(la0, la1, nj); lon = (lo0 + dlon * np.arange(ni)) % 360.0
    return lat, lon, vals


def _box_to(vals, lat, lon, lat_target, lon_target):
    """Среднее по клетке 2,5° (5×5 узлов 0,5°) вокруг узла целевой сетки: сглаживание, близкое к
    реанализу 2,5°, а не выбор одного узла — иначе у GFS остаётся мелкий масштаб, которого нет у R1,
    и корреляция карт (время жизни) занижается только от смены источника."""
    out = np.empty((len(lat_target), len(lon_target)))
    dlat = abs(lat[1] - lat[0]); dlon = abs(lon[1] - lon[0])
    for i, la in enumerate(lat_target):
        li = np.where(np.abs(lat - la) <= 1.25 + 1e-6)[0]
        for j, lo in enumerate(lon_target):
            dd = np.abs(((lon - lo + 180) % 360) - 180)
            oi = np.where(dd <= 1.25 + 1e-6)[0]
            out[i, j] = vals[np.ix_(li, oi)].mean()
    return out


def fetch_gfs_day(d, lat_target, lon_target):
    """Анализ GFS 00Z за сутки d на сетке R1 (2,5°): среднее по клетке 2,5° из узлов 0,5°."""
    lat, lon, hgt = _gfs_field(d, r":HGT:500 mb:")
    _, _, prmsl = _gfs_field(d, r":PRMSL:mean sea level:")
    return _box_to(hgt, lat, lon, lat_target, lon_target), _box_to(prmsl, lat, lon, lat_target, lon_target) / 100.0


def fetch_overlap(verbose=True):
    """Дни, где есть и R1, и GFS (январь–март 2026): отдельный кэш для проверки шва — regimes.py
    считает время жизни на обоих источниках в те же дни и пишет расхождение."""
    have = load_year(date.today().year)
    if not have:
        return
    days, src, hgt, slp, lat, lon = have
    r1_days = [d for d, s in zip(days, src) if s == "ncep_r1"]
    p = CACHE / f"{date.today().year}_gfs_overlap.npz"
    done = {}
    if p.exists():
        z = np.load(p); done = {d: i for i, d in enumerate(json.loads(str(z["days"])))}
        H0, S0 = z["hgt"].astype(float), z["slp"].astype(float) / 10.0
    out_d, out_h, out_s = [], [], []
    for iso in r1_days:
        if iso in done:
            out_d.append(iso); out_h.append(H0[done[iso]]); out_s.append(S0[done[iso]]); continue
        try:
            hg, sp = fetch_gfs_day(date.fromisoformat(iso), lat, lon)
            out_d.append(iso); out_h.append(hg); out_s.append(sp)
        except Exception as e:                                   # noqa: BLE001
            print(f"  overlap {iso}: пропуск: {str(e)[:80]}", flush=True)
    if out_d:
        np.savez_compressed(p, hgt=np.round(np.array(out_h)).astype(np.int16), slp=np.round(np.array(out_s) * 10).astype(np.int16), days=json.dumps(out_d))
        if verbose:
            print(f"  overlap: {len(out_d)} суток GFS на днях R1", flush=True)


def build(y0=1948, verbose=True):
    t0 = time.time()
    today = date.today()
    lat_t = lon_t = None
    # история из R1 — по годам, готовые годы не трогаем (текущий год — всегда заново, он растёт)
    for y in range(y0, today.year + 1):
        have = load_year(y)
        if have and y < today.year and have[0] and len(have[0]) >= 365:
            lat_t, lon_t = have[4], have[5]
            continue
        try:
            days, src, hgt, slp, lat, lon = fetch_r1_year(y, verbose)
            lat_t, lon_t = lat, lon
        except Exception as e:                                   # noqa: BLE001
            print(f"  R1 {y}: НЕ ВЗЯТ: {str(e)[:100]}", flush=True)
            if have:
                days, src, hgt, slp, lat, lon = have; lat_t, lon_t = lat, lon
            else:
                continue
        if y == today.year:
            # хвост из GFS: от дня после конца R1 по вчера; уже взятые дни из кэша не перекачиваем
            cached = {d: i for i, d in enumerate(have[0])} if have else {}
            last = date.fromisoformat(days[-1]) if days else date(y, 1, 1) - timedelta(days=1)
            d = last + timedelta(days=1)
            add_days, add_h, add_s = [], [], []
            while d < today:
                iso = d.isoformat()
                if iso in cached and have[1][cached[iso]] == "gfs_anl":
                    add_days.append(iso); add_h.append(have[2][cached[iso]]); add_s.append(have[3][cached[iso]])
                else:
                    try:
                        hg, sp = fetch_gfs_day(d, lat_t, lon_t)
                        add_days.append(iso); add_h.append(hg); add_s.append(sp)
                        if verbose and len(add_days) % 20 == 0:
                            print(f"  GFS {iso}: {len(add_days)} суток, {time.time() - t0:.0f} с", flush=True)
                    except Exception as e:                       # noqa: BLE001
                        print(f"  GFS {iso}: пропуск: {str(e)[:80]}", flush=True)
                d += timedelta(days=1)
            if add_days:
                days = days + add_days; src = src + ["gfs_anl"] * len(add_days)
                hgt = np.concatenate([hgt, np.array(add_h)]); slp = np.concatenate([slp, np.array(add_s)])
        _save(y, days, src, hgt, slp, lat, lon)
    print(f"готово, {time.time() - t0:.0f} с")


if __name__ == "__main__":
    y0 = int(sys.argv[sys.argv.index("--from") + 1]) if "--from" in sys.argv else 1948
    build(y0)
    if "--overlap" in sys.argv:
        fetch_overlap()
