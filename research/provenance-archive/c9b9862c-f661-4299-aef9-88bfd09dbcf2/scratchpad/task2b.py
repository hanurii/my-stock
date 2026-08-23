# -*- coding: utf-8 -*-
"""국면 에피소드 수 / 시간 군집 확인 — 유효 표본이 몇 덩어리인가"""
import sys, json
sys.path.insert(0, r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
from daytable import build
from collections import defaultdict

rows=[r for r in build() if r['nres']>0]
# 에피소드 라벨
ep=[]; cur=None; k=0
for r in rows:
    if r['days_since_flip']==0 or cur is None or r['up']!=cur:
        # 새 에피소드 (경과일 리셋 또는 국면 바뀜)
        pass
    ep.append(r)
# 정확히: 스캔일 순서대로 days_since_flip 이 감소하면 새 에피소드
lab=[]; k=0; prev=None
for r in rows:
    if prev is None or r['days_since_flip'] < prev:
        k+=1
    lab.append(k); prev=r['days_since_flip']
for r,l in zip(rows,lab): r['ep']=l
eps=defaultdict(list)
for r in rows: eps[r['ep']].append(r)
print(f"국면 에피소드 {len(eps)}개 (스캔일이 있는 구간 기준)")
for k in sorted(eps):
    g=eps[k]
    w=sum(x['w'] for x in g); l=sum(x['l'] for x in g); n=w+l
    print(f"  #{k} {'상승' if g[0]['up'] else '조정'} {g[0]['scan_date']}~{g[-1]['scan_date']} 날{len(g):3d} 거래{n:3d} 승률{100*w/n if n else 0:5.1f}% 경과일 {g[0]['days_since_flip']}~{g[-1]['days_since_flip']}")

# 경과일 Q1(0~3) 이 몇 개 에피소드에서 나오나
q1=[r for r in rows if r['days_since_flip']<=3]
c=defaultdict(int)
for r in q1: c[r['ep']]+=1
print(f"\n경과일 0~3일 날 {len(q1)}개 → 에피소드 {len(c)}개에 분포: {dict(c)}")
w=sum(r['w'] for r in q1); l=sum(r['l'] for r in q1)
print(f"  거래 {w+l}, 승률 {100*w/(w+l):.1f}%")
# 에피소드별
for k in sorted(c):
    g=[r for r in q1 if r['ep']==k]
    w=sum(x['w'] for x in g); l=sum(x['l'] for x in g)
    print(f"    #{k} ({'상승' if g[0]['up'] else '조정'}) 날{len(g)} 거래{w+l} 승{w} 승률 {100*w/(w+l) if w+l else 0:.0f}%")
