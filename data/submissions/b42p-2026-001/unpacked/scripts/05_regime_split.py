# -*- coding: utf-8 -*-
"""Шаг решётки по режимам сервера (fix A/B, hz) из config_history.log."""
from common import *
import numpy as np, os, re, collections, datetime as dt
def hist_of(day):
    out=[]
    rx=re.compile(r"(\S+ \S+) \| dur=\S+ \| buf=(\S+) \| fix=(\S+) \| order=\S+ \| hz=(\d+)")
    for line in open(os.path.join(DATA,day,"config_history.log"),encoding="utf-8"):
        m=rx.match(line)
        if m: out.append((dt.datetime.strptime(m.group(1),"%Y-%m-%d %H:%M:%S"),
                          m.group(3),int(m.group(4))))
    return out
grp=collections.defaultdict(list)
for day in ["data_seno","data_soloma","data_seno_soloma"]:
    H=hist_of(day); d0=H[0][0].date()
    for f in files_of(day):
        dev=os.path.basename(f)[:-4]
        if dev not in STATIC_DEVS: continue
        sess=os.path.basename(os.path.dirname(f))
        t=dt.datetime.combine(d0,dt.time(int(sess[:2]),int(sess[2:])))
        cfg=None
        for ht,fx,hz in H:
            if ht<=t: cfg=(fx,hz)
        if cfg:
            a=np.atleast_1d(np.genfromtxt(f,delimiter=",",skip_header=1,usecols=(2,)))
            grp[(dev,)+cfg].append(a)
for key in sorted(grp,key=str):
    g=np.concatenate(grp[key]); g=g[(g>0.5)&(g<1.5)]
    if g.size<2500: continue
    p,P=residual_spectrum(g); i=np.argmax(P)
    print(f"{key[0][-5:]} fix={key[1]} hz={key[2]:4d}: n={g.size:6d} "
          f"step={p[i]:.4f} g ({p[i]/LSB:.0f} LSB) peak/bg={P[i]:.1f}")
