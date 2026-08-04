# -*- coding: utf-8 -*-
"""Залипшие чтения ничем не отличаются: тесты против checked_since, dt, prime."""
from common import *
import numpy as np
from scipy import stats as st
rows=[]
for f in files_of("data_seno_soloma","58_E6_C5_14_2C_0C"):
    a=np.genfromtxt(f,delimiter=",",skip_header=1,usecols=(1,2,3,4))
    if a.ndim==1 or a.size==0: continue
    dt_=np.diff(a[:,2],prepend=a[0,2]); rows.append(np.column_stack([a,dt_]))
A=np.vstack(rows); g=A[:,1]; m=(g>0.5)&(g<1.5); A=A[m]; g=g[m]
c=g/LSB; ph=np.abs(((c-47+128)%256)-128)
stuck=ph<=8; norm=ph>24
print(f"stuck {stuck.mean()*100:.1f}%")
for name,x in [("checked_since",A[:,3]),("dt_us",A[:,4]),
               ("prime%256",(A[:,0].astype(np.uint64)%256).astype(float))]:
    u,p=st.mannwhitneyu(x[stuck],x[norm])
    print(f"  {name:14s}: p={p:.3f}")
s=stuck.astype(float)
print(f"  clustering corr(lag1)={np.corrcoef(s[:-1],s[1:])[0,1]:.3f}")
