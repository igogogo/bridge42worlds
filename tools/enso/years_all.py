# -*- coding: utf-8 -*-
"""ГОДЫ ДЛЯ СРАВНЕНИЯ: 4 сильнейших / все Эль-Ниньо / все годы (владелец 23.09).

На графиках «против сильнейших» стояли четыре года (1982, 1997, 2015, 2023 — пики ONI +2.1…+2.6).
Этот слой даёт панели остальное: список всех событий Эль-Ниньо по правилу CPC (ONI ≥ +0.5 пять
сезонов подряд; год начала, сезон, длина, пик) и суточные ряды КАЖДОГО года для Niño 3.4 и
мирового океана (аномалия к норме 1991–2020, день года + 120 дней следующего), чтобы сцена
«Against analogues» могла показать любое подмножество без пересборки. Ряды — из тех же копий
источника, что читает разбор (last_good, climatereanalyzer).
"""
import io
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeio           # noqa: E402
import sources as S     # noqa: E402
from numfmt import r2   # noqa: E402

DATA = ROOT / "data" / "enso"
OUT = DATA / "years.json"
STRONG = (1982, 1997, 2015, 2023)
NEXT_DAYS = 120

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def elnino_events(oni_path):
    """События Эль-Ниньо по ONI: пять сезонов подряд ≥ +0.5 (правило CPC). Год начала — год первого
    сезона; пик — наибольший ONI внутри события."""
    rows = [l.split() for l in io.open(oni_path, encoding="utf-8", errors="replace") if re.match(r"\s*[A-Z]{3}\s+\d{4}", l)]
    v = [(r[0], int(r[1]), float(r[3])) for r in rows]
    ev, i = [], 0
    while i < len(v):
        if v[i][2] >= 0.5:
            j = i
            while j < len(v) and v[j][2] >= 0.5:
                j += 1
            if j - i >= 5:
                pk = max(v[i:j], key=lambda x: x[2])
                ev.append({"year": v[i][1], "onset": v[i][0], "seasons": j - i, "peak": pk[2], "peak_season": pk[0] + " " + str(pk[1]),
                           "strong": v[i][1] in STRONG})
            i = j
        else:
            i += 1
    return ev


def daily_all(path):
    """Все годы суточного ряда: аномалия по дню года (366) плюс 120 дней следующего года."""
    d = S.read_cr_json(path)
    years, clim = d["years"], d["clim"]
    if clim is None:
        return {}
    ca = np.array([np.nan if v is None else v for v in clim], float)
    out = {}
    ys = sorted(years)
    for k, y in enumerate(ys):
        a = np.array([np.nan if v is None else v for v in years[y]], float) - ca[:len(years[y])]
        if np.isfinite(a).sum() < 200:
            continue
        nxt = []
        if k + 1 < len(ys):
            b = np.array([np.nan if v is None else v for v in years[ys[k + 1]]], float) - ca[:len(years[ys[k + 1]])]
            nxt = b[:NEXT_DAYS]
        ser = [None if not np.isfinite(x) else r2(float(x), 2) for x in a[:366]]
        while len(ser) < 366:
            ser.append(None)
        nx = [None if not np.isfinite(x) else r2(float(x), 2) for x in nxt]
        fin = [x for x in ser if x is not None]
        out[str(y)] = {"series": ser, "next": nx, "peak": r2(max(fin), 2) if fin else None, "n": len(fin)}
    return out


def build():
    t0 = time.time()
    ev = elnino_events(S.LAST / "oni.txt") if (S.LAST / "oni.txt").exists() else []
    daily = {}
    for key, fn in (("sst_nino34", "sst_nino34.json"), ("sst_world", "sst_world.json")):
        p = S.LAST / fn
        if p.exists():
            try:
                daily[key] = daily_all(p)
            except Exception as e:                               # noqa: BLE001
                print("  ", key, "skipped:", str(e)[:120])
    cy = datetime.now().year
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "strong": list(STRONG),
           "elnino": ev, "elnino_years": [e["year"] for e in ev],
           "rule": "El Niño by the NOAA CPC rule: ONI at or above +0.5 for five overlapping seasons in a row; the year is the year of the first such season",
           "daily": daily, "current_year": cy,
           "note": ("Years for comparison. The four strongest events (by the peak of ONI) are the default on every chart; "
                    "this file lets a chart show every El Niño year since 1950, or every year the series holds, "
                    "without a rebuild. Daily series are anomalies against the 1991–2020 normal, day of year plus "
                    "the first 120 days of the next year, from the same source copies the assessment reads.")}
    safeio.write_text(OUT, json.dumps(doc, ensure_ascii=False, allow_nan=False))
    print(f"years.json: {len(ev)} El Niño events since 1950, daily years " +
          ", ".join(f"{k} {len(v)}" for k, v in daily.items()) + f"; {OUT.stat().st_size // 1024} KB, {time.time() - t0:.1f} s")
    return doc


def main():
    build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
