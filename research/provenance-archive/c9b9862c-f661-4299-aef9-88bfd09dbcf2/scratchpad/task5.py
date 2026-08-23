# -*- coding: utf-8 -*-
"""③규칙 유의성: 날블록 순열 · 순환이동 · 종목블록 부트스트랩 · 컷 민감도"""
import sys, math, random
sys.path.insert(0, r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
from daytable import build
from collections import defaultdict

rows=build(); res=[r for r in rows if r['nres']>0]
up=[r for r in res if r['up']]

def cutv(key,q,sel=None):
    vs=sorted(r[key] for r in rows if r.get(key) is not None and (sel is None or sel(r)))
    return vs[int(len(vs)*q)]

print("=== 컷 민감도: 상승국면 안에서 '지수 10일 수익률 상위 X% 제외' ===")
for q in (0.5,0.6,0.7,0.75,0.8,0.9):
    c=cutv('ret10',q,lambda r:r['up'])
    a=[r for r in up if r['ret10']<c]; b=[r for r in up if r['ret10']>=c]
    wa=sum(r['w'] for r in a); la=sum(r['l'] for r in a)
    wb=sum(r['w'] for r in b); lb=sum(r['l'] for r in b)
    print(f"  상위 {100*(1-q):.0f}% 제외(컷 {c:5.2f}%): 남김 {100*wa/(wa+la):5.1f}%({wa+la:3d}) vs 버림 {100*wb/(wb+lb):5.1f}%({wb+lb:3d})  차 {100*wa/(wa+la)-100*wb/(wb+lb):+5.1f}%p")

print("\n=== 52주 신고가 비율 컷 민감도 (상승국면) ===")
for q in (0.5,0.6,0.7,0.75,0.8,0.9):
    c=cutv('pct_nh52',q,lambda r:r['up'])
    a=[r for r in up if r['pct_nh52']<c]; b=[r for r in up if r['pct_nh52']>=c]
    wa=sum(r['w'] for r in a); la=sum(r['l'] for r in a); wb=sum(r['w'] for r in b); lb=sum(r['l'] for r in b)
    print(f"  상위 {100*(1-q):.0f}% 제외(컷 {c:5.2f}%): 남김 {100*wa/(wa+la):5.1f}%({wa+la:3d}) vs 버림 {100*wb/(wb+lb):5.1f}%({wb+lb:3d})  차 {100*wa/(wa+la)-100*wb/(wb+lb):+5.1f}%p")

# --- 유의성: 규칙 통과 라벨을 섞기 ---
C=cutv('ret10',0.75,lambda r:r['up'])
def diff(days, mask):
    wa=sum(d['w'] for d,m in zip(days,mask) if m); la=sum(d['l'] for d,m in zip(days,mask) if m)
    wb=sum(d['w'] for d,m in zip(days,mask) if not m); lb=sum(d['l'] for d,m in zip(days,mask) if not m)
    if wa+la==0 or wb+lb==0: return 0.0
    return 100*wa/(wa+la)-100*wb/(wb+lb)

days=up[:]  # 시간순
mask=[d['ret10']<C for d in days]
obs=diff(days,mask)
print(f"\n[③ 통계량] 상승국면 안, 과열제외 승률 - 과열 승률 = {obs:+.1f}%p")

rnd=random.Random(11); reps=5000; cnt=0
for _ in range(reps):
    m=mask[:]; rnd.shuffle(m)
    if abs(diff(days,m))>=abs(obs): cnt+=1
print(f"  날블록 순열(날 순서 무시)      p = {(cnt+1)/(reps+1):.4f}")

n=len(days); cnt=0; tot=0
for k in range(1,n):
    m=mask[k:]+mask[:k]
    if abs(diff(days,m))>=abs(obs): cnt+=1
    tot+=1
print(f"  순환이동(시간 자기상관 보존)   p = {(cnt+1)/(tot+1):.4f}   ← 이게 정직한 값")

# 종목 블록 부트스트랩 (같은 종목 반복 보정)
bycode=defaultdict(list)
for d in days:
    for e in d['events']:
        if e['result'] in ('win','loss'):
            bycode[e['code']].append((e['result']=='win', d['ret10']<C))
codes=list(bycode)
rnd=random.Random(5); vals=[]
for _ in range(3000):
    wa=la=wb=lb=0
    for _ in codes:
        c=codes[rnd.randrange(len(codes))]
        for win,keep in bycode[c]:
            if keep:
                if win: wa+=1
                else: la+=1
            else:
                if win: wb+=1
                else: lb+=1
    if wa+la and wb+lb: vals.append(100*wa/(wa+la)-100*wb/(wb+lb))
vals.sort()
print(f"  종목블록 부트스트랩 95% 구간  [{vals[int(.025*len(vals))]:+.1f}, {vals[int(.975*len(vals))]:+.1f}]%p  (부호 유지 비율 {100*sum(1 for v in vals if v>0)/len(vals):.1f}%)")
print(f"  고유 종목 {len(codes)}개 / 결착 {sum(len(v) for v in bycode.values())}건")
