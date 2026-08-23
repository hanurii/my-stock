# -*- coding: utf-8 -*-
"""순환이동(circular shift) 순열검정 — 지표의 시간 자기상관 + 결과의 날 군집을 동시에 보존"""
import sys, math, random
sys.path.insert(0, r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
from daytable import build

rows=[r for r in build() if r['nres']>0]
up=[r for r in rows if r['up']]

METRICS=[('dist_ma20','지수 20일선 이격'),('slope_ma20_5','20일선 5일 기울기'),('slope_ma20_10','20일선 10일 기울기'),
 ('ret1','지수 전일 수익률'),('ret5','지수 5일 수익률'),('ret10','지수 10일 수익률'),('ret20','지수 20일 수익률'),
 ('days_since_flip','국면 전환 후 경과일'),('pct_above200','200일선 위 종목 비율'),('pct_nh52','52주 신고가 비율'),
 ('d_above200_5','200일선위 5일 변화'),('d_nh52_5','신고가비율 5일 변화'),('ad','그날 상승종목 비율'),
 ('ad_liq','상승비율(유동성)'),('ad5','상승비율 5일'),('ad10','상승비율 10일'),
 ('n_candidates','그날 후보 수'),('n_entered','그날 진입 수')]

def stat(vals, wl):
    """지표순위 vs 승패 상관 (거래 단위)"""
    n=len(vals)
    order=sorted(range(n), key=lambda i:vals[i]); rank=[0]*n
    for rr,i in enumerate(order): rank[i]=rr
    sx=sxx=sy=syy=sxy=0.0; m=0
    for i,(w,l) in enumerate(wl):
        for _ in range(w+l):
            y=1.0 if _<w else 0.0
            x=float(rank[i]); sx+=x; sxx+=x*x; sy+=y; syy+=y*y; sxy+=x*y; m+=1
    if m<10: return 0.0
    num=sxy-sx*sy/m; dx=math.sqrt(max(1e-12,sxx-sx*sx/m)); dy=math.sqrt(max(1e-12,syy-sy*sy/m))
    return num/(dx*dy)

def circ_test(sub,key):
    days=[r for r in sub if r.get(key) is not None]
    vals=[r[key] for r in days]; wl=[(r['w'],r['l']) for r in days]
    n=len(vals); obs=stat(vals,wl)
    cnt=0; tot=0
    for k in range(1,n):
        sh=vals[k:]+vals[:k]
        s=stat(sh,wl); tot+=1
        if abs(s)>=abs(obs): cnt+=1
    return obs,(cnt+1)/(tot+1),n

for label,sub in (("전체 137일",rows),("상승국면 88일",up)):
    print(f"\n===== {label} · 순환이동 검정 =====")
    out=[]
    for key,name in METRICS:
        o,p,n=circ_test(sub,key); out.append((p,name,o,n))
    out.sort()
    for p,name,o,n in out:
        star='***' if p<0.05/18 else ('*' if p<0.05 else '')
        print(f"{name:20s} r={o:+.3f}  p_circ={p:.3f} {star}")
