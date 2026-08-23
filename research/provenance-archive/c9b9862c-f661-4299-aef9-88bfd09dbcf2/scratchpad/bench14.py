# -*- coding: utf-8 -*-
import numpy as np, time, os
from pathlib import Path
PM=Path(r"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/aff259ca-1adc-48bc-b0c7-37693e4ef158/scratchpad/passmatrix.npz")
print("npz 파일 크기", round(PM.stat().st_size/1e6,1),"MB")
t0=time.time(); z=np.load(PM, allow_pickle=True)
tot=0
arrs={}
for k in z.files:
    a=z[k]; arrs[k]=a; tot+=a.nbytes
print(f"전체 배열 압축해제 {time.time()-t0:.1f}s, 메모리 {tot/1e6:.0f} MB")
need=("dates","codes","idx","open_r","hi_r","lo_r","vol","all_pass","eligible","present","rs","crit_bits","nhist")
t0=time.time(); z2=np.load(PM,allow_pickle=True)
sub=sum(z2[k].nbytes for k in need)
print(f"검출기·집계에 필요한 것만 {time.time()-t0:.1f}s, {sub/1e6:.0f} MB")
