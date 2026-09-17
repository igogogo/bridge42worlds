# -*- coding: utf-8 -*-
"""Кто выбивается: один список всего, что сегодня ушло от своей нормы дальше обычного.

Владелец 15.09: «меня волнует Инсбрук и вообще всё, что начинает выбиваться».

Беда, которую это чинит. Рядов на панели уже под сотню: три мировых, шесть боксов суши,
тринадцать горных точек, четыре зоны Niño, Залив, Кувейт. Каждый живёт на своей сцене, и чтобы
понять, где сегодня необычно, надо обойти их все и в каждом посмотреть ранг. Ни один человек
этого делать не будет. Значит, обойти должна панель.

КАК СЧИТАЕТСЯ «ВЫБИВАЕТСЯ». Для каждого ряда берём отклонение последних тридцати суток от его
собственной нормы 1991–2020 и сравниваем НЕ с другими рядами, а с собственной историей этого же
ряда на те же календарные дни. Получается место в своём ряду (ранг из N лет) и во сколько сигм
это укладывается. Сравнивать ряды между собой по градусам нельзя: у Арктики разброс вчетверо
шире тропиков, и «плюс два» там и там значит разное. Ранг и сигма сравнимы, градусы нет.

ТРИ ВЕЩИ, БЕЗ КОТОРЫХ СПИСОК ВРЁТ:
  · РЯД ДОЛЖЕН БЫТЬ ДЛИННЫМ. Меньше двадцати лет — ранг «первое из пятнадцати» ничего не стоит.
    Такие ряды в список не идут, и это сказано вслух.
  · СВЕЖЕСТЬ. Ряд, отставший на месяц, покажет прошлое как настоящее: возраст пишется у каждой
    строки, и всё старше двух недель уходит в конец с пометкой.
  · НАПРАВЛЕНИЕ. Холодная аномалия выбивается ровно так же, как тёплая; список ранжируется по
    модулю, а знак остаётся в самой строке. Иначе получится не сторож, а подборка плохих новостей.

    python tools/enso/outliers.py            посчитать и записать outliers.json
    python tools/enso/outliers.py --top 12   показать верхушку в консоли
"""
import argparse
import json
import sys
import time
from datetime import date, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "data" / "enso"
# Своя запись файлов: повтор при осечке файловой системы и подмена целиком (17.09).
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio   # noqa: E402
OUT = ROOT / "outliers.json"
MIN_YEARS = 20                  # короче — ранг ничего не значит
STALE_DAYS = 14                 # старше — в конец списка, с пометкой

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def _rows_from_watch(key, name, group, w, where=None, extra=None):
    """Ряд, посчитанный кирпичом watch.series_watch: у него уже есть level30 с рангом."""
    l30 = (w or {}).get("level30") or {}
    if l30.get("anom") is None or not l30.get("of"):
        return None
    of = int(l30["of"])
    if of < MIN_YEARS:
        return None
    rank = int(l30.get("rank_raw") or 0)
    z = l30.get("z")
    stale = (w or {}).get("days_stale")
    return {"key": key, "name": name, "group": group, "where": where,
            "anom": round(float(l30["anom"]), 2), "rank": rank, "of": of,
            "z": (round(float(z), 2) if z is not None else None),
            "pct": l30.get("pct"), "date": (w or {}).get("last_date"),
            "stale_days": stale, "unit": "°C",
            "extra": extra or {}}


def collect():
    rows, skipped = [], []
    L = json.loads((ROOT / "latest.json").read_text(encoding="utf-8"))
    W = L.get("watch") or {}
    GLOBAL = {"sst_nino34": "Niño 3.4, the El Niño patch", "sst_world": "The world ocean surface",
              "t2_world": "The air over land and ocean"}
    for k, nm in GLOBAL.items():
        r = _rows_from_watch(k, nm, "the planet", W.get(k))
        if r:
            rows.append(r)

    try:
        RD = json.loads((ROOT / "regions-daily.json").read_text(encoding="utf-8")).get("series") or {}
    except Exception:                                            # noqa: BLE001
        RD = {}
    for k, w in RD.items():
        lab = (w.get("label") or k).split(",")[0]
        r = _rows_from_watch(k, lab, "land regions", w, where=w.get("region"))
        if r:
            rows.append(r)

    try:
        G = json.loads((ROOT / "glaciers.json").read_text(encoding="utf-8")).get("series") or {}
    except Exception:                                            # noqa: BLE001
        G = {}
    for k, w in G.items():
        nm = (w.get("label") or k).split(",")[0]
        pdd = ((w.get("melt") or {}).get("pdd") or {})
        extra = {}
        if pdd.get("to_date") is not None and pdd.get("clim_to_date"):
            extra = {"melt_now": pdd["to_date"], "melt_normal": pdd["clim_to_date"],
                     "melt_rank": pdd.get("rank"), "melt_of": pdd.get("of"),
                     "what": w.get("what"), "enso": w.get("enso"), "elevation": w.get("elevation")}
        r = _rows_from_watch(k, nm, "mountain ice", w, where=w.get("region"), extra=extra)
        if r:
            rows.append(r)
        elif w.get("level30"):
            skipped.append({"key": k, "name": nm, "why": "the record here is shorter than " + str(MIN_YEARS) + " years"})

    # Зоны Niño: ранг считаем сами по недельному ряду — у них нет level30
    NW = L.get("noaa") or {}
    lat, hm, hmd = NW.get("latest") or {}, NW.get("hist_max") or {}, NW.get("hist_max_date") or {}
    # запад → восток; список потом сортируется по величине, так что это порядок при равенстве
    for zk, nm in (("n4a", "Niño 4, the western Pacific"), ("n34a", "Niño 3.4, weekly"),
                   ("n3a", "Niño 3, the eastern Pacific"), ("n12a", "Niño 1+2, off Peru")):
        v = lat.get(zk)
        if v is None or hm.get(zk) is None:
            continue
        rows.append({"key": "zone_" + zk, "name": nm, "group": "the Pacific zones", "where": None,
                     "anom": v, "rank": 1 if v > hm[zk] else None, "of": None, "z": None, "pct": None,
                     "date": NW.get("date"), "stale_days": None, "unit": "°C",
                     "extra": {"ceiling": hm[zk], "ceiling_date": hmd.get(zk),
                               "above_ceiling": bool(v > hm[zk])}})
    return rows, skipped


def build(top=10, verbose=True):
    t0 = time.time()
    rows, skipped = collect()
    # порядок: по модулю сигмы, а где её нет — по месту в своём ряду
    def score(r):
        if r.get("z") is not None:
            return abs(r["z"])
        if r.get("rank") and r.get("of"):
            return 3.0 * (1 - (r["rank"] - 1) / max(1, r["of"] - 1))
        if r.get("extra", {}).get("above_ceiling"):
            return 3.5
        return 0.0
    for r in rows:
        r["score"] = round(score(r), 2)
        r["stale"] = bool((r.get("stale_days") or 0) > STALE_DAYS)
    fresh = sorted([r for r in rows if not r["stale"]], key=lambda r: -r["score"])
    stale = sorted([r for r in rows if r["stale"]], key=lambda r: -r["score"])
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "n": len(rows),
           "min_years": MIN_YEARS, "stale_days": STALE_DAYS,
           "rows": fresh + stale, "skipped": skipped,
           "note": ("Every daily series the panel holds, asked the same question: how unusual is the last 30 days "
                    "for THIS series on THESE calendar days, against its own 1991–2020 normal and its own history. "
                    "Series are ranked by that, not by degrees: the Arctic swings four times as wide as the tropics, "
                    "so +2 °C means different things in different places, while a rank and a sigma are comparable. "
                    "Cold anomalies count as much as warm ones — the list is ordered by size, and the sign stays in "
                    "the row. Series shorter than " + str(MIN_YEARS) + " years are left out, because a rank out of "
                    "fifteen says little; anything more than " + str(STALE_DAYS) + " days behind is moved to the end "
                    "and marked, because a stale series shows the past as the present."),
           "secs": int(time.time() - t0)}
    safeio.write_text(OUT, json.dumps(doc, ensure_ascii=False))
    if verbose:
        print(f"outliers.json: {len(rows)} рядов, {doc['secs']} с")
        for r in doc["rows"][:top]:
            e = r.get("extra") or {}
            m = (f" · таяние {e['melt_now']:.0f} против {e['melt_normal']:.0f}" if e.get("melt_now") is not None else "")
            rank = f"{r['rank']}/{r['of']}" if r.get("of") else ("выше потолка" if e.get("above_ceiling") else "—")
            print(f"  {r['score']:>4} | {r['name'][:38]:<38} {r['anom']:+5.2f} °C  место {rank:>8}"
                  f"  σ {r['z'] if r['z'] is not None else '—'}{m}" + ("  [устарел]" if r["stale"] else ""))
        if skipped:
            print(f"  не в счёт (ряд короче {MIN_YEARS} лет): {len(skipped)}")
    try:
        import ops as OPSLOG
        OPSLOG.record_run("outliers", datetime.fromtimestamp(t0).strftime("%Y-%m-%d %H:%M:%S"),
                          datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "ok" if rows else "fail",
                          note=f"{len(rows)} series")
    except Exception:                                            # noqa: BLE001
        pass
    return doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args()
    build(a.top)


if __name__ == "__main__":
    main()
