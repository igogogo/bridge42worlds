# -*- coding: utf-8 -*-
"""Каталог: по каждой серии и устройству - n, среднее, разброс."""
from common import *
import numpy as np, os
series=[d for d in sorted(os.listdir(DATA)) if d.startswith("data_")]
print(f"{'серия':16s} {'устройство':22s} {'n':>7s} {'mean':>7s} {'std':>6s} {'p05':>6s} {'p95':>6s}")
for s in series:
    devs=set(os.path.basename(f)[:-4] for f in files_of(s))
    for dev in sorted(devs):
        g=load_g(s,dev)
        if g.size<1000: continue
        print(f"{s:16s} {dev:22s} {g.size:7d} {g.mean():7.4f} {g.std():6.4f} "
              f"{np.percentile(g,5):6.3f} {np.percentile(g,95):6.3f}")
