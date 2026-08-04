# -*- coding: utf-8 -*-
"""Свёрнутые профили (счёты-47) mod 256. -> figures/fold_profiles.png"""
from common import *
import numpy as np, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
cases=[("data_seno_soloma","58_E6_C5_14_2C_0C","CARRIER 2C_0C 11.06"),
       ("data_seno_soloma","58_E6_C5_14_64_E8","64_E8 11.06"),
       ("data_1234","58_E6_C5_14_2C_0C","2C_0C 27.06 NO WHEEL")]
fig,axes=plt.subplots(1,3,figsize=(13,3.2),sharey=True)
for ax,(s,dev,ttl) in zip(axes,cases):
    g=load_g(s,dev,0.5,1.5); c=g/LSB
    h,e=np.histogram((c-47)%256,bins=64,range=(0,256))
    ax.bar((e[:-1]+e[1:])/2,h/h.mean(),width=4)
    ax.axhline(1,color="k",lw=0.7,ls="--"); ax.set_title(f"{ttl} (n={g.size})",fontsize=9)
fig.savefig(os.path.join(FIG,"fold_profiles.png"),dpi=125,bbox_inches="tight")
print("ok -> figures/fold_profiles.png")
