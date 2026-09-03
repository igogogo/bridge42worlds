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
OUTDIR = ROOT / "summaries"
MODEL = os.environ.get("ELNINO_LLM_MODEL", "deepseek-v4-pro")

SYSTEM = """You are the watchdog for the state of El Niño and global temperature. You are given a digest of
facts computed from today's data. Your job: say what is happening, whether the course of the event has
changed, and what to expect in the next two to three weeks.

Rules, no exceptions:
1. Use ONLY numbers from the digest. Not one number from outside, from memory, or "roughly".
2. If the digest contains alerts of level SHOUT, the verdict starts with the word ALERT and the first
   sentence names what exactly happened.
3. Forecast only for a 2–3 week horizon and only from the p10/p50/p90 forecast and the analogues in the
   digest. Do not put a number on the peak of the event if the digest says the analogues lead beyond the
   record of the series; then talk about "when the growth stops".
4. Distinguish "above all analogues" from "above anything measured": these are different claims.
5. Write in English, briefly, no exclamation marks except the word ALERT, no generalities about
   climate. Every statement must be checkable against the digest.
6. Write for an intelligent person who is not a climatologist. Every number comes with what it means in
   practice ("+2.6 °C: water in the key patch of the Pacific is two and a half degrees warmer than
   normal; the threshold of a very strong event is two"). Spell out abbreviations at first use:
   Niño 3.4 is the patch of ocean by which El Niño is judged; ONI is NOAA's official three-month
   measure; CUSUM is a gauge that accumulates excess; IRI is a digest of two dozen forecast models. No
   "percentile", "z-score", "detrended" without a plain-language translation in the same sentence.
   Short sentences. Join thoughts with words, not dashes.
7. The digest has a section on the IRI forecast models: how many are already below reality and how
   they revised the peak from issue to issue. Say what that means: if models are rewriting the forecast
   upward and some have already fallen behind, their winter numbers should be read as a lower bound.
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
                "slope_14d": w["slope14"]["now"], "slope_percentile_of_season": w["slope14"]["pct"],
                "acceleration": w["slope14"]["accel"],
                "records_of_last_30_days": w["records"]["last30"], "record_run_days": w["records"]["streak"],
                "records_this_year": f"{w['records']['year']} of {w['records']['year_days']}",
                "cusum": {"value": w["cusum"]["final"], "threshold": w["cusum"]["threshold"], "alarm": w["cusum"]["alarm"],
                          "first_days_ago": w["cusum"]["first_alarm_days_ago"]},
                "forecast_14d": {k2: w["forecast14"][k2] for k2 in ("from", "p10", "p50", "p90", "n", "analog_p50")},
                "year_to_date_same_days": W[k]["ytd"]}
    pe = N["peak_estimate"]
    return {
        "digest_date": cur["generated"], "stamp": cur["stamp"],
        "risk_index_0_100": cur["risk_index"],
        "detector_alerts": cur.get("alerts", []),
        "series": {"Niño 3.4": card("sst_nino34"), "world ocean": card("sst_world"), "land+ocean": card("t2_world")},
        "Nino34_vs_analogues": {
            "same_30_days": {"now": N["current30"], **{str(y): a["same30"] for y, a in N["analogs"].items()}},
            "rank_among_analogues": N["rank_same30"], "rank_among_all_years_since_1982": N["all_years_rank"],
            "analogue_peaks": {str(y): {"peak": a["peak"], "date": a["peak_date"]} for y, a in N["analogs"].items()},
            "record_of_series": pe["hist_ceiling"],
            "peak_estimate": {"additive": [pe["additive_low"], pe["additive_high"]], "note": pe["note"]}},
        "NOAA_weekly": {"week": NW["date"], "anomalies": NW["latest"], "change_4_weeks": NW.get("chg4w"),
                        "change_8_weeks": NW.get("chg8w"), "type": NW["type"],
                        "Nino34_percentile_of_season": NW["n34_rank_pct"],
                        "historical_maximum": NW.get("hist_max")},
        "ONI": {"year": O["year"], "last_season": O["last_season"], "values_this_year": O["current"],
                "analogues_same_season": {str(y): O["analogs"].get(y, {}).get(O["last_season"]) for y in (1982, 1997, 2015, 2023)},
                "analogue_peaks": O["analog_event_peak"]},
        "risks": [{"level": r["level"], "risk": r["title"], "horizon": r["horizon"],
                   "plain": r.get("plain")} for r in cur["risks"]],
        "what_changed": cur.get("diff", []),
        "IRI_forecast_models": _iri_facts(cur.get("iri")),
    }


def _iri_facts(iri):
    if not iri or "error" in iri:
        return {"no_data": (iri or {}).get("error", "IRI not loaded")}
    ao = iri.get("against_observed") or {}
    rv = iri.get("revisions") or {}
    seasons = iri["seasons"]
    comb = iri["summary"].get("combined") or []
    return {
        "issue": iri["issued"], "models": iri["n_models"],
        "combined_forecast_by_season": {s: v for s, v in zip(seasons, comb) if v is not None},
        "spread_by_season": [{k: t[k] for k in ("season", "mean", "min", "max", "sd")} for t in iri["summary"]["seasons"]],
        "reality_vs_models": {"season": ao.get("season"), "reality_weekly": ao.get("observed_weekly"),
                              "models_below_reality": len(ao.get("below", [])), "of": ao.get("n"),
                              "which_below": ao.get("below"), "model_mean": ao.get("mean"),
                              "model_max": ao.get("max"),
                              "reality_above_all": ao.get("reality_above_all")},
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
        "turning_point": {"happened": bool(shout), "why": "; ".join(a["detail"] for a in al) or "no detector alerts"},
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
            result["model"] = MODEL
            result["usage"] = {"in": r.usage.prompt_tokens, "out": r.usage.completion_tokens} if r.usage else None
        except Exception as e:                       # noqa: BLE001
            err = str(e)[:300]
    if result is None:
        result = fallback_text(cur)
        result["error"] = err or "DEEPSEEK_API_KEY is not set"
    result["stamp"] = cur["stamp"]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    (OUTDIR / f"{stamp}.json").write_text(json.dumps({"facts": facts, "summary": result}, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    return result


if __name__ == "__main__":
    cur = json.loads((ROOT / "latest.json").read_text(encoding="utf-8"))
    s = summarize(cur)
    print(json.dumps(s, ensure_ascii=False, indent=1))
