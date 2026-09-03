# -*- coding: utf-8 -*-
"""Одно обновление: забрать источники → пересчитать → сравнить с прошлым → отрисовать.

    python refresh.py            # с сетью
    python refresh.py --cached   # без сети, из последних удачных копий

Каждый прогон оставляет снимок в data/snapshots/<штамп>.json, и следующий прогон
рассказывает, что изменилось: сколько прибавил Niño 3.4, появились ли новые дни,
изменился ли индекс риска. Так «зашёл, нажал, увидел» отвечает и на вопрос
«а что нового с прошлого раза».
"""
import json
import sys
from datetime import datetime
from pathlib import Path

# Ключ DeepSeek живёт в .env репозитория, как у всего конвейера; summary.py читает окружение.
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import sources as S   # noqa: E402
import watch          # noqa: E402

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"   # данные дашборда живут в data/enso/, код в tools/enso/
SNAP = ROOT / "snapshots"


def diff_against(prev, cur):
    if not prev:
        return ["First update: nothing to compare with yet."]
    out = []
    pW, cW = prev["watch"], cur["watch"]
    for k, lab in (("sst_nino34", "Niño 3.4"), ("sst_world", "world ocean"), ("t2_world", "land+ocean")):
        p, c = pW[k], cW[k]
        if c["last_date"] != p["last_date"]:
            out.append(f"{lab}: data advanced from {p['last_date']} to {c['last_date']}; "
                       f"last day {c['last_value']:+.2f} °C (was {p['last_value']:+.2f}), "
                       f"30-day anomaly {c['level30']['anom']:+.2f} (was {p['level30']['anom']:+.2f}).")
        else:
            out.append(f"{lab}: no new days, the series still ends on {c['last_date']}.")
        if c["records"]["streak"] != p["records"]["streak"]:
            out.append(f"{lab}: run of daily records {p['records']['streak']} → {c['records']['streak']} days.")
        if c["cusum"]["alarm"] != p["cusum"]["alarm"]:
            out.append(f"{lab}: CUSUM {'RAISED its alarm' if c['cusum']['alarm'] else 'dropped its alarm'}.")
    pn, cn = prev["noaa"], cur["noaa"]
    if cn["date"] != pn["date"]:
        out.append(f"NOAA weekly: new week {cn['date']}, Niño 3.4 {cn['latest']['n34a']:+.1f} "
                   f"(was {pn['latest']['n34a']:+.1f}), Niño 1+2 {cn['latest']['n12a']:+.1f} (was {pn['latest']['n12a']:+.1f}).")
    if cur["risk_index"] != prev["risk_index"]:
        out.append(f"Risk index {prev['risk_index']} → {cur['risk_index']}.")
    pt = {r["title"] for r in prev["risks"]}; ct = {r["title"] for r in cur["risks"]}
    for t in sorted(ct - pt):
        out.append(f"New risk: {t}.")
    for t in sorted(pt - ct):
        out.append(f"Risk cleared: {t}.")
    if len(out) == 0:
        out.append("Nothing changed.")
    return out


def clean(o):
    """NaN и inf из numpy — не JSON: браузер такой файл не читает вовсе (поймано живьём:
    «Unexpected token 'N'»). Всё нечисловое → null, до записи."""
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, float) and (o != o or o in (float("inf"), float("-inf"))):
        return None
    return o


def history(snaps):
    """Линии для блока «Динамика»: по одной строке на снимок, странице хватает малого.
    Снимки — единственный источник истории нашего индекса; удаление любого из них
    ничего не ломает: строка просто исчезает."""
    rows = []
    for p in snaps:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                # noqa: BLE001 — битый снимок пропускаем
            continue
        iri = d.get("iri") if isinstance(d.get("iri"), dict) else {}
        ao = iri.get("against_observed") or {}
        comb = [v for v in (iri.get("summary") or {}).get("combined") or [] if v is not None]
        W = d.get("watch") or {}
        rows.append({
            "stamp": d.get("stamp"), "date": d.get("generated"),
            "risk_index": d.get("risk_index"), "n_risks": len(d.get("risks") or []),
            "shout": bool(d.get("shout")), "n_alerts": len(d.get("alerts") or []),
            "noaa_date": (d.get("noaa") or {}).get("date"),
            "n34_weekly": ((d.get("noaa") or {}).get("latest") or {}).get("n34a"),
            "n34_daily": (W.get("sst_nino34") or {}).get("last_value"),
            "sst_world": (W.get("sst_world") or {}).get("last_value"),
            "t2_world": (W.get("t2_world") or {}).get("last_value"),
            "iri_issued": iri.get("issued"), "combined_peak": max(comb) if comb else None,
            "n_below": len(ao.get("below") or []), "n_models": ao.get("n"),
        })
    return rows


def main(fetch=True, llm=True):
    SNAP.mkdir(parents=True, exist_ok=True)
    snaps = sorted(SNAP.glob("*.json"))
    prev = json.loads(snaps[-1].read_text(encoding="utf-8")) if snaps else None

    cur = watch.run(fetch=fetch)
    cur["stamp"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    diff = diff_against(prev, cur)
    cur["diff"] = diff

    # детектор перелома — правила; потом саммари моделью по фактам, включая срабатывания
    import alerts as A
    cur["alerts"], cur["shout"] = A.detect(cur, prev)
    import summary as SM
    if llm:
        cur["summary"] = SM.summarize(cur)
    elif prev and prev.get("summary") and not prev["summary"].get("error"):
        # Прогон без модели (правка кода, офлайн): прежнее саммари модели ценнее сводки
        # правилами — оставляем его с пометкой, из какого снимка оно взято.
        cur["summary"] = dict(prev["summary"], reused_from=prev.get("stamp"))
    else:
        # Без модели страница всё равно не пустая: сводка правилами с пометкой (ТЗ, п. 7).
        cur["summary"] = dict(SM.fallback_text(cur), error="run without the model", stamp=cur["stamp"])

    cur = clean(cur)
    (ROOT / "latest.json").write_text(json.dumps(cur, ensure_ascii=False, default=str, allow_nan=False), encoding="utf-8")
    (SNAP / (datetime.now().strftime("%Y%m%d_%H%M%S") + ".json")).write_text(
        json.dumps(cur, ensure_ascii=False, default=str), encoding="utf-8")
    (ROOT / "history.json").write_text(json.dumps(history(sorted(SNAP.glob("*.json"))), ensure_ascii=False),
                                       encoding="utf-8")
    stale = [k for k, v in cur["sources"].items() if not v["fresh"]]
    print("готово:", cur["stamp"], "| индекс риска", cur["risk_index"],
          "| рисков", len(cur["risks"]), "| несвежих источников", len(stale), stale or "")
    for d in diff:
        print("  ·", d)
    if cur["shout"]:
        print("  !!! ТРЕВОГА:", "; ".join(a["title"] for a in cur["alerts"] if a["level"] == "SHOUT"))
    elif cur["alerts"]:
        print("  внимание:", "; ".join(a["title"] for a in cur["alerts"]))
    if cur.get("summary"):
        s = cur["summary"]
        print("  саммари (%s): %s" % (s.get("model"), s.get("verdict", "")[:200]))
        if s.get("error"):
            print("  модель недоступна:", s["error"])
    return cur


if __name__ == "__main__":
    main(fetch="--cached" not in sys.argv, llm="--no-llm" not in sys.argv)
