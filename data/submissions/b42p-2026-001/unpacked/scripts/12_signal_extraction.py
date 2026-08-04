# -*- coding: utf-8 -*-
"""Раскадровка «как сигнал достаётся из шума» по трём дням-источникам.
Колонки: (1) гистограмма + гауссова модель шума; (2) остаток после вычитания
гладкой формы; (3) свёрнутый профиль mod 256 против полосы «если бы ничего
не было»; (4) таймлайн R по сессиям. Выход: figures/signal_extraction.png"""
from common import *
import numpy as np, os, collections
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats as st

DAYS = [("data_seno", "09.06 · seno"),
        ("data_soloma", "10.06 · soloma"),
        ("data_seno_soloma", "11.06 · seno_soloma")]
rng = np.random.default_rng(7)

fig, axes = plt.subplots(3, 4, figsize=(16, 9.5))
for row, (day, label) in enumerate(DAYS):
    # носитель дня = статик с бОльшим R
    stats = []
    for dev in STATIC_DEVS:
        g = load_g(day, dev, 0.5, 1.5)
        stats.append((stick_R(g)[0], dev, g))
    stats.sort(reverse=True)
    Rbest, dev, g = stats[0]
    c = g / LSB

    # (1) гистограмма + гаусс
    ax = axes[row, 0]
    h, e = np.histogram(g, bins=200, density=True)
    ax.plot((e[:-1]+e[1:])/2, h, lw=0.7)
    xs = np.linspace(g.min(), g.max(), 300)
    ax.plot(xs, st.norm.pdf(xs, g.mean(), g.std()), "r--", lw=1,
            label="если только шум (гаусс)")
    ax.set_title(f"{label}\n{dev[-5:]}: данные vs просто шум", fontsize=9)
    ax.legend(fontsize=7)

    # (2) остаток после гладкой формы
    ax = axes[row, 1]
    step = 0.001
    bins = np.arange(g.mean()-0.3, g.mean()+0.3, step)
    hh, _ = np.histogram(g, bins=bins)
    k = 25
    sm = np.convolve(hh, np.ones(k)/k, mode="same")
    ax.plot(bins[:-1], hh - sm, lw=0.6)
    ax.axhline(0, color="k", lw=0.5)
    ax.set_title("минус гладкая форма = остаток\n(тут живёт сигнал, если есть)", fontsize=9)

    # (3) свёрнутый профиль против нуль-полосы
    ax = axes[row, 2]
    prof, e2 = np.histogram((c-47) % 256, bins=32, range=(0, 256))
    prof = prof / prof.mean()
    # нуль-полоса: 30 суррогатов «непрерывного мира»
    band = []
    hk = 1.06*g.std()*g.size**(-1/5)
    for _ in range(30):
        gs = rng.choice(g, g.size) + rng.normal(0, hk, g.size)
        p2, _ = np.histogram((gs/LSB-47) % 256, bins=32, range=(0, 256))
        band.append(p2/p2.mean())
    band = np.array(band)
    lo, hi = np.percentile(band, [2.5, 97.5], axis=0)
    xc = (e2[:-1]+e2[1:])/2
    ax.fill_between(xc, lo, hi, color="gray", alpha=0.4,
                    label="так выглядело бы «ничего»")
    ax.plot(xc, prof, "o-", ms=3, lw=1, color="#A83E3E", label="данные")
    ax.set_ylim(0.7, max(1.4, prof.max()*1.08))
    R, z = stick_R(g)
    ax.set_title(f"свёртка mod 256: сигнал {'ЕСТЬ' if z>4 else 'НЕТ'} (z={z:.0f})",
                 fontsize=9)
    ax.legend(fontsize=7)

    # (4) таймлайн R по сессиям (оба статика)
    ax = axes[row, 3]
    for dev2, cl in zip(STATIC_DEVS, ["#2F6B8F", "#A96F26"]):
        per = collections.defaultdict(list)
        for f in files_of(day, dev2):
            sess = os.path.basename(os.path.dirname(f))
            a = np.atleast_1d(np.genfromtxt(f, delimiter=",", skip_header=1, usecols=(2,)))
            per[sess].append(a)
        xs2, ys2 = [], []
        for sess in sorted(per):
            gg = np.concatenate(per[sess]); gg = gg[(gg > 0.5) & (gg < 1.5)]
            if gg.size < 1200: continue
            xs2.append(sess); ys2.append(stick_R(gg)[0])
        ax.plot(range(len(xs2)), ys2, "o-", ms=3, lw=0.8, color=cl, label=dev2[-5:])
        ax.set_xticks(range(len(xs2)))
        ax.set_xticklabels(xs2, rotation=90, fontsize=5)
    ax.axhline(0.05, color="gray", lw=0.6, ls="--")
    ax.set_ylim(0, 0.65)
    ax.set_title("уровень сигнала по сессиям\n(выше пунктира = виден)", fontsize=9)
    ax.legend(fontsize=7)

fig.suptitle("Сигнал из шума, шаг за шагом: данные → минус модель → остаток → свёртка против «ничего» → динамика по сессиям",
             fontsize=12)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "signal_extraction.png"), dpi=120, bbox_inches="tight")
print("ok -> figures/signal_extraction.png")
