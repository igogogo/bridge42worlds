# -*- coding: utf-8 -*-
"""Блок F: риск региона = воздействие × уязвимость × сила события (ТЗ, 6.5).

Справочник — data/enso/regions-ref.json (телесвязи по сезонам с силой связи, уязвимость по
еде, источники). Здесь только арифметика и выбор фразы «что делать»; ничего из головы.

Три сценария по силе события:
  base    — сводный прогноз моделей (p50 плюма) на ближайший пик;
  strong  — верх разброса моделей (≈p90);
  record  — реальность выше всех моделей, сегодняшний случай: недельный уровень уже выше
            максимума плюма.
Надбавка сценария: base +0 · strong +0.5 · record +1.0; если сводный пик ниже «сильного»
(1.5 °C), всё на балл ниже. Какой сценарий идёт сейчас — решают данные (against_observed).

Уровень региона (1–5) на ближайшие три сезона:
  impact  = max по сезонам силы связи с воздействием: robust 4 · likely 3 · weak 1.5 · none 0
  level   = round_half_up(0.6·impact + 0.4·vulnerability + scenario), обрезка 1..5
Записано на странице словами; читатель видит и формулу, и вход.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"
STRENGTH = {"robust": 4.0, "likely": 3.0, "weak": 1.5}
ACTION_BY_IMPACT = {"dry": "drought", "heat": "heat", "wet": "flood", "flood": "flood", "none": "none"}


def _scenario_bonus(peak_p50, peak_max, observed_weekly):
    """Надбавка к уровню по сценарию. Первая калибровка (множитель 1.44 при p50 3.28) выводила
    почти все регионы в 5 — шкала теряла смысл. Надбавка фиксированная и читаемая:
    base +0 (событие как в сводном прогнозе), strong +0.5, record +1.0; если сводный пик
    ниже «сильного» (1.5 °C), всё на балл ниже."""
    weak = -1.0 if (peak_p50 is not None and peak_p50 < 1.5) else 0.0
    return {"base": weak, "strong": weak + 0.5, "record": weak + 1.0}


def _round_half_up(x):
    return int(x + 0.5)


def build(iri, noaa_latest_n34):
    ref = json.loads((ROOT / "regions-ref.json").read_text(encoding="utf-8"))
    summ = (iri or {}).get("summary") or {}
    comb = [v for v in (summ.get("combined") or []) if v is not None]
    seasons_tbl = summ.get("seasons") or []
    peak_p50 = max(comb) if comb else None
    # «Сильный» сценарий — верх разброса моделей как среднее + одно отклонение по сезону
    # пика, а не максимум одной модели-выброса (тот давал +4.99 и ничего не значил).
    peak_max = max((t["mean"] + t["sd"] for t in seasons_tbl), default=None) if seasons_tbl else None
    peak_max = round(peak_max, 2) if peak_max is not None else None
    factors = _scenario_bonus(peak_p50, peak_max, noaa_latest_n34)
    # какой сценарий идёт сейчас: реальность выше всех моделей → record
    ao = (iri or {}).get("against_observed") or {}
    current = "record" if ao.get("reality_above_all") else ("strong" if ao.get("reality_above_mean_sd") else "base")

    items = []
    for r in ref["regions"]:
        impact = 0.0; worst = "none"; worst_season = None
        for s in ref["seasons"]:
            row = r["seasons"].get(s) or {}
            st = STRENGTH.get(row.get("strength"), 0.0) if row.get("impact", "none") != "none" else 0.0
            if st > impact:
                impact, worst, worst_season = st, row.get("impact"), s
        vuln = r["vulnerability"]["level"]
        levels = {}
        for k, bonus in factors.items():
            lv = _round_half_up(0.6 * impact + 0.4 * vuln + bonus)
            levels[k] = int(max(1, min(5, lv)))
        acts = []
        key = ACTION_BY_IMPACT.get(worst, "none")
        acts.append(ref["actions"][key])
        if vuln >= 4:
            acts.append(ref["actions"]["import"])
        if r["id"] == "andes_peru":
            acts.append(ref["actions"]["fisheries"])
        items.append({
            "id": r["id"], "name": r["name"], "countries": r["countries"],
            "seasons": r["seasons"], "impact_score": impact, "worst": worst, "worst_season": worst_season,
            "vulnerability": r["vulnerability"], "levels": levels, "actions": acts,
            "sources": [ref["sources"][k] for k in r["sources"] if k in ref["sources"]],
        })
    items.sort(key=lambda x: (-x["levels"][current], -x["vulnerability"]["level"]))
    return {
        "as_of": ref["as_of"], "seasons": ref["seasons"], "current_scenario": current,
        "factors": factors, "peak_p50": peak_p50, "peak_max": peak_max, "observed_weekly": noaa_latest_n34,
        "items": items,
        "method": "level = round(0.6 × impact + 0.4 × vulnerability + scenario), clipped to 1–5; impact: robust 4, likely 3, weak 1.5, none 0; scenario: base +0 (the event as in the combined forecast), strong +0.5 (top of the model spread), record +1 (reality above every model); one point lower everywhere if the combined peak is below 1.5 °C.",
        "sources": ref["sources"],
    }
