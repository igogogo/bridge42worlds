# -*- coding: utf-8 -*-
"""Шестьдесят пять названных мест сборщика радианс — компактный слой для панели.

Выдача v15 (18.09.2026): places_daily.csv, 65 мест × два узла × 142 суток, микроволновый
ATMS на NOAA-20, сетка 2,5°. Величина — вертикальный контраст vc_10_13 (тропопауза минус
средняя стратосфера, K, приведён к надиру); рядом уровень ch16 (окно 88,2 ГГц), число
наблюдений, местное время съёмки. Файл 4 МБ панели не нужен целиком: здесь из него берётся
то, что можно прочитать глазами за минуту.

ЧТО СЧИТАЕМ. У 2026 года есть сплошной отрезок 17.08–17.09 (31 сутки, «опорный отрезок»
сборщика); у прошлых лет — 13 плановых дат в году, из них в тот же сезон попадают две
(день года 238 и 266, конец августа и конец сентября). Среднее по отрезку 2026 против
среднего тех же сезонных дат 2018–2025 — это и есть «где место стоит против своих прошлых
лет»: разность в K и в сигмах разброса прошлых лет. Это НЕ порог обнаружения (сборщик свои
пороги снял 16.09 как опровергнутые) и не тревога: тревог у детектора сборщика ноль.

ПРАВИЛА ЧТЕНИЯ, взятые из записки сборщика: строки complete = 0 не используются (пропуск
гранул — кусок орбиты, смещение одностороннее); lst_mean печатается рядом с величиной,
потому что неровное расписание съёмки подделывает смену режима; поправка и сырой контраст
лежат рядом, чтобы поправку можно было проверить.

Русские имена групп и механизмов переведены здесь: панель английская.
"""
import csv
import json
import statistics
import sys
import time
from datetime import datetime, date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio   # noqa: E402

CL = Path(r"C:\CL\radiance\data")
INCOMING = ROOT / "data" / "enso" / "incoming" / "radiance-v15"
OUT = ROOT / "data" / "enso" / "radiance-places.json"

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GROUP_EN = {"край конвекции": "edge of convection", "бистабильность": "bistability",
            "телесвязь": "teleconnection", "контроль": "control", "решётка": "lattice"}
GROUP_WHY_EN = {
    "edge of convection": "where the boundary of deep convection moves as the warm pool spreads east; a shift here is the event itself, seen in the tropopause",
    "bistability": "the SPCZ axis and the double ITCZ: places that can flip between two states, so a change is a regime change, not a trend",
    "teleconnection": "the far ends of the event: coasts and monsoons that answer the Pacific with a lag",
    "control": "deserts, subtropical highs and the Antarctic plateau: places that should not move; if they do, the instrument or the schedule moved, not the climate",
    "lattice": "forty points on an even grid for coverage; no mechanism is named, so they get no verdict of their own",
}
WHY_EN = {
    "edge_150e": "the western warm-pool boundary moving", "edge_170e": "the warm-pool boundary moving",
    "edge_175w": "the boundary moving toward the centre", "edge_140w": "convection breaking out east",
    "edge_110w": "the eastern limit of convection",
    "spcz_nw": "SPCZ axis, north-western end", "spcz_mid": "SPCZ axis, middle", "spcz_se": "SPCZ axis, south-eastern end",
    "spcz_far": "SPCZ axis, far end", "ditcz_n_110w": "northern branch of the double ITCZ", "ditcz_s_110w": "southern branch of the double ITCZ",
    "ditcz_n_140w": "northern branch, further west", "ditcz_s_140w": "southern branch, further west",
    "tele_peru": "the coast of Peru", "tele_nebrazil": "north-east Brazil", "tele_eafrica": "East Africa",
    "tele_india": "India, the monsoon", "tele_eaustralia": "eastern Australia", "tele_california": "California",
    "ctl_sahara": "Sahara, a calibration site", "ctl_arabia": "the Arabian desert", "ctl_atacama": "Atacama",
    "ctl_spac_high": "clear sky, the South Pacific high", "ctl_natl_high": "clear sky, the North Atlantic high",
    "ctl_antarctic": "the Antarctic plateau",
}
NAME_EN = {
    "edge_150e": "Warm pool edge, 150°E", "edge_170e": "Warm pool edge, 170°E", "edge_175w": "Date line, 175°W",
    "edge_140w": "Central Pacific, 140°W", "edge_110w": "Eastern Pacific, 110°W",
    "spcz_nw": "SPCZ north-west", "spcz_mid": "SPCZ middle", "spcz_se": "SPCZ south-east", "spcz_far": "SPCZ far end",
    "ditcz_n_110w": "ITCZ north, 110°W", "ditcz_s_110w": "ITCZ south, 110°W", "ditcz_n_140w": "ITCZ north, 140°W", "ditcz_s_140w": "ITCZ south, 140°W",
    "tele_peru": "Peru coast", "tele_nebrazil": "North-east Brazil", "tele_eafrica": "East Africa", "tele_india": "India",
    "tele_eaustralia": "Eastern Australia", "tele_california": "California",
    "ctl_sahara": "Sahara", "ctl_arabia": "Arabia", "ctl_atacama": "Atacama", "ctl_spac_high": "South Pacific high",
    "ctl_natl_high": "North Atlantic high", "ctl_antarctic": "Antarctic plateau",
}
SEASON_DOY = (224, 272)          # окно сезона для прошлых лет: плановые даты 238 и 266 попадают в него


def _f(x):
    try:
        v = float(x)
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def _mean(v):
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else None


def _r(x, nd=2):
    return None if x is None else round(x, nd)


def load_rows():
    src = CL / "places_daily.csv" if (CL / "places_daily.csv").exists() else INCOMING / "places_daily.csv"
    rows = [r for r in csv.DictReader(open(src, encoding="utf-8")) if r.get("complete") == "1"]
    return rows, src


def load_places():
    p = CL / "places.json" if (CL / "places.json").exists() else INCOMING / "places.json"
    P = json.loads(p.read_text(encoding="utf-8"))
    out = []
    for bank in ("hypothesis", "lattice"):
        for pl in (P.get(bank) or {}).get("places") or []:
            out.append({"id": pl["id"], "lat": pl["lat"], "lon": pl["lon"], "bank": bank,
                        "group": GROUP_EN.get(pl.get("group"), pl.get("group")),
                        "why": WHY_EN.get(pl["id"], "coverage, no mechanism named"),
                        "name": NAME_EN.get(pl["id"], pl["id"])})
    return out, P.get("frozen"), P.get("changelog") or []


def provenance():
    """Версия обработки по суткам и прибору (provenance_daily.csv сборщика): сколько суток, с какой
    по какую, какие версии и сколько суток на каждой, версия последних суток, сколько суток
    собраны из двух версий сразу. Для вкладки Ops: смена версии — то, что маскируется под климат."""
    p = CL / "provenance_daily.csv" if (CL / "provenance_daily.csv").exists() else INCOMING / "provenance_daily.csv"
    if not p.exists():
        return None
    by = {}
    for r in csv.DictReader(open(p, encoding="utf-8")):
        r["versions"] = (r.get("versions") or "").replace("неизвестна", "unknown")   # панель английская
        by.setdefault(r["src"], []).append(r)
    out = []
    for s, rs in sorted(by.items()):
        rs.sort(key=lambda r: r["date"])
        cnt = {}
        for r in rs:
            for v in (r.get("versions") or "").split(";"):
                v = v.split(":")[0].strip()
                if v:
                    cnt[v] = cnt.get(v, 0) + 1
        top = sorted(cnt.items(), key=lambda kv: -kv[1])
        last = rs[-1]
        out.append({"src": s, "days": len(rs), "first": rs[0]["date"], "last": last["date"],
                    "last_version": ";".join(v.split(":")[0] for v in (last.get("versions") or "").split(";")),
                    "versions": [{"v": v, "days": n} for v, n in top[:6]], "n_versions": len(cnt),
                    "multi_version_days": sum(1 for r in rs if int(float(r.get("n_versions") or 1)) > 1),
                    "unknown_days": sum(1 for r in rs if "unknown" in (r.get("versions") or ""))})
    return {"file": str(p.name), "items": out,
            "note": "Processing version of each instrument's granules, day by day, reconstructed from granule names by the collector. A version change is the first suspect when a series steps."}


def main():
    t0 = time.time()
    rows, src = load_rows()
    places, frozen, changelog = load_places()
    RA = json.loads((ROOT / "data" / "enso" / "radiance.json").read_text(encoding="utf-8"))
    PW = ((RA.get("sources") or {}).get("places_watch") or {})
    blk = ((PW.get("matching") or {}).get("continuous_block") or {})
    b0, b1 = blk.get("first") or "2026-08-17", blk.get("last") or "2026-09-17"
    cur_year = b1[:4]
    by = {}
    for r in rows:
        by.setdefault((r["place_id"], r["node"]), []).append(r)
    out_places = []
    for pl in places:
        nodes = {}
        for node in ("A", "D"):
            rs = sorted(by.get((pl["id"], node)) or [], key=lambda r: r["date"])
            if not rs:
                continue
            block = [r for r in rs if b0 <= r["date"] <= b1]
            prior = []
            for r in rs:
                d = date.fromisoformat(r["date"])
                if d.year < int(cur_year) and SEASON_DOY[0] <= d.timetuple().tm_yday <= SEASON_DOY[1]:
                    prior.append(r)
            bv = [_f(r["vc_10_13"]) for r in block]
            pv = [_f(r["vc_10_13"]) for r in prior]
            bm, pm = _mean(bv), _mean(pv)
            psd = statistics.pstdev([x for x in pv if x is not None]) if len([x for x in pv if x is not None]) >= 3 else None
            bsd = statistics.pstdev([x for x in bv if x is not None]) if len([x for x in bv if x is not None]) >= 3 else None
            last = rs[-1]
            nodes[node] = {
                "block_mean": _r(bm), "block_sd": _r(bsd), "block_n": len(block),
                "prior_mean": _r(pm), "prior_sd": _r(psd), "prior_n": len(prior),
                "prior_years": sorted({r["date"][:4] for r in prior}),
                "delta": _r(bm - pm) if bm is not None and pm is not None else None,
                "z": _r((bm - pm) / psd, 1) if bm is not None and pm is not None and psd else None,
                "level_block": _r(_mean([_f(r["ch16"]) for r in block])),
                "level_prior": _r(_mean([_f(r["ch16"]) for r in prior])),
                "lst_block_h": _r(_mean([_f(r["lst_mean"]) for r in block])),
                "lst_prior_h": _r(_mean([_f(r["lst_mean"]) for r in prior])),
                "n_obs_block": _r(_mean([_f(r["n_obs"]) for r in block]), 1),
                "raw_minus_adj_block": _r(_mean([(_f(r["vc_10_13_raw"]) or 0) - (_f(r["vc_10_13"]) or 0) for r in block])),
                "last": {"date": last["date"], "vc": _f(last["vc_10_13"]), "vc_raw": _f(last["vc_10_13_raw"]),
                         "level": _f(last["ch16"]), "n_obs": int(float(last["n_obs"] or 0)), "lst_h": _f(last["lst_mean"])},
                "series": [[r["date"], _f(r["vc_10_13"])] for r in block],
                "prior": [[r["date"], _f(r["vc_10_13"])] for r in prior],
            }
        out_places.append(dict(pl, nodes=nodes))
    hyp = [p for p in out_places if p["bank"] == "hypothesis"]
    lat = [p for p in out_places if p["bank"] == "lattice"]

    def zs(ps, node):
        return [abs(p["nodes"][node]["z"]) for p in ps if p["nodes"].get(node) and p["nodes"][node].get("z") is not None]
    summary = {node: {"hypothesis_median_abs_z": _r(statistics.median(zs(hyp, node)), 1) if zs(hyp, node) else None,
                      "hypothesis_n_above_2": sum(1 for z in zs(hyp, node) if z >= 2),
                      "lattice_median_abs_z": _r(statistics.median(zs(lat, node)), 1) if zs(lat, node) else None,
                      "lattice_n_above_2": sum(1 for z in zs(lat, node) if z >= 2)} for node in ("A", "D")}
    ls = PW.get("level_share") or {}
    doc = {
        "built": datetime.now().strftime("%Y-%m-%d %H:%M"), "source_file": str(src), "frozen": frozen,
        "changelog": [{"date": c.get("date"), "what": "list created and frozen: 25 places by failure mechanism, 40 lattice points for coverage"} for c in changelog][:3],
        "instrument": "ATMS on NOAA-20, 2.5° grid, microwave", "quantity": "vertical contrast ch10 − ch13 (tropopause minus middle stratosphere), K, corrected to nadir",
        "block": {"first": b0, "last": b1, "days": blk.get("days")}, "season_doy": list(SEASON_DOY), "cur_year": cur_year,
        "collector": {"date": PW.get("date"), "alerts_now": len(RA.get("alerts") or []),
                      "thresholds": "none: the collector's detection thresholds were refuted by its own check on 2026-09-16 and withdrawn",
                      "level_share_verdict": {n: (ls.get("vc_10_13_" + n) or {}).get("verdict") for n in ("A", "D")},
                      "level_share_r2_median": {n: (ls.get("vc_10_13_" + n) or {}).get("r2_level_median") for n in ("A", "D")},
                      "complete_gate": "days with fewer than 236 of 241 granules are dropped: a missing granule is a piece of orbit and biases one way (0.41 K on a day with 179 granules)"},
        "groups": GROUP_WHY_EN, "summary": summary, "places": out_places, "provenance": provenance(),
        "note": ("Sixty-five named places on the microwave sounder, each with the mechanism by which it can fail: the edge of convection, "
                 "a bistable axis, a far teleconnection, or a control that must not move. The number is the block mean of this year's "
                 "continuous run against the same season of 2018–2025, in K and in sigmas of those years. Not a threshold and not an alarm: "
                 "the collector raises none today."),
    }
    safeio.write_text(OUT, json.dumps(doc, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
    top = sorted([p for p in hyp if p["nodes"].get("A", {}).get("z") is not None], key=lambda p: -abs(p["nodes"]["A"]["z"]))[:5]
    for p in top:
        n = p["nodes"]["A"]
        print(f"  {p['name']:26s} A block {n['block_mean']:+.2f} prior {n['prior_mean']:+.2f} ±{n['prior_sd']}  Δ {n['delta']:+.2f} K  z {n['z']:+.1f}")
    print(f"radiance-places.json: {len(out_places)} places, block {b0}…{b1}, {OUT.stat().st_size // 1024} KB, {time.time() - t0:.0f} s")
    try:
        import ops as OPSLOG
        OPSLOG.record_run("radiance_places", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ok", note=f"{len(out_places)} places, block to {b1}")
    except Exception:                                            # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
