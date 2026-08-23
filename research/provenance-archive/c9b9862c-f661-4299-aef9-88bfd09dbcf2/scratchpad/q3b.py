# -*- coding: utf-8 -*-
from engine import *
from statistics import mean, median
def first_touch(p,l):
    for k,b in enumerate(p["path"]):
        if b["h"]>=l: return k
    return None
def first_stop(p,l=-10.0):
    for k,b in enumerate(p["path"]):
        if b["l"]<=l: return k
    return None
winners=[]
for p in PATHS:
    t=first_touch(p,20.0); s=first_stop(p)
    if t is None or (s is not None and s<=t): continue
    winners.append((p,t))
tot=len(winners)
print("승자 표본", tot)
mnc=[]; retrc=[]; retrl=[]
for p,t in winners:
    seg=p["path"][:t+1]
    mnc.append(min(b["c"] for b in seg))
    pk=-1e9; w=0.0
    for b in seg:
        pk=max(pk,b["c"]); w=min(w,b["c"]-pk)
    retrc.append(w)
    pk=-1e9; w2=0.0
    for i,b in enumerate(seg):
        if i>0: w2=min(w2, b["l"]-pk)
        pk=max(pk,b["h"])
    retrl.append(w2)
def show(lbl,v):
    print(f"  {lbl}: 중앙 {median(v):.1f}  Q1 {q(v,.25):.1f}  Q3 {q(v,.75):.1f}  P10 {q(v,.10):.1f}  최악 {min(v):.1f}")
show("최저 '종가' (진입가 대비 %)", mnc)
show("종가기준 최대 되돌림(%p)", retrc)
show("전일고점→당일저가 최대 되돌림(%p)", retrl)
for c in (-3,-5,-8):
    n=sum(1 for v in mnc if v<=c); print(f"  종가가 {c}% 아래로 간 승자 {n}/{tot} ({n/tot*100:.0f}%)")
for c in (-5,-8,-10,-12):
    n=sum(1 for v in retrc if v<=c); print(f"  종가기준 고점대비 {abs(c)}%p+ 되돌린 승자 {n}/{tot} ({n/tot*100:.0f}%)")
# +10% 를 먼저 찍고 +20 가는 경우, +10 이후 얼마나 되돌리나 (사용자가 익절 유혹 느끼는 지점)
print("\n[+8~+12% 구간을 지난 승자가 그 뒤 겪는 되돌림]")
for lvl in (8.0,10.0,12.0,15.0):
    sub=[]
    for p,t in winners:
        k=first_touch(p,lvl)
        if k is None or k>t: continue
        seg=p["path"][k:t+1]
        pk=lvl; w=0.0
        for b in seg: pk=max(pk,b["c"]); w=min(w,b["c"]-pk)
        sub.append((t-k, w, min(b["c"] for b in seg)))
    d=[x[0] for x in sub]; ww=[x[1] for x in sub]; lc=[x[2] for x in sub]
    print(f"  +{lvl:.0f}% 통과 승자 {len(sub)}건: 거기서 +20까지 중앙 {median(d):.0f}일(Q3 {q(d,.75):.0f}), "
          f"그 사이 종가되돌림 중앙 {median(ww):.1f}%p(P10 {q(ww,.10):.1f}), 최저종가 중앙 +{median(lc):.1f}%")
