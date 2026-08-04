# -*- coding: utf-8 -*-
"""Точность шага (бутстреп): 256 или 246(=0.030g)?"""
from common import *
import numpy as np
g=load_g("data_seno_soloma","58_E6_C5_14_2C_0C",0.5,1.5); c=g/LSB
rng=np.random.default_rng(5); qs=np.linspace(250,262,4801); best=[]
for b in range(40):
    cb=rng.choice(c,c.size,replace=True)[::4]
    R=np.abs(np.exp(2j*np.pi*cb[:,None]/qs[None,:]).mean(axis=0))
    best.append(qs[np.argmax(R)])
b=np.array(best)
print(f"step={b.mean():.3f}+-{b.std():.3f} LSB; 256 at {abs(b.mean()-256)/b.std():.1f} sigma; "
      f"246 (=0.030g) at {abs(b.mean()-246)/b.std():.0f} sigma - excluded")
