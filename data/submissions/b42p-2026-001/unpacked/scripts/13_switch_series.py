# -*- coding: utf-8 -*-
"""Реальные посессионные картинки: «вот эффект — вот переключили — вот его нет».
Ряд 1: data_seno, статик 64_E8, сессии подряд — включение эффекта на старте колеса (16:56).
Ряд 2: data_soloma, статик 64_E8 — смена мелкого шага на границе команды сервера (09:38→09:40).
Выход: figures/switch_series.png"""
from common import *
import numpy as np, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

def fold_profile(g):
    c = g / LSB
    h, e = np.histogram((c - 47) % 256, bins=24, range=(0, 256))
    return (e[:-1] + e[1:]) / 2, h / max(1e-9, h.mean())

def session_g(day, dev, sess):
    for f in files_of(day, dev):
        if os.path.basename(os.path.dirname(f)) == sess:
            a = np.atleast_1d(np.genfromtxt(f, delimiter=",", skip_header=1, usecols=(2,)))
            return a[(a > 0.5) & (a < 1.5)]
    return np.array([])

DEV = "58_E6_C5_14_64_E8"

# ---- Ряд 1: seno, включение
SESS1 = ["1654", "1655", "1656", "1657", "1658", "1659"]
fig, axes = plt.subplots(2, 6, figsize=(16, 6))
for j, sess in enumerate(SESS1):
    ax = axes[0, j]
    g = session_g("data_seno", DEV, sess)
    if g.size > 800:
        x, p = fold_profile(g)
        R, z = stick_R(g)
        ax.bar(x, p, width=9, color="#A83E3E" if z > 4 else "#2F6B8F")
        ax.set_title(f"{sess[:2]}:{sess[2:]}\n{'ЭФФЕКТ z=%.0f' % z if z > 4 else 'нет (z=%.1f)' % z}",
                     fontsize=9, color="#A83E3E" if z > 4 else "#444")
    else:
        ax.set_title(f"{sess[:2]}:{sess[2:]}\nмало данных", fontsize=9)
    ax.axhline(1, color="k", lw=0.5, ls="--")
    ax.set_ylim(0, 3.4); ax.set_xticks([]); ax.set_yticks([0, 1, 2, 3])
axes[0, 0].set_ylabel("data_seno 09.06\n64_E8, свёртка mod 256", fontsize=9)
fig.text(0.42,0.905,"до  |  СТАРТ КОЛЕСА 16:56  |  после",fontsize=11,color="#A83E3E",ha="center")

# ---- Ряд 2: soloma, смена мелкого шага — агрегаты до/после команды 09:39
def agg(day,dev,lo,hi):
    gs=[]
    for f in files_of(day,dev):
        sess=os.path.basename(os.path.dirname(f))
        if lo<=sess<=hi:
            a=np.atleast_1d(np.genfromtxt(f,delimiter=",",skip_header=1,usecols=(2,)))
            gs.append(a[(a>0.5)&(a<1.5)])
    return np.concatenate(gs) if gs else np.array([])
g_before=agg("data_soloma",DEV,"0920","0931")
g_after =agg("data_soloma",DEV,"0940","0959")
for j in range(6): axes[1,j].axis("off")
ax=fig.add_subplot(2,3,4); ax2=fig.add_subplot(2,3,5); ax3=fig.add_subplot(2,3,6)
for a_,g_,ttl,cl in [(ax,g_before,"ДО команды: доминирует шаг 0.0128","#A96F26"),
                     (ax2,g_after,"ПОСЛЕ: доминирует шаг 0.0083","#3E7A52")]:
    p,P=residual_spectrum(g_)
    a_.plot(p,P,lw=1,color=cl)
    a_.axvline(0.0128,color="#A96F26",ls="--",lw=0.8)
    a_.axvline(0.0083,color="#3E7A52",ls="--",lw=0.8)
    a_.set_xlim(0.004,0.03); a_.set_title(ttl,fontsize=9); a_.set_yticks([])
    a_.set_xlabel("период, g")
p1,P1=residual_spectrum(g_before); p2,P2=residual_spectrum(g_after)
ax3.plot(p1,P1,lw=1,color="#A96F26",label="до")
ax3.plot(p2,P2,lw=1,color="#3E7A52",label="после")
ax3.axvline(0.0128,color="#A96F26",ls="--",lw=0.8); ax3.axvline(0.0083,color="#3E7A52",ls="--",lw=0.8)
ax3.set_xlim(0.004,0.03); ax3.set_yticks([]); ax3.legend(fontsize=8)
ax3.set_title("наложение: пик переехал (команда 09:39)",fontsize=9)
ax3.set_xlabel("период, g")
fig.suptitle("Реальные пакеты (сессии) вокруг переключений: эффект появляется и меняется в конкретную минуту",
             fontsize=12)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "switch_series.png"), dpi=120, bbox_inches="tight")
print("ok -> figures/switch_series.png")
