#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Журнал значений: когда изменились ДАННЫЕ, а не когда мы обновились.

Владелец 04.09: «изменение данных не равно времени обновления — мы обновили, данные не
поменялись; надо уметь показать, как данные менялись, и на каждом кирпичике стрелочку».

РАЗНИЦА, РАДИ КОТОРОЙ ВСЁ ЗАТЕЯНО. Панель до сих пор сравнивала с ПРОШЛЫМ ПРОГОНОМ: снимок
`prev` внутри latest.json. Прогонов за сутки бывает шесть, а недельный индекс NOAA выходит
раз в неделю — пять сравнений из шести показывали ноль и говорили «ничего не изменилось»,
хотя изменилось не число, а наш будильник. Здесь запись появляется, только когда изменилось
САМО ЗНАЧЕНИЕ или дата данных под ним; всё остальное журнал не замечает.

ДВЕ ДАТЫ У ЗАПИСИ, И ЭТО НЕ ИЗБЫТОК. `d` — дата самих данных (неделя NOAA, месяц FAO,
выпуск IRI): её показываем, она отвечает на вопрос «за когда это». `seen` — когда мы это
увидели: нужна для разбора полётов («данные вышли третьего, а мы взяли пятого»), на панели
не показывается. Владелец 04.09: «время там не обязательно, главная дата».

ОТКУДА БЕРЁТСЯ ПРОШЛОЕ. Каждый прогон обновления кладёт полный снимок в snapshots/. Их уже
два десятка, и они лежали мёртвым грузом. Журнал строится по ним ЗАДНИМ ЧИСЛОМ и дальше
дописывается каждым обновлением — то есть история появляется сразу, а не «через месяц
накопится».

«ОТ НАЧАЛА СОБЫТИЯ» — отдельная строка и отдельный источник. Наши снимки начинаются со
2 сентября, а событие идёт с мая (первый трёхмесячный сезон с ONI ≥ +0.5). Поэтому вторая
строка считается не по журналу, а по САМИМ РЯДАМ данных, где они есть: недельный ряд NOAA,
месячные средние океана, месячный ряд FAO. Где ряда нет (наш индекс риска, счётчики моделей),
честно говорим «с первого нашего замера» и не притворяемся, что помним май.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "enso"
SNAP = ROOT / "snapshots"


# ---------------------------------------------------------------- достать из снимка
def _g(d, *path, default=None):
    """Пройти по вложенным ключам, не падая на пустом промежуточном узле."""
    for k in path:
        if not isinstance(d, dict):
            return default
        d = d.get(k)
    return default if d is None else d


def _weekly_at(d, ym, field="n34a"):
    """Значение недельного ряда NOAA в первую неделю указанного месяца."""
    ser = _g(d, "noaa", "series", default=[]) or []
    hit = [r for r in ser if isinstance(r, dict) and (r.get("date") or "").startswith(ym)]
    return (hit[0].get(field) if hit else None)


def _month_at(d, block, ym):
    """Месячное среднее из тринадцатимесячного окна watch: (год, месяц) → аномалия."""
    try:
        y, m = int(ym[:4]), int(ym[5:7])
    except (ValueError, IndexError):
        return None
    for r in _g(d, "watch", block, "months13", default=[]) or []:
        if r.get("y") == y and r.get("m") == m:
            return r.get("anom")
    return None


def _food_at(d, ym):
    ser = _g(d, "food", "series", default={}) or {}
    months, vals = ser.get("months") or [], ser.get("index") or ser.get("values") or []
    if ym in months and len(vals) == len(months):
        return vals[months.index(ym)]
    return None


def _oni_last(d):
    """Последний сезон ONI с числом: значение и подпись сезона вместо даты."""
    cur = _g(d, "oni", "current", default={}) or {}
    last = [(k, v) for k, v in cur.items() if v is not None]
    return (last[-1][1], last[-1][0]) if last else (None, None)


def _live_at(d):
    """Сводное по живым моделям на том сезоне, с которым сравниваем реальность."""
    lv, ao = _g(d, "iri", "live", default={}) or {}, _g(d, "iri", "against_observed", default={}) or {}
    ss, mean = _g(d, "iri", "seasons", default=[]) or [], lv.get("mean") or []
    if ao.get("season") in ss:
        i = ss.index(ao["season"])
        return mean[i] if i < len(mean) else None
    return None


def _air_part(d, key):
    for p in _g(d, "air", "coupling", "parts", default=[]) or []:
        if p.get("key") == key:
            return p.get("value")
    return None


def _air_part_date(d, key):
    for p in _g(d, "air", "coupling", "parts", default=[]) or []:
        if p.get("key") == key:
            return p.get("date")
    return None


def _layer(d, key):
    for x in _g(d, "air", "layers", "items", default=[]) or []:
        if x.get("key") == key:
            return x.get("tropics")
    return None


def _layer_date(d, key):
    for x in _g(d, "air", "layers", "items", default=[]) or []:
        if x.get("key") == key:
            return x.get("date")
    return None


def _price(d, key):
    for c in _g(d, "air", "commodities", "items", default=[]) or []:
        if c.get("key") == key:
            return c.get("value")
    return None


def _price_date(d, key):
    for c in _g(d, "air", "commodities", "items", default=[]) or []:
        if c.get("key") == key:
            return c.get("date")
    return None


def _peak(d):
    comb = [v for v in (_g(d, "iri", "summary", "combined", default=[]) or []) if v is not None]
    return max(comb) if comb else None


# ---------------------------------------------------------------- реестр показателей
#
# Ключ здесь = ключ на кирпичике в панели (data-k). Один реестр на обе стороны: если
# показателя нет тут, у кирпичика не будет ни стрелки, ни истории — и это видно сразу,
# а не «почему-то не работает».
METRICS = {
    "n34_weekly": dict(
        title="Niño 3.4, weekly", unit="°C", digits=2, src="NOAA CPC weekly",
        val=lambda d: _g(d, "noaa", "latest", "n34a"), date=lambda d: _g(d, "noaa", "date"),
        at=lambda d, ym: _weekly_at(d, ym, "n34a")),
    "n12_weekly": dict(
        title="Niño 1+2, weekly", unit="°C", digits=2, src="NOAA CPC weekly",
        val=lambda d: _g(d, "noaa", "latest", "n12a"), date=lambda d: _g(d, "noaa", "date"),
        at=lambda d, ym: _weekly_at(d, ym, "n12a")),
    "n34_daily": dict(
        title="Niño 3.4, daily", unit="°C", digits=2, src="OISST v2.1 daily",
        val=lambda d: _g(d, "watch", "sst_nino34", "last_value"),
        date=lambda d: _g(d, "watch", "sst_nino34", "last_date"),
        at=lambda d, ym: _month_at(d, "sst_nino34", ym)),
    "oni": dict(
        title="ONI, official", unit="°C", digits=2, src="NOAA CPC / ERSST v6",
        val=lambda d: _oni_last(d)[0], date=lambda d: _oni_last(d)[1]),
    "sst_world": dict(
        title="World ocean, 60°S–60°N", unit="°C", digits=3, src="OISST v2.1 daily",
        val=lambda d: _g(d, "watch", "sst_world", "last_value"),
        date=lambda d: _g(d, "watch", "sst_world", "last_date"),
        at=lambda d, ym: _month_at(d, "sst_world", ym)),
    "t2_world": dict(
        title="Land + ocean, 2 m", unit="°C", digits=3, src="ERA5 daily",
        val=lambda d: _g(d, "watch", "t2_world", "last_value"),
        date=lambda d: _g(d, "watch", "t2_world", "last_date"),
        at=lambda d, ym: _month_at(d, "t2_world", ym)),
    "risk_index": dict(
        title="Risk index", unit="", digits=0, src="our own calculation",
        val=lambda d: d.get("risk_index"), date=lambda d: d.get("generated")),
    "n_risks": dict(
        title="Risks on the board", unit="", digits=0, src="our own calculation",
        val=lambda d: len(d.get("risks") or []), date=lambda d: d.get("generated")),
    "n_alerts": dict(
        title="Watchdog alerts", unit="", digits=0, src="our own rules",
        val=lambda d: len(d.get("alerts") or []), date=lambda d: d.get("generated")),
    "iri_peak": dict(
        title="Model peak, combined", unit="°C", digits=2, src="IRI plume",
        val=_peak, date=lambda d: _g(d, "iri", "issued")),
    "iri_share_below": dict(
        title="Models below reality", unit="%", digits=0, src="IRI plume vs NOAA",
        val=lambda d: _g(d, "iri", "against_observed", "share_below"),
        date=lambda d: _g(d, "iri", "issued")),
    "models_broke": dict(
        title="Models that broke", unit="", digits=0, src="IRI plume, our verification",
        val=lambda d: _g(d, "iri", "class_tally", "broke"), date=lambda d: _g(d, "iri", "issued")),
    "models_ok": dict(
        title="Models keeping up", unit="", digits=0, src="IRI plume, our verification",
        val=lambda d: _g(d, "iri", "class_tally", "ok"), date=lambda d: _g(d, "iri", "issued")),
    "food_index": dict(
        title="FAO food price index", unit="", digits=1, src="FAO GIEWS monthly",
        val=lambda d: _g(d, "food", "index"), date=lambda d: _g(d, "food", "last_month"),
        at=_food_at),
    # Экспертиза 04.09: свежие боксы OISST, глубина, ветер, RONI, Залив, фон
    "n34_box": dict(
        title="Niño 3.4, our box, daily NRT", unit="°C", digits=2, src="NOAA OISST NRT via ERDDAP",
        val=lambda d: _g(d, "oisst", "boxes", "nino34", "last_anom"), date=lambda d: _g(d, "oisst", "boxes", "nino34", "last_date")),
    "n12_box": dict(
        title="Niño 1+2, our box, daily NRT", unit="°C", digits=2, src="NOAA OISST NRT via ERDDAP",
        val=lambda d: _g(d, "oisst", "boxes", "nino12", "last_anom"), date=lambda d: _g(d, "oisst", "boxes", "nino12", "last_date")),
    "gulf_sst": dict(
        title="Persian Gulf SST, daily", unit="°C", digits=2, src="NOAA OISST NRT via ERDDAP",
        val=lambda d: _g(d, "oisst", "boxes", "gulf", "last_sst"), date=lambda d: _g(d, "oisst", "boxes", "gulf", "last_date")),
    "subsurface_warmest": dict(
        title="Warmest subsurface anomaly, moorings", unit="°C", digits=1, src="TAO/TRITON via ERDDAP",
        val=lambda d: _g(d, "subsurface", "tao", "warmest", "value"), date=lambda d: _g(d, "subsurface", "tao", "warmest", "date")),
    "d20_east": dict(
        title="20 °C isotherm depth, east", unit="m", digits=0, src="TAO/TRITON via ERDDAP",
        val=lambda d: _g(d, "subsurface", "tao", "d20_east"), date=lambda d: _g(d, "subsurface", "tao", "last_date")),
    "wind_week": dict(
        title="Westerly anomaly, 130°E–180°, 7-day", unit="m/s", digits=1, src="ERA5 via Open-Meteo",
        val=lambda d: _g(d, "wind", "era5", "mean7"), date=lambda d: _g(d, "wind", "era5", "last_date")),
    "roni": dict(
        title="RONI, relative ONI", unit="°C", digits=2, src="NOAA CPC",
        val=lambda d: _g(d, "oni", "roni", "last"), date=lambda d: _g(d, "oni", "roni", "last_season")),
    "mjo_amp": dict(
        title="MJO amplitude (OMI)", unit="", digits=1, src="NOAA PSL",
        val=lambda d: _g(d, "mjo", "last", "amp"), date=lambda d: _g(d, "mjo", "last", "d")),
    "ohc_2000": dict(
        title="Ocean heat content 0–2000 m", unit="10²² J", digits=1, src="NOAA NCEI",
        val=lambda d: _g(d, "background", "ohc_2000", "last"), date=lambda d: _g(d, "background", "ohc_2000", "date")),
    "dmi": dict(
        title="Indian Ocean Dipole", unit="°C", digits=2, src="HadISST via PSL",
        val=lambda d: _g(d, "background", "dmi", "last"), date=lambda d: _g(d, "background", "dmi", "date")),
    "kuwait_tmax30": dict(
        title="Kuwait, 30-day max-temperature anomaly", unit="°C", digits=1, src="ERA5 via Open-Meteo",
        val=lambda d: _g(d, "gulf", "kuwait", "tmax_anom_30d"), date=lambda d: _g(d, "gulf", "kuwait", "last_date")),
    "food_yoy": dict(
        title="Food prices, year on year", unit="%", digits=1, src="FAO GIEWS monthly",
        val=lambda d: _g(d, "food", "yoy_pct"), date=lambda d: _g(d, "food", "last_month")),
    "n34_30d": dict(
        title="Niño 3.4, mean of 30 days", unit="°C", digits=2, src="OISST v2.1 daily",
        val=lambda d: _g(d, "nino34", "current30"), date=lambda d: _g(d, "watch", "sst_nino34", "last_date")),
    # Показатели, которых не хватало на кирпичах вкладок «Модели», «Динамика» и «Регионы»
    # (владелец 04.09: «где на KPI стрелочки изменения от прошлого — я их не вижу»).
    "live_mean": dict(
        title="Mean over the live models", unit="°C", digits=2, src="IRI plume, our verification",
        val=lambda d: _live_at(d), date=lambda d: _g(d, "iri", "issued")),
    "n_live": dict(
        title="Models counted as live", unit="", digits=0, src="IRI plume, our verification",
        val=lambda d: _g(d, "iri", "live", "n_live"), date=lambda d: _g(d, "iri", "issued")),
    "models_above": dict(
        title="Models above reality", unit="", digits=0, src="IRI plume vs NOAA",
        val=lambda d: len(_g(d, "iri", "against_observed", "above", default=[]) or []),
        date=lambda d: _g(d, "iri", "issued")),
    "models_below_n": dict(
        title="Models below reality", unit="", digits=0, src="IRI plume vs NOAA",
        val=lambda d: len(_g(d, "iri", "against_observed", "below", default=[]) or []),
        date=lambda d: _g(d, "iri", "issued")),
    "models_lag": dict(
        title="Models lagging", unit="", digits=0, src="IRI plume, our verification",
        val=lambda d: _g(d, "iri", "class_tally", "lag"), date=lambda d: _g(d, "iri", "issued")),
    "scenario": dict(
        title="Scenario in force", unit="", digits=0, src="IRI plume vs the lived part of the season",
        val=lambda d: _g(d, "regions", "current_scenario"), date=lambda d: _g(d, "iri", "issued")),
    "fc14_sst_nino34": dict(
        title="Niño 3.4, forecast +14 days", unit="°C", digits=2, src="our analogue-day forecast",
        val=lambda d: _g(d, "watch", "sst_nino34", "forecast14", "p50"),
        date=lambda d: _g(d, "watch", "sst_nino34", "last_date")),
    "fc14_sst_world": dict(
        title="World ocean, forecast +14 days", unit="°C", digits=3, src="our analogue-day forecast",
        val=lambda d: _g(d, "watch", "sst_world", "forecast14", "p50"),
        date=lambda d: _g(d, "watch", "sst_world", "last_date")),
    "fc14_t2_world": dict(
        title="Land + ocean, forecast +14 days", unit="°C", digits=3, src="our analogue-day forecast",
        val=lambda d: _g(d, "watch", "t2_world", "forecast14", "p50"),
        date=lambda d: _g(d, "watch", "t2_world", "last_date")),
    "rec_sst_nino34": dict(
        title="Niño 3.4, record days in a row", unit="days", digits=0, src="OISST daily, our counting",
        val=lambda d: _g(d, "watch", "sst_nino34", "records", "streak"),
        date=lambda d: _g(d, "watch", "sst_nino34", "last_date")),
    "rec_sst_world": dict(
        title="World ocean, record days in a row", unit="days", digits=0, src="OISST daily, our counting",
        val=lambda d: _g(d, "watch", "sst_world", "records", "streak"),
        date=lambda d: _g(d, "watch", "sst_world", "last_date")),
    "rec_t2_world": dict(
        title="Land + ocean, record days in a row", unit="days", digits=0, src="ERA5 daily, our counting",
        val=lambda d: _g(d, "watch", "t2_world", "records", "streak"),
        date=lambda d: _g(d, "watch", "t2_world", "last_date")),
    # Воздух, топливо, слои и цены поимённо (владелец 04.09).
    "soi": dict(
        title="Southern Oscillation Index", unit="σ", digits=2, src="NOAA CPC (Tahiti−Darwin)",
        val=lambda d: _air_part(d, "soi"), date=lambda d: _air_part_date(d, "soi")),
    "olr": dict(
        title="Convection at the date line", unit="σ", digits=2, src="NOAA CPC outgoing longwave radiation",
        val=lambda d: _air_part(d, "olr"), date=lambda d: _air_part_date(d, "olr")),
    "u850_west": dict(
        title="Trade wind, western Pacific", unit="σ", digits=2, src="NOAA CPC 850 hPa zonal wind",
        val=lambda d: _air_part(d, "u850_west"), date=lambda d: _air_part_date(d, "u850_west")),
    "coupling_score": dict(
        title="Atmospheric signs in place", unit="of 3", digits=0, src="our own rule over CPC series",
        val=lambda d: _g(d, "air", "coupling", "score"),
        date=lambda d: _air_part_date(d, "soi")),
    "wwv": dict(
        title="Warm water volume", unit="10¹⁴ m³", digits=2, src="NOAA PMEL / TAO",
        val=lambda d: (_g(d, "air", "fuel", "value") or 0) / 1e14 or None,
        date=lambda d: _g(d, "air", "fuel", "date")),
    "wwv_share": dict(
        title="Fuel, share of the record", unit="%", digits=0, src="NOAA PMEL / TAO",
        val=lambda d: _g(d, "air", "fuel", "share_of_record"), date=lambda d: _g(d, "air", "fuel", "date")),
    "tlt_tropics": dict(
        title="Lower troposphere, tropics", unit="°C", digits=2, src="UAH satellite v6.1",
        val=lambda d: _layer(d, "tlt"), date=lambda d: _layer_date(d, "tlt")),
    "tls_tropics": dict(
        title="Lower stratosphere, tropics", unit="°C", digits=2, src="UAH satellite v6.1",
        val=lambda d: _layer(d, "tls"), date=lambda d: _layer_date(d, "tls")),
    "price_palm_oil": dict(
        title="Palm oil", unit="$/mt", digits=0, src="World Bank Pink Sheet",
        val=lambda d: _price(d, "palm_oil"), date=lambda d: _price_date(d, "palm_oil")),
    "price_rice": dict(
        title="Rice, Thai 5%", unit="$/mt", digits=0, src="World Bank Pink Sheet",
        val=lambda d: _price(d, "rice"), date=lambda d: _price_date(d, "rice")),
    "price_fishmeal": dict(
        title="Fishmeal", unit="$/mt", digits=0, src="World Bank Pink Sheet",
        val=lambda d: _price(d, "fishmeal"), date=lambda d: _price_date(d, "fishmeal")),
    "price_wheat": dict(
        title="Wheat, US HRW", unit="$/mt", digits=0, src="World Bank Pink Sheet",
        val=lambda d: _price(d, "wheat"), date=lambda d: _price_date(d, "wheat")),
    "peak_estimate": dict(
        title="Peak estimate by analogues", unit="°C", digits=2, src="analogues 1982/1997/2015/2023",
        val=lambda d: (_g(d, "nino34", "peak_estimate", "value")
                       if isinstance(_g(d, "nino34", "peak_estimate"), dict)
                       else _g(d, "nino34", "peak_estimate")),
        date=lambda d: _g(d, "watch", "sst_nino34", "last_date")),
}


def _round(v, digits):
    if v is None or isinstance(v, str):
        return v
    try:
        return int(round(float(v))) if digits == 0 else round(float(v), digits)
    except (TypeError, ValueError):
        return None


def _slug(title):
    return "".join(c if c.isalnum() else "_" for c in (title or "").lower()).strip("_")[:48]


# ---------------------------------------------------------------- сборка
def build(verbose=False):
    """Пройти по всем снимкам по порядку и собрать журнал изменений."""
    snaps = sorted(SNAP.glob("*.json"))
    out = {k: {"title": m["title"], "unit": m["unit"], "digits": m["digits"],
               "src": m["src"], "entries": []} for k, m in METRICS.items()}
    # ИМЯ РИСКА ПОВЕРХ ЗАГОЛОВКА. Имена появились 4 сентября (watch.py), а снимки до этого
    # знают риск только по заголовку — и часть из них ещё по-русски, до перевода панели.
    # Собираем связку «заголовок → имя» по всем снимкам, где имя уже есть, и ею опознаём
    # старые записи. Что не опознали (русские заголовки умерших правил) — отбрасываем:
    # ложная непрерывность хуже честного обрыва.
    title2id = {}
    for p2 in snaps:
        try:
            for r in (json.loads(p2.read_text(encoding="utf-8")).get("risks") or []):
                if r.get("id") and r.get("title"):
                    title2id[r["title"]] = r["id"]
        except Exception:                                    # noqa: BLE001
            continue
    risks = {}
    onset = None
    last_snap = None
    for p in snaps:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001 — битый снимок пропускаем
            continue
        last_snap = d
        onset = _g(d, "food", "overlay", "onset") or onset
        seen = d.get("stamp") or p.stem
        for k, m in METRICS.items():
            try:
                v, dt = _round(m["val"](d), m["digits"]), m["date"](d)
            except Exception:                                # noqa: BLE001 — форма снимка могла быть другой
                continue
            if v is None:
                continue
            e = out[k]["entries"]
            if e and e[-1]["v"] == v and e[-1]["d"] == dt:
                continue
            e.append({"v": v, "d": dt, "seen": seen})
        # УРОВНИ РИСКОВ — тем же порядком. Их список не задан заранее: риск появляется и
        # исчезает по данным, поэтому ключи набираются из самих снимков.
        for r in d.get("risks") or []:
            rid = r.get("id") or title2id.get(r.get("title", ""))
            if not rid:
                continue
            key = "risk:" + rid
            rec = risks.setdefault(key, {"title": r.get("title"), "unit": "level", "digits": 0,
                                         "src": "our own calculation", "entries": []})
            rec["title"] = r.get("title") or rec["title"]
            if rec["entries"] and rec["entries"][-1]["v"] == r.get("level"):
                continue
            rec["entries"].append({"v": r.get("level"), "d": d.get("generated"), "seen": seen})
    out.update(risks)

    # «От начала события» — по самим рядам, из последнего снимка, а не по журналу.
    if last_snap and onset:
        for k, m in METRICS.items():
            f = m.get("at")
            if not f:
                continue
            try:
                v = _round(f(last_snap, onset), m["digits"])
            except Exception:                                # noqa: BLE001
                v = None
            if v is not None:
                out[k]["since_event"] = {"v": v, "d": onset}

    # ИСТОРИЯ ВЕРДИКТОВ. Владелец 04.09: вердикт слева должен стать отдельной вкладкой,
    # «тоже history, чтобы там было». Храним только СМЕНУ текста: модель пишет вердикт каждым
    # прогоном, но пока числа те же, он повторяется слово в слово, и такой список читать
    # невозможно.
    verdicts = []
    for p3 in snaps:
        try:
            d3 = json.loads(p3.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            continue
        sm = d3.get("summary") or {}
        v = (sm.get("verdict") or "").strip()
        if not v or (verdicts and verdicts[-1]["v"] == v):
            continue
        verdicts.append({"v": v, "d": d3.get("generated"), "seen": d3.get("stamp"),
                         "model": sm.get("model") or ("rules" if sm.get("error") else ""),
                         "risk_index": d3.get("risk_index"), "shout": bool(d3.get("shout"))})

    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "onset": onset,
           "snapshots": len(snaps), "metrics": out, "verdicts": verdicts[-40:]}
    (ROOT / "journal.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    if verbose:
        moved = sorted(((len(v["entries"]), k) for k, v in out.items()), reverse=True)
        print(f"журнал: снимков {len(snaps)}, показателей {len(out)}, начало события {onset}")
        for n, k in moved[:12]:
            e = out[k]["entries"]
            print(f"  {k:18s} изменений {n:2d}  последнее {e[-1]['v']} за {e[-1]['d']}" if e else f"  {k}: пусто")
    return doc


if __name__ == "__main__":
    sys.exit(0 if build(verbose=True) else 1)
