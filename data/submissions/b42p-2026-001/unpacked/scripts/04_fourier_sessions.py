# -*- coding: utf-8 -*-
"""Фурье остатка гистограммы по каждой сессии (статики, 3 дня). -> figures/fourier_*.png"""
from common import *
import numpy as np, os, collections
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
for day in ["data_seno","data_soloma","data_seno_soloma"]:
    per=collections.defaultdict(dict)
    for f in files_of(day):
        dev=os.path.basename(f)[:-4]
        if dev not in STATIC_DEVS: continue
        a=np.atleast_1d(np.genfromtxt(f,delimiter=",",skip_header=1,usecols=(2,)))
        per[dev][os.path.basename(os.path.dirname(f))]=a
    fig,axes=plt.subplots(1,2,figsize=(14,4))
    for ax,dev in zip(axes,STATIC_DEVS):
        sess=sorted(per[dev])[2:-2]
        M=[];periods=None
        for s in sess:
            g=per[dev][s]; g=g[(g>0.5)&(g<1.5)]
            if g.size<1200: M.append(None); continue
            p,P=residual_spectrum(g)
            if periods is None: periods=p
            M.append(P)
        img=np.full((len(periods),len(M)),np.nan)
        for j,P in enumerate(M):
            if P is not None: img[:,j]=P
        idx=np.argsort(periods)
        pc=ax.pcolormesh(np.arange(len(M)+1),np.append(periods[idx],periods[idx][-1]+1e-4),
                         img[idx,:],cmap="magma",vmin=0,vmax=15)
        ax.set_ylim(0.004,0.04); ax.set_title(f"{day} {dev[-5:]}")
        ax.set_xticks(np.arange(len(sess))+0.5); ax.set_xticklabels(sess,rotation=90,fontsize=6)
        plt.colorbar(pc,ax=ax)
    fig.savefig(os.path.join(FIG,"fourier_"+day.replace("data_","")+".png"),dpi=125,bbox_inches="tight")
    plt.close(); print("ok",day)
