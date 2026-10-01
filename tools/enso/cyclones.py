# -*- coding: utf-8 -*-
"""Тропические циклоны: треки и энергия сезона по бассейнам (владелец 01.10: «добавь треки тропических
циклонов»; в дайджесте новостей три дня подряд всплывало: тихий сентябрь в Атлантике, ураган «Поло» у Мексики).

Источник — IBTrACS v04r01 (NOAA NCEI, без регистрации): история с 1980 года одним файлом (`since1980`, 144 МБ,
качается один раз, в кэш идут только итоги), текущий сезон — `last3years` (10 МБ, NCEI обновляет его дважды в
неделю, треки текущего года — предварительные) и `ACTIVE` (идущие сейчас штормы). Ветер — оценка американских
центров (NHC и JTWC, `USA_WIND`, узлы, 1-минутный), одна шкала во всех трёх бассейнах; точки — только
синоптические сроки 00/06/12/18 UTC, стадия — тропическая или субтропическая по статусу.

ACE (accumulated cyclone energy) — сумма квадратов ветра по шестичасовым точкам с ветром от 35 узлов, × 10⁻⁴:
мера энергии сезона, в которой сходятся число, сила и длительность штормов. Норма — 1991–2020 на ту же дату
года; прошлые события — 1982, 1997, 2015, 2023 на ту же дату.

    python cyclones.py            # текущий сезон (история из кэша)
    python cyclones.py --refresh  # пересчитать историю из since1980
"""
import csv
import json
import sys
import time
import urllib.request
from datetime import date, datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import safeio                                                     # noqa: E402

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
csv.field_size_limit(10 ** 7)

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "enso"
CACHE = DATA / "cyclones"
OUT = DATA / "cyclones.json"
COAST_OUT = DATA / "coast-world.json"
IB = "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/"
LAND_URL = "https://cdn.jsdelivr.net/gh/nvkelso/natural-earth-vector@master/geojson/ne_110m_land.geojson"
UA = "Mozilla/5.0 (bridge42worlds El Nino panel)"
BASINS = {"NA": "North Atlantic", "EP": "Eastern North Pacific", "WP": "Western North Pacific"}
CLIM = (1991, 2020)
EVENTS = (1982, 1997, 2015, 2023)
TROPICAL = {"TD", "TS", "HU", "TY", "STY", "TC", "SD", "SS", "MH", "ST"}
KEEP_TYPES = {"main", "MAIN", "PROVISIONAL", "US-PROVISIONAL"}
SEAM = 45.0          # долготы карты: [45°E, 405°) — шов через Аравию, окно карты 90°E…0°


def _get(url, path, timeout=900):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r, open(path, "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)


def lonr(lon):
    """Долгота в представлении карты: непрерывно через 180°, шов на 45°E."""
    return lon if lon >= SEAM else lon + 360.0


def rows(path):
    """Шестичасовые точки основных треков: (sid, год, бассейн, имя, время, широта, долгота, ветер, тропическая)."""
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        rd = csv.reader(f)
        h = next(rd)
        next(rd)                                           # строка единиц
        ix = {k: i for i, k in enumerate(h)}
        for r in rd:
            try:
                if r[ix["TRACK_TYPE"]] not in KEEP_TYPES:
                    continue
                t = r[ix["ISO_TIME"]]
                if t[14:16] != "00" or t[11:13] not in ("00", "06", "12", "18"):
                    continue
                st = r[ix["USA_STATUS"]].strip()
                nat = r[ix["NATURE"]].strip()
                la0 = float(r[ix["LAT"]])
                # СТАДИЯ НЕ УКАЗАНА (01.10): в предварительных треках западной Пацифики нет ни статуса, ни природы
                # («NR» у 599 из 651 точек), и фильтр выкидывал почти весь сезон. Не указано — тропический, если
                # южнее 45°; известные «ET» (внетропический) и «DS» (возмущение) по-прежнему не считаются.
                trop = (st in TROPICAL) if st else ((nat in ("TS", "SS")) or (nat in ("NR", "MX", "") and abs(la0) <= 45))
                w = r[ix["USA_WIND"]].strip()
                wind = int(float(w)) if w else None
                yield (r[ix["SID"]], int(t[:4]), r[ix["BASIN"]].strip() or "NA", r[ix["NAME"]].strip(), t[:16],
                       float(r[ix["LAT"]]), float(r[ix["LON"]]), wind, trop)
            except (ValueError, IndexError, KeyError):
                continue


def storms_from(path, years=None):
    S = {}
    for sid, y, b, nm, t, la, lo, w, tr in rows(path):
        if years and y not in years:
            continue
        s = S.setdefault(sid, {"sid": sid, "name": nm, "pts": []})
        s["pts"].append((t, b, la, lo, w, tr))
    for s in S.values():
        s["pts"].sort()
    return S


def doy(t):
    d = date(int(t[:4]), int(t[5:7]), int(t[8:10]))
    return (d - date(d.year, 1, 1)).days                      # 0…365


def season_curves(S, year):
    """По бассейнам: накопленные ACE и счёт (штормы ≥34 уз., ураганы ≥64, сильные ≥96) по дню года."""
    out = {b: {"ace": np.zeros(366), "named": np.zeros(366), "hur": np.zeros(366), "major": np.zeros(366)} for b in BASINS}
    for s in S.values():
        done = set()
        for (t, b, la, lo, w, tr) in s["pts"]:
            if int(t[:4]) != year or b not in BASINS or w is None or not tr:
                continue
            k = doy(t)
            if w >= 35:
                out[b]["ace"][k] += w * w * 1e-4
            for lim, key in ((34, "named"), (64, "hur"), (96, "major")):
                if w >= lim and key not in done:
                    done.add(key)
                    out[b][key][k] += 1
    return {b: {k: np.cumsum(v) for k, v in c.items()} for b, c in out.items()}


def history(refresh=False, verbose=True):
    """Итоги 1980 — прошлый год из since1980: кривые по годам и треки сильных событий. Кэш на диске."""
    p = CACHE / "hist.json"
    if p.exists() and not refresh:
        return json.loads(p.read_text(encoding="utf-8"))
    src = CACHE / "since1980.csv"
    if not src.exists():
        if verbose:
            print("  качаю since1980 (144 МБ)…", flush=True)
        _get(IB + "ibtracs.since1980.list.v04r01.csv", src)
    t0 = time.time()
    S = storms_from(src)
    last = date.today().year - 1
    years = list(range(1980, last + 1))
    curves = {}
    for y in years:
        c = season_curves(S, y)
        curves[str(y)] = {b: {k: [round(float(x), 1) for x in v] for k, v in cb.items()} for b, cb in c.items()}
    tracks = {str(y): tracks_of(S, y) for y in EVENTS}
    h = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "years": years, "curves": curves, "tracks": tracks}
    safeio.write_text(p, json.dumps(h))
    if verbose:
        print(f"  история: штормов {len(S)}, лет {len(years)}, {time.time() - t0:.0f} с", flush=True)
    return h


def cat(w):
    if w is None:
        return 0
    return 0 if w < 34 else 1 if w < 64 else 2 if w < 83 else 3 if w < 96 else 4 if w < 113 else 5 if w < 137 else 6


def tracks_of(S, year, every=1):
    """Треки штормов года (все бассейны), точки — [широта, долгота карты, ветер]; только набравшие 34 уз."""
    out = []
    for s in S.values():
        pts = [p for p in s["pts"] if int(p[0][:4]) == year]
        if not pts:
            continue
        mx = max((p[4] or 0) for p in pts)
        if mx < 34:
            continue
        ace = sum((p[4] or 0) ** 2 * 1e-4 for p in pts if p[5] and (p[4] or 0) >= 35)
        out.append({"name": s["name"].title() if s["name"] not in ("UNNAMED", "NOT_NAMED") else "unnamed", "sid": s["sid"],
                    "basin": pts[0][1], "start": pts[0][0][:10], "end": pts[-1][0][:10], "max": mx, "cat": cat(mx),
                    "ace": round(ace, 1),
                    "pts": [[round(p[2], 1), round(lonr(p[3]), 1), p[4]] for p in pts[::every]]})
    out.sort(key=lambda x: x["start"])
    return out


def coast(verbose=True):
    """Контуры суши для карты треков: Natural Earth 110m (общественное достояние), долготы в представлении
    карты, линии рвутся на шве; Антарктида и полярные куски вне окна отброшены."""
    if COAST_OUT.exists():
        return
    src = CACHE / "ne_110m_land.geojson"
    if not src.exists():
        _get(LAND_URL, src, timeout=120)
    g = json.loads(src.read_text(encoding="utf-8"))
    lines = []
    for f in g.get("features") or []:
        geom = f.get("geometry") or {}
        polys = geom["coordinates"] if geom.get("type") == "MultiPolygon" else [geom.get("coordinates") or []]
        for poly in polys:
            for ring in poly[:1]:
                cur = []
                prev = None
                for lo, la in ring:
                    x = lonr(lo)
                    if prev is not None and abs(x - prev) > 180:
                        if len(cur) > 1:
                            lines.append(cur)
                        cur = []
                    if -50 <= la <= 66:
                        cur.append([round(x, 2), round(la, 2)])
                    elif len(cur) > 1:
                        lines.append(cur)
                        cur = []
                    else:
                        cur = []
                    prev = x
                if len(cur) > 1:
                    lines.append(cur)
    doc = {"note": "Natural Earth 110m land outlines (public domain), longitudes continuous across 180°, seam at 45°E",
           "src": "naturalearthdata.com", "lines": lines}
    safeio.write_text(COAST_OUT, json.dumps(doc, separators=(",", ":")))
    if verbose:
        print(f"  coast-world.json: линий {len(lines)}, {COAST_OUT.stat().st_size // 1024} КБ")


def build(refresh=False, verbose=True):
    t0 = time.time()
    CACHE.mkdir(parents=True, exist_ok=True)
    coast(verbose)
    H = history(refresh, verbose)
    cur_y = date.today().year
    src = CACHE / "last3years.csv"
    try:
        _get(IB + "ibtracs.last3years.list.v04r01.csv", src, timeout=300)
    except Exception as e:                                       # noqa: BLE001
        if verbose:
            print(f"  last3years не скачан ({str(e)[:80]}), беру прежнюю копию", flush=True)
    S = storms_from(src, years={cur_y})
    act = CACHE / "active.csv"
    try:
        _get(IB + "ibtracs.ACTIVE.list.v04r01.csv", act, timeout=120)
        A = storms_from(act, years={cur_y})
        for sid, s in A.items():                                 # свежие точки идущих штормов поверх
            have = {p[0] for p in S.get(sid, {"pts": []})["pts"]}
            S.setdefault(sid, {"sid": sid, "name": s["name"], "pts": []})["pts"] += [p for p in s["pts"] if p[0] not in have]
            S[sid]["pts"].sort()
    except Exception:                                            # noqa: BLE001
        A = {}
    last_t = max((p[0] for s in S.values() for p in s["pts"]), default=None)
    cur = season_curves(S, cur_y)
    k_now = doy(last_t) if last_t else 0
    basins = {}
    for b, nm in BASINS.items():
        clim = {key: np.array([H["curves"][str(y)][b][key] for y in range(CLIM[0], CLIM[1] + 1)]) for key in ("ace", "named", "hur", "major")}
        allv = np.array([H["curves"][str(y)][b]["ace"][k_now] for y in H["years"]])
        now = {key: round(float(cur[b][key][k_now]), 1) for key in ("ace", "named", "hur", "major")}
        rank = int(1 + np.sum(allv > now["ace"]))              # 1 — самый энергичный на эту дату
        basins[b] = {
            "name": nm, "to_date": now,
            "normal_to_date": {key: round(float(clim[key][:, k_now].mean()), 1) for key in clim},
            "normal_season": {key: round(float(clim[key][:, -1].mean()), 1) for key in clim},
            "rank_ace": rank, "of": len(H["years"]) + 1, "years_from": H["years"][0],
            "events_to_date": {str(y): {key: H["curves"][str(y)][b][key][k_now] for key in ("ace", "named", "hur", "major")} for y in EVENTS},
            "events_season": {str(y): {key: H["curves"][str(y)][b][key][-1] for key in ("ace", "named", "hur", "major")} for y in EVENTS},
            "curve": {"now": [round(float(x), 1) for x in cur[b]["ace"][:k_now + 1]],
                      "mean": [round(float(x), 1) for x in clim["ace"].mean(axis=0)],
                      "p10": [round(float(x), 1) for x in np.percentile(clim["ace"], 10, axis=0)],
                      "p90": [round(float(x), 1) for x in np.percentile(clim["ace"], 90, axis=0)],
                      **{str(y): H["curves"][str(y)][b]["ace"] for y in EVENTS}},
        }
    active = []
    for sid, s in A.items():
        p = s["pts"][-1] if s["pts"] else None
        if p and last_t and p[0] >= last_t[:10]:
            active.append({"name": s["name"].title(), "basin": p[1], "t": p[0], "lat": p[2], "lon": p[3], "kt": p[4], "cat": cat(p[4])})
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "year": cur_y, "last_time": last_t, "day_of_year": k_now,
           "basins": basins, "active": active,
           "tracks": {str(cur_y): tracks_of(S, cur_y), **{y: H["tracks"][y] for y in H["tracks"]}},
           "clim": f"{CLIM[0]}–{CLIM[1]}", "events": list(EVENTS), "secs": round(time.time() - t0),
           "source": "IBTrACS v04r01, NOAA NCEI: since1980 for the history, last3years and ACTIVE for this season "
                     "(provisional tracks, updated about twice a week); wind from the US agencies (NHC, JTWC), 1-minute, knots",
           "note": "ACE, accumulated cyclone energy: the sum of the squared wind of every six-hourly fix of a tropical or "
                   "subtropical storm at 35 knots or more, times 10^-4. It folds the number, strength and lifetime of "
                   "storms into one number for the season. This season's tracks are provisional and can still change."}
    safeio.write_text(OUT, json.dumps(doc, ensure_ascii=False, separators=(",", ":"), allow_nan=False))
    if verbose:
        for b, v in basins.items():
            print(f"  {b}: ACE {v['to_date']['ace']} против нормы {v['normal_to_date']['ace']} на эту дату, место {v['rank_ace']} из {v['of']}; "
                  f"штормов {v['to_date']['named']:.0f} ({v['normal_to_date']['named']}), ураганов {v['to_date']['hur']:.0f} "
                  f"({v['normal_to_date']['hur']}), сильных {v['to_date']['major']:.0f} ({v['normal_to_date']['major']})", flush=True)
        print(f"cyclones.json: данные к {last_t}, активных {len(active)}, {OUT.stat().st_size // 1024} КБ, {doc['secs']} с")
    return doc


if __name__ == "__main__":
    build(refresh="--refresh" in sys.argv)
