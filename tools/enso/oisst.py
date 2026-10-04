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
# Своя запись файлов: повтор при осечке файловой системы и подмена целиком (17.09).
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio   # noqa: E402
import netguard  # noqa: E402  — отсечка хоста, не ответившего в этом прогоне (04.10)
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
    # ОБЛАСТИ ПОВЕРХ ЗОН (владелец 29.09): моря, где El Niño отзывается погодой и хозяйством. Годы и
    # норма — из плашек PSL (oisst_years.py), как у зон; суточный хвост — с ERDDAP, как у всех.
    "eaus": {"lat": (-38, -25), "lon": [(150, 160)], "stride": 2, "title": "East Australia coast"},
    "med": {"lat": (30, 46), "lon": [(0, 36)], "stride": 4, "title": "Mediterranean"},
    "panama": {"lat": (5, 9), "lon": [(-82, -77)], "stride": 1, "title": "Gulf of Panama"},
    "barents": {"lat": (70, 78), "lon": [(20, 55)], "stride": 4, "title": "Barents Sea"},
    "bengal": {"lat": (8, 20), "lon": [(82, 94)], "stride": 4, "title": "Bay of Bengal"},
    # ПУТЬ ПРИБРЕЖНОЙ ВОЛНЫ КЕЛЬВИНА (владелец 29.09, статья Guardian о волне у Калифорнии): три бокса у
    # берега; норма — суточная норма PSL 1991–2020 («clim»: «ltm»), годы — одной плашкой на три бокса.
    "baja": {"lat": (24, 31), "lon": [(-118, -113)], "stride": 2, "title": "Baja California coast", "clim": "ltm"},
    "socal": {"lat": (32, 35), "lon": [(-121, -117)], "stride": 1, "title": "Southern California Bight", "clim": "ltm"},
    "ncal": {"lat": (36, 42), "lon": [(-127, -122)], "stride": 2, "title": "Northern California coast", "clim": "ltm"},
    # Мировой океан 60°S–60°N нужен только как хвост к ряду climatereanalyzer: климатология и
    # аналоги у него берутся оттуда, поэтому climatology для него не строим (см. build()).
    "world": {"lat": (-59.875, 59.875), "lon": [(-179.875, 179.875)], "stride": 8, "title": "World ocean 60°S–60°N",
              "tail_only": True},
}
CLIM_YEARS = (1991, 2020)
ANALOG_YEARS = (1982, 1997, 2015, 2023)
# Сколько суток СЛЕДУЮЩЕГО года держим у каждого аналога. Столько же берёт watch.py для
# Niño 3.4, и ровно на столько ось графика шире календарного года (js/enso.js: 366 + 120).
NEXT_DAYS = 120
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
    netguard.guard(q)                                   # хост уже не ответил в этом прогоне — не ждём (04.10)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = r.read()
    except Exception as e:                              # noqa: BLE001
        netguard.mark(q, e)
        raise
    ds = netCDF4.Dataset("inmem.nc", memory=data)
    try:
        t = ds["time"]
        times = [x.strftime("%Y-%m-%d") for x in netCDF4.num2date(t[:], t.units)]
        lats = np.array(ds["latitude"][:], float)
        sst = _fill_masked(ds["sst"][:])[:, 0]          # (t, lat, lon)
    finally:
        ds.close()
    return times, lats, sst


def last_time(dataset, timeout=60):
    q = f"{E}{dataset}.json?time[(last)]"
    req = urllib.request.Request(q, headers={"User-Agent": UA})
    netguard.guard(q)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
    except Exception as e:                              # noqa: BLE001
        netguard.mark(q, e)
        raise
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
    safeio.write_text(p, json.dumps(obj, ensure_ascii=False))


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


def _full_year(y, arr):
    """Год считается полным, когда в нём есть каждый день (366 в високосный, 365 в обычный)."""
    return int(np.isfinite(arr).sum()) >= (366 if calendar.isleap(y) else 365)


def _years_file(box):
    """Полные годы бокса из years_<бокс>.json (years_all.py, PSL NCSS): та же сетка 366 слотов."""
    try:
        return json.loads((CACHE / f"years_{box}.json").read_text(encoding="utf-8")).get("years") or {}
    except Exception:                                            # noqa: BLE001
        return {}


def clim_coverage(box):
    """Сколько лет вошло в каждый слот нормы: (мин, макс, слотов с недобором, слотов с перебором)."""
    cl = _load(CACHE / f"clim_{box}.json", {})
    n = [int(x) for i, x in enumerate(cl.get("n") or []) if i != 59]
    want = CLIM_YEARS[1] - CLIM_YEARS[0] + 1
    if not n:
        return None
    return min(n), max(n), sum(1 for x in n if x < want), sum(1 for x in n if x > want), cl.get("built")


LTM_URL = "https://psl.noaa.gov/thredds/dodsC/Datasets/noaa.oisst.v2.highres/sst.day.mean.ltm.1991-2020.nc"


def ltm_box_means(boxes, verbose=False):
    """Суточная норма PSL 1991–2020 (365 дней) — среднее по каждому боксу. Читается по OPeNDAP сплошными
    блоками по 92 дня (прореженный срез сервер не отдаёт, полный запрос NCSS упирается в минуту прокси)."""
    import netCDF4
    ds = netCDF4.Dataset(LTM_URL)
    try:
        lat = np.array(ds["lat"][:], float)
        lon = np.mod(np.array(ds["lon"][:], float), 360.0)
        out = {}
        for bx in boxes:
            b = BOXES[bx]
            li = np.where((lat >= b["lat"][0] - 1e-6) & (lat <= b["lat"][1] + 1e-6))[0]
            lo_m = np.zeros(len(lon), bool)
            for lo, hi in b["lon"]:
                lo_m |= (lon >= (lo % 360.0) - 1e-6) & (lon <= (hi % 360.0) + 1e-6)
            lj = np.where(lo_m)[0]
            parts = []
            for k0 in range(0, 365, 92):
                t0 = time.time()
                blk = ds["sst"][k0:min(k0 + 92, 365), li[0]:li[-1] + 1, lj[0]:lj[-1] + 1]
                a = np.ma.filled(np.ma.masked_invalid(blk.astype(float)), np.nan)
                with np.errstate(all="ignore"):
                    parts.append(np.nanmean(np.nanmean(a, axis=2), axis=1))
                if verbose:
                    print(f"  {bx}: норма PSL, дни {k0}…{min(k0 + 92, 365) - 1}, {time.time() - t0:.0f} с")
            out[bx] = np.concatenate(parts)
        return out
    finally:
        ds.close()


def build_clim_ltm(box, verbose=False, save=True):
    """Норма бокса из суточной нормы PSL 1991–2020 — там, где 30 лет суточных данных качать долго (боксы у
    Калифорнии, 29.09). Сверено на Niño 3.4 с нашей нормой из 30 полных лет: −0,015 ± 0,012 °C."""
    p = CACHE / f"clim_{box}.json"
    b = BOXES[box]
    m = ltm_box_means([box], verbose)[box]
    a = np.concatenate([m[:59], [np.nan], m[59:]])       # 365 дней → сетка 366, 29 февраля — среднее соседей
    a[59] = np.nanmean([a[58], a[60]])
    k, h = 15, 7
    ext = np.concatenate([a[-h:], a, a[:h]])
    sm = np.array([np.nanmean(ext[i:i + k]) for i in range(366)])
    have = _years_file(box)
    yrs = have if isinstance(have, dict) else {}
    try:
        nxt = json.loads((CACHE / f"years_{box}.json").read_text(encoding="utf-8")).get("next") or {}
    except Exception:                                            # noqa: BLE001
        nxt = {}
    ly = str(date.today().year - 1)
    cl = {"doy": [round(float(v), 4) for v in sm], "n": [30] * 366,
          "years": list(CLIM_YEARS), "stride": b["stride"], "smooth_days": k, "complete": True, "from_ltm": True,
          "analogs": {str(y): yrs[str(y)] for y in ANALOG_YEARS if str(y) in yrs},
          "analogs_next": {str(y): nxt[str(y)] for y in ANALOG_YEARS if str(y) in nxt},
          "last_years": {ly: yrs[ly]} if ly in yrs else {},
          "built": datetime.now().strftime("%Y-%m-%d %H:%M"),
          "source": "NOAA OISST v2.1 daily long-term mean 1991–2020 from PSL (sst.day.mean.ltm.1991-2020.nc), box mean, "
                    "15-day centred smoothing; past years from the final grid via PSL"}
    if save:
        _save(p, cl)
    return cl


def build_clim(box, verbose=False, force=False, save=True):
    """Климатология 1991–2020 и аналоги по календарю — один раз, из окончательного набора.

    ПОЛНОТА ЛЕТ ОБЯЗАТЕЛЬНА (29.09). Норма, собранная 10.09, вобрала по дням года от 7 до 32 лет вместо
    30: годы с ERDDAP приходили обрывками, а даты соседних лет задваивали слоты. Норма вышла кривой по
    сезону (против нормы CPC: март −0,17, июль +0,26 °C), и наш бокс Niño 3.4 показывал +2,94 там, где
    NOAA и climatereanalyzer давали +3,07. Теперь годы берутся из years_<бокс>.json (PSL, полные),
    недостающие докачиваются с проверкой, чужие даты отбрасываются, и норма НЕ пишется, пока в каждом
    слоте (кроме 29 февраля) не ровно 30 лет. Окно сглаживания центрированное: прежнее брало 15 дней ДО
    дня и запаздывало на неделю. Пересборка — только `python oisst.py --clim` (по слову владельца:
    меняются уровни аномалий боксов на панели).
    """
    if BOXES[box].get("clim") == "ltm":
        return build_clim_ltm(box, verbose, save)
    p = CACHE / f"clim_{box}.json"
    cl = _load(p, {})
    if not force and cl.get("complete") and cl.get("doy") and cl.get("analogs") \
            and all(str(y) in cl["analogs"] for y in ANALOG_YEARS):
        return cl
    b = BOXES[box]
    years = list(range(CLIM_YEARS[0], CLIM_YEARS[1] + 1))
    analogs = dict(cl.get("analogs") or {})
    have = _years_file(box)
    got = {}
    for y in years + [y for y in ANALOG_YEARS if y not in years]:
        arr = have.get(str(y))
        if arr and len(arr) == 366:
            a = np.array([np.nan if v is None else float(v) for v in arr])
            if _full_year(y, a):
                got[y] = a
                continue
        for attempt in range(3):
            t0 = time.time()
            try:
                m = box_means(FINAL, box, f"{y}-01-01", f"{y}-12-31")
                a = np.full(366, np.nan)
                for dt, v in m.items():
                    if dt[:4] == str(y):                         # только свой год: чужие даты задваивали слоты
                        a[grid_index(date.fromisoformat(dt))] = v
                if _full_year(y, a):
                    got[y] = a
                    if verbose:
                        print(f"  {box} {y}: {int(np.isfinite(a).sum())} дней, {time.time() - t0:.0f} с")
                    break
                if verbose:
                    print(f"  {box} {y}: неполный год ({int(np.isfinite(a).sum())} дней), попытка {attempt + 1}")
            except Exception as e:                               # noqa: BLE001
                if verbose:
                    print(f"  {box} {y}: {str(e)[:100]}")
            time.sleep(3)
    sums, cnts = np.zeros(366), np.zeros(366)
    for y in years:
        a = got.get(y)
        if a is None:
            continue
        ok = np.isfinite(a)
        sums[ok] += a[ok]
        cnts[ok] += 1
    for y in ANALOG_YEARS:
        if y in got:
            analogs[str(y)] = [None if not np.isfinite(v) else round(float(v), 3) for v in got[y]]
    complete = all(int(cnts[i]) == len(years) for i in range(366) if i != 59)
    if not complete:
        missing = [y for y in years if y not in got]
        print(f"  {box}: норма НЕ записана — не хватает лет {missing or '(слоты с недобором)'}; прежний файл оставлен")
        return cl
    mean = sums / np.maximum(cnts, 1)
    # 29 февраля видно раз в четыре года: заполняем соседями до сглаживания
    if cnts[59] < 5:
        mean[59] = np.nanmean([mean[58], mean[60]])
    # 15-дневное круговое сглаживание, центрированное (±7 дней) — как у суточных климатологий
    k, h = 15, 7
    ext = np.concatenate([mean[-h:], mean, mean[:h]])
    sm = np.array([np.nanmean(ext[i:i + k]) for i in range(len(mean))])
    cl = {"doy": [round(float(v), 4) for v in sm], "n": [int(c) for c in cnts],
          "years": list(CLIM_YEARS), "stride": b["stride"], "smooth_days": k, "complete": True,
          "analogs": analogs, "built": datetime.now().strftime("%Y-%m-%d %H:%M"),
          "source": f"NOAA OISST v2.1 final ({FINAL}) via CoastWatch ERDDAP; full years from years_{box}.json (PSL NCSS) where present"}
    if save:
        _save(p, cl)
    return cl


def build_analog_next(box, verbose=False):
    """Продолжение каждого аналога в следующий год: первые 120 суток года y+1.

    Владелец 10.09: «на графике они заканчиваются январём, а почему не проследовать
    следующий год, обычно следующий год важен, чтобы увидеть историческую динамику».
    Он прав, и данных нам хватало: ось графика и так шире календарного года на 120
    суток, для Niño 3.4 продолжение приходит из watch.py, а остальные зоны собирались на
    клиенте из этого файла, где лежал ровно календарный год. Четверть картинки пустовала.
    Для Niño 1+2 обрезанным оказывался как раз тот год, где стоит исторический максимум
    зоны: 29 июня 1983 года.

    Считается один раз, как климатология, и дописывается в тот же файл отдельным ключом:
    ежедневный прогон от этого не тяжелеет. Год, который уже посчитан, повторно не берём —
    прерванный сбор можно продолжить тем же вызовом.
    """
    p = CACHE / f"clim_{box}.json"
    cl = _load(p, {})
    if not cl.get("doy"):
        return cl
    nxt = cl.get("analogs_next") or {}
    need = [y for y in ANALOG_YEARS if str(y) not in nxt]
    if not need:
        return cl
    got = 0
    for y in need:
        t0 = time.time()
        try:
            m = box_means(FINAL, box, f"{y + 1}-01-01", f"{y + 1}-05-31")
        except Exception as e:                                   # noqa: BLE001
            if verbose:
                print(f"  {box} {y + 1}: {str(e)[:100]}")
            continue
        arr = np.full(366, np.nan)                               # та же сетка, что у аналогов
        for dt, v in m.items():
            arr[grid_index(date.fromisoformat(dt))] = v
        nxt[str(y)] = [None if not np.isfinite(v) else round(float(v), 3) for v in arr[:NEXT_DAYS]]
        got += 1
        if verbose:
            print(f"  {box} {y}→{y + 1}: {len(m)} дней, {time.time() - t0:.0f} с")
    if not got:
        return cl
    cl["analogs_next"] = nxt
    cl["next_days"] = NEXT_DAYS
    cl["built"] = datetime.now().strftime("%Y-%m-%d %H:%M")
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


# ------------------------------------------------------------------ рекорды суточных боксов
# РЕКОРДЫ БОКСОВ (04.10, владелец: «у зоны 1+2 дневной супер-рекорд, а этого нигде нет — ни в KPI, ни в
# обзоре; как ты следишь за рекордами?»). Правила рекордов были у недельных индексов NOAA, у суточного
# Niño 3.4 (climatereanalyzer), у мирового океана, у буёв и у тёплого объёма — а у наших суточных боксов
# не было никакого, хотя все годы с 1982 лежат в years_<бокс>.json с 24.09. Потолок — всё, что бокс видел
# в прошлые календарные годы (продолжения next не берём: это начало следующего года, а последнее из них —
# уже этот год). Три меры: суточная аномалия, среднее за 7 суток до дня, сама температура воды.
BR_FILE = ROOT / "box-records.json"


def _gdate(y, i):
    """клетка 366-дневной сетки → дата года y (у невисокосного клетка 59 пуста, дальше сдвиг на день)"""
    leap = calendar.isleap(y)
    if not leap and i >= 59:
        i -= 1
    return (date(y, 1, 1) + timedelta(days=i)).isoformat()


def _trail7(a):
    out, win = [], []
    for v in a:
        win = (win + [v])[-7:]
        f = [x for x in win if x is not None]
        out.append(sum(f) / len(f) if v is not None and len(f) >= 4 else None)
    return out


def box_record(box, s, cl):
    if not s or not cl.get("doy"):
        return None
    p = CACHE / f"years_{box}.json"
    if not p.exists():
        return None
    Y = json.loads(p.read_text(encoding="utf-8")).get("years") or {}
    doy = cl["doy"]
    cy = int(s["last_date"][:4])
    best = {"day": None, "week": None, "abs": None}

    def up(k, v, y, i):
        if v is not None and (best[k] is None or v > best[k][0]):
            best[k] = (v, _gdate(y, i))
    years = sorted(int(y) for y in Y if int(y) < cy)
    for y in years:
        arr = Y[str(y)] or []
        an = [None if v is None or i >= len(doy) or doy[i] is None else v - doy[i] for i, v in enumerate(arr)]
        for i, v in enumerate(an):
            up("day", v, y, i)
            up("abs", arr[i], y, i)
        for i, v in enumerate(_trail7(an)):
            up("week", v, y, i)
    if not best["day"]:
        return None
    # этот год: файл годов (окончательный ряд) и сверху хвост бокса (NRT, свежее)
    cur = list(Y.get(str(cy)) or [None] * 366) + [None] * max(0, 366 - len(Y.get(str(cy)) or []))
    for d, v in zip(s["dates"], s["sst"]):
        dd = date.fromisoformat(d)
        if dd.year == cy and v is not None:
            cur[grid_index(dd)] = v
    an = [None if v is None or doy[i] is None else v - doy[i] for i, v in enumerate(cur[:366])]
    w7 = _trail7(an)
    out = {"since": years[0] if years else None, "until": years[-1] if years else None,
           "date": s["last_date"], "preliminary_days": REFETCH_DAYS}
    for k, ser, now in (("day", an, s.get("last_anom")), ("week", w7, s.get("mean7")), ("abs", cur, s.get("last_sst"))):
        pv, pd = best[k]
        mx, mi = None, None
        above = [i for i, v in enumerate(ser) if v is not None and v > pv]
        for i, v in enumerate(ser):
            if v is not None and (mx is None or v > mx):
                mx, mi = v, i
        out[k] = {"prior": round(pv, 2), "prior_date": pd, "now": None if now is None else round(now, 2),
                  "above": bool(now is not None and now > pv),
                  "max_this_year": None if mx is None else round(mx, 2), "max_date": None if mi is None else _gdate(cy, mi),
                  "days_above": len(above), "first_above": _gdate(cy, above[0]) if above else None}
    return out


def write_box_records(boxes):
    """Сжатый файл для панели: лента KPI, обзор и сцена берут его сразу, без годовых файлов."""
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "note": ("Each daily box against everything it measured in earlier calendar years since 1982: the daily "
                    "anomaly, the mean of the 7 days up to the day, and the water temperature itself. The last "
                    f"{REFETCH_DAYS} days are NOAA's preliminary values and can move by a few hundredths."),
           "boxes": {b: {"title": r.get("title"), "last_date": r.get("last_date"), "record": r.get("record")}
                     for b, r in boxes.items() if r.get("record")}}
    safeio.write_text(BR_FILE, json.dumps(doc, ensure_ascii=False))
    return doc


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
        # источник уже мог пометить свои предварительные дни (20.09): предварительное начинается с раннего из двух
        cr["prelim_from"] = min(cr.get("prelim_from") or first.isoformat(), first.isoformat())
        cr["splice_offset"] = round(off, 3)
    return first


def build(today=None, cr_nino34=None, cr_world=None, verbose=False):
    """Всё для панели: хвосты, аномалии, аналоги, сверка. Климатологии читаются из кэша; если
    какой-то нет, бокс отдаётся без аномалии и с пометкой — refresh не должен ждать полчаса."""
    today = today or date.today()
    CACHE.mkdir(parents=True, exist_ok=True)
    out = {"boxes": {}, "source": f"NOAA OISST v2.1 NRT ({NRT}) via CoastWatch ERDDAP, box means computed by us",
           "clim": f"own {CLIM_YEARS[0]}–{CLIM_YEARS[1]} daily climatology from the final OISST grid, 15-day smoothing",
           "note": ("Direct from the NOAA grid, a day or two behind. The preliminary (NRT) values of the last "
                    "two weeks are revised by NOAA later, so the last days can move by a few hundredths. "
                    "The Niño 3.4 box is checked every day against climatereanalyzer on the days both have.")}
    # ПРОБА СЕРВЕРА ПЕРЕД ЧЕТЫРНАДЦАТЬЮ БОКСАМИ (04.10): один короткий запрос; не ответил — хвосты берутся
    # из кэша с пометкой, вместо 14 × 300 секунд ожидания
    try:
        last_time(NRT, timeout=30)
    except Exception as e:                                       # noqa: BLE001
        if verbose:
            print(f"  ERDDAP не ответил на пробу ({str(e)[:80]}): хвосты боксов — из кэша")
    for box, b in BOXES.items():
        store = update_tail(box, today, verbose)
        cl = {} if b.get("tail_only") else _load(CACHE / f"clim_{box}.json", {})
        s = _series(store, cl, today) if store.get("sst") else None
        rec = {"title": b["title"], "stride": b["stride"], "error": store.get("error") or "",
               "fetched": store.get("fetched"), "has_clim": bool(cl.get("doy"))}
        if s:
            rec.update(s)
            try:
                rec["record"] = box_record(box, s, cl)          # рекорды бокса против всех прошлых лет (04.10)
            except Exception as e:                               # noqa: BLE001
                rec["record_error"] = str(e)[:120]
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
    try:
        write_box_records(out["boxes"])
    except Exception as e:                                       # noqa: BLE001
        out["records_error"] = str(e)[:120]
    return out


if __name__ == "__main__":
    import sys
    if "--check-clim" in sys.argv:
        # покрытие норм без записи: сколько лет в слоте (29.09: было 7…32 вместо 30)
        for bx, bb in BOXES.items():
            if bb.get("tail_only"):
                continue
            c = clim_coverage(bx)
            print(f"{bx:8s}", "нормы нет" if c is None else f"лет в слоте {c[0]}…{c[1]}, недобор {c[2]}, перебор {c[3]}, сборка {c[4]}")
        raise SystemExit(0)
    if "--records" in sys.argv:
        # рекорды боксов без сети: склад хвостов и годовые файлы с диска (04.10)
        tdy, bxs = date.today(), {}
        for bx, bb in BOXES.items():
            if bb.get("tail_only"):
                continue
            cl0 = _load(CACHE / f"clim_{bx}.json", {})
            s0 = _series(_load(CACHE / f"{bx}.json", {}), cl0, tdy)
            if not s0:
                continue
            r0 = {"title": bb["title"]}; r0.update(s0)
            r0["record"] = box_record(bx, s0, cl0)
            bxs[bx] = r0
        doc = write_box_records(bxs)
        for bx, r0 in doc["boxes"].items():
            rc = r0["record"]
            print(f"{bx:8s} день {rc['day']['now']:+.2f} против {rc['day']['prior']:+.2f} ({rc['day']['prior_date']})"
                  f"{' РЕКОРД' if rc['day']['above'] else ''} · 7 дн {rc['week']['now']:+.2f} против {rc['week']['prior']:+.2f}"
                  f" · вода {rc['abs']['now']:.2f} против {rc['abs']['prior']:.2f}{' РЕКОРД' if rc['abs']['above'] else ''}"
                  f" · дней выше суточного рекорда {rc['day']['days_above']}")
        raise SystemExit(0)
    if "--clim" in sys.argv:
        for bx, bb in BOXES.items():
            if bb.get("tail_only"):
                continue
            print("климатология", bx)
            build_clim(bx, verbose=True, force="--force" in sys.argv)
            build_analog_next(bx, verbose=True)          # продолжение аналогов в следующий год
            build_last_year(bx, date.today().year - 1, verbose=True)
        print("готово")
    else:
        r = build(verbose=True)
        for bx, rec in r["boxes"].items():
            print(f"{bx:8s} {rec.get('last_date')} sst {rec.get('last_sst')} anom {rec.get('last_anom')} "
                  f"stale {rec.get('days_stale')} clim {rec.get('has_clim')} {rec.get('error') or ''}")
        print("check:", r["check"])
