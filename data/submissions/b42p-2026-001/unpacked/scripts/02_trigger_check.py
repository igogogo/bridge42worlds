# -*- coding: utf-8 -*-
"""Честность триггера: checked_since геометрический, p = 1/ln(2^32) = 0.0451."""
from common import *
import numpy as np
chk=[]
for f in files_of("data_last"):
    a=np.genfromtxt(f,delimiter=",",skip_header=1,usecols=(4,))
    chk.append(np.atleast_1d(a))
chk=np.concatenate(chk); chk=chk[chk>0]
print(f"n={chk.size}, mean={chk.mean():.3f}, p={1/chk.mean():.5f}, theory={1/np.log(2**32):.5f}")
