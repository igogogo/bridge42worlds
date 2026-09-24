# -*- coding: utf-8 -*-
"""ШЕСТЬ СОБЫТИЙ ПО ДНЮ ГОДА — составные картины сборщика радианса (поставка 23.09.2026).

Ответ сборщика на просьбу панели «радианс по AIRS 2003–2022 по боксам Niño по дню года»:
`incoming/radiance-events/events_doy.csv` — по боксу (Niño 3.4, тёплый бассейн), узлу (день A /
ночь D), метрике (frac_lt235, bt900_mean, bt690_mean, bt750_mean, lst_mean) и дню года: фон
(медиана и квартили НЕсобытийных лет) и значения шести событий 2004, 2006, 2009, 2015, 2018, 2023.
Два предупреждения сборщика едут с данными: `common6` (общих дней у всех шести только 84 из 143 —
сравнивать события между собой только по ним) и часы Aqua у 2023 года (+20 минут к остальным).
Раньше 2003 года у AIRS ничего нет.
"""
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio           # noqa: E402

DATA = ROOT / "data" / "enso"
SRC = DATA / "incoming" / "radiance-events"
CL = Path(r"C:\CL\radiance\data")
OUT = DATA / "radiance-events.json"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _f(x):
    try:
        return None if x in (None, "", "nan") else float(x)
    except ValueError:
        return None


def build():
    t0 = time.time()
    p = next((c for c in (CL / "events_doy.csv", SRC / "events_doy.csv") if c.exists()), None)
    if p is None:
        raise SystemExit("нет events_doy.csv")
    pp = next((c for c in (CL / "events_doy.json", SRC / "events_doy.json") if c.exists()), None)
    passport = json.loads(pp.read_text(encoding="utf-8")) if pp else {}
    events = [str(y) for y in (passport.get("events") or [2004, 2006, 2009, 2015, 2018, 2023])]
    series = {}
    for r in csv.DictReader(open(p, encoding="utf-8")):
        key = f"{r['box']}|{r['node']}|{r['metric']}"
        s = series.setdefault(key, {"box": r["box"], "node": r["node"], "metric": r["metric"], "doy": [], "common6": [],
                                    "n_ref": [], "ref_median": [], "ref_p25": [], "ref_p75": [], "events": {y: [] for y in events}})
        s["doy"].append(int(r["doy"])); s["common6"].append(r.get("common6") == "1"); s["n_ref"].append(int(r.get("n_ref_years") or 0))
        s["ref_median"].append(_f(r.get("ref_median"))); s["ref_p25"].append(_f(r.get("ref_p25"))); s["ref_p75"].append(_f(r.get("ref_p75")))
        for y in events:
            s["events"][y].append(_f(r.get("y" + y)))
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "delivered": passport.get("built") or "2026-09-23",
           "src": "AIRS on Aqua, the radiance collector’s own daily series 2003–2026 (airs_daily.csv), composed by day of year",
           "events": events, "metrics": passport.get("metrics") or [], "boxes": passport.get("boxes") or [], "nodes": passport.get("nodes") or [],
           "coverage": passport.get("coverage") or {}, "series": series,
           "metric_names": {"frac_lt235": "share of deep convection (BT900 < 235 K)", "bt900_mean": "window brightness temperature, K",
                            "bt690_mean": "upper-troposphere channel 690 cm⁻¹, K", "bt750_mean": "lower-troposphere channel 750 cm⁻¹, K",
                            "lst_mean": "local solar time of the overpass, h"},
           "warnings": {"common6": "the six event years were collected unevenly — 2004 has 87 days, the others 138–140; only 84 of 143 days of the year are common to all six (column common6). Events are compared with each other only on those days; one event against the background may use every day, because the background is built for the same day of the year",
                        "clock": "the 2023 event was observed by a clock that had drifted +20 minutes against the other five (Aqua’s clock stood still within 2003–2022 and drifted after); for the night node that is not a detail, because night cooling goes on. lst_mean is delivered so the correction can be made, not discovered later",
                        "no_smoothing": "no smoothing or interpolation across days of the year: a gap in the sample is shown as a gap",
                        "events_list": "the list of six years came from the panel and is taken as given; the collector does not claim they are the events"},
           "note": "Six El Niño years since 2003 seen by one infrared instrument on the same calendar: each event against the background of the non-event years of the same day of the year. Before 2003 AIRS did not exist, so no earlier event can be shown this way."}
    safeio.write_text(OUT, json.dumps(doc, ensure_ascii=False, allow_nan=False))
    print(f"radiance-events.json: {len(series)} series, events {', '.join(events)}, {OUT.stat().st_size // 1024} KB, {time.time() - t0:.1f} s")
    return doc


def main():
    build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
