# -*- coding: utf-8 -*-
"""NCEP CFSv2 по дням: как одна модель переписывает прогноз Niño 3.4 между выпусками IRI.

Владелец 03.10: «у нас месяц прогнозирования отличается от прогнозного месяца: я обновляю планы каждую
неделю — так ли у каждой модели?» В плюме IRI каждая модель стоит раз в месяц. Но CFSv2 считается каждый
день, четыре прогона в сутки, и CPC выкладывает его ансамбли за последние 30 дней тремя файлами по десять
дней (dataInd1..3/nino34Sea.nc): в каждом 40 членов от самого свежего старта к самому раннему, по четыре на
день, и сорок первый — наблюдение. Из трёх файлов восстанавливается среднее по каждому дню старта за весь
месяц, а история копится в data/enso/cfs.json день за днём: так видно, как «план едет» внутри месяца.

ОГОВОРКИ, без которых числа врут:
  · наблюдение у CFSv2 — OISST с нормой 1991–2020 (JAS 2026: +2,54 против нашего +2,55), а модели плюма
    проверяются по ONI (ERSST), который в 2026-м ниже OISST на 0,1–0,3;
  · шаги времени — «первый день среднего месяца сезона» (OND → ноябрь); два шага, названные в note2
    файла, — месячные (наблюдённый месяц и прогноз следующего), они хранятся отдельно, как месяцы.

    python tools/enso/cfs.py        скачать три файла и дописать историю
"""
import datetime as dt
import json
import re
import sys
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio                                                    # запись с повтором и подменой целиком

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "enso" / "cfs"
OUT = ROOT / "data" / "enso" / "cfs.json"
URL = "https://www.cpc.ncep.noaa.gov/products/CFSv2/dataInd{e}/nino34Sea.nc"
UA = "Mozilla/5.0 bridge42worlds enso"
SEASONS = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
KEEP_DAYS = 400


def fetch(e):
    req = urllib.request.Request(URL.format(e=e), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        b = r.read()
    RAW.mkdir(parents=True, exist_ok=True)
    p = RAW / f"nino34Sea_E{e}.nc"
    p.write_bytes(b)
    return p


def decode(path):
    """Один файл: {init, days: {дата старта: {n, f: {цель: среднее}}}, obs: {цель: значение}}."""
    import netCDF4
    d = netCDF4.Dataset(path)
    try:
        a = d.variables["anom"]
        t0s, t1s = [x.strip() for x in a.getncattr("initial_time").split("-")]
        t1 = dt.datetime.strptime(t1s, "%Y%m%d").date()
        base = dt.date.fromisoformat(d.variables["time"].units.split("since")[1].strip()[:10])
        times = [base + dt.timedelta(days=float(x)) for x in d.variables["time"][:]]
        A = np.ma.filled(a[:, :, 0, 0, 0].astype(float), np.nan)
        monthly = set()
        if "note2" in a.ncattrs():                      # 'T=12 & 13 are monthly anomaly' — с единицы
            monthly = {int(x) - 1 for x in re.findall(r"\d+", a.getncattr("note2"))}
    finally:
        d.close()
    keys = [(f"{t.year}-{t.month:02d}" if j in monthly else f"{SEASONS[t.month - 1]} {t.year}")
            for j, t in enumerate(times)]
    nmem = A.shape[0] - 1                               # последний член — наблюдение
    obs = {k: round(float(A[nmem][j]), 3) for j, k in enumerate(keys) if not np.isnan(A[nmem][j])}
    by_day = {}
    for m in range(nmem):                               # от самого свежего старта к раннему, по четыре на день
        by_day.setdefault((t1 - dt.timedelta(days=m // 4)).isoformat(), []).append(A[m])
    days = {}
    for day, rows in by_day.items():
        R = np.array(rows)
        f = {}
        for j, k in enumerate(keys):
            col = R[:, j][~np.isnan(R[:, j])]
            if len(col):
                f[k] = round(float(col.mean()), 3)
        if f:
            days[day] = {"n": len(rows), "f": f}
    return {"init": f"{t0s} - {t1s}", "days": days, "obs": obs}


def _window(days, d0, d1):
    """Среднее прогнозов по дням старта d0..d1 включительно — тот же десятидневный срез, что у CPC."""
    acc = {}
    for d, rec in days.items():
        if d0 <= d <= d1:
            for k, v in rec["f"].items():
                acc.setdefault(k, []).append(v)
    return {k: round(sum(v) / len(v), 3) for k, v in acc.items()}


def main():
    try:
        old = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:                                            # noqa: BLE001
        old = {}
    days = {r["date"]: {"n": r["n"], "f": r["f"]} for r in (old.get("days") or [])}
    obs = dict(old.get("obs") or {})
    files, errors = [], []
    for e in (1, 2, 3):
        try:
            got = decode(fetch(e))
            files.append(got["init"])
            days.update(got["days"])
            obs.update(got["obs"])
        except Exception as ex:                                  # noqa: BLE001
            errors.append(f"E{e}: {str(ex)[:120]}")
    if not days:
        print("CFSv2: нет данных", errors)
        return 1
    keep = sorted(days)[-KEEP_DAYS:]
    days = {d: days[d] for d in keep}
    last = dt.date.fromisoformat(keep[-1])
    wins = []
    for k in range(3):                                           # три десятидневки, как у CPC: свежая первой
        d1 = last - dt.timedelta(days=10 * k)
        d0 = d1 - dt.timedelta(days=9)
        wins.append({"from": d0.isoformat(), "to": d1.isoformat(), "mean": _window(days, d0.isoformat(), d1.isoformat())})
    doc = {"built": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "source": "NOAA CPC, CFSv2 Climate Forecast Monitoring",
           "url": "https://www.cpc.ncep.noaa.gov/products/CFSv2/CFSv2seasonal.shtml",
           "files": files, "errors": errors, "last_init": keep[-1],
           "note": ("NCEP CFSv2 runs four forecasts a day; CPC keeps the last 30 days. Each row is the mean of "
                    "one day's runs for every target season (and the next month). Its observation is OISST "
                    "against 1991–2020, not the ERSST-based ONI the plume is scored on."),
           "windows": wins, "obs": dict(sorted(obs.items())),
           "days": [{"date": d, "n": days[d]["n"], "f": days[d]["f"]} for d in keep]}
    safeio.write_text(OUT, json.dumps(doc, ensure_ascii=False))
    w = wins[0]["mean"]
    print(f"✅ cfs.json: {len(keep)} дней старта, последний {keep[-1]}; последние 10 дней: "
          + ", ".join(f"{k} {v:+.2f}" for k, v in w.items() if not k[:4].isdigit())
          + (f"; ошибки {errors}" if errors else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
