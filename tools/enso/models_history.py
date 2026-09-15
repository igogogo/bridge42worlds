# -*- coding: utf-8 -*-
"""Прогнозы сквозь годы: как ошибались модели двадцать лет назад, десять и сейчас.

Владелец 15.09: «хочу увидеть, как сдвигаются прогнозы и отличие — что было раньше, скажем
10, 20 лет назад, и что сейчас; как двигаются прогнозы по нашим особенным годам Эль-Ниньо;
и что происходит с прогнозами прямо сейчас на горизонте этого события».

Откуда. IRI хранит плюм каждого выпуска с 2002 года тем же адресом, что и текущий
(figure4_plot/<год>/<месяц>), и тот же разбор SVG (iri_plume.py) читает старые выпуски без
правок — проверено на 2004, 2009, 2015 и 2023. Это единственная открытая история прогнозов
двух десятков центров одним файлом на выпуск.

Что считаем, и только это:
  · ОШИБКА ПО ГОДАМ. Для каждого выпуска — прогноз COMBINED на сезоны вперёд против ONI,
    который потом действительно случился. Заблаговременность в сезонах: JAS из августовского
    выпуска — первый сезон вперёд. Среднее |ошибки| по выпускам года на 3, 6 и 9 сезонов вперёд.
    Отдельно средние по десятилетиям, чтобы «раньше — сейчас» было одним числом.
  · СОБЫТИЯ. Для каждого Эль-Ниньо в записи (год начала) — как менялся прогноз пика от выпуска к
    выпуску в году начала и до весны следующего, против пика ONI, который случился. Один и тот
    же путь для 2026-го, только без наблюдённого пика: он ещё впереди.
  · ЗНАК ОШИБКИ НА ТОЙ ЖЕ ФАЗЕ. В прошлых событиях августовский выпуск занижал или завышал
    будущий пик — и на сколько. Это честный ориентир для чтения сегодняшнего плюма.

Чего не делаем: не пересчитываем «умение» по формулам из статей (ACC, RMSSS с климатологией) —
это другая работа; здесь ошибка в градусах, которую читатель поймёт без подготовки.

    python tools/enso/models_history.py --fetch     докачать выпуски (2002 → сегодня), разобрать, посчитать
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
# годы начала событий Эль-Ниньо в записи IRI (ONI ≥ +0.5 пять сезонов подряд); 2026 — наше
ONSETS = [2002, 2004, 2006, 2009, 2015, 2018, 2023, 2026]
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


# ---------------------------------------------------------------- выпуски
def issues():
    """Все адреса (год, месяц) от FIRST до последнего, который мог выйти (адрес = месяц выпуска − 1)."""
    t = date.today()
    y, m = FIRST
    out = []
    while (y, m) <= (t.year, t.month - 1 if t.month > 1 else 12) and (y, m) < (t.year + 1, 1):
        out.append((y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return [(y, m) for (y, m) in out if (y, m) < (t.year, t.month)]


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
                miss.append(f"{y}-{m:02d}: {len(b)} байт"); continue
            p.write_bytes(b); got += 1
            if verbose and got % 20 == 0:
                print(f"  скачано {got}, последний {y}-{m:02d}")
        except Exception as e:                                   # noqa: BLE001
            miss.append(f"{y}-{m:02d}: {str(e)[:60]}")
        time.sleep(pause)
    if verbose:
        print(f"выпусков докачано {got}, не отдано {len(miss)}" + (": " + "; ".join(miss[:6]) if miss else ""))
    return got, miss


def parsed(y, m):
    """Разбор с кэшем: SVG читается один раз."""
    p = RAW / f"plume_{y}_{m:02d}.svg"
    if not p.exists():
        return None
    cache = RAW / f"parsed_{y}_{m:02d}.json"
    if cache.exists() and cache.stat().st_mtime >= p.stat().st_mtime:
        return json.loads(cache.read_text(encoding="utf-8"))
    try:
        pl = IP.parse(p)
    except Exception as e:                                       # noqa: BLE001
        return {"error": str(e)[:120], "addr": [y, m]}
    keep = {"addr": [y, m], "issued": pl.get("issued"), "seasons": pl.get("seasons") or [],
            "models": {k: {"section": v["section"], "values": v["values"]} for k, v in (pl.get("models") or {}).items() if v.get("values")}}
    cache.write_text(json.dumps(keep, ensure_ascii=False), encoding="utf-8")
    return keep


# ---------------------------------------------------------------- счёт
def season_year(y, m, i):
    """Год ONI для сезона с индексом i в плюме адреса (y, m): сезон i начинается в месяце m+(i−2),
    ONI подписывает сезон годом среднего месяца."""
    cm = m + (i - 2) + 1
    return y + (cm - 1) // 12


def build(verbose=True):
    t0 = time.time()
    oni = {(s, y): v for s, y, v in S.read_oni(S.LAST / "oni.txt")}
    rows = []                                                    # по выпуску
    for y, m in issues():
        pl = parsed(y, m)
        if not pl or pl.get("error"):
            continue
        comb = (pl["models"].get("COMBINED AVG") or {}).get("values")
        if not comb:
            continue
        seas = pl["seasons"]
        errs, fc = {}, {}
        for i, lab in enumerate(seas):
            if i < 2 or "OBS" in lab or comb[i] is None:
                continue
            lead = i - 1
            yy = season_year(y, m, i)
            fc[lead] = {"season": lab, "year": yy, "fc": comb[i]}
            if (lab, yy) in oni:
                errs[lead] = round(comb[i] - oni[(lab, yy)], 3)
        n_models = len([k for k, v in pl["models"].items() if v["section"] in ("dyn", "stat")])
        rows.append({"y": y, "m": m, "issued": pl.get("issued"), "n_models": n_models, "fc": fc, "err": errs,
                     "models": {k: v["values"] for k, v in pl["models"].items() if v["section"] in ("dyn", "stat")},
                     "seasons": seas})
    # ── ошибка по годам выпуска
    by_year = {}
    for r in rows:
        d = by_year.setdefault(r["y"], {"issues": 0, "n_models": [], "abs": {l: [] for l in LEADS}, "bias": {l: [] for l in LEADS}})
        d["issues"] += 1; d["n_models"].append(r["n_models"])
        for l in LEADS:
            if l in r["err"]:
                d["abs"][l].append(abs(r["err"][l])); d["bias"][l].append(r["err"][l])
    years = {}
    for y, d in sorted(by_year.items()):
        years[str(y)] = {"issues": d["issues"], "models": int(round(np.mean(d["n_models"]))) if d["n_models"] else None,
                         "mae": {str(l): (round(float(np.mean(v)), 2) if v else None) for l, v in d["abs"].items()},
                         "bias": {str(l): (round(float(np.mean(v)), 2) if v else None) for l, v in d["bias"].items()},
                         "n": {str(l): len(v) for l, v in d["abs"].items()}}
    # ── десятилетия
    decades = {}
    for name, lo, hi in (("2002–2010", 2002, 2010), ("2011–2020", 2011, 2020), ("2021–2026", 2021, 2026)):
        acc = {l: [] for l in LEADS}
        for r in rows:
            if lo <= r["y"] <= hi:
                for l in LEADS:
                    if l in r["err"]:
                        acc[l].append(abs(r["err"][l]))
        decades[name] = {str(l): (round(float(np.mean(v)), 2) if v else None) for l, v in acc.items()}
        decades[name]["n"] = len(acc[LEADS[0]])
    # ── события: путь прогноза пика по выпускам
    def obs_peak(onset):
        vals = []
        for (lab, yy), v in oni.items():
            if yy == onset and lab in ("JAS", "ASO", "SON", "OND", "NDJ"):
                vals.append((v, lab, yy))
            if yy == onset + 1 and lab in ("DJF", "JFM", "FMA"):
                vals.append((v, lab, yy))
        return max(vals) if vals else None
    events = {}
    for onset in ONSETS:
        op = obs_peak(onset)
        path = []
        for r in rows:
            if not ((r["y"] == onset and r["m"] >= 1) or (r["y"] == onset + 1 and r["m"] <= 3)):
                continue
            # пик прогноза внутри окна события: сезоны с центром от июля года начала до апреля следующего
            best, best_lab, mm = None, None, []
            for l, f in r["fc"].items():
                cm = r["m"] + (l + 1) + 1 - 1          # центр сезона lead l: месяц m + l  (сезон l начинается в m+l−1)
                cy = r["y"] + (cm - 1) // 12; cmm = (cm - 1) % 12 + 1
                inwin = (cy == onset and cmm >= 7) or (cy == onset + 1 and cmm <= 4)
                if inwin and (best is None or f["fc"] > best):
                    best, best_lab = f["fc"], f"{f['season']} {f['year']}"
            # разброс моделей по тому же пику
            for k, vals in r["models"].items():
                v = [x for x in vals[2:] if x is not None]
                if v:
                    mm.append(max(v))
            if best is not None:
                path.append({"issued": r["issued"], "months_from_jan": (r["y"] - onset) * 12 + r["m"] + 1 - 1,
                             "peak_fc": round(best, 2), "peak_season": best_lab,
                             "models_lo": round(min(mm), 2) if mm else None, "models_hi": round(max(mm), 2) if mm else None,
                             "n_models": len(mm)})
        events[str(onset)] = {"observed_peak": ({"value": op[0], "season": op[1], "year": op[2]} if op else None),
                              "path": path, "current": onset == 2026}
    # ── на той же фазе: ошибка августовского выпуска по пику в прошлых событиях
    same_phase = {}
    for mname, mnum in (("Jun", 7), ("Jul", 8), ("Aug", 9)):        # адрес m = месяц выпуска − 1
        errs = []
        for onset, ev in events.items():
            if ev["current"] or not ev["observed_peak"]:
                continue
            pt = [p for p in ev["path"] if p["issued"] == f"{mname} {onset}"]
            if pt:
                errs.append({"event": onset, "fc": pt[0]["peak_fc"], "obs": ev["observed_peak"]["value"], "err": round(pt[0]["peak_fc"] - ev["observed_peak"]["value"], 2)})
        same_phase[mname] = {"cases": errs, "mean_err": round(float(np.mean([e["err"] for e in errs])), 2) if errs else None,
                             "under_in": sum(1 for e in errs if e["err"] < 0), "of": len(errs)}
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "issues": len(rows),
           "first": f"{rows[0]['issued']}" if rows else None, "last": f"{rows[-1]['issued']}" if rows else None,
           "leads": list(LEADS), "years": years, "decades": decades, "events": events, "same_phase": same_phase,
           "note": ("Every IRI/CPC plume issue since 2002, read from the archive figures with the same parser as the "
                    "current plume. Error = the COMBINED forecast for a season minus the ONI that later happened; lead "
                    "is counted in seasons ahead of the issue (JAS from an August issue is lead 1). Mean absolute "
                    "error by issue year and by decade; for each El Niño the forecast of the coming peak issue by "
                    "issue against the peak that came. The 2026 path has no observed peak yet."),
           "secs": int(time.time() - t0)}
    OUT.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    if verbose:
        print(f"models-history.json: выпусков {len(rows)}, {doc['first']} → {doc['last']}, {doc['secs']} с")
        for k, v in decades.items():
            print(f"  {k}: MAE lead3 {v['3']} lead6 {v['6']} lead9 {v['9']} (n {v['n']})")
        for k, v in same_phase.items():
            print(f"  {k} выпуск в год начала: средняя ошибка пика {v['mean_err']}, занижал в {v['under_in']} из {v['of']}")
    try:
        import ops as OPSLOG
        OPSLOG.record_run("models-history", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ok" if rows else "fail", note=f"{len(rows)} issues")
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
