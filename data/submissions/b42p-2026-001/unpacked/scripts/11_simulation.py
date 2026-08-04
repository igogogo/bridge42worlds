# -*- coding: utf-8 -*-
"""Модель: квантование + залипание младшего байта. -> figures/simulation.png"""
from common import *
import numpy as np, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
rng=np.random.default_rng(3); N=80000
def sim(tilt,stick_frac=0.1):
    th=np.radians(tilt)
    axs=np.sin(th)+rng.normal(0,.045,N); ays=.12*np.sin(th)+rng.normal(0,.045,N)
    azs=np.cos(th)+rng.normal(0,.045,N)
    def q(v):
        c=np.round(v/LSB)
        stm=rng.random(N)<stick_frac
        c[stm]=np.floor(c[stm]/256)*256+47
        return c*LSB
    return np.sqrt(q(axs)**2+q(ays)**2+q(azs)**2)
fig,axes=plt.subplots(1,2,figsize=(11,3))
for ax_,tilt,ttl in [(axes[0],4,"flat mount: bright comb"),(axes[1],38,"38 deg tilt: smeared")]:
    ax_.hist(sim(tilt),bins=np.arange(.6,1.4,.005))
    ax_.set_title(ttl,fontsize=9)
fig.savefig(os.path.join(FIG,"simulation.png"),dpi=125,bbox_inches="tight")
print("ok -> figures/simulation.png")
