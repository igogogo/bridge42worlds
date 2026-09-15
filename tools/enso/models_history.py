# -*- coding: utf-8 -*-
"""Прогнозы сквозь годы: чего стоили выпуски плюма с 2002-го и как читать сегодняшний.

Владелец 15.09: «хочу увидеть, как сдвигаются прогнозы и отличие — что было раньше, скажем
10, 20 лет назад, и что сейчас; как двигаются прогнозы по нашим особенным годам Эль-Ниньо;
и что происходит с прогнозами прямо сейчас на горизонте этого события».

Откуда. IRI держит фигуру каждого выпуска с 2002 года тем же адресом, что и текущий
(figure4_plot/<год>/<месяц>), и наш разбор SVG (iri_plume.py) читает старые выпуски без правок —
проверено на 2004 (22 модели), 2009 (26), 2015 (30), 2023 (30). Это единственная открытая
история прогнозов двух десятков центров, лежащая одним файлом на выпуск.

ТРИ ЛОВУШКИ, ИЗ-ЗА КОТОРЫХ ЭТОТ ФАЙЛ УСТРОЕН СЛОЖНЕЕ, ЧЕМ «СРЕДНЯЯ ОШИБКА ПО ГОДАМ»
(разбор вида 15.09; каждую поймал независимый судья, и каждая убивает вывод целиком):

  1. ТИХИЙ ГОД ЛЁГОК САМ ПО СЕБЕ. Сравнивать сырую ошибку 2004-го и 2015-го нельзя: в год без
     события прогноз «около нуля» верен даром. Поэтому рядом с ошибкой считаются ДВА опорных
     прогноза на ТЕХ ЖЕ целях: климатология (всегда 0,0) и затухающая инерция (последний
     наблюдённый ONI × 0,8 за сезон). Стало лучше — это когда разрыв между центрами и опорой
     вырос, а не когда число ошибки упало. Плюс `activity` — средний |ONI| тех самых целей.
  2. ВЫБОРКА ПО ИСХОДУ НЕ ОТВЕЧАЕТ НА ВОПРОС О ПРОГНОЗЕ. «Августовский выпуск занижал пик в
     шести событиях из семи» — это отобрано по тому, что событие СЛУЧИЛОСЬ. Читателю же нужно
     другое: среди всех августов, когда центры ОБЕЩАЛИ тёплую зиму, куда легло то, что пришло.
     Поэтому `same_phase.forecast` (выборка по прогнозу, включая обещания, из которых ничего не
     вышло) — основная, а `same_phase.outcome` (по исходу) лежит рядом и подписана своей
     оговоркой.
  3. ПИК СРЕДНЕГО ПЛОЩЕ ПИКА РЯДА. COMBINED — среднее двух десятков моделей, и его максимум по
     построению ниже максимума отдельной реализации. Поэтому основная мера — попадание в ОДИН
     И ТОТ ЖЕ сезон (NDJ), а «пик против пика» лежит вторым и с оговоркой.

Плюс мелочи, без которых числа врут: пик прогноза берётся по ФИКСИРОВАННОМУ окну события
(центры сезонов с июля года начала по апрель следующего), а не «по тем девяти сезонам, что
выпуск успел напечатать»; пропущенные выпуски перечислены поимённо; всё, что не удалось
разобрать, лежит в `meta.parse_failures`, а не исчезает.

    python tools/enso/models_history.py --fetch     докачать выпуски (2002 → сегодня) и посчитать
    python tools/enso/models_history.py             посчитать по тому, что уже скачано
"""
import argparse
import json
import sys
import time
import urllib.request
from datetime import date, datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import iri_plume as IP                                          # noqa: E402
import sources as S                                             # noqa: E402

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"
RAW = ROOT / "raw" / "iri"
OUT = ROOT / "models-history.json"
URL = "https://ensoforecast.iri.columbia.edu/figure4_plot/{y}/{m}"
UA = "Mozilla/5.0 bridge42worlds enso"
FIRST = (2002, 1)
LEADS = (1, 3, 6, 9)
DAMP = 0.8                       # затухание инерции за сезон
WARM_CALL = 1.0                  # «тёплый зов»: прогноз на ближайший NDJ не ниже этого
SEASONS = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
DECADES = (("2002_2010", 2002, 2010), ("2011_2020", 2011, 2020), ("2021_2026", 2021, 2030))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


# ---------------------------------------------------------------- вспомогательное
def season_of_centre(cm):
    """Сезон по месяцу его центра: центр января — это DJF."""
    return SEASONS[(cm - 1) % 12]


def centre(y, m, i):
    """Центр сезона с индексом i в плюме адреса (y, m): у i = 2 это месяц m + 1."""
    cm = m + (i - 1)
    yy = y + (cm - 1) // 12
    return yy, (cm - 1) % 12 + 1


def issues():
    t = date.today()
    out, (y, m) = [], FIRST
    while (y, m) < (t.year, t.month):
        out.append((y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


# ---------------------------------------------------------------- сеть и разбор
def fetch_all(pause=1.5, verbose=True):
    RAW.mkdir(parents=True, exist_ok=True)
    got, miss = 0, []
    for y, m in issues():
        p = RAW / f"plume_{y}_{m:02d}.svg"
        if p.exists() and p.stat().st_size > 20000:
            continue
        try:
            req = urllib.request.Request(URL.format(y=y, m=m), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                b = r.read()
            if len(b) < 20000:
                miss.append(f"{y}-{m:02d}"); continue
            p.write_bytes(b); got += 1
            if verbose and got % 25 == 0:
                print(f"  скачано {got}, последний {y}-{m:02d}", flush=True)
        except Exception as e:                                   # noqa: BLE001
            miss.append(f"{y}-{m:02d}: {str(e)[:40]}")
        time.sleep(pause)
    if verbose:
        print(f"выпусков докачано {got}, не отдано {len(miss)}")
    return got, miss


def parsed(y, m):
    # Свежие выпуски лежат в data/enso/iri (их кладёт ежедневный сбор), старые — в raw/iri.
    # Читаем обе папки: иначе история обрывается там, где кончилась перекачка архива.
    p = RAW / f"plume_{y}_{m:02d}.svg"
    if not p.exists():
        p = ROOT / "iri" / f"plume_{y}_{m:02d}.svg"
    if not p.exists():
        return None
    cache = RAW / f"parsed_{y}_{m:02d}.json"
    RAW.mkdir(parents=True, exist_ok=True)
    if cache.exists() and cache.stat().st_mtime >= p.stat().st_mtime:
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except Exception:                                        # noqa: BLE001
            pass
    try:
        pl = IP.parse(p)
    except Exception as e:                                       # noqa: BLE001
        return {"error": str(e)[:120]}
    keep = {"addr": [y, m], "issued": pl.get("issued"), "seasons": pl.get("seasons") or [],
            "models": {k: {"section": v["section"], "values": v["values"]}
                       for k, v in (pl.get("models") or {}).items() if v.get("values")}}
    cache.write_text(json.dumps(keep, ensure_ascii=False), encoding="utf-8")
    return keep


# ---------------------------------------------------------------- события по ONI
def events_from_oni(oni):
    """Событие: ONI ≥ +0.5 пять перекрывающихся сезонов подряд. Год начала — год первого сезона."""
    seq = sorted(oni.items(), key=lambda kv: (kv[0][1], SEASONS.index(kv[0][0])))
    runs, cur = [], []
    for (s, y), v in seq:
        if v >= 0.5:
            cur.append((s, y, v))
        else:
            if len(cur) >= 5:
                runs.append(cur)
            cur = []
    if len(cur) >= 5:
        runs.append(cur)
    # СОБЫТИЕ ИМЕНУЕТСЯ ГОДОМ ПИКА, А НЕ ПЕРВОГО СЕЗОНА. Правило «пять сезонов подряд» склеивает
    # соседние потепления: 2014-й и 2015-й идут одной полосой, и событие, которое весь мир знает
    # как «2015», получало ярлык 2014. Читателю нужен тот год, в который событие достигло пика,
    # и окно прогноза считается от него же.
    out = {}
    for r in runs:
        pk = max(r, key=lambda t: t[2])
        year = pk[1] if SEASONS.index(pk[0]) >= 6 else pk[1] - 1      # пик в DJF…JJA принадлежит прошлой зиме
        out[year] = {"peak": pk[2], "season": pk[0], "year": pk[1], "seasons": len(r),
                     "first_season": f"{r[0][0]} {r[0][1]}"}
    return out


# ---------------------------------------------------------------- счёт
def build(verbose=True):
    t0 = time.time()
    oni = {(s, y): v for s, y, v in S.read_oni(S.LAST / "oni.txt")}
    oni_years = sorted({y for _, y in oni})
    ev_obs = events_from_oni(oni)
    rows, missing, failures = [], [], []
    for y, m in issues():
        pl = parsed(y, m)
        if pl is None:
            missing.append(f"{y}-{m:02d}"); continue
        if pl.get("error"):
            failures.append(f"{y}-{m:02d}: {pl['error']}"); continue
        comb = (pl["models"].get("COMBINED AVG") or {}).get("values")
        seas = pl.get("seasons") or []
        if not comb or not seas:
            failures.append(f"{y}-{m:02d}: нет COMBINED"); continue
        # последний наблюдённый сезон — индекс 0 (центр m − 1)
        oy, om = centre(y, m, 0)
        last_obs = oni.get((season_of_centre(om), oy))
        fc = {}
        for i, lab in enumerate(seas):
            if i < 2 or "OBS" in lab or comb[i] is None:
                continue
            cy, cm = centre(y, m, i)
            lead = i - 1
            obs = oni.get((season_of_centre(cm), cy))
            fc[lead] = {"season": season_of_centre(cm), "year": cy, "fc": round(comb[i], 3),
                        "obs": obs,
                        "err": (None if obs is None else round(comb[i] - obs, 3)),
                        "clim_err": (None if obs is None else round(0.0 - obs, 3)),
                        "pers_err": (None if obs is None or last_obs is None
                                     else round(last_obs * (DAMP ** lead) - obs, 3))}
        mods = {k: v["values"] for k, v in pl["models"].items() if v["section"] in ("dyn", "stat")}
        rows.append({"y": y, "m": m, "issued": pl.get("issued"), "seasons": seas,
                     "n_models": len(mods), "comb": comb, "fc": fc, "models": mods,
                     "last_obs": last_obs})
    if verbose:
        print(f"выпусков разобрано {len(rows)}, нет файла {len(missing)}, не разобрано {len(failures)}")

    # ── по годам выпуска: ошибка, смещение, опоры, «насколько год был событийным»
    years = {}
    for r in rows:
        d = years.setdefault(str(r["y"]), {"n_issues": 0, "models": [], "_": {l: [] for l in LEADS}})
        d["n_issues"] += 1; d["models"].append(r["n_models"])
        for l in LEADS:
            f = r["fc"].get(l)
            if f and f["err"] is not None:
                d["_"][l].append(f)
    for k, d in years.items():
        d["n_models"] = int(round(float(np.mean(d["models"])))) if d["models"] else None
        for name in ("mae", "bias", "n_scored", "activity", "mae_clim", "mae_persist"):
            d[name] = {}
        for l in LEADS:
            v = d["_"][l]
            d["n_scored"][str(l)] = len(v)
            if not v:
                for name in ("mae", "bias", "activity", "mae_clim", "mae_persist"):
                    d[name][str(l)] = None
                continue
            d["mae"][str(l)] = round(float(np.mean([abs(x["err"]) for x in v])), 3)
            d["bias"][str(l)] = round(float(np.mean([x["err"] for x in v])), 3)
            d["activity"][str(l)] = round(float(np.mean([abs(x["obs"]) for x in v])), 3)
            d["mae_clim"][str(l)] = round(float(np.mean([abs(x["clim_err"]) for x in v])), 3)
            pe = [abs(x["pers_err"]) for x in v if x["pers_err"] is not None]
            d["mae_persist"][str(l)] = round(float(np.mean(pe)), 3) if pe else None
        d.pop("_"); d.pop("models")

    # ── по десятилетиям, по тем же целям
    decades = {}
    for name, lo, hi in DECADES:
        acc = {l: {"e": [], "c": [], "p": [], "a": []} for l in LEADS}
        for r in rows:
            if not (lo <= r["y"] <= hi):
                continue
            for l in LEADS:
                f = r["fc"].get(l)
                if f and f["err"] is not None:
                    acc[l]["e"].append(abs(f["err"])); acc[l]["c"].append(abs(f["clim_err"]))
                    acc[l]["a"].append(abs(f["obs"]))
                    if f["pers_err"] is not None:
                        acc[l]["p"].append(abs(f["pers_err"]))
        decades[name] = {"years": [lo, min(hi, max(r["y"] for r in rows))]}
        for l in LEADS:
            a = acc[l]
            decades[name][str(l)] = {
                "mae": round(float(np.mean(a["e"])), 3) if a["e"] else None,
                "mae_clim": round(float(np.mean(a["c"])), 3) if a["c"] else None,
                "mae_persist": round(float(np.mean(a["p"])), 3) if a["p"] else None,
                "activity": round(float(np.mean(a["a"])), 3) if a["a"] else None,
                "n": len(a["e"])}

    # ── месяц выпуска × заблаговременность × десятилетие
    cells = {}
    for r in rows:
        mo = SEASONS and datetime(2000, (r["m"] % 12) + 1, 1).strftime("%b")   # месяц ВЫПУСКА = адрес + 1
        dec = next((n for n, lo, hi in DECADES if lo <= r["y"] <= hi), None)
        if not dec:
            continue
        for l in LEADS:
            f = r["fc"].get(l)
            if not f or f["err"] is None:
                continue
            c = cells.setdefault(mo, {}).setdefault(str(l), {}).setdefault(dec, {"e": [], "c": []})
            c["e"].append(abs(f["err"])); c["c"].append(abs(f["clim_err"]))
    for mo, by_l in cells.items():
        for l, by_d in by_l.items():
            for dec, c in by_d.items():
                by_d[dec] = {"mae": round(float(np.mean(c["e"])), 3), "n": len(c["e"]),
                             "mae_clim": round(float(np.mean(c["c"])), 3)}

    # ── события: путь прогноза пика по фиксированному окну
    def window_peak(r, onset):
        """Максимум COMBINED по сезонам с центром июль(onset) … апрель(onset+1)."""
        best, lab, full = None, None, True
        want = [(onset, mm) for mm in range(7, 13)] + [(onset + 1, mm) for mm in range(1, 5)]
        seen = set()
        for i, s in enumerate(r["seasons"]):
            if i < 2 or "OBS" in s or r["comb"][i] is None:
                continue
            cy, cm = centre(r["y"], r["m"], i)
            if (cy, cm) in want:
                seen.add((cy, cm))
                if best is None or r["comb"][i] > best:
                    best, lab = r["comb"][i], f"{season_of_centre(cm)} {cy}"
        return best, lab, len(seen) == len(want)

    def ndj_of(r, yy):
        for i, s in enumerate(r["seasons"]):
            if i < 2 or "OBS" in s or r["comb"][i] is None:
                continue
            cy, cm = centre(r["y"], r["m"], i)
            if cy == yy and cm == 12:
                return round(r["comb"][i], 3)
        return None

    onsets = sorted(ev_obs) + ([date.today().year] if date.today().year not in ev_obs else [])
    onsets = [o for o in onsets if o >= FIRST[0] - 1]
    events = {}
    for onset in onsets:
        path, prev, seen_issue = [], None, set()
        for r in rows:
            if not ((r["y"] == onset and r["m"] >= 1) or (r["y"] == onset + 1 and r["m"] <= 4)):
                continue
            pk, lab, full = window_peak(r, onset)
            if pk is None:
                continue
            if r["issued"] in seen_issue:      # один выпуск может лежать в обеих папках
                continue
            seen_issue.add(r["issued"])
            path.append({"issue": r["issued"], "y": r["y"], "m": r["m"], "peak_fc": round(pk, 2),
                         "peak_season": lab, "window_full": full,
                         "models_lo": round(min(max(v for v in vals[2:] if v is not None)
                                                for vals in r["models"].values()
                                                if any(v is not None for v in vals[2:])), 2) if r["models"] else None,
                         "models_hi": round(max(max(v for v in vals[2:] if v is not None)
                                                for vals in r["models"].values()
                                                if any(v is not None for v in vals[2:])), 2) if r["models"] else None,
                         "n_models": r["n_models"],
                         "ndj_fc": ndj_of(r, onset),
                         "d_prev": (None if prev is None else round(pk - prev, 2))})
            prev = pk
        obs = ev_obs.get(onset)
        settle = {}
        if obs:
            # ТОЛЬКО ВЫПУСКИ ДО ПИКА. Считать «устаканился» по выпускам, вышедшим ПОСЛЕ пика,
            # бессмысленно: их окно — уже спад, и их число обязано быть ниже. Раньше из-за этого
            # ни одно событие не «устаканивалось» вовсе.
            pk_abs = obs["year"] * 12 + SEASONS.index(obs["season"]) + 1
            before = [p for p in path if (p["y"] * 12 + p["m"] + 1) <= pk_abs]
            for t in (0.15, 0.25, 0.40):
                idx = None
                for i in range(len(before)):
                    if all(abs(q["peak_fc"] - obs["peak"]) <= t for q in before[i:]):
                        idx = i; break
                if idx is not None:
                    settle[str(t)] = {"issue": before[idx]["issue"],
                                      "months_before": pk_abs - (before[idx]["y"] * 12 + before[idx]["m"] + 1),
                                      "value": before[idx]["peak_fc"]}
        events[str(onset)] = {"path": path, "current": obs is None,
                              "observed_peak": (obs["peak"] if obs else None),
                              "observed_peak_season": (f"{obs['season']} {obs['year']}" if obs else None),
                              "ndj_obs": oni.get(("NDJ", onset)),
                              "settle": settle}

    # ── та же фаза календаря: выборка ПО ПРОГНОЗУ и, отдельно, по исходу
    same_phase = {"threshold_c": WARM_CALL, "forecast": {}, "outcome": {}}
    for mname, addr_m in (("Jun", 5), ("Jul", 6), ("Aug", 7)):
        fore, outc = [], []
        for r in rows:
            if r["m"] != addr_m:
                continue
            ndj_fc = ndj_of(r, r["y"])
            ndj_obs = oni.get(("NDJ", r["y"]))
            if ndj_fc is None or ndj_obs is None:
                continue
            item = {"issue": r["issued"], "year": r["y"], "ndj_fc": ndj_fc, "ndj_obs": ndj_obs,
                    "miss_ndj": round(ndj_fc - ndj_obs, 2), "became_event": r["y"] in ev_obs}
            if ndj_fc >= WARM_CALL:
                fore.append(item)
            if r["y"] in ev_obs:
                pk, lab, _f = window_peak(r, r["y"])
                outc.append(dict(item, peak_fc=(round(pk, 2) if pk is not None else None),
                                 obs_peak=ev_obs[r["y"]]["peak"],
                                 miss_peak=(None if pk is None else round(pk - ev_obs[r["y"]]["peak"], 2))))
        def pack(lst, key):
            v = [x[key] for x in lst if x.get(key) is not None]
            return {"cases": lst, "n": len(lst),
                    "low_n": sum(1 for x in v if x < 0), "high_n": sum(1 for x in v if x > 0),
                    "median": round(float(np.median(v)), 2) if v else None}
        same_phase["forecast"][mname] = pack(fore, "miss_ndj")
        same_phase["outcome"][mname] = pack(outc, "miss_peak")

    # ── сегодня и рекорд ряда
    last = rows[-1] if rows else None
    today = {}
    if last:
        cur = date.today().year
        pk, lab, full = window_peak(last, cur if cur in events or str(cur) in events else last["y"])
        # РАЗГОН ПЕРЕСМОТРОВ СЧИТАЕТСЯ ПО ВСЕМ ВЫПУСКАМ, А НЕ ПО ОКНУ СОБЫТИЯ: серия «одиннадцать
        # выпусков подряд вверх» начинается ещё в прошлом году, когда события не было.
        run_n, run_from, run_issue = 0, None, None
        seq, seen_i = [], set()
        for r in rows:
            if r["issued"] in seen_i:
                continue
            pk, _lab, _f = window_peak(r, last["y"])
            if pk is not None:
                seen_i.add(r["issued"]); seq.append((r["issued"], round(pk, 2)))
        for i in range(len(seq) - 1, 0, -1):
            if seq[i][1] > seq[i - 1][1]:
                run_n += 1; run_from, run_issue = seq[i - 1][1], seq[i - 1][0]
            else:
                break
        lastp = ((events.get(str(last["y"])) or {}).get("path") or [None])[-1]
        today = {"issue": last["issued"], "combined_peak": (round(pk, 2) if pk is not None else None),
                 "peak_season": lab, "n_models": last["n_models"],
                 "models_lo": (lastp["models_lo"] if lastp else None),
                 "models_hi": (lastp["models_hi"] if lastp else None),
                 "run_up_n": run_n, "run_up_from_value": (round(run_from, 2) if run_from is not None else None),
                 "run_up_from_issue": run_issue}
    rec_key, rec_val = max(oni.items(), key=lambda kv: kv[1])
    record = {"value": rec_val, "season": rec_key[0], "year": rec_key[1], "since": min(oni_years)}

    # ── СЫРЫЕ КРИВЫЕ ВСЕХ ВЫПУСКОВ (владелец 15.09: «сырые тоже показывать, чтобы сравнить, как
    # у нас в Long term»). Каждый выпуск — своя тонкая линия в календарном времени, и рядом то,
    # что на самом деле пришло. Ничего не усредняем: это и есть вся история одним взглядом.
    spa, seen_sp = [], set()
    for r in rows:
        if r["issued"] in seen_sp:
            continue
        seen_sp.add(r["issued"])
        pts = []
        for i, lab in enumerate(r["seasons"]):
            if i < 2 or "OBS" in lab or r["comb"][i] is None:
                continue
            cy, cm = centre(r["y"], r["m"], i)
            pts.append([cy * 12 + cm, round(r["comb"][i], 2)])
        if len(pts) >= 4:
            spa.append({"issue": r["issued"], "y": r["y"], "m": r["m"], "pts": pts})
    oni_pts = sorted([[y * 12 + ((SEASONS.index(s) + 1) if SEASONS.index(s) else 1), v]
                      for (s, y), v in oni.items() if y >= FIRST[0] - 1])
    spaghetti = {"issues": spa, "oni": oni_pts,
                 "x_from": min(p[0] for i in spa for p in i["pts"]) if spa else None,
                 "x_to": max(p[0] for i in spa for p in i["pts"]) if spa else None}

    doc = {"spaghetti": spaghetti,
           "meta": {"built": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "first_issue": rows[0]["issued"] if rows else None,
                    "last_issue": rows[-1]["issued"] if rows else None,
                    "n_issues": len(rows), "missing_issues": missing, "parse_failures": failures,
                    "oni_source": "NOAA CPC ONI (ERSST v5, 1991–2020 base), oni.txt",
                    "damping": DAMP, "warm_call_c": WARM_CALL},
           "years": years, "decades": decades, "cells": cells, "events": events,
           "same_phase": same_phase, "today": today, "record": record,
           "note": ("Every IRI/CPC plume issue since 2002, read from the archive figures with the same parser as "
                    "this week's plume. Error is the COMBINED forecast for a season minus the ONI that later came; "
                    "lead counts seasons ahead of the issue. Two reference forecasts are scored on exactly the same "
                    "targets — climatology (always 0.0) and damped persistence — because a quiet year is easy for "
                    "everyone and a raw error cannot say whether the centres improved. The forecast-conditional "
                    "sample keeps every summer issue that called a warm winter, including the calls nothing "
                    "followed; the outcome-conditional sample keeps only the summers an El Niño followed and cannot "
                    "say how often a warm call came to nothing."),
           "secs": int(time.time() - t0)}
    OUT.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    if verbose:
        print(f"models-history.json: {len(rows)} выпусков, {doc['meta']['first_issue']} → {doc['meta']['last_issue']}, {doc['secs']} с")
        for n, d in decades.items():
            print(f"  {n}: lead3 {d['3']['mae']} против климатологии {d['3']['mae_clim']} (n {d['3']['n']}, активность {d['3']['activity']}) | "
                  f"lead6 {d['6']['mae']} против {d['6']['mae_clim']} | lead9 {d['9']['mae']} против {d['9']['mae_clim']}")
        f = same_phase["forecast"]["Aug"]
        print(f"  август, зов ≥ +{WARM_CALL}: случаев {f['n']}, ниже пришедшего {f['low_n']}, выше {f['high_n']}, медиана {f['median']}")
        o = same_phase["outcome"]["Aug"]
        print(f"  август по исходу (событий {o['n']}): ниже пика {o['low_n']}, медиана {o['median']}")
    try:
        import ops as OPSLOG
        OPSLOG.record_run("models-history", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ok" if rows else "fail",
                          note=f"{len(rows)} issues")
    except Exception:                                            # noqa: BLE001
        pass
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--pause", type=float, default=1.5)
    a = ap.parse_args()
    if a.fetch:
        fetch_all(a.pause)
    build()


if __name__ == "__main__":
    main()
