# -*- coding: utf-8 -*-
"""Горные точки и лёд: где теплее нормы и сколько дней в году там тает.

Владелец 14.09: «нам нужны города не только в зоне, но и вообще города, где наблюдается
аномалия и куда мы можем дотянуться; горные районы, угрозы ледникам — хороший показатель».

Почему точки, а не города. Города панели (cities.py) меряют ДРУГОЕ: насколько врут три
прогнозные модели против факта. Здесь вопрос иной — насколько воздух над самим льдом ушёл
от собственной нормы и сколько дней он держится выше нуля. Это и есть угроза леднику,
выраженная величиной, которую можно померить каждый день, а не раз в год.

ТРИ ЧИСЛА НА ТОЧКУ, И ТОЛЬКО ОНИ ЧЕСТНЫЕ:

  · АНОМАЛИЯ ВОЗДУХА — тот же кирпич, что считает Niño 3.4 и шесть регионов суши
    (watch.series_watch): отклонение от среднего 1991–2020 на тот же день года, полоса всех
    лет с 1981, рекорды, CUSUM, прогноз на 14 дней, годы-аналоги события.
  · ДНИ ТАЯНИЯ — сколько дней в году максимум был выше нуля. Ледник живёт не средней
    температурой, а тем, сколько суток по нему течёт вода. Считаем за каждый год ряда и
    отдельно «сколько уже набежало в этом году к этому дню против нормы к этому же дню» —
    иначе неполный год врёт в меньшую сторону.
  · ДОЛЯ СНЕГА — какая часть дождливых дней выпала снегом. Ледник кормится снегом; когда та
    же вода приходит дождём, она не прибавляет массу, а ускоряет таяние. Считаем долю дней
    с ненулевым снегопадом среди дней с осадками, за год.

ЧЕГО ЗДЕСЬ НЕТ И ПОЧЕМУ:
  · НУЛЕВОЙ ИЗОТЕРМЫ (высоты, где 0 °C) нет: у Open-Meteo `freezing_level_height` и уровни
    давления живут только в прогнозном срезе, в архиве они пустые — проверено 14.09 на
    1995, 2023 и 2026 годах. Врать расчётом по одной точке не будем.
  · БАЛАНСА МАССЫ здесь нет тоже: его меряют на самих ледниках, и он у нас уже есть годовым
    рядом WGMS (ice_snow.py). Этот слой — суточная приставка к той годовой записи, а не
    замена: «сколько воды ледник потерял» и «сколько дней над ним текло» — разные величины.
  · ERA5 НЕ ЕСТЬ ПОВЕРХНОСТЬ ЛЬДА. Сетка отдаёт свою высоту (её и печатаем), и она обычно
    ниже вершины и выше долины. Дни таяния на высоте сетки — показатель, а не замер на льду.

Точки выбраны по двум признакам сразу: там есть лёд, и туда дотягивается либо Эль-Ниньо
(тропические Анды, Новая Зеландия, Восточная Африка), либо наш же вопрос «а где событие
видно НЕ должно быть» (Альпы, Норвегия, Кавказ).

    python tools/enso/glaciers.py --plan      список точек, без сети
    python tools/enso/glaciers.py             дотянуть архив и пересчитать glaciers.json
    python tools/enso/glaciers.py --full      перекачать всю историю с 1981 (раз в жизни)
"""
import argparse
import calendar
import json
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio                                                    # запись с повтором и подменой целиком (17.09)
import watch as WT                                              # noqa: E402

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"
RAW = ROOT / "raw" / "glaciers"
OUT = ROOT / "glaciers.json"
CLIM = (1991, 2020)
START = "1981-01-01"
VARS = ["temperature_2m_mean", "temperature_2m_max", "snowfall_sum", "precipitation_sum"]

# ключ, имя на панели, широта, долгота, id региона панели, что это за лёд и при чём тут событие
POINTS = [
    ("oetztal", "Ötztal Alps, Austria", 46.80, 10.77, "europe",
     "Hintereisferner and its neighbours above Innsbruck — one of the longest measured glacier records in the world (WGMS reference glacier since 1952).",
     "no reliable El Niño signal here: this point is the control, the place where the event should NOT show."),
    ("mont_blanc", "Mont Blanc, France–Italy", 45.87, 6.87, "europe",
     "Mer de Glace and the Argentière basin, the largest ice body of the western Alps.",
     "control point, like the Ötztal: the Alps answer the North Atlantic, not the Pacific."),
    ("jostedal", "Jostedalsbreen, Norway", 61.65, 7.00, "europe",
     "The largest ice cap of mainland Europe, fed by Atlantic snowfall.",
     "maritime control: it gains mass in stormy winters and loses it in warm summers, on the Atlantic clock."),
    ("elbrus", "Elbrus, Caucasus", 43.35, 42.44, "europe",
     "The ice cap of the highest point of Europe; the water tower of the northern Caucasus.",
     "control point between the Atlantic and the monsoon."),
    ("cordillera_blanca", "Cordillera Blanca, Peru", -9.12, -77.61, "andes_peru",
     "The largest tropical ice field on the planet; the dry-season water of the Santa valley comes off it.",
     "direct El Niño reach: warm years melt the tropical Andes fastest, and the coast below is where this event is strongest."),
    ("quelccaya", "Quelccaya, Peru", -13.93, -70.83, "andes_peru",
     "The tropical ice cap that holds the Andean climate record in its layers.",
     "direct El Niño reach: its ice cores are read as a record of past events."),
    ("zongo", "Zongo, Bolivia", -16.25, -68.15, "andes_peru",
     "Huayna Potosí and the Zongo glacier, a WGMS reference glacier above La Paz.",
     "direct El Niño reach: mass balance here swings with the Pacific, negative in warm years."),
    ("central_andes", "Central Andes, Chile–Argentina", -32.90, -70.10, "andes_peru",
     "The Olivares and Aconcagua basins: snowpack rather than ice, and the summer water of Santiago and Mendoza.",
     "El Niño usually brings MORE winter snow here, so this point can move the other way from the tropics."),
    ("southern_alps", "Southern Alps, New Zealand", -43.55, 170.17, "pacific_islands",
     "Tasman and Franz Josef, the fastest-responding glaciers of the temperate zone.",
     "El Niño reach: it turns the westerlies on, which changes both snowfall and melt within a season."),
    ("khumbu", "Khumbu, Nepal", 27.97, 86.85, "south_asia",
     "The Everest glaciers; the pre-monsoon water of the Dudh Koshi.",
     "the monsoon rules here; the El Niño link is indirect, through a weaker monsoon."),
    ("baltoro", "Baltoro, Karakoram", 35.75, 76.40, "south_asia",
     "Baltoro and its neighbours — the glaciers that famously did NOT retreat while the rest of the world's did.",
     "the Karakoram anomaly: the one mountain range where the ice held its ground. Worth watching for when that ends."),
    ("mount_kenya", "Mount Kenya", -0.15, 37.31, "east_africa",
     "The last equatorial ice of Africa: a few hundred metres of it left, and shrinking.",
     "El Niño reach: East Africa gets its short rains from it, and the ice reads the same air."),
    ("wrangell", "Wrangell–St Elias, Alaska", 61.40, -142.50, "pacific_north",
     "The largest ice field of North America, the biggest single contributor of glacier melt to the sea.",
     "North Pacific reach: the event changes the winter storm track that feeds it."),
]


# ---------------------------------------------------------------- сеть
def _get(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "bridge42worlds enso"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:                                   # noqa: BLE001
            last = e
            time.sleep(4 * (i + 1))                              # 429 у Open-Meteo лечится паузой
    raise RuntimeError(str(last)[:200])


def fetch(key, lat, lon, d0, d1):
    # НАБОР ДАННЫХ ПРИБИТ ГВОЗДЁМ. Поймано 14.09 на первом же прогоне: у Йостедальсбреена
    # 2020-е дали 297 градусо-дней против 560 в 2000-х, а 2026-й вышел самым холодным сезоном
    # за 46 лет — в теплеющем мире. Причина не в погоде: без ключа `models` Open-Meteo сам
    # выбирает набор, и на свежих годах выбирает ДРУГОЙ. Тот же день, та же точка, 15 июля:
    #   1995   умолчание 9.4   era5 10.0   era5_land 9.4
    #   2015   умолчание 2.2   era5  2.1   era5_land 2.2
    #   2025   умолчание 5.8   era5 14.4   era5_land 12.7
    # До середины 2010-х умолчание совпадает с era5_land, дальше расходится на семь градусов —
    # это как если бы точка уехала на километр вверх. Склеенный из двух наборов ряд даёт
    # ложное похолодание ровно там, где мы ищем потепление.
    # Берём ERA5-Land и только его: 9 км против 31 км у ERA5 (для гор это решает), история
    # с 1950 года, отставание около пяти суток.
    u = (f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
         f"&start_date={d0}&end_date={d1}&timezone=UTC&models=era5_land&daily=" + ",".join(VARS))
    res = _get(u)
    d = res.get("daily") or {}
    rows = {}
    for i, t in enumerate(d.get("time") or []):
        vals = [(d.get(v) or [None] * (i + 1))[i] for v in VARS]
        if vals[0] is None:                                      # без средней температуры день бесполезен
            continue
        rows[t] = [None if v is None else round(float(v), 2) for v in vals]
    return rows, res.get("elevation")


def store_path(key):
    return RAW / f"{key}.json"


def load_store(key):
    p = store_path(key)
    if not p.exists():
        return {"rows": {}, "elevation": None}
    return json.loads(p.read_text(encoding="utf-8"))


def save_store(key, st):
    RAW.mkdir(parents=True, exist_ok=True)
    safeio.write_text(store_path(key), json.dumps(st, ensure_ascii=False))


def top_up(key, lat, lon, full=False, verbose=True):
    """Догрузить хвост (или всю историю). Архив ERA5 отстаёт на несколько суток."""
    st = load_store(key)
    rows = st.get("rows") or {}
    end = (date.today() - timedelta(days=2)).isoformat()
    d0 = START if (full or not rows) else (date.fromisoformat(max(rows)) - timedelta(days=10)).isoformat()
    if d0 > end:
        return st, 0
    got, elev = fetch(key, lat, lon, d0, end)
    rows.update(got)
    st["rows"] = rows
    if elev is not None:
        st["elevation"] = elev
    st["lat"], st["lon"] = lat, lon
    save_store(key, st)
    if verbose:
        print(f"  {key:<18} +{len(got):5d} дней, всего {len(rows)}, сетка {st.get('elevation')} м")
    return st, len(got)


# ---------------------------------------------------------------- счёт
def grid_index(d):
    doy = d.timetuple().tm_yday - 1
    return doy if calendar.isleap(d.year) or doy < 59 else doy + 1


def dataset(rows, col=0):
    """{дата: [tmean, tmax, snow, prec]} → вид, который понимает watch.series_watch."""
    years = {}
    for k, v in rows.items():
        if v[col] is None:
            continue
        d = date.fromisoformat(k)
        years.setdefault(d.year, np.full(366, np.nan))[grid_index(d)] = float(v[col])
    cy = [y for y in range(CLIM[0], CLIM[1] + 1) if y in years]
    if len(cy) < 20:
        raise RuntimeError(f"мало лет климатологии: {len(cy)}")
    clim = np.nanmean(np.array([years[y] for y in cy]), axis=0)
    clim = np.where(np.isfinite(clim), clim, np.nanmean(clim))
    pad = np.concatenate([clim[-7:], clim, clim[:7]])
    clim = np.convolve(pad, np.ones(15) / 15, mode="valid")
    y_last = max(years)
    fin = np.where(np.isfinite(years[y_last]))[0]
    last_idx = int(fin[-1])
    d0 = date(y_last, 1, 1)
    last_date = d0 + timedelta(days=last_idx if calendar.isleap(y_last) or last_idx < 59 else last_idx - 1)
    return {"years": years, "clim": clim, "last_year": y_last, "last_n": int(len(fin)),
            "last_idx": last_idx, "last_date": last_date}


def melt_days(rows):
    """Дни, когда максимум был выше нуля: за каждый год и отдельно «к этому же дню».

    Неполный год нельзя ставить рядом с полными: к середине сентября в северных горах
    набежало не всё. Поэтому у текущего года две цифры — сколько уже, и сколько бывало к
    этому же дню года в среднем за 1991–2020."""
    by_year, to_date = {}, {}
    pdd_year, pdd_to = {}, {}
    cut = None
    for k, v in sorted(rows.items()):
        if v[1] is None:
            continue
        d = date.fromisoformat(k)
        gi = grid_index(d)
        by_year.setdefault(d.year, 0)
        pdd_year.setdefault(d.year, 0.0)
        to_date.setdefault(d.year, {})
        pdd_to.setdefault(d.year, {})
        if v[1] > 0:
            by_year[d.year] += 1
        # ГРАДУСО-ДНИ, А НЕ ТОЛЬКО ДНИ. На 2769 м дни таяния летом насыщаются: каждый июльский
        # день и так выше нуля, и жаркий год ничем не отличается от обычного (Эцталь 14.09:
        # 145 дней при норме 145,5, хотя воздух третий по теплу за 46 лет). Сумма положительных
        # СРЕДНИХ суточных — то, чем таяние меряют в гляциологии: она растёт и числом дней, и
        # их теплом сразу, и прямо входит в модель степень-дня.
        if v[0] is not None and v[0] > 0:
            pdd_year[d.year] += float(v[0])
        to_date[d.year][gi] = by_year[d.year]
        pdd_to[d.year][gi] = round(pdd_year[d.year], 1)
    y_last = max(by_year)
    # индекс последнего дня текущего года
    cut = max(to_date[y_last]) if to_date.get(y_last) else 0
    def _upto(store, y):
        m = store.get(y) or {}
        ks = [g for g in m if g <= cut]
        return m[max(ks)] if ks else 0

    def upto(y):
        return _upto(to_date, y)

    def upto_pdd(y):
        return _upto(pdd_to, y)
    cl_years = [y for y in range(CLIM[0], CLIM[1] + 1) if y in by_year]
    full = {y: by_year[y] for y in sorted(by_year) if y != y_last}
    clim_full = float(np.mean([by_year[y] for y in cl_years])) if cl_years else float("nan")
    clim_todate = float(np.mean([upto(y) for y in cl_years])) if cl_years else float("nan")
    now = upto(y_last)
    # ранг текущего года по «к этому же дню» среди всех лет ряда
    same = sorted(((upto(y), y) for y in by_year), reverse=True)
    rank = [y for _, y in same].index(y_last) + 1
    # тренд по полным годам, дней за десятилетие
    ys = np.array([y for y in full], dtype=float)
    ds = np.array([full[y] for y in full], dtype=float)
    trend = float(np.polyfit(ys, ds, 1)[0] * 10) if len(ys) > 10 else None
    pdd_full = {y: round(pdd_year[y], 1) for y in sorted(pdd_year) if y != y_last}
    pdd_now = upto_pdd(y_last)
    pdd_clim_td = float(np.mean([upto_pdd(y) for y in cl_years])) if cl_years else float("nan")
    pdd_clim_full = float(np.mean([pdd_year[y] for y in cl_years])) if cl_years else float("nan")
    p_same = sorted(((upto_pdd(y), y) for y in pdd_year), reverse=True)
    pdd_rank = [y for _, y in p_same].index(y_last) + 1
    # РАНГ СРЕДИ НУЛЕЙ — НЕ РАНГ. На 6458 м (Кордильера-Бланка) суточная средняя не бывает выше
    # нуля ни в одном году: сумма 0 против нормы 0 давала «1-е место из 46» (проверка Fable
    # 14.09). Там таяние идёт только днём, и его меряет счёт дней по максимуму, не эта сумма.
    if pdd_now <= 0 and pdd_clim_full < 1:
        pdd_rank = None
    pys = np.array(list(pdd_full), dtype=float)
    pds = np.array([pdd_full[y] for y in pdd_full], dtype=float)
    pdd_trend = float(np.polyfit(pys, pds, 1)[0] * 10) if len(pys) > 10 else None
    return {"by_year": full, "year": y_last, "to_date": now, "clim_to_date": round(clim_todate, 1),
            "clim_full": round(clim_full, 1), "rank": rank, "of": len(by_year),
            "trend_per_decade": None if trend is None else round(trend, 1),
            "day_index": cut,
            "pdd": {"by_year": pdd_full, "to_date": round(pdd_now, 1), "clim_to_date": round(pdd_clim_td, 1),
                    "clim_full": round(pdd_clim_full, 1), "rank": pdd_rank, "of": len(pdd_year),
                    "trend_per_decade": None if pdd_trend is None else round(pdd_trend, 1),
                    "unit": "°C·day",
                    "what": "the sum of daily mean temperatures above freezing — the standard melt index"}}


def snow_share(rows):
    """Доля дней с осадками, в которые шёл снег, за год. Дождь на леднике — не прибавка."""
    wet, snowy = {}, {}
    for k, v in rows.items():
        prec, snow = v[3], v[2]
        if prec is None or prec <= 0.2:                          # 0.2 мм — уже не сухо, но ещё и не событие
            continue
        y = int(k[:4])
        wet[y] = wet.get(y, 0) + 1
        if snow and snow > 0:
            snowy[y] = snowy.get(y, 0) + 1
    out = {}
    for y in sorted(wet):
        if wet[y] >= 30:
            out[y] = round(100.0 * snowy.get(y, 0) / wet[y], 1)
    # НЕТ ДАННЫХ — НЕТ ЧИСЛА. У ERA5-Land через Open-Meteo суточные осадки приходят пустыми
    # (проверено 14.09: 16 687 дней подряд None), и доля снега считалась как «0 из 0» = 0,0 %.
    # На экране это читалось как «в Альпах снег не идёт вообще». Лучше молчать.
    if not out:
        return None
    y_last = max(out)
    cl = [out[y] for y in out if CLIM[0] <= y <= CLIM[1]]
    return {"by_year": out, "year": y_last, "now": out.get(y_last),
            "clim": round(float(np.mean(cl)), 1) if cl else None}



def build(full=False, verbose=True, pause=3.0, offline=False, only=None):
    t0 = time.time()
    series, meta, errs = {}, {}, []
    for i, (key, name, lat, lon, rid, what, enso) in enumerate(POINTS):
        try:
            # МОЛЧАНИЕ ИСТОЧНИКА НЕ СТИРАЕТ СКЛАД. Первый прогон 14.09: четыре точки словили 429
            # (рядом шла докачка городов по тому же API), и каждая выпадала из файла целиком —
            # вместе с сорока пятью годами, которые уже лежали на диске. Считаем по тому, что
            # есть, и честно пишем, на какой день оно кончается.
            try:
                # --only ограничивает СКАЧИВАНИЕ, а не файл. Поймано 14.09: шесть прогонов с
                # --only по неотвечающим точкам переписали glaciers.json одной строкой каждый
                # и обнулили семь уже посчитанных. Остальные точки считаются по складу.
                if offline or (only and key != only):
                    raise RuntimeError("offline")
                st, _n = top_up(key, lat, lon, full=full, verbose=verbose)
            except Exception as e:                               # noqa: BLE001
                st = load_store(key)
                if not (st.get("rows") or {}):
                    raise
                if not offline and not (only and key != only):
                    errs.append(f"{key}: не дотянулся ({str(e)[:60]}), считаю по складу")
                    if verbose:
                        print(f"  {key:<18} источник молчит, беру склад: {len(st['rows'])} дней")
            rows = st["rows"]
            label = f"{name}, 2 m air at {int(st.get('elevation') or 0)} m (ERA5 point)"
            w = WT.series_watch(dataset(rows, 0), label + ", daily", analog_years=WT.ANALOGS)
            w["source"] = "ERA5-Land (9 km) via Open-Meteo archive, single grid point at the glacier"
            w["point"] = [lat, lon]
            w["elevation"] = st.get("elevation")
            w["region"] = rid
            w["what"] = what
            w["enso"] = enso
            w["melt"] = melt_days(rows)
            w["snow"] = snow_share(rows)
            series["ice_" + key] = w
            if verbose:
                m = w["melt"]
                pd_ = m["pdd"]
                print(f"     {w['last_date']}: {w['last_value']:+.2f} °C, 30 d {w['level30']['anom']:+.2f} "
                      f"rank {w['level30']['rank_raw']}/{w['level30']['of']} · melt {m['to_date']} d "
                      f"vs {m['clim_to_date']} · PDD {pd_['to_date']:.0f} vs {pd_['clim_to_date']:.0f} "
                      f"rank {pd_['rank']}/{pd_['of']}")
        except Exception as e:                                   # noqa: BLE001
            errs.append(f"{key}: {str(e)[:140]}")
            if verbose:
                print(f"  {key}: {str(e)[:140]}")
        if pause and not offline and not only and i < len(POINTS) - 1:
            time.sleep(pause)
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "series": series, "errors": errs,
           "points": [{"key": "ice_" + p[0], "name": p[1], "lat": p[2], "lon": p[3], "region": p[4]} for p in POINTS],
           "note": ("Thirteen mountain points where there is ice, read exactly like the ocean boxes: the anomaly of "
                    "2 m air (ERA5-Land, 9 km, one dataset pinned across the whole history) against the "
                    "1991–2020 mean of the same calendar day, with the band of all years since "
                    "1981. Two glacier numbers come with it: how hard the melt season pushed — days above "
                    "freezing and, more tellingly, the sum of daily temperatures above freezing, the standard melt "
                    "index of glaciology — and, where the dataset serves precipitation, what share of wet days fell as snow. ERA5 is a grid, not the ice surface: the grid elevation is given for each "
                    "point, and these are indices of the pressure on the ice, not a mass balance. The measured mass "
                    "balance is the annual WGMS record on the Long term tab."),
           "secs": int(time.time() - t0)}
    safeio.write_text(OUT, json.dumps(doc, ensure_ascii=False))
    if verbose:
        print(f"glaciers.json: {len(series)} точек, {doc['secs']} с" + (f", ошибок {len(errs)}" if errs else ""))
    try:
        import ops as OPSLOG
        OPSLOG.record_run("glaciers", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                          "ok" if series and not errs else ("partial" if series else "fail"),
                          note=f"{len(series)} points")
    except Exception:                                            # noqa: BLE001
        pass
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true", help="список точек, без сети")
    ap.add_argument("--full", action="store_true", help="перекачать историю с 1981")
    ap.add_argument("--pause", type=float, default=3.0, help="пауза между точками, секунды")
    ap.add_argument("--only", help="одна точка по ключу")
    ap.add_argument("--offline", action="store_true", help="не ходить в сеть, пересчитать по складу")
    a = ap.parse_args()
    if a.plan:
        print(f"{len(POINTS)} точек:")
        for key, name, lat, lon, rid, what, _e in POINTS:
            p = store_path(key)
            have = len(json.loads(p.read_text(encoding="utf-8")).get("rows") or {}) if p.exists() else 0
            print(f"  {key:<18} {name:<32} {lat:>7.2f} {lon:>8.2f}  {rid:<14} дней в складе {have}")
        return
    if a.only and a.only not in [p[0] for p in POINTS]:
        sys.exit("нет такой точки")
    build(full=a.full, pause=a.pause, offline=a.offline, only=a.only)


if __name__ == "__main__":
    main()
