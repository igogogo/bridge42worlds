# -*- coding: utf-8 -*-
"""ЗАРЯД ТОПЛИВА: рост накопленного тепла против прошлых событий и траектория с учётом замедления.

Владелец 22.09: «идёт рост накопленного тепла, хотя в этот период обычно начинается спад; мы не
только выше абсолютного максимума — главный драйвер всё ещё растёт; отдельная вкладка, графики
сравнения, траектория, это как вторая производная».

Из месячных рядов PMEL (объём тёплой воды с 1980, T300) для каждого года начала Эль-Ниньо —
путь за 24 месяца (январь года события — декабрь следующего), что было у него в ЭТОТ месяц
(уровень, ход за 3 месяца, ускорение, шёл ли спад), ранг этого года, и два рода сценариев:
  · по форме аналогов: к нынешнему уровню прибавляется путь каждого события от этого месяца;
  · по инерции: текущий ход за месяц продолжается с текущим замедлением (парабола) — где и когда
    он обнулится. Это ОЦЕНКА арифметикой, не прогноз, и на панели так и подписана.
"""
import json
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
from air import EVENT_YEARS, ANALOG_YEARS, charge_stats, J_PER_K   # noqa: E402

DATA = ROOT / "data" / "enso"
OUT = DATA / "charge.json"
HORIZON = 12

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _mk(y, m):
    return f"{y:04d}-{m:02d}"


def _path24(d, y, div):
    """Январь года y — декабрь года y+1: 24 значения (None — пропуск)."""
    out = []
    for i in range(24):
        yy, mm = y + i // 12, i % 12 + 1
        v = d.get(_mk(yy, mm))
        out.append(None if v is None else r2(v / div, 3))
    return out


def _series(d, div):
    ks = sorted(d)
    return ks, [d[k] / div for k in ks]


def trajectory(d, div, last_key, years):
    """Сценарии на HORIZON месяцев вперёд от last_key."""
    y0, m0 = int(last_key[:4]), int(last_key[5:7])
    now = d[last_key] / div
    months = []
    for i in range(1, HORIZON + 1):
        yy, mm = y0 + (m0 + i - 1) // 12, (m0 + i - 1) % 12 + 1
        months.append(_mk(yy, mm))
    analog = {}
    for y in years:
        base = d.get(_mk(y, m0))
        if base is None:
            continue
        p = []
        for i in range(1, HORIZON + 1):
            yy, mm = y + (m0 + i - 1) // 12, (m0 + i - 1) % 12 + 1
            v = d.get(_mk(yy, mm))
            p.append(None if v is None else r2(now + (v - base) / div, 3))
        analog[str(y)] = p
    arr = np.array([[np.nan if v is None else v for v in p] for p in analog.values()], float) if analog else np.zeros((0, HORIZON))
    med = [r2(float(np.nanmedian(arr[:, i])), 3) if arr.shape[0] and np.isfinite(arr[:, i]).any() else None for i in range(HORIZON)]
    p10 = [r2(float(np.nanpercentile(arr[:, i], 10)), 3) if arr.shape[0] and np.isfinite(arr[:, i]).any() else None for i in range(HORIZON)]
    p90 = [r2(float(np.nanpercentile(arr[:, i], 90)), 3) if arr.shape[0] and np.isfinite(arr[:, i]).any() else None for i in range(HORIZON)]
    # по инерции: ход за месяц (среднее трёх последних) с ускорением (среднее трёх последних вторых разностей)
    # ХОД И ЕГО ЗАМЕДЛЕНИЕ — ИЗ ТЕХ ЖЕ ТРЁХМЕСЯЧНЫХ РАЗНОСТЕЙ, ЧТО НА КАРТОЧКАХ (22.09): по
    # месячным вторым разностям одна апрельская просадка давала «ускорение» и парабола улетала
    # в 15·10¹⁴; ход за месяц = ход за 3 месяца / 3, изменение хода за месяц = ускорение / 9.
    cs = charge_stats(d, last_key, div) or {}
    mom = None
    if cs.get("rate3") is not None and cs.get("accel") is not None:
        v = cs["rate3"] / 3.0
        a = min(0.0, cs["accel"] / 9.0)        # ускорение вверх не экстраполируем: «не замедляется» и линейный ход
        path, level, rate = [], now, v
        peak_in, peak_val = None, None
        for i in range(1, HORIZON + 1):
            rate = rate + a
            level = level + rate
            path.append(r2(level, 3))
            if peak_in is None and rate <= 0:
                peak_in, peak_val = i, r2(level, 3)
        mom = {"path": path, "rate_per_month": r2(v, 3), "accel_per_month": r2(a, 4),
               "peak_in_months": peak_in, "peak_value": peak_val,
               "note": ("if the monthly rise keeps fading at its current pace, the volume stops rising in "
                        f"{peak_in} month{'s' if peak_in != 1 else ''}" if peak_in else
                        "the three-month rise is not fading yet: at its current pace the volume keeps rising through the whole horizon"),
               "estimate": True}
    return {"months": months, "now": r2(now, 3), "analog": analog, "median": med, "p10": p10, "p90": p90, "momentum": mom}


def build():
    t0 = time.time()
    D = json.loads((DATA / "latest.json").read_text(encoding="utf-8"))
    F = ((D.get("air") or {}).get("fuel") or {})
    wwv = S.read_pmel(S.LAST / "wwv.txt") if (S.LAST / "wwv.txt").exists() else {}
    t300 = S.read_pmel(S.LAST / "t300.txt") if (S.LAST / "t300.txt").exists() else {}
    if not wwv:
        raise SystemExit("нет wwv.txt в last_good")
    last_w, last_t = sorted(wwv)[-1], (sorted(t300)[-1] if t300 else None)
    cy = int(last_w[:4])
    csw = charge_stats(wwv, last_w, 1e14)
    cst = charge_stats(t300, last_t, 1.0) if t300 else None
    events = []
    for y in EVENT_YEARS:
        ew = next((e for e in (csw or {}).get("events", []) if e["year"] == y), None)
        et = next((e for e in (cst or {}).get("events", []) if e["year"] == y), None) if cst else None
        events.append({"year": y, "strong": y in ANALOG_YEARS,
                       "wwv": _path24(wwv, y, 1e14), "t300": _path24(t300, y, 1.0) if t300 else None,
                       "at_month": {"wwv": ew, "t300": et}})
    this = {"wwv": _path24(wwv, cy, 1e14), "t300": _path24(t300, cy, 1.0) if t300 else None}
    level_higher = sum(1 for e in (csw or {}).get("events", []) if e["value"] is not None and e["value"] > wwv[last_w] / 1e14)
    doc = {"built": datetime.now().strftime("%Y-%m-%d %H:%M"), "assessed_stamp": D.get("stamp"),
           "month": last_w, "t300_month": last_t, "year": cy,
           "now": {"wwv": r2(wwv[last_w] / 1e14, 3), "t300": None if not last_t else r2(t300[last_t], 3),
                   "heat_e22": None if not last_t else r2(t300[last_t] * J_PER_K / 1e22, 2),
                   "share_of_record": F.get("share_of_record"),
                   "level_rank": level_higher + 1, "level_of": len((csw or {}).get("events", [])) + 1},
           "wwv": csw, "t300": cst,
           "events": events, "this": this,
           "trajectory": {"wwv": trajectory(wwv, 1e14, last_w, EVENT_YEARS),
                          "t300": trajectory(t300, 1.0, last_t, EVENT_YEARS) if t300 else None},
           "lead": F.get("lead") or {},
           "j_per_k_e22": r2(J_PER_K / 1e22, 3),
           "note": ("The charge of the event: not only how much warm water is stored under the equator, but whether "
                    "it is still being added. Every El Niño year since 1980 is laid on the same calendar; the tables "
                    "say what each had in this month, whether it was already falling, and when it peaked. The paths "
                    "forward are scenarios by our own arithmetic — the shape of past events added to today's level, "
                    "and today's monthly rise carried on with its own fading — not a forecast from a model.")}
    safeio.write_text(OUT, json.dumps(doc, ensure_ascii=False, allow_nan=False))
    w = csw or {}
    print(f"charge.json: {last_w} volume {doc['now']['wwv']} (rank {doc['now']['level_rank']} of {doc['now']['level_of']}), "
          f"3-mo change {w.get('rate3')} (rank {w.get('rate_rank')}), accel {w.get('accel')}, "
          f"falling by this month {w.get('falling_n')} of {w.get('falling_of')}; {time.time() - t0:.1f} s")
    return doc


def main():
    build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
