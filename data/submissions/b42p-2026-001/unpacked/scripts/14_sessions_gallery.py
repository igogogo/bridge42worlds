# -*- coding: utf-8 -*-
"""Галерея РЕАЛЬНЫХ гистограмм по сессиям: гребёнка видна на сырых данных.
Ряд 1: data_seno, 64_E8 — включение на старте колеса (16:56) и смена fix A→B (17:00).
Ряд 2: data_soloma, 64_E8 — вокруг команды 09:39 (fix B→A).
Ряд 3: data_seno_soloma, 2C_0C — режим не менялся (A весь день): гребёнка стоит в каждой сессии.
Выход: figures/sessions_gallery.png"""
from common import *
import numpy as np, os, re, datetime as dt
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

def fixmode_of(day):
    out = []
    rx = re.compile(r"(\S+ \S+) \| dur=\S+ \| buf=\S+ \| fix=(\S+) \| order=\S+ \| hz=(\d+)")
    for line in open(os.path.join(DATA, day, "config_history.log"), encoding="utf-8"):
        m = rx.match(line)
        if m:
            out.append((dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"),
                        m.group(2), int(m.group(3))))
    def q(sess):
        t = dt.datetime.combine(out[0][0].date(), dt.time(int(sess[:2]), int(sess[2:])))
        cur = None
        for ht, fx, hz in out:
            if ht <= t:
                cur = (fx, hz)
        return cur or ("?", 0)
    return q

def session_g(day, dev, sess):
    for f in files_of(day, dev):
        if os.path.basename(os.path.dirname(f)) == sess:
            a = np.atleast_1d(np.genfromtxt(f, delimiter=",", skip_header=1, usecols=(2,)))
            return a[(a > 0.5) & (a < 1.5)]
    return np.array([])

ROWS = [
    ("data_seno", "58_E6_C5_14_64_E8",
     ["1654", "1655", "1656", "1657", "1658", "1659", "1700", "1713"],
     "data_seno 09.06 · 64_E8 — колесо стартует в 16:56; смена fix A→B в 17:00"),
    ("data_soloma", "58_E6_C5_14_64_E8",
     ["0922", "0925", "0926", "0927", "0940", "0941", "0942", "0943"],
     "data_soloma 10.06 · 64_E8 — команда сервера 09:39 (fix B→A) между 4-й и 5-й колонками"),
    ("data_seno_soloma", "58_E6_C5_14_2C_0C",
     ["1701", "1703", "1705", "1708", "1710", "1712", "1715", "1718"],
     "data_seno_soloma 11.06 · 2C_0C — режим не менялся (A весь день): гребёнка в каждой сессии"),
]

fig, axes = plt.subplots(3, 8, figsize=(18, 9))
for r, (day, dev, sess_list, title) in enumerate(ROWS):
    q = fixmode_of(day)
    for j, sess in enumerate(sess_list):
        ax = axes[r, j]
        g = session_g(day, dev, sess)
        fx, hz = q(sess)
        if g.size > 800:
            mu = np.median(g)
            bins = np.arange(mu - 0.11, mu + 0.11, 0.002)
            h, e = np.histogram(g, bins=bins)
            R, z = stick_R(g)
            col = "#A83E3E" if z > 4 else "#2F6B8F"
            ax.bar((e[:-1] + e[1:]) / 2, h, width=0.002, color=col, alpha=0.9)
            ax.set_title(f"{sess[:2]}:{sess[2:]} · fix={fx}\nz={z:.0f}"
                         + (" ЕСТЬ" if z > 4 else " нет"),
                         fontsize=8, color=col)
        else:
            ax.set_title(f"{sess[:2]}:{sess[2:]} · fix={fx}\nмало данных", fontsize=8)
        ax.set_xticks([]); ax.set_yticks([])
    axes[r, 0].set_ylabel(title.split(chr(0x2014))[0].strip(), fontsize=8)
fig.suptitle("РЕАЛЬНЫЕ гистограммы g по сессиям (бин 0.002): красное = гребёнка есть (z>4), синее = нет",
             fontsize=13)
fig.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig(os.path.join(FIG, "sessions_gallery.png"), dpi=120, bbox_inches="tight")
print("ok -> figures/sessions_gallery.png")
