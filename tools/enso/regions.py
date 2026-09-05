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


def scenario_support(iri, observed_weekly, record):
    """Насколько каждый сценарий поддержан моделями (владелец 03.09: «надо как-то оценить
    вероятность base / strong / record»).

    Честно это НЕ вероятность: у нас 26 прогнозов, а не ансамбль розыгрышей одной модели.
    Считаем долю моделей, чей пик не ниже порога сценария, и говорим об этом словами.
    Пороги: base — медиана пиков моделей, strong — 90-й процентиль, record — рекорд
    недельного ряда NOAA. Оговорка обязательна: реальность уже выше части плюма, значит
    доли занижены — это нижняя граница, а не оценка сверху."""
    # СЛОМАННЫЕ МОДЕЛИ НЕ ЗАДАЮТ СЦЕНАРИИ. Владелец 04.09 сказал это про среднее на графиках,
    # но болезнь та же и здесь, а последствия хуже: пороги сценариев — это медиана и 90-й
    # процентиль пиков, и модели, уже занизившие прожитые сезоны, тянут их вниз. Отсюда и
    # выходила лестница, где порог «record» оказывался ниже медианы. Считаем по живым:
    # сломанные исключены, остальные равноправны (веса тут ни к чему — это порядковые
    # статистики, а не среднее). Если живых почему-то меньше пяти, берём всех и говорим об
    # этом полем models_used: молчаливая подмена выборки хуже широкого порога.
    models = (iri or {}).get("models") or {}
    classes = (iri or {}).get("classes") or {}

    def _peaks(only_live):
        out = []
        for nm, m in models.items():
            if m.get("section") not in ("dyn", "stat") or not m.get("values"):
                continue
            if only_live and (classes.get(nm) or {}).get("cls") == "broke":
                continue
            vv = [v for v in m["values"] if v is not None]
            if vv:
                out.append(max(vv))
        return out

    peaks, used = _peaks(True), "live"
    if len(peaks) < 5:
        peaks, used = _peaks(False), "all"
    if not peaks:
        return None
    peaks.sort()
    n = len(peaks)
    p50 = peaks[n // 2]
    p90 = peaks[min(n - 1, int(round(0.9 * (n - 1))))]
    th = {"base": p50, "strong": p90,
          "record": record if record is not None else peaks[-1]}
    words = {
        "base": "the event peaks near the middle of the plume, counting only the models that kept up",
        "strong": "the event peaks at the top of the spread of the models that kept up",
        "record": "the peak goes above the record of the weekly NOAA series",
    }
    out = {}
    for k, t in th.items():
        at = sum(1 for p in peaks if p >= t - 1e-9)
        out[k] = {"threshold": round(float(t), 2), "models_at_or_above": at, "of": n,
                  "share": round(100 * at / n), "what": words[k]}
    below_now = len([p for p in peaks if observed_weekly is not None and p < observed_weekly])
    out["_note"] = (f"Share of the {n} IRI models whose peak reaches the threshold"
                    + (" — counting only the models that kept up with reality; the ones that broke are "
                       "left out, because a forecast already below the lived part of the season cannot "
                       "set the scale for the ones ahead" if used == "live" else
                       " — counting every model, because too few passed verification this month")
                    + f". Not a probability: these are {n} different models, not draws from one. "
                    f"Reality is already above {below_now} of them, so every share here is a lower bound.")
    out["_median_peak"] = round(float(p50), 2)
    out["_p90_peak"] = round(float(p90), 2)
    out["_models_used"] = used
    out["_n_models"] = len(peaks)
    return out


def build(iri, noaa_latest_n34, record_weekly=None):
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
    support = scenario_support(iri, noaa_latest_n34, record_weekly)
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
        "season_notes": ref.get("season_notes") or {}, "scenario_support": support,
        "factors": factors, "peak_p50": peak_p50, "peak_max": peak_max, "observed_weekly": noaa_latest_n34,
        "items": items,
        "method": "level = round(0.6 × impact + 0.4 × vulnerability + scenario), clipped to 1–5; impact: robust 4, likely 3, weak 1.5, none 0; scenario: base +0 (the event as in the combined forecast), strong +0.5 (top of the model spread), record +1 (reality above every model); one point lower everywhere if the combined peak is below 1.5 °C.",
        "sources": ref["sources"],
    }
