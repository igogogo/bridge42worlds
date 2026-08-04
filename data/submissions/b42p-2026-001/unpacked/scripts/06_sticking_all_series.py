# -*- coding: utf-8 -*-
"""Главная таблица: залипание (256/47) по всем сериям; серии без колеса - контроль."""
from common import *
import numpy as np
WHEEL={"data_delta":"+","data_uno":"+","data_seno":"+","data_soloma":"+",
       "data_seno_soloma":"+","data_last":"+","data_123":"-","data_solo":"-",
       "data_FM0":"-","data_duo_woD":"-","data_1234":"-"}
for s in WHEEL:
    for dev in STATIC_DEVS:
        g=load_g(s,dev,0.5,1.5)
        if g.size<3000: continue
        R,z=stick_R(g)
        print(f"{s:17s} wheel{WHEEL[s]} {dev[-5:]}: n={g.size:6d} R={R:.3f} z={z:6.1f}")
