# -*- coding: utf-8 -*-
"""Независимая перепроверка выводов сборщика радианс по его таблицам первого слоя.

Владелец 08.09: «а ты перепроверяешь их выводы? мы же берём их данные и сами тоже на них
смотрим». Здесь считается заново, без их signals.py, из cris_daily_v2.csv (гистограмма окна
900 см⁻¹ по 2 K) и sst_daily.csv (OISST по боксам):
  • доля глубокой конвекции (BT900 < 235 K) и доля ясного неба (BT900 > SST − 4 K);
  • G_clear = SST(K) − BT900 на p90 и на p99 (проверка на остаточные облака);
  • «сырой Уокер» = BT900(Niño 3.4) − BT900(тёплый бассейн).
Всё по окну 1 июля – 6 сентября, 2026 против 2023/2024/2025, день (A) и ночь (D).
Печатает таблицу и расхождения с утверждениями документа сборщика. Только чтение, ничего не пишет.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

RAD = Path(r"C:\CL\radiance")
sys.path.insert(0, str(RAD))
try:
    import config as C                                          # noqa: E402
    H0 = float(getattr(C, "HIST_MIN", getattr(C, "HIST_LO", 180.0)))
    HW = float(getattr(C, "HIST_BIN", getattr(C, "HIST_STEP", 2.0)))
except Exception:                                                # noqa: BLE001
    H0, HW = 180.0, 2.0
CONV_T, CLEAR_DT = 235.0, 4.0

sst = {}
for r in csv.DictReader(open(RAD / "data" / "sst_daily.csv", encoding="utf-8")):
    try:
        sst[(r["date"], r["box"])] = float(r["sst"]) + 273.15
    except ValueError:
        pass

rows = defaultdict(list)          # (year, box, node) -> list of dicts
for r in csv.DictReader(open(RAD / "data" / "cris_daily_v2.csv", encoding="utf-8")):
    h = np.array([float(x) for x in r["hist900"].split(";")], float)
    n = h.sum()
    if n < 100:
        continue
    edges = H0 + HW * np.arange(len(h) + 1)
    centers = edges[:-1] + HW / 2
    cdf = np.cumsum(h) / n
    def pct(q):
        i = int(np.searchsorted(cdf, q))
        return float(centers[min(i, len(centers) - 1)])
    T = sst.get((r["date"], r["box"]))
    deep = float(h[centers < CONV_T].sum() / n)
    clear = float(h[centers > T - CLEAR_DT].sum() / n) if T else None
    rows[(r["date"][:4], r["box"], r["node"])].append({
        "deep": deep, "clear": clear, "bt_mean": float(r["bt900_mean"]),
        "g_p90": (T - pct(0.90)) if T else None, "g_p99": (T - pct(0.99)) if T else None})


def mean(key, y, box, node):
    v = [x[key] for x in rows[(y, box, node)] if x.get(key) is not None]
    return (float(np.mean(v)), len(v)) if v else (None, 0)


years = ["2023", "2024", "2025", "2026"]
print(f"гистограмма: начало {H0} K, шаг {HW} K; строк с данными: {sum(len(v) for v in rows.values())}")
print("\n%-10s %-5s %-6s %8s %8s %8s %8s %6s" % ("показатель", "бокс", "узел", *years, "n26"))
for box in ("nino34", "warmpool"):
    for node in ("A", "D"):
        for key, lab in (("deep", "conv %"), ("clear", "clear %"), ("g_p90", "G_clr p90"), ("g_p99", "G_clr p99")):
            vals = [mean(key, y, box, node) for y in years]
            f = (lambda v: "·" if v[0] is None else (f"{v[0]*100:8.1f}" if key in ("deep", "clear") else f"{v[0]:8.2f}"))
            print("%-10s %-5s %-6s %s %s %s %s %6d" % (lab, box[:5], node, f(vals[0]), f(vals[1]), f(vals[2]), f(vals[3]), vals[3][1]))
print("\nсырой Уокер, K (BT900 Niño 3.4 − тёплый бассейн), среднее по окну:")
for node in ("A", "D"):
    out = []
    for y in years:
        a = mean("bt_mean", y, "nino34", node)[0]; b = mean("bt_mean", y, "warmpool", node)[0]
        out.append("·" if a is None or b is None else f"{a-b:+6.1f}")
    print(f"  узел {node}: " + "  ".join(f"{y} {v}" for y, v in zip(years, out)))

print("\nутверждения документа сборщика (08.09) — проверка:")
d26, _ = mean("deep", "2026", "nino34", "A"); c26, _ = mean("clear", "2026", "nino34", "A")
g26, _ = mean("g_p90", "2026", "nino34", "A"); g99, _ = mean("g_p99", "2026", "nino34", "A")
an = [mean("g_p90", y, "nino34", "A")[0] for y in years[:3]]; an99 = [mean("g_p99", y, "nino34", "A")[0] for y in years[:3]]
print(f"  конвекция над Niño 3.4 днём: они 7.4 %, мы {d26*100:.1f} %")
print(f"  ясное небо над Niño 3.4 днём: они 5.8 %, мы {c26*100:.1f} % (аналоги {', '.join(f'{mean(chr(99)+'lear', y, 'nino34', 'A')[0]*100:.1f}' for y in years[:3])})")
print(f"  G_clear p90 над Niño 3.4 днём: они +2.6…+2.8 K к аналогам, мы {g26 - np.mean([v for v in an if v is not None]):+.2f} K "
      f"(2026 {g26:.2f} K; аналоги {', '.join(f'{v:.2f}' for v in an if v is not None)})")
print(f"  G_clear p99 над Niño 3.4 днём: они +1.4 K, мы {g99 - np.mean([v for v in an99 if v is not None]):+.2f} K")
wp26, _ = mean("g_p90", "2026", "warmpool", "A"); wpan = [mean("g_p90", y, "warmpool", "A")[0] for y in years[:3]]
print(f"  G_clear p90 над тёплым бассейном днём: они −3.0…−3.1 K, мы {wp26 - np.mean([v for v in wpan if v is not None]):+.2f} K")
wc = [mean("clear", y, "warmpool", "A")[0] for y in years]
print(f"  ясных сцен над тёплым бассейном днём, %: " + ", ".join(f"{y} {v*100:.1f}" for y, v in zip(years, wc) if v is not None) + "  (они: 3.0 против 0.0–0.2)")
