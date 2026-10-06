# -*- coding: utf-8 -*-
"""Саммари по результатам дашборда через DeepSeek.

Модель получает НЕ сырые ряды, а готовую сводку фактов из latest.json — числа,
ранги, прогноз, срабатывания детектора — и пишет по ним. Ей запрещено приносить
числа со стороны: каждое число в тексте должно быть из сводки. Ответ — JSON с
фиксированными полями, чтобы страница могла его разложить, а не вставить простыню.

Ключ — только из DEEPSEEK_API_KEY. Модель — ELNINO_LLM_MODEL, по умолчанию
deepseek-v4-pro. Без ключа или при сбое сети страница получает детерминированную
сводку из тех же фактов и честную пометку, что модель не участвовала.
"""
import json
import os
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"   # данные дашборда живут в data/enso/, код в tools/enso/
# Своя запись файлов: повтор при осечке файловой системы и подмена целиком (17.09).
import sys as _sys
import pathlib as _pl
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
import safeio   # noqa: E402
OUTDIR = ROOT / "summaries"
MODEL = os.environ.get("ELNINO_LLM_MODEL", "deepseek-v4-pro")

SYSTEM = """You are the watchdog for the state of El Niño and global temperature. You are given a digest of
facts computed from today's data. Your job: say what is happening, whether the course of the event has
changed, and what to expect in the next two to three weeks.

Rules, no exceptions:
1. Use ONLY numbers from the digest. Not one number from outside, from memory, or "roughly".
2. If the digest contains alerts of level SHOUT, the verdict starts with the word ALERT and the first
   sentence names what exactly happened.
3. Forecast only for the next two weeks (say "two weeks") and only from the 14-day p10/p50/p90 forecast and the analogues in the
   digest. Do not put a number on the peak of the event if the digest says the analogues lead beyond the
   record of the series; then talk about "when the growth stops".
4. Distinguish "above all analogues" from "above anything measured": these are different claims.
3a. "Turning point" means the course of the event REVERSED: a rise became a fall, a run of records
   ended, CUSUM turned down. A new record or a SHOUT alert is NOT a turning point; while the 14-day
   change is positive and the record run is intact, answer false. The record run is the run of days above
   the historical maximum for that calendar day; it ends on a day below that day's maximum, not when the
   value falls back below the record of the whole series.
4a. Units are in the "units" section of the digest. The 14-day change is a TOTAL over the last 14 days;
   never write "per day". Quote alert titles as they are; do not stretch "highest since <date>" into
   "highest in N years" or the reverse.
5. Write in English, briefly, no exclamation marks except the word ALERT, no generalities about
   climate. Every statement must be checkable against the digest.
6. Write for an intelligent person who is not a climatologist. Every number comes with what it means in
   practice ("+2.6 °C: water in the key patch of the Pacific is two and a half degrees warmer than
   normal; the threshold of a very strong event is two"). Spell out abbreviations at first use:
   Niño 3.4 is the patch of ocean by which El Niño is judged; ONI is NOAA's official three-month
   measure; CUSUM is a gauge that accumulates excess; IRI is a digest of two dozen forecast models. No
   "percentile", "z-score", "detrended" without a plain-language translation in the same sentence.
   Short sentences. Join thoughts with words, not dashes.
6a. Never write the name of a data field in the text (discharging, share_of_record, slope14, flag): say
   what it means in plain words. A temperature anomaly is a temperature in °C, not "heat"; outside the
   Niño indices write it as "+X °C above normal" (water at 100 m, a sea box). A forecast
   issue that is already published is never revised: say "the next issue" instead. The record of the
   daily series is the record of single days: never compare a 30-day or 7-day mean with it. Say the
   14-day acceleration in °C in words ("0.11 °C more than in the previous 14 days"). A forecast range
   "stays above" a value only if its low path does; otherwise say where its middle path is. The +2.0
   "very strong" threshold belongs to the three-month ONI: never set a daily or weekly value or a forecast
   path against it. Say how early a model forecast was as "issued as the season began" or "N months
   before the season began" (months_from_issue_to_season_start), never "no lead", "lead" or "at N months
   lead"; a mean error is a miss ("1.42 °C below on average"), never "models averaged -1.42". Never draw
   "no turn is expected" from the forecast range: whether the course turned is judged on measured data
   (rule 3a), and a low path below today's value means a fall is within the range; say where the middle
   path is against today's value. A season still under way is "not scored yet"; "provisional" belongs
   only to a closed season whose official ONI is not out.
7. The digest has a section on the IRI forecast models. Judge them only on CLOSED seasons: the last
   closed season (its official ONI, or a corridor while the ONI is not out yet; then say it is
   provisional) and the model classes. Never compare a three-month forecast with a weekly value or
   with a season that has only begun. The lead error says how far below the models came at each lead
   on this year's closed seasons, and the revisions how they rewrote the peak. Say what that means: if
   models are rewriting the forecast upward and have been below reality at every lead, their winter
   numbers should be read as a lower bound.
7a. Prices: the commodity list carries a food-security weight from 1 to 5. Talk about staples (weight 4–5)
   before niche crops, and say whether a monthly jump is unusual for the season (month_unusual_z of 2 or
   more) or within the usual swing. A move since the event began is a coincidence in time, not a cause.
8. Besides the overall summary, give one short summary (two or three sentences) for each block of the
   page, strictly from that block's facts: C "where we are" (Niño 3.4 against the analogues, ONI, type),
   D "risks" (levels and the index), E "models" (IRI against reality, revisions), G "dynamics" (daily
   series, records, forecast). Keys: blocks.C, blocks.D, blocks.E, blocks.G.
9. Answer strictly as JSON with the fields:
   verdict          one or two sentences, the most important thing
   turning_point    {"happened": true/false, "why": "..."}: did the course of the event turn
   changed          what changed since the last update (from the diff section), 1–3 sentences
   outlook_2_3w     what to expect in 2–3 weeks, with numbers from the forecast, 2–4 sentences
   watch            a list of 3–5 concrete signals by which to see a turn earlier
   confidence       "high" | "medium" | "low" and why, one sentence
   caveats          1–3 caveats about the data (freshness, the analogue ceiling, etc.)
   blocks           {"C": "...", "D": "...", "E": "...", "G": "..."}"""


def facts_from(cur):
    """Сводка фактов — ровно то, на что модели можно опираться. Ключи по-английски: модель
    отвечает по-английски, и словарь фактов должен читаться на том же языке."""
    W = cur["watch"]; N = cur["nino34"]; NW = cur["noaa"]; O = cur["oni"]
    def card(k):
        w = W[k]
        return {"series": w["label"], "data_until": w["last_date"], "days_ago": w["days_stale"],
                "last_day": w["last_value"], "mean_7d": w["level7"],
                "mean_30d": w["level30"]["anom"], "rank_30d": f"{w['level30']['rank_raw']} of {w['level30']['of']}",
                "above_trend_30d": w["level30"]["det"], "z_30d": w["level30"]["z"],
                # ЕДИНИЦА В ИМЕНИ КЛЮЧА. slope14 в watch.py — это изменение ЗА 14 ДНЕЙ
                # (наклон × 14), не скорость в сутки; ключ «slope_14d» без единицы модель
                # прочитала как «°C per day» и написала так в вердикте 06.09 (проверка Fable).
                "change_over_last_14_days_c": w["slope14"]["now"],
                "change_14d_percentile_of_season": w["slope14"]["pct"],
                "acceleration_c_per_14_days": w["slope14"]["accel"],
                "records_of_last_30_days": w["records"]["last30"], "record_run_days": w["records"]["streak"],
                "records_this_year": f"{w['records']['year']} of {w['records']['year_days']}",
                "cusum": {"value": w["cusum"]["final"], "threshold": w["cusum"]["threshold"], "alarm": w["cusum"]["alarm"],
                          "first_days_ago": w["cusum"]["first_alarm_days_ago"]},
                "forecast_14d": {k2: w["forecast14"][k2] for k2 in ("from", "p10", "p50", "p90", "n", "analog_p50")},
                "year_to_date_same_days": W[k]["ytd"]}
    pe = N["peak_estimate"]
    return {
        "digest_date": cur["generated"], "stamp": cur["stamp"],
        "units": {"change_over_last_14_days_c": "°C, total change over the last 14 days (NOT per day)",
                  "acceleration_c_per_14_days": "°C, this 14-day change minus the previous 14-day change",
                  "cusum": "dimensionless gauge in units of the series' spread",
                  "anomalies": "°C against the 1991–2020 norm for the same day of year, never absolute temperature",
                  "daily_record_before_this_year": "°C, the warmest single day of all earlier years; compare only with "
                                                   "single days, never with a 30-day or 7-day mean",
                  "months_from_issue_to_season_start": "months between a forecast issue and the start of the season it was checked on; "
                                                       "0 means the issue was made as the season began: say it that way, never "
                                                       "\"no lead\" or \"lead 0\"",
                  "record_run_days": "consecutive days on which the series was above the historical maximum for THAT calendar "
                                     "day; it is a different test from being above the record of the whole series, and falling "
                                     "below the all-time record does not end it",
                  "daily_boxes_against_their_records": "our daily OISST boxes against everything each box measured in earlier "
                                                       "calendar years since 1982: day_* and mean7_* are °C anomalies against the "
                                                       "box's own 1991–2020 normal, water_* are absolute °C; compare a day with a "
                                                       "day and a 7-day mean with a 7-day mean"},
        "risk_index_0_100": cur["risk_index"],
        "detector_alerts": cur.get("alerts", []),
        "series": {"Niño 3.4": card("sst_nino34"), "world ocean": card("sst_world"), "land+ocean": card("t2_world")},
        "Nino34_vs_analogues": {
            "same_30_days": {"now": N["current30"], **{str(y): a["same30"] for y, a in N["analogs"].items()}},
            "rank_among_analogues": N["rank_same30"], "rank_among_all_years_since_1982": N["all_years_rank"],
            "analogue_peaks": {str(y): {"peak": a["peak"], "date": a["peak_date"]} for y, a in N["analogs"].items()},
            # РЕКОРД ОДНОГО ДНЯ (02.10): ключ record_of_series лежал рядом с 30-дневными средними, и модель
            # написала, что 30-дневное +2,97 «уже выше прежнего рекорда +3,02» — это рекорд суток
            "daily_record_before_this_year": pe["hist_ceiling"],
            "peak_estimate": {"additive": [pe["additive_low"], pe["additive_high"]], "note": pe["note"]}},
        # РЕКОРДЫ СУТОЧНЫХ БОКСОВ (04.10): у каждой зоны — потолок всех прошлых лет по дню, неделе и самой воде
        "daily_boxes_against_their_records": _box_records(cur),
        "NOAA_weekly": {"week": NW["date"], "anomalies": NW["latest"], "change_4_weeks": NW.get("chg4w"),
                        "change_8_weeks": NW.get("chg8w"), "type": NW["type"],
                        "Nino34_percentile_of_season": NW["n34_rank_pct"],
                        "historical_maximum": NW.get("hist_max")},
        "ONI": {"year": O["year"], "last_season": O["last_season"], "values_this_year": O["current"],
                "analogues_same_season": {str(y): O["analogs"].get(y, {}).get(O["last_season"]) for y in (1982, 1997, 2015, 2023)},
                "analogue_peaks": O["analog_event_peak"]},
        "risks": [{"level": r["level"], "risk": r["title"], "horizon": r["horizon"],
                   "plain": r.get("plain")} for r in cur["risks"]],
        # СЧЁТ ГОТОВЫЙ (28.09): модель написала «five level-5 risks» при четырёх в списке — считать ей не даём
        "risks_count_by_level": {str(k): sum(1 for r in cur["risks"] if r["level"] == k)
                                 for k in sorted({r["level"] for r in cur["risks"]}, reverse=True)},
        "what_changed": cur.get("diff", []),
        "IRI_forecast_models": _iri_facts(cur.get("iri")),
        # Атмосфера, топливо и цены поимённо: без них модель писала сводку по одному океану
        # и не могла сказать ни про сцепку, ни про запас тепла под поверхностью.
        "atmosphere_and_fuel": _air_facts(cur.get("air")),
        # Экспертиза 04.09: под поверхностью, ветер по дням, RONI, Залив, фон — без них модель
        # не могла сказать ни про тепло на глубине, ни про всплески, ни про относительный индекс.
        "subsurface_and_wind": _deep_facts(cur),
    }


def _deep_facts(cur):
    out = {}
    t = ((cur.get("subsurface") or {}).get("tao") or {})
    if t and not t.get("error"):
        out["moorings"] = {"live": t.get("n_live"), "warmest_anomaly": t.get("warmest"),
                           "thermocline_20C_depth_m": {"west": t.get("d20_west"), "east": t.get("d20_east")},
                           "data_until": t.get("last_date")}
    g = ((cur.get("subsurface") or {}).get("godas") or {})
    if g and not g.get("error"):
        hc = g.get("heat_content") or {}
        out["reanalysis_section"] = {"month": g.get("month"), "max_anomaly": g.get("max_anom"),
                                     "upper_300m_heat_index_c": (hc.get("values") or [None])[-1]}
    e = ((cur.get("wind") or {}).get("era5") or {})
    if e and not e.get("error"):
        out["westerly_wind_bursts"] = {"events_last_120_days": e.get("events"), "active_now": e.get("active"),
                                       "last_week_anomaly_ms": e.get("mean7"), "threshold_ms": e.get("threshold")}
    m = cur.get("mjo") or {}
    if m and not m.get("error"):
        out["mjo"] = {"phase": (m.get("last") or {}).get("phase"), "amplitude": (m.get("last") or {}).get("amp"),
                      "in_burst_window": m.get("burst_window")}
    r = ((cur.get("oni") or {}).get("roni") or {})
    if r and not r.get("error"):
        out["RONI"] = {"last_season": r.get("last_season"), "value": r.get("last"), "oni_minus_roni": r.get("gap_last"),
                       "analogues_same_season": r.get("analogs_same_season"), "event_peaks": r.get("analog_event_peak")}
    gf = (cur.get("gulf") or {})
    if gf and not gf.get("error"):
        sea = gf.get("sea") or {}; kw = gf.get("kuwait") or {}
        out["kuwait_and_gulf"] = {"gulf_sst": sea.get("last_sst"), "gulf_anomaly": sea.get("last_anom"),
                                  "days_over_35C_of_120": sea.get("days_over_35"),
                                  "kuwait_tmax_anomaly_30d": kw.get("tmax_anom_30d"), "hot_days_45C": kw.get("hot_days"),
                                  "rain_since_1_sep_mm": kw.get("rain_season_mm")}
    b = cur.get("background") or {}
    if b and not b.get("error"):
        out["background"] = {"ocean_heat_0_2000m": (b.get("ohc_2000") or {}).get("last"),
                             "ohc_record": (b.get("ohc_2000") or {}).get("record"),
                             "indian_ocean_dipole": (b.get("dmi") or {}).get("last"),
                             "mei_v2": (b.get("mei") or {}).get("last")}
    return out


def _air_facts(A):
    if not A or A.get("error"):
        return {"no_data": (A or {}).get("error", "air block not loaded")}
    C, F, L = A.get("coupling") or {}, A.get("fuel") or {}, A.get("layers") or {}
    out = {
        "coupling": {"verdict": C.get("verdict"), "signs_in_place": C.get("score"), "of": C.get("of"),
                     "values_in_sigma": {p["key"]: p["value"] for p in C.get("parts", [])}},
        "warm_water_volume": {"date": F.get("date"), "share_of_record_percent": F.get("share_of_record"),
                              "peak_month": F.get("peak_date"), "months_since_peak": F.get("months_since_peak"),
                              "leads_surface_by_months": (F.get("lead") or {}).get("lag"),
                              "discharging": F.get("discharging")},
        "satellite_layers": {x["key"]: {"tropics_c": x["tropics"], "lag_months": x["lag"], "r": x["r"]}
                             for x in L.get("items", [])},
    }
    cm = (A.get("commodities") or {}).get("items") or []
    # ТОВАРЫ С ВЕСОМ И СЕЗОННОСТЬЮ (владелец 06.09): модель видит, что важно (вес 1–5), что
    # необычно для месяца (month_unusual_z) и где стоит годовое изменение в истории с 1960.
    out["commodity_prices"] = [
        {"name": c["name"], "weight_1_to_5": c.get("weight"), "yoy_pct": c.get("yoy_pct"),
         "yoy_percentile_since_1960": c.get("yoy_rank"), "month_pct": c.get("mom_pct"),
         "month_unusual_z": c.get("mom_z"), "since_onset_pct": c.get("since_onset_pct")}
        for c in cm if (c.get("weight") or 1) >= 3 or abs(c.get("mom_z") or 0) >= 2 or abs(c.get("since_onset_pct") or 0) >= 15]
    return out


def _box_records(cur):
    out = {}
    for k, b in ((cur.get("oisst") or {}).get("boxes") or {}).items():
        r = b.get("record") or {}
        if k not in ("nino12", "nino3", "nino34", "nino4") or not r:
            continue
        d, w, a = r.get("day") or {}, r.get("week") or {}, r.get("abs") or {}
        out[b.get("title") or k] = {
            "date": r.get("date"), "day_now": d.get("now"), "day_record_before_this_year": d.get("prior"), "day_record_date": d.get("prior_date"),
            "days_above_that_record_this_year": d.get("days_above"), "first_day_above": d.get("first_above"),
            "mean7_now": w.get("now"), "mean7_record_before_this_year": w.get("prior"), "mean7_record_date": w.get("prior_date"),
            "water_now_c": a.get("now"), "warmest_water_before_this_year_c": a.get("prior"), "warmest_water_date": a.get("prior_date")}
    return out


def _iri_facts(iri):
    if not iri or "error" in iri:
        return {"no_data": (iri or {}).get("error", "IRI not loaded")}
    rv = iri.get("revisions") or {}
    seasons = iri["seasons"]
    comb = iri["summary"].get("combined") or []
    sc = iri.get("scored") or {}

    def _check(r):
        """Проверка выпуска на ЗАКРЫТОМ сезоне (02.10: не неделя против начавшегося сезона)."""
        if not r:
            return None
        # месяцев от выпуска до начала сезона: первый сезон выпуска с числами начинается в его же месяц (03.10)
        out = {"season": r["season"], "checked_issue": r["issue"], "months_from_issue_to_season_start": r["lead"] - 2,
               "models": r["n"], "below": r["below"], "within": r["within"], "above": r["above"],
               "mean_forecast": r["mean_forecast"]}
        if r.get("official"):
            out.update({"official_oni": r["observed"], "mean_error": r["mean_err"]})
        else:
            out.update({"provisional": True, "official_oni_not_out_yet": True,
                        "corridor_our_oisst_and_oisst_less_this_years_gap": r["ref"],
                        "mean_error_range": r["mean_err_range"]})
        return out

    cls = iri.get("classes") or {}
    by = {}
    for nm, c in cls.items():
        by.setdefault(c.get("cls") or "unchecked", []).append(nm)
    under_way = [{"season": p["season"], "months_measured": p["months_done"], "mean_so_far": p["todate"]}
                 for p in (iri.get("position") or []) if not p.get("complete")]
    lf = iri.get("last_full_season") or {}
    return {
        "issue": iri["issued"], "models": iri["n_models"],
        "combined_forecast_by_season": {s: v for s, v in zip(seasons, comb) if v is not None},
        "spread_by_season": [{k: t[k] for k in ("season", "mean", "min", "max", "sd")} for t in iri["summary"]["seasons"]],
        "last_closed_season_check": _check(sc.get("latest")),
        "latest_check_on_an_official_oni": _check(sc.get("latest_official")),
        "model_classes": {"rule": "decided by the last three issues, each checked on the nearest closed season "
                                  "(the season that begins in the issue month): broken = all three 0.5 °C or more below; lagging = the last one and one "
                                  "more 0.3 °C below; running_high = the same above; caught_up = was broken, last "
                                  "one within 0.3 °C",
                          "broken": sorted(by.get("broke", [])), "lagging": sorted(by.get("lag", [])),
                          "running_high": sorted(by.get("hot", [])), "caught_up": sorted(by.get("caught", [])),
                          "keeping_up": len(by.get("ok", [])), "unchecked": len(by.get("unchecked", []))},
        "lead_error_this_year": [{"months_from_issue_to_season_start": r["lead"] - 2, "mean_error": r["mean_err"],
                                  "share_0_5_or_more_below_pct": r["share_low"]} for r in (iri.get("lead_profile") or [])],
        "last_closed_season_our_daily_oisst": {"season": lf.get("season"), "value": lf.get("value"),
                                               "official_oni": lf.get("oni")},
        "seasons_under_way_not_scored": under_way,
        "revision_since_last_issue": {"previous_issue": rv.get("prev_issued"),
                                      "combined_peak_was": rv.get("combined_peak_prev"),
                                      "combined_peak_now": rv.get("combined_peak_cur"),
                                      "raised_peak": rv.get("n_up"), "lowered": rv.get("n_down"), "total": rv.get("n"),
                                      "largest_rewrites": [{"model": r["model"], "peak_was": r["peak_prev"],
                                                            "peak_now": r["peak_cur"]} for r in (rv.get("rows") or [])[:5]]},
        "combined_peak_history": [{"issue": h["issued"], "peak": max(v for v in h["combined"] if v is not None)}
                                  for h in iri.get("history", []) if h.get("combined")],
    }


def fallback_text(cur):
    """Сводка без модели: те же факты, сухим языком."""
    W = cur["watch"]; N = cur["nino34"]; NW = cur["noaa"]
    n34 = W["sst_nino34"]; f = n34["forecast14"]
    shout = cur.get("shout")
    al = cur.get("alerts", [])
    head = ("ALERT. " + "; ".join(a["title"] for a in al if a["level"] == "SHOUT") + ". ") if shout else ""
    return {
        "verdict": head + f"Niño 3.4 {NW['latest']['n34a']:+.1f} °C by the NOAA weekly index, rank {N['all_years_rank']} among "
                          f"all years for the same 30 days; risk index {cur['risk_index']}.",
        # разворот — это смена хода (rise became fall, run ended, CUSUM turned down), а не рекорд
        "turning_point": {"happened": any(k in (a.get("title") or "").lower() for a in al for k in ("turned", "fell", "ended", "deflating")),
                          "why": "; ".join(a["detail"] for a in al) or "no detector alerts"},
        "changed": " ".join(cur.get("diff", [])[:3]),
        "outlook_2_3w": f"By the analogue forecast Niño 3.4 in 14 days: {f['p10']:+.2f} … {f['p50']:+.2f} … {f['p90']:+.2f} °C.",
        "watch": ["NOAA weekly Niño 3.4", "14-day slope of Niño 3.4", "the ocean's run of records", "CUSUM", "Niño 1+2"],
        "confidence": "medium: the model did not take part, the digest was composed by rules",
        "caveats": [f"daily OISST lags: data until {n34['last_date']}"],
        "model": "no model",
    }


def summarize(cur):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    facts = facts_from(cur)
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    result = None
    err = ""
    if key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=key, base_url="https://api.deepseek.com", timeout=120)
            r = client.chat.completions.create(
                model=MODEL, temperature=0.2,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": "Digest of facts:\n" + json.dumps(facts, ensure_ascii=False, indent=1)}])
            txt = r.choices[0].message.content
            result = json.loads(txt)
            # СПИСКИ — СПИСКАМИ. Модель иногда отдаёт watch/caveats одной строкой (13:04 06.09,
            # проверка Fable): панель переживёт, а check.py и лента считают по элементам.
            for k in ("watch", "caveats"):
                v = result.get(k)
                if isinstance(v, str):
                    parts = [x.strip() for x in v.replace(chr(10), " ").split(". ") if x.strip()]
                    result[k] = [x if x.endswith(".") else x + "." for x in parts] if len(parts) > 1 else [v.strip()]
            result["model"] = MODEL
            result["usage"] = {"in": r.usage.prompt_tokens, "out": r.usage.completion_tokens} if r.usage else None
        except Exception as e:                       # noqa: BLE001
            err = str(e)[:300]
    if result is None:
        result = fallback_text(cur)
        result["error"] = err or "DEEPSEEK_API_KEY is not set"
    result["stamp"] = cur["stamp"]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safeio.write_text(OUTDIR / f"{stamp}.json", json.dumps({"facts": facts, "summary": result}, ensure_ascii=False, indent=1))
    return result


if __name__ == "__main__":
    cur = json.loads((ROOT / "latest.json").read_text(encoding="utf-8"))
    s = summarize(cur)
    print(json.dumps(s, ensure_ascii=False, indent=1))
