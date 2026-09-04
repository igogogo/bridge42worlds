# -*- coding: utf-8 -*-
"""OISST напрямую: суточные средние по боксам с NOAA ERDDAP, задержка один день.

ЗАЧЕМ. До 4 сентября суточный Niño 3.4 приходил через climatereanalyzer с хвостом в 18 дней:
панель жила с трёхнедельным запозданием в главном ряду (экспертиза 04.09, п. 3.1). NOAA
раздаёт ту же сетку OISST v2.1 (0.25°) через ERDDAP CoastWatch двумя наборами: окончательный
(ncdcOisst21Agg, отстаёт на две недели, с сентября 1981) и предварительный NRT (ncdcOisst21NrtAgg,
отстаёт на сутки). Средние по боксам считаем сами, с весом cos(широты), по морским ячейкам.

ЧТО СЧИТАЕМ. Четыре зоны Niño плюс бокс Персидского залива (24–30°N, 48–56°E) — для кувейтской
вкладки. Климатология 1991–2020 у каждого бокса СВОЯ, из той же сетки окончательного набора,
сглаженная 15-дневным окном; прошлые сильные события (1982, 1997, 2015, 2023) и прошлый год
лежат рядом по тому же календарю. climatereanalyzer остаётся вторым источником для сверки:
на перекрытии дней считаем смещение между нашим Niño 3.4 и его — и показываем его на панели.

ШАГ СЕТКИ. Большие боксы берём с шагом 4 ячейки (1°), Niño 1+2 — с шагом 2, Залив — целиком:
для среднего по гладкому полю SST прореживание меняет результат на сотые доли, а тянет в
четыре-шестнадцать раз меньше. Хвост NRT и климатология у бокса считаются на ОДНОМ шаге, чтобы
не сравнивать разное. Вшивка в ряд climatereanalyzer идёт со смещением, измеренным на
перекрытии, — оно и есть цена прореживания плюс разница NRT/окончательного.

ХРАНЕНИЕ. data/enso/oisst/<box>.json — суточный склад (дата → SST), дописывается; последние
14 дней перетягиваются каждый раз, потому что NRT их ещё правит. clim_<box>.json — климатология
и аналоги, строятся один раз (десятки минут сетевого времени) и дальше только читаются.
"""
import calendar
import json
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"
CACHE = ROOT / "oisst"
E = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/"
NRT = "ncdcOisst21NrtAgg_LonPM180"
FINAL = "ncdcOisst21Agg_LonPM180"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

BOXES = {
    "nino12": {"lat": (-10, 0), "lon": [(-90, -80)], "stride": 2, "title": "Niño 1+2"},
    "nino3": {"lat": (-5, 5), "lon": [(-150, -90)], "stride": 4, "title": "Niño 3"},
    "nino34": {"lat": (-5, 5), "lon": [(-170, -120)], "stride": 4, "title": "Niño 3.4"},
    "nino4": {"lat": (-5, 5), "lon": [(160, 179.875), (-179.875, -150)], "stride": 4, "title": "Niño 4"},
    "gulf": {"lat": (24, 30), "lon": [(48, 56)], "stride": 1, "title": "Persian Gulf"},
    # Мировой океан 60°S–60°N нужен только как хвост к ряду climatereanalyzer: климатология и
    # аналоги у него берутся оттуда, поэтому climatology для него не строим (см. build()).
    "world": {"lat": (-59.875, 59.875), "lon": [(-179.875, 179.875)], "stride": 8, "title": "World ocean 60°S–60°N",
              "tail_only": True},
}
CLIM_YEARS = (1991, 2020)
ANALOG_YEARS = (1982, 1997, 2015, 2023)
TAIL_DAYS = 120
REFETCH_DAYS = 14


# ------------------------------------------------------------------ сетка дней
def grid_index(d):
    """Индекс дня в 366-дневной сетке (календарь високосного года): 29 февраля — 59,
    в невисокосный год эта ячейка пропускается. Та же сетка, что у climatereanalyzer."""
    doy = d.timetuple().tm_yday - 1
    if calendar.isleap(d.year) or doy < 59:
        return doy
    return doy + 1


def _fill_masked(a):
    return np.ma.filled(np.ma.masked_invalid(a), np.nan).astype(float)


# ------------------------------------------------------------------ сеть
def _grid(dataset, t0, t1, lat, lon, stride):
    """Кусок сетки sst[t, lat, lon] за t0..t1 (даты ISO или 'last') — через netCDF в памяти."""
    import netCDF4
    tt0 = t0 if t0 == "last" else f"{t0}T12:00:00Z"
    tt1 = t1 if t1 == "last" else f"{t1}T12:00:00Z"
    q = (f"{E}{dataset}.nc?sst[({tt0}):1:({tt1})][(0.0)]"
         f"[({lat[0]}):{stride}:({lat[1]})][({lon[0]}):{stride}:({lon[1]})]")
    req = urllib.request.Request(q, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = r.read()
    ds = netCDF4.Dataset("inmem.nc", memory=data)
    try:
        t = ds["time"]
        times = [x.strftime("%Y-%m-%d") for x in netCDF4.num2date(t[:], t.units)]
        lats = np.array(ds["latitude"][:], float)
        sst = _fill_masked(ds["sst"][:])[:, 0]          # (t, lat, lon)
    finally:
        ds.close()
    return times, lats, sst


def last_time(dataset):
    q = f"{E}{dataset}.json?time[(last)]"
    req = urllib.request.Request(q, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode("utf-8"))
    return d["table"]["rows"][0][0][:10]


def box_means(dataset, box, t0, t1):
    """Среднее по боксу на каждый день: {дата: SST}. Бокс через линию перемены дат — две части,
    суммы складываются до деления."""
    b = BOXES[box]
    num, den, dates = None, None, None
    for lon in b["lon"]:
        times, lats, sst = _grid(dataset, t0, t1, b["lat"], lon, b["stride"])
        w = np.cos(np.deg2rad(lats))[None, :, None] * np.ones_like(sst)
        ok = np.isfinite(sst)
        n = np.nansum(np.where(ok, sst * w, 0.0), axis=(1, 2))
        d = np.sum(np.where(ok, w, 0.0), axis=(1, 2))
        if num is None:
            num, den, dates = n, d, times
        else:
            m = min(len(num), len(n))
            num, den, dates = num[:m] + n[:m], den[:m] + d[:m], dates[:m]
    out = {}
    for i, dt in enumerate(dates):
        if den[i] > 0:
            out[dt] = round(float(num[i] / den[i]), 4)
    return out


# ------------------------------------------------------------------ склад
def _load(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                            # noqa: BLE001
        return default


def _save(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def update_tail(box, today=None, verbose=False):
    """Дотянуть суточный склад бокса до последнего дня NRT. Возвращает {дата: SST} (весь склад)."""
    today = today or date.today()
    p = CACHE / f"{box}.json"
    store = _load(p, {"sst": {}, "src": NRT})
    have = store.get("sst") or {}
    last_have = max(have) if have else None
    t0 = today - timedelta(days=TAIL_DAYS)
    if last_have:
        t0 = max(t0, date.fromisoformat(last_have) - timedelta(days=REFETCH_DAYS))
    try:
        fresh = box_means(NRT, box, t0.isoformat(), "last")
        have.update(fresh)
        store["sst"] = dict(sorted(have.items())[-(TAIL_DAYS + 40):])
        store["fetched"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        store["error"] = ""
        _save(p, store)
        if verbose:
            print(f"  {box}: +{len(fresh)} дней, до {max(fresh) if fresh else '—'}")
    except Exception as e:                                       # noqa: BLE001
        store["error"] = str(e)[:160]
        if verbose:
            print(f"  {box}: NRT не ответил: {store['error']}")
    return store


def build_clim(box, verbose=False):
    """Климатология 1991–2020 и аналоги по календарю — один раз, из окончательного набора."""
    p = CACHE / f"clim_{box}.json"
    cl = _load(p, {})
    if cl.get("doy") and cl.get("analogs") and all(str(y) in cl["analogs"] for y in ANALOG_YEARS):
        return cl
    b = BOXES[box]
    sums, cnts = np.zeros(366), np.zeros(366)
    analogs = cl.get("analogs") or {}
    years = list(range(CLIM_YEARS[0], CLIM_YEARS[1] + 1))
    need = years + [y for y in ANALOG_YEARS if str(y) not in analogs]
    for y in need:
        t0 = time.time()
        try:
            m = box_means(FINAL, box, f"{y}-01-01", f"{y}-12-31")
        except Exception as e:                                   # noqa: BLE001
            if verbose:
                print(f"  {box} {y}: {str(e)[:100]}")
            continue
        arr = np.full(366, np.nan)
        for dt, v in m.items():
            arr[grid_index(date.fromisoformat(dt))] = v
        if y in years:
            ok = np.isfinite(arr)
            sums[ok] += arr[ok]
            cnts[ok] += 1
        if y in ANALOG_YEARS:
            analogs[str(y)] = [None if not np.isfinite(v) else round(float(v), 3) for v in arr]
        if verbose:
            print(f"  {box} {y}: {len(m)} дней, {time.time() - t0:.0f} с")
    if cnts.max() == 0:
        return cl
    mean = np.where(cnts > 0, sums / np.maximum(cnts, 1), np.nan)
    # 29 февраля видно раз в четыре года: заполняем соседями до сглаживания
    if not np.isfinite(mean[59]) or cnts[59] < 5:
        mean[59] = np.nanmean([mean[58], mean[60]])
    # 15-дневное круговое сглаживание — как у большинства суточных климатологий
    k = 15
    ext = np.concatenate([mean[-k:], mean, mean[:k]])
    sm = np.array([np.nanmean(ext[i:i + k]) for i in range(len(mean))])
    cl = {"doy": [round(float(v), 4) for v in sm], "n": [int(c) for c in cnts],
          "years": list(CLIM_YEARS), "stride": b["stride"], "smooth_days": k,
          "analogs": analogs, "built": datetime.now().strftime("%Y-%m-%d %H:%M"),
          "source": f"NOAA OISST v2.1 final ({FINAL}) via CoastWatch ERDDAP"}
    _save(p, cl)
    return cl


def build_last_year(box, year, verbose=False):
    """Прошлый год по тому же календарю (серая линия «год назад» на панели)."""
    p = CACHE / f"clim_{box}.json"
    cl = _load(p, {})
    ly = cl.setdefault("last_years", {})
    if str(year) in ly:
        return ly[str(year)]
    try:
        m = box_means(FINAL, box, f"{year}-01-01", f"{year}-12-31")
    except Exception as e:                                       # noqa: BLE001
        if verbose:
            print(f"  {box} {year}: {str(e)[:100]}")
        return None
    arr = [None] * 366
    for dt, v in m.items():
        arr[grid_index(date.fromisoformat(dt))] = round(v, 3)
    ly[str(year)] = arr
    _save(p, cl)
    return arr


# ------------------------------------------------------------------ сборка для панели
def _series(store, cl, today):
    """Хвост в TAIL_DAYS дней: даты, SST, аномалия, аналоги по тому же календарю."""
    sst = store.get("sst") or {}
    if not sst:
        return None
    last = date.fromisoformat(max(sst))
    days = [last - timedelta(days=i) for i in range(TAIL_DAYS - 1, -1, -1)]
    dates = [d.isoformat() for d in days]
    vals = [sst.get(d) for d in dates]
    doy = cl.get("doy") or []
    anom = [None if v is None or not doy else round(v - doy[grid_index(d)], 3) for v, d in zip(vals, days)]
    out = {"dates": dates, "sst": vals, "anom": anom,
           "last_date": last.isoformat(), "days_stale": (today - last).days,
           "last_sst": sst.get(last.isoformat()),
           "last_anom": anom[-1]}
    fin = [a for a in anom if a is not None]
    out["mean7"] = round(float(np.mean([a for a in anom[-7:] if a is not None])), 3) if fin else None
    a30 = anom[-31] if len(anom) > 30 else None
    out["chg30"] = round(anom[-1] - a30, 3) if anom[-1] is not None and a30 is not None else None
    # прошлые события и прошлый год — аномалии на те же дни календаря
    an = {}
    for y, arr in ((cl.get("analogs") or {}) | (cl.get("last_years") or {})).items():
        if not arr or not doy:
            continue
        an[y] = [None if arr[grid_index(d)] is None else round(arr[grid_index(d)] - doy[grid_index(d)], 3) for d in days]
    out["analogs"] = an
    return out


def _check_against_cr(our, cr):
    """Смещение нашего ряда против climatereanalyzer на перекрытии: цена прореживания и NRT."""
    if not our or not cr:
        return None
    years = cr["years"]; y = cr["last_year"]
    diffs = []
    for dt, v in our.items():
        d = date.fromisoformat(dt)
        if d.year != y:
            continue
        c = years[y][grid_index(d)]
        if np.isfinite(c) and v is not None:
            diffs.append(float(c) - v)
    if len(diffs) < 3:
        return None
    return {"offset": round(float(np.mean(diffs)), 3), "sd": round(float(np.std(diffs)), 3),
            "n_days": len(diffs)}


def splice(cr, box, our, check):
    """Вшить хвост NRT в ряд climatereanalyzer: дни после его последнего — из нашего склада,
    со смещением, измеренным на перекрытии. Возвращает дату, с которой ряд предварительный."""
    if not our or not cr or not cr.get("last_date"):
        return None
    off = (check or {}).get("offset") or 0.0
    y = cr["last_year"]
    arr = cr["years"][y]
    first = None
    for dt, v in sorted(our.items()):
        d = date.fromisoformat(dt)
        if d.year != y or d <= cr["last_date"] or v is None:
            continue
        arr[grid_index(d)] = v + off
        first = first or d
    if first:
        fin = np.where(np.isfinite(arr))[0]
        cr["last_idx"] = int(fin[-1])
        cr["last_n"] = int(len(fin))
        from sources import grid_index_to_date
        cr["last_date"] = grid_index_to_date(y, cr["last_idx"])
        cr["prelim_from"] = first.isoformat()
        cr["splice_offset"] = round(off, 3)
    return first


def build(today=None, cr_nino34=None, cr_world=None, verbose=False):
    """Всё для панели: хвосты, аномалии, аналоги, сверка. Климатологии читаются из кэша; если
    какой-то нет, бокс отдаётся без аномалии и с пометкой — refresh не должен ждать полчаса."""
    today = today or date.today()
    CACHE.mkdir(parents=True, exist_ok=True)
    out = {"boxes": {}, "source": f"NOAA OISST v2.1 NRT ({NRT}) via CoastWatch ERDDAP, box means computed by us",
           "clim": f"own {CLIM_YEARS[0]}–{CLIM_YEARS[1]} daily climatology from the final OISST grid, 15-day smoothing",
           "note": ("Direct from the NOAA grid, one day behind. The preliminary (NRT) values of the last "
                    "two weeks are revised by NOAA later, so the last days can move by a few hundredths. "
                    "The Niño 3.4 box is checked every day against climatereanalyzer on the days both have.")}
    for box, b in BOXES.items():
        store = update_tail(box, today, verbose)
        cl = {} if b.get("tail_only") else _load(CACHE / f"clim_{box}.json", {})
        s = _series(store, cl, today) if store.get("sst") else None
        rec = {"title": b["title"], "stride": b["stride"], "error": store.get("error") or "",
               "fetched": store.get("fetched"), "has_clim": bool(cl.get("doy"))}
        if s:
            rec.update(s)
        if box == "gulf" and s:
            # порог стресса для опреснения и рыболовства — по абсолютной температуре
            hot = [v for v in s["sst"] if v is not None and v >= 35.0]
            rec["days_over_35"] = len(hot)
            rec["max_sst"] = max(v for v in s["sst"] if v is not None) if any(v is not None for v in s["sst"]) else None
            rec["max_sst_date"] = s["dates"][[v for v in s["sst"]].index(rec["max_sst"])] if rec.get("max_sst") is not None else None
        out["boxes"][box] = rec
    # сверка и вшивка: Niño 3.4 по-настоящему, мировой океан — только хвост
    checks = {}
    if cr_nino34 is not None:
        our = (out["boxes"].get("nino34") or {})
        st = _load(CACHE / "nino34.json", {}).get("sst") or {}
        checks["nino34"] = _check_against_cr(st, cr_nino34)
        first = splice(cr_nino34, "nino34", st, checks["nino34"])
        out["boxes"]["nino34"]["spliced_from"] = first.isoformat() if first else None
    if cr_world is not None:
        st = _load(CACHE / "world.json", {}).get("sst") or {}
        checks["world"] = _check_against_cr(st, cr_world)
        first = splice(cr_world, "world", st, checks["world"])
        out["boxes"]["world"]["spliced_from"] = first.isoformat() if first else None
        # у мирового океана аномалия — от климатологии climatereanalyzer, со смещением
        w = out["boxes"]["world"]
        if w.get("sst") and cr_world.get("clim") is not None:
            off = (checks["world"] or {}).get("offset") or 0.0
            clim = cr_world["clim"]
            w["anom"] = [None if v is None else round(v + off - float(clim[grid_index(date.fromisoformat(d))]), 3)
                         for v, d in zip(w["sst"], w["dates"])]
            w["last_anom"] = w["anom"][-1]
            w["has_clim"] = True
    out["check"] = checks
    return out


if __name__ == "__main__":
    import sys
    if "--clim" in sys.argv:
        for bx, bb in BOXES.items():
            if bb.get("tail_only"):
                continue
            print("климатология", bx)
            build_clim(bx, verbose=True)
            build_last_year(bx, date.today().year - 1, verbose=True)
        print("готово")
    else:
        r = build(verbose=True)
        for bx, rec in r["boxes"].items():
            print(f"{bx:8s} {rec.get('last_date')} sst {rec.get('last_sst')} anom {rec.get('last_anom')} "
                  f"stale {rec.get('days_stale')} clim {rec.get('has_clim')} {rec.get('error') or ''}")
        print("check:", r["check"])
