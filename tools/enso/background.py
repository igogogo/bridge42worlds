# -*- coding: utf-8 -*-
"""Фон системы и календарь выпусков.

ФОН. Экспертиза 04.09 (пп. 2 и 3.7): тезис «система показывает состояния, на которых
статистика не училась» должен опираться на два ряда, а не на слова. Теплосодержание океана
NCEI (0–700 и 0–2000 м, квартально с 1955) — живой ряд. Энергетический дисбаланс Земли по
CERES — живого ряда без регистрации нет; даём число из литературы с источником и датой и
подписываем как литературу, а не как замер.

ИНДЕКСЫ. MEI v2 (пять полей, независимая сверка «сцепки 3 из 3»), DMI (Индийский океан:
для Залива второй по важности индекс, для еды — муссон Индии и осень Австралии), RONI
(относительный ONI, по которому NOAA с февраля 2026 классифицирует события). У всех — то же
сравнение с прошлыми сильными событиями по календарю, что у остальных рядов панели.

КАЛЕНДАРЬ. Экспертиза, п. 3.9: панель должна знать, когда ждать следующий выпуск каждого
источника. Даты считаются от сегодняшнего дня по правилам источников; где правило
«около такого-то числа», так и подписано.
"""
import calendar
from datetime import date, timedelta

import numpy as np

ANALOG_YEARS = (1982, 1997, 2015, 2023)
SEASONS = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]

EEI = {"value": "1.4–1.5", "unit": "W/m²", "year": 2025,
       "claim": ("Earth's energy imbalance measured by CERES has more than doubled in two decades and was "
                 "at a record in 2025, about twice what the CMIP6 models expected."),
       "src": "Mauritsen et al., AGU Advances, 2025; NASA CERES EBAF", "url": "https://ceres.larc.nasa.gov/data/",
       "kind": "literature",
       "note": "Quoted from the paper, not a live series: CERES global means are distributed as NetCDF behind an ordering tool."}


def _same_month_levels(d, key):
    if not d or not key or len(key) < 7:
        return {}
    mm = key[5:7]
    return {str(y): round(float(d[f"{y}-{mm}"]), 2) for y in ANALOG_YEARS if f"{y}-{mm}" in d and d[f"{y}-{mm}"] is not None}


def _monthly_block(series, title, unit, n=60):
    """Месячный ряд {ГГГГ-ММ: v} → блок панели с хвостом, последним значением и планками аналогов."""
    if not series:
        return None
    keys = sorted(k for k, v in series.items() if v is not None and v == v)
    if not keys:
        return None
    last = keys[-1]
    tail = keys[-n:]
    return {"title": title, "unit": unit, "months": tail, "values": [round(float(series[k]), 2) for k in tail],
            "last": round(float(series[last]), 2), "date": last,
            "levels": _same_month_levels(series, last),
            "analog_year_after": {str(y): {f"{y + 1}-{m:02d}": round(float(series[f"{y + 1}-{m:02d}"]), 2)
                                           for m in range(1, 13) if f"{y + 1}-{m:02d}" in series and series[f"{y + 1}-{m:02d}"] is not None}
                                  for y in ANALOG_YEARS}}


def psl_to_monthly(rows):
    """{год: [12]} → {ГГГГ-ММ: v} (NaN выброшены)."""
    out = {}
    for y, vals in (rows or {}).items():
        for i, v in enumerate(vals, 1):
            if v is not None and v == v:
                out[f"{y}-{i:02d}"] = float(v)
    return out


def ohc_block(rows, title):
    """Теплосодержание NCEI: ряд, последнее значение, рост за десять лет, рекорд ли."""
    if not rows:
        return None
    ys = [r[0] for r in rows]; vs = [r[1] for r in rows]
    last_y, last_v = ys[-1], vs[-1]
    ten = [v for y, v in zip(ys, vs) if abs(y - (last_y - 10)) < 0.2]
    rec = last_v >= max(vs)
    iy = int(last_y); q = int(round((last_y - iy - 0.125) / 0.25)) + 1
    frac = last_y - iy
    levels = {}
    for ay in ANALOG_YEARS:
        hit = [v for y, v in zip(ys, vs) if abs(y - (ay + frac)) < 0.13]
        if hit:
            levels[str(ay)] = round(hit[0], 2)
    return {"title": title, "unit": "10²² J", "years": [round(y, 3) for y in ys[-160:]],
            "values": [round(v, 2) for v in vs[-160:]], "last": round(last_v, 2),
            "date": f"{iy} Q{max(1, min(4, q))}", "record": bool(rec),
            "rise_10y": round(last_v - ten[0], 2) if ten else None, "levels": levels,
            "src": "NOAA NCEI, 3-month means, anomaly from the 1955–2006 mean"}


# ------------------------------------------------------------------ календарь
def _nth_weekday(y, m, weekday, n):
    d = date(y, m, 1)
    off = (weekday - d.weekday()) % 7
    return d + timedelta(days=off + 7 * (n - 1))


def _next_monthly(today, day, label):
    d = date(today.year, today.month, min(day, calendar.monthrange(today.year, today.month)[1]))
    if d < today:
        y, m = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
        d = date(y, m, min(day, calendar.monthrange(y, m)[1]))
    return d, label


def _next_nth_weekday(today, weekday, n, label):
    d = _nth_weekday(today.year, today.month, weekday, n)
    if d < today:
        y, m = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
        d = _nth_weekday(y, m, weekday, n)
    return d, label


def _next_weekday(today, weekday, label):
    off = (weekday - today.weekday()) % 7
    return today + timedelta(days=off), label


def release_calendar(today=None):
    today = today or date.today()
    items = [
        ("OISST daily, NRT", "NOAA via ERDDAP", today + timedelta(days=1), "every day, one day behind"),
        ("NOAA weekly Niño indices", "NOAA CPC", *_next_weekday(today, 0, "Mondays, for the week to the previous Wednesday")),
        ("CPC ENSO diagnostic discussion", "NOAA CPC", *_next_nth_weekday(today, 3, 2, "second Thursday of the month")),
        ("IRI model plume", "IRI / CPC", *_next_monthly(today, 19, "around the 19th")),
        ("NMME", "NOAA CPC", *_next_monthly(today, 8, "around the 8th")),
        ("Warm water volume", "NOAA PMEL", *_next_monthly(today, 10, "around the 10th, for the previous month")),
        ("GODAS reanalysis", "NCEP via PSL", *_next_monthly(today, 15, "mid-month, for the month before last")),
        ("UAH satellite layers", "UAH", *_next_monthly(today, 3, "first days of the month")),
        ("FAO Food Price Index", "FAO", *_next_nth_weekday(today, 4, 1, "first Friday of the month")),
        ("World Bank Pink Sheet", "World Bank", *_next_monthly(today, 3, "around the 3rd")),
        ("AMIS Market Monitor", "AMIS", *_next_nth_weekday(today, 3, 1, "first Thursday of the month")),
        ("USDA WASDE", "USDA", *_next_monthly(today, 11, "around the 10th–12th")),
        ("ABARES crop report", "ABARES", *_next_quarterly(today)),
        ("Ocean heat content", "NOAA NCEI", *_next_quarterly(today, months=(1, 4, 7, 10), day=20, label="quarterly, with a lag of about a month")),
    ]
    out = []
    for name, src, d, rule in items:
        out.append({"name": name, "src": src, "next": d.isoformat(), "in_days": (d - today).days, "rule": rule})
    out.sort(key=lambda x: x["in_days"])
    return {"today": today.isoformat(), "items": out,
            "note": "Computed from each source's stated schedule; 'around' means the day moves by a few days."}


def _next_quarterly(today, months=(3, 6, 9, 12), day=None, label="quarterly: first Tuesday of March, June, September, December"):
    cands = []
    for y in (today.year, today.year + 1):
        for m in months:
            d = _nth_weekday(y, m, 1, 1) if day is None else date(y, m, day)
            if d >= today:
                cands.append(d)
    return min(cands), label


# ------------------------------------------------------------------ сборка
def build(parsed, oni, today=None):
    today = today or date.today()
    out = {"eei": EEI, "calendar": release_calendar(today)}
    out["ohc_700"] = ohc_block(parsed.get("ohc_700"), "Ocean heat content, 0–700 m")
    out["ohc_2000"] = ohc_block(parsed.get("ohc_2000"), "Ocean heat content, 0–2000 m")
    out["mei"] = _monthly_block(psl_to_monthly(parsed.get("mei")), "Multivariate ENSO Index v2", "σ")
    out["dmi"] = _monthly_block(psl_to_monthly(parsed.get("dmi")), "Indian Ocean Dipole (DMI)", "°C")
    if out["mei"]:
        out["mei"]["note"] = ("Five fields in one index: pressure, wind, temperature of sea and air, cloudiness. "
                              "Bimonthly, so its last value is a two-month mean. Independent of our three-sign coupling score.")
    if out["dmi"]:
        d = out["dmi"]
        d["phase"] = "positive" if d["last"] >= 0.4 else ("negative" if d["last"] <= -0.4 else "neutral")
        d["note"] = ("West minus east of the tropical Indian Ocean. A positive dipole with an El Niño usually means a "
                     "drier Indian monsoon and a dry southern Australian autumn — rice and wheat, the two grains "
                     "Kuwait imports — and a wetter East Africa.")
    # RONI рядом с ONI: последний сезон, аналоги на том же сезоне, пики событий
    R = (oni or {}).get("roni") or {}
    out["roni"] = R or None
    out["note"] = ("Background means the state the whole system is in while this event runs: how much heat the "
                   "ocean holds below the surface and how far the planet is out of energy balance. Neither is "
                   "an El Niño measure, and both are why the statistical models trained on the past keep running low.")
    return out


def risks(B):
    out = []
    for key in ("ohc_2000", "ohc_700"):
        o = (B or {}).get(key)
        if o and o.get("record"):
            out.append((
                f"The ocean holds more heat than ever measured ({o['title'].split(',')[1].strip()})", 3, "years",
                f"{o['last']} × 10²² J in {o['date']}, a record of the series since 1955; up {o.get('rise_10y')} in ten years.",
                "This is the reservoir the event draws on and returns to. A record reservoir means the statistical "
                "forecasts, trained on a cooler ocean, are reading a different system than the one they learned.",
                "the next quarterly NCEI update; whether the 0–2000 m series keeps rising through the event",
                {"name": o["title"], "unit": o["unit"], "step": "quarter", "dates": [str(y) for y in o["years"]],
                 "values": o["values"], "levels": o.get("levels") or {}},
                "climate", f"{key}_record"))
            break
    d = (B or {}).get("dmi")
    if d and d.get("last") is not None and d["last"] >= 0.4:
        out.append((
            "A positive Indian Ocean Dipole is running alongside the El Niño", 3, "this season",
            f"DMI {d['last']:+.2f} °C in {d['date']}; the same month of the analogues: "
            + ", ".join(f"{y} {v:+.2f}" for y, v in (d.get('levels') or {}).items()) + ".",
            "The two together are the classic recipe for a weak Indian monsoon and a dry autumn in southern "
            "Australia — the origins of Kuwait's rice and wheat — and for a wet East Africa. In 1997 both ran together.",
            "the DMI through November; the Indian monsoon withdrawal and the Australian sowing reports",
            {"name": d["title"], "unit": d["unit"], "step": "month", "dates": d["months"], "values": d["values"],
             "levels": d.get("levels") or {}},
            "climate", "iod_positive"))
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(release_calendar(), ensure_ascii=False, indent=1)[:1500])
