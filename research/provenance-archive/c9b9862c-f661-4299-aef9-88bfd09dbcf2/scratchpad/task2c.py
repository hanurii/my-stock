# -*- coding: utf-8 -*-
"""상위 후보 잣대의 견고성: 에피소드 구성 · 전후반 분할 · 상호 중복"""
import sys, math
sys.path.insert(0, r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
from daytable import build
from collections import defaultdict, Counter

rows=[r for r in build() if r['nres']>0]
lab=[];prev=None;k=0
for r in rows:
    if prev is None or r['days_since_flip']<prev: k+=1
    lab.append(k); prev=r['days_since_flip']
for r,l in zip(rows,lab): r['ep']=l

up=[r for r in rows if r['up']]
KEYS=[('ret10','지수 10일 수익률'),('pct_nh52','52주 신고가 비율'),('pct_above200','200일선 위 비율'),
      ('ad10','상승비율 10일'),('slope_ma20_5','20일선 5일 기울기'),('days_since_flip','국면 경과일'),
      ('dist_ma20','20일선 이격'),('slope_ma20_10','20일선 10일 기울기')]

def q4mask(sub,key):
    vals=sorted(r[key] for r in sub)
    cut=vals[int(len(vals)*0.75)]
    return set(r['scan_date'] for r in sub if r[key]>=cut), cut

print("=== 상승국면 Q4(가장 많이 달린 4분위) 날들의 에피소드 구성 ===")
for key,name in KEYS:
    m,cut=q4mask(up,key)
    g=[r for r in up if r['scan_date'] in m]
    c=Counter(r['ep'] for r in g)
    w=sum(r['w'] for r in g); l=sum(r['l'] for r in g)
    print(f"{name:18s} cut>={cut:6.2f} 날{len(g):3d} 거래{w+l:3d} 승률{100*w/(w+l):5.1f}% 에피소드 {dict(sorted(c.items()))}")

print("\n=== 전후반 분할 (진입일 2026-03-25 기준) — 상승국면, Q4 vs 나머지 ===")
SPL='2026-03-25'
for key,name in KEYS:
    m,cut=q4mask(up,key)
    out=[]
    for half,sel in (('전반', lambda r: r['entry_date']<SPL), ('후반', lambda r: r['entry_date']>=SPL)):
        gq=[r for r in up if sel(r) and r['scan_date'] in m]
        gr=[r for r in up if sel(r) and r['scan_date'] not in m]
        wq=sum(r['w'] for r in gq); lq=sum(r['l'] for r in gq)
        wr=sum(r['w'] for r in gr); lr=sum(r['l'] for r in gr)
        a=100*wq/(wq+lq) if wq+lq else float('nan')
        b=100*wr/(wr+lr) if wr+lr else float('nan')
        out.append(f"{half}: Q4 {a:5.1f}%({wq+lq:3d}) vs 나머지 {b:5.1f}%({wr+lr:3d}) 차 {a-b:+6.1f}%p")
    print(f"{name:18s} " + " | ".join(out))

print("\n=== 에피소드별 부호검정 (상승국면, Q4 승률 < 나머지 승률?) ===")
for key,name in KEYS:
    m,_=q4mask(up,key)
    pos=neg=tie=0
    for ep in sorted(set(r['ep'] for r in up)):
        gq=[r for r in up if r['ep']==ep and r['scan_date'] in m]
        gr=[r for r in up if r['ep']==ep and r['scan_date'] not in m]
        nq=sum(r['nres'] for r in gq); nr=sum(r['nres'] for r in gr)
        if nq<3 or nr<3: continue
        a=sum(r['w'] for r in gq)/nq; b=sum(r['w'] for r in gr)/nr
        if a<b: pos+=1
        elif a>b: neg+=1
        else: tie+=1
    print(f"{name:18s} Q4가 더 나쁨 {pos}개 에피소드 / 더 좋음 {neg} / 동률 {tie}  (비교 가능한 에피소드 {pos+neg+tie}개)")

print("\n=== 잣대들 상호 중복 (상승국면 Q4 날 집합 겹침 %) ===")
masks={name:q4mask(up,key)[0] for key,name in KEYS}
names=[n for _,n in KEYS]
print(" "*18 + "".join(f"{n[:6]:>8s}" for n in names))
for a in names:
    line=f"{a:18s}"
    for b in names:
        inter=len(masks[a]&masks[b]); uni=len(masks[a]|masks[b])
        line+=f"{100*inter/uni:7.0f}%"
    print(line)
