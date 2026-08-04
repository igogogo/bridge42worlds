# -*- coding: utf-8 -*-
"""Вращающиеся: залипание по устройствам/дням; фаза по участкам оборота. -> figures/wheel_phase.png"""
from common import *
import numpy as np, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
for day in ["data_seno","data_soloma","data_seno_soloma"]:
    devs=set(os.path.basename(f)[:-4] for f in files_of(day))-set(STATIC_DEVS)
    for dev in sorted(devs):
        g=load_g(day,dev,0.25,2.2)
        if g.size<20000: continue
        R,z=stick_R(g)
        print(f"{day:17s} {dev[-5:]}: n={g.size:6d} z={z:5.1f}")
g=np.concatenate([load_g("data_seno_soloma",d,0.05,2.3) for d in ROT_CARRIERS])
c=g/LSB; rng=[(0.05,.3),(.3,.6),(.6,.9),(.9,1.2),(1.2,1.5),(1.5,1.8),(1.8,2.1)]
mid=[];zv=[];ph=[]
for lo,hi in rng:
    m=(g>=lo)&(g<hi)
    Z=np.mean(np.exp(2j*np.pi*(c[m]-47)/256))
    mid.append((lo+hi)/2); zv.append(abs(Z)*np.sqrt(m.sum()))
    ph.append((np.angle(Z)/(2*np.pi)*256+47)%256)
fig,axes=plt.subplots(1,2,figsize=(11,3.2))
axes[0].bar(mid,zv,width=0.22); axes[0].set_xlabel("|a|, g"); axes[0].set_ylabel("z")
axes[1].plot(mid,ph,"o-"); axes[1].axhline(47,ls="--",lw=0.8,color="k")
axes[1].set_ylim(0,256); axes[1].set_xlabel("|a|, g"); axes[1].set_ylabel("phase, LSB")
fig.savefig(os.path.join(FIG,"wheel_phase.png"),dpi=125,bbox_inches="tight")
print("ok -> figures/wheel_phase.png")
