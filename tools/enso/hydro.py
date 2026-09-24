# -*- coding: utf-8 -*-
"""Вода на суше и в воздухе — сводка рек и пара для разбора, журнала и правил рисков.

Владелец 18.09: «добавь в Overview, риски, KPI состояния, чтобы всё появилось по теме». Реки
(rivers.json, GloFAS) и пар (vapour.json, ERA5) собирают свои скрипты в лёгком прогоне; здесь
из них берётся то, что нужно разбору: доска рек и 30-суточный пар над тропиками и Niño 3.4.
Сводка кладётся в latest.json как блок hydro — оттуда её читают журнал (полоса KPI, история)
и правила ниже. Правила осторожные: это модельный расход и редкая сетка, уровень не выше 3.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "enso"


def _load(name):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except Exception:                                            # noqa: BLE001
        return None


RISK_DAYS = 120          # окно ряда на карточке риска (как у суточных рядов океана)


def _river_metric(RV, keys):
    """РЯД ДЛЯ КАРТОЧКИ РИСКА РЕК (владелец 24.09): сток той реки из рекордно низких, у которой
    30-дневное среднее ниже всего против нормы, за 120 суток в тыс. м³/с; аналоги 2015/2023 по тем
    же дням года — из того же rivers.json (там они уже лежат по датам своего года)."""
    items = {p["key"]: p for p in RV.get("items") or []}
    cand = [items[k] for k in keys if k in items and items[k].get("series")]
    if not cand:
        return None
    it = min(cand, key=lambda p: ((p.get("mean30") or {}).get("pct") if (p.get("mean30") or {}).get("pct") is not None else 999))
    ser = it["series"][-RISK_DAYS:]
    dates = [d for d, v in ser]
    vals = [None if v is None else round(v / 1000.0, 1) for d, v in ser]
    an = {}
    for y, rows in (it.get("analogs") or {}).items():
        by = {d[5:]: v for d, v in rows}
        an[str(y)] = [None if by.get(d[5:]) is None else round(by[d[5:]] / 1000.0, 1) for d in dates]
    return {"name": it["name"] + ", discharge", "unit": "10³ m³/s", "step": "day", "dates": dates, "values": vals, "analogs": an,
            "note": "GloFAS modelled discharge, 120 days; the past events on the same days of their year"}


def _vapour_metric(VP, key="tropics"):
    """РЯД ДЛЯ КАРТОЧКИ РИСКА ПАРА (владелец 24.09): суточная влага столба над поясом за 120 суток,
    аналоги 1997/2015/2023 по тем же дням года из vapour.json."""
    it = next((x for x in VP.get("items") or [] if x.get("key") == key), None)
    if not it or not it.get("this_year"):
        return None
    y = str((it.get("last") or {}).get("date") or "")[:4]
    ty = it["this_year"][-RISK_DAYS:]
    dates = [f"{y}-{md}" for md, v in ty]
    vals = [None if v is None else round(v, 2) for md, v in ty]
    an = {}
    for ay, rows in (it.get("analogs") or {}).items():
        by = {md: v for md, v in rows}
        an[str(ay)] = [None if by.get(d[5:]) is None else round(by[d[5:]], 2) for d in dates]
    return {"name": it.get("name") or "Water vapour over the tropics", "unit": "kg/m²", "step": "day", "dates": dates, "values": vals, "analogs": an,
            "note": "ERA5 column water vapour, daily, 120 days; the past events on the same days of their year"}


def block():
    RV, VP = _load("rivers.json"), _load("vapour.json")
    out = {}
    if RV and RV.get("board"):
        b = RV["board"]
        names = {p["key"]: p["name"] for p in RV.get("items") or []}
        out["rivers"] = {"as_of": b.get("as_of"), "n": b.get("n"), "below_p25": b.get("below_p25"), "above_p75": b.get("above_p75"),
                         "record_low": b.get("record_low") or [], "record_low_names": [names.get(k, k) for k in (b.get("record_low") or [])],
                         "record_high": b.get("record_high") or [], "built": RV.get("built"),
                         "metric": _river_metric(RV, b.get("record_low") or [])}
    if VP and VP.get("items"):
        regs = {}
        for it in VP["items"]:
            m = it.get("mean30") or {}
            regs[it["key"]] = {"date": (it.get("last") or {}).get("date"), "mean30": m.get("value"), "anom30": m.get("anom"),
                               "rank": m.get("rank"), "of": m.get("of"), "clim_complete": it.get("clim_complete")}
        out["vapour"] = {"regions": regs, "built": VP.get("built"), "c3s": VP.get("c3s"), "metric": _vapour_metric(VP)}
    return out or None


def risks(H):
    """Формат watch.risks: (заголовок, уровень, горизонт, что видно, что значит, за чем следить,
    ряд, вид, имя правила)."""
    out = []
    R = (H or {}).get("rivers") or {}
    if R.get("n") and R.get("record_low"):
        n_rec = len(R["record_low"])
        if n_rec >= 3:
            out.append((
                f"{n_rec} of {R['n']} El Niño rivers are at a record low for the date", 3, "now",
                f"GloFAS modelled discharge to {R.get('as_of')}: the 30-day mean is the lowest of 2000–2026 for these days on "
                f"{', '.join(R.get('record_low_names') or R['record_low'])}; {R.get('below_p25')} of {R['n']} rivers sit below their lower quartile.",
                "These are the rivers whose basins dry when El Niño takes the rain away — the Amazon's north and east, the Orinoco, "
                "the Ethiopian highlands. A model on observed weather, not gauges, and it knows no dams; but a record on several "
                "basins at once is the pattern, not the noise.",
                "the same board day by day: whether the count of record lows grows, and whether Paraná and the southern United "
                "States turn wet, as they should in El Niño",
                R.get("metric"), "impact", "rivers_record_low",
                min(1.0, (n_rec - 3) / 5.0)))
    V = ((H or {}).get("vapour") or {}).get("regions") or {}
    T = V.get("tropics") or {}
    if T.get("rank") and T.get("of", 0) >= 10:
        if T["rank"] == 1:
            out.append((
                "The air over the tropics holds more water than in any year of the record", 3, "now",
                f"ERA5 column water vapour over 20°S–20°N, 30 days to {T.get('date')}: {T.get('mean30')} kg/m², "
                f"{T.get('anom30'):+.1f} against 1991–2020, the highest of {T.get('of')} years on these days"
                + ("" if T.get("clim_complete") else " (the climatology is still being back-filled, so the rank is against the years already fetched)") + ".",
                "Warm oceans evaporate and warmer air holds about 7 % more water per degree; the extra vapour is fuel for "
                "heavier rain and stronger storms, and C3S names the tropical oceans and El Niño as the source of the global record.",
                "the tropics belt and the Niño 3.4 box on the Water vapour scene; the global monthly value from C3S",
                ((H or {}).get("vapour") or {}).get("metric"), "climate", "vapour_record", 1.0))
        elif T["rank"] <= 3:
            out.append((
                f"Water vapour over the tropics is the {T['rank']}{'nd' if T['rank'] == 2 else 'rd'} highest of the record", 2, "now",
                f"ERA5 column water vapour over 20°S–20°N, 30 days to {T.get('date')}: {T.get('mean30')} kg/m², rank {T['rank']} of {T.get('of')} years.",
                "More water in the tropical air than in almost any year: heavier rain where it falls, and more energy for storms.",
                "whether the belt moves to rank 1 as the event grows", None, "climate", "vapour_high", 0.5))
    return out
