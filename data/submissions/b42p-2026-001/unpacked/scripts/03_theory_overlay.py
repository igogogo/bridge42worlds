# -*- coding: utf-8 -*-
"""Распределение |a| вращающихся против классической теории. -> figures/theory_overlay.png"""
from common import *
import numpy as np, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
def theory_pdf(a,ac):
    u=(a**2-ac**2-1)/(2*ac); p=np.zeros_like(a); m=np.abs(u)<0.9999
    p[m]=a[m]/(np.pi*ac*np.sqrt(1-u[m]**2)); return p
fig,axes=plt.subplots(1,2,figsize=(13,4))
for ax,dev,ttl in [(axes[0],"58_E6_C5_14_36_D8","36_D8 (носитель)"),
                   (axes[1],"58_E6_C5_15_86_50","86_50 (чистый)")]:
    gs=[]
    for f in files_of("data_seno_soloma",dev):
        a=np.atleast_1d(np.genfromtxt(f,delimiter=",",skip_header=1,usecols=(2,)))
        if a.size>500 and a[a>-0.5].std()>0.35: gs.append(a)
    g=np.concatenate(gs); g=g[(g>0.02)&(g<2.5)]
    lo,hi=np.percentile(g,[0.5,99.5]); ac=(hi+lo)/2 if (hi+lo)/2>1 else (hi-lo)/2
    h,e=np.histogram(g,bins=np.arange(0,2.4,0.004),density=True)
    ax.plot((e[:-1]+e[1:])/2,h,lw=0.6,label=f"data n={g.size}")
    aa=np.linspace(0.01,2.4,3000); pt=theory_pdf(aa,ac); st=aa[1]-aa[0]
    ax.plot(aa,gaussian_filter1d(pt,0.08/st),lw=1.6,label=f"theory a_c={ac:.2f} + noise")
    ax.plot(aa,pt,ls="--",lw=1,alpha=0.6)
    ax.set_xlim(0,2.4); ax.set_ylim(0,2); ax.legend(fontsize=8); ax.set_title(ttl)
fig.savefig(os.path.join(FIG,"theory_overlay.png"),dpi=125,bbox_inches="tight")
print("ok -> figures/theory_overlay.png")
