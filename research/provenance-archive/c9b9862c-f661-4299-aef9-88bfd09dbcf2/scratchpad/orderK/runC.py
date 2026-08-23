# -*- coding: utf-8 -*-
"""(b) 돌파순서 대리지표 3종 + 민감도 + 거래대금 상대순위 재현."""
import json, random, math, sys
from pathlib import Path
from collections import defaultdict
from engine import ROWS, BYDAY, DAYS, pick, pick_random, agg
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TIE=200; FLIP=5000
def binom_p(k,n):
    if n==0: return 1.0
    return min(1.0, 2*sum(math.comb(n,i) for i in range(0,min(k,n-k)+1))/2**n)

B_RULES=[
 ("(b1) 시가/피벗 높은 순(갭 큰 것부터)", lambda r: r["open_ratio"], True),
 ("(b2) 갭업만 먼저(갭>0), 나머지 무작위", lambda r: (1 if r["gap"]>0 else 0), True),
 ("(b3) 시가/피벗 낮은 순(갭업 회피)",     lambda r: r["open_ratio"], False),
 ("(b4) 갭 0.5~3% 만 먼저(과열 제외)",    lambda r: (1 if 0.3<=r["gap"]<=3.0 else 0), True),
 ("(g)  스캔일 종가 피벗 근접 순",         lambda r: r["pct_to_pivot"], False),
]
print("■ (b) 돌파순서 대리지표 검정 — 무작위 대비 기대값 차이(%p) / 같은날 부호검정")
for K in (1,2,3,5,6):
    dsel=[d for d in DAYS if len(BYDAY[d])>K]
    print(f"\n  K={K}  (갈리는 날 {len(dsel)}일)")
    for name,keyf,desc in B_RULES:
        rng=random.Random(hash(name)&0xffff)
        evs=[]; dayavg=defaultdict(list)
        for _ in range(TIE):
            s=[]
            for d in dsel:
                p=pick(BYDAY[d],keyf,desc,K,rng); s+=p
                dayavg[d].append(sum(x["ret"] for x in p)/len(p))
            evs.append(agg(s)[0])
        ev=sum(evs)/TIE
        # 무작위 기대 = 날평균 가중
        tot=len(dsel)*K
        base=sum(K*sum(x["ret"] for x in BYDAY[d])/len(BYDAY[d]) for d in dsel)/tot
        pos=neg=tie=0
        for d in dsel:
            rm=sum(dayavg[d])/len(dayavg[d]); dm=sum(x["ret"] for x in BYDAY[d])/len(BYDAY[d])
            if abs(rm-dm)<1e-9: tie+=1
            elif rm>dm: pos+=1
            else: neg+=1
        print(f"    {name:<34}{ev-base:>+7.2f}%p  기대 {ev:>+6.2f}%  부호 {pos}-{neg}({tie}무) p={binom_p(min(pos,neg),pos+neg):.3f}")

# ── 갭업 여부 자체의 성적(같은날 짝비교) ────────────────
print("\n■ 갭업(시가가 피벗 위) vs 갭 없음 — 같은날 짝비교")
pos=neg=0; gs=[]; ns=[]
for d in DAYS:
    g=[r for r in BYDAY[d] if r["gap"]>0]; n=[r for r in BYDAY[d] if r["gap"]<=0]
    if not g or not n: continue
    gm=sum(r["ret"] for r in g)/len(g); nm=sum(r["ret"] for r in n)/len(n)
    gs+=g; ns+=n
    if gm>nm: pos+=1
    elif gm<nm: neg+=1
print(f"  갭업 n={sum(1 for r in ROWS if r['gap']>0)} 기대 {sum(r['ret'] for r in ROWS if r['gap']>0)/max(1,sum(1 for r in ROWS if r['gap']>0)):+.2f}%  "
      f"승률 {100*sum(1 for r in ROWS if r['gap']>0 and r['result']=='win')/max(1,sum(1 for r in ROWS if r['gap']>0 and r['win'] is not None)):.1f}%")
print(f"  갭없음 n={sum(1 for r in ROWS if r['gap']<=0)} 기대 {sum(r['ret'] for r in ROWS if r['gap']<=0)/max(1,sum(1 for r in ROWS if r['gap']<=0)):+.2f}%  "
      f"승률 {100*sum(1 for r in ROWS if r['gap']<=0 and r['result']=='win')/max(1,sum(1 for r in ROWS if r['gap']<=0 and r['win'] is not None)):.1f}%")
print(f"  같은날 짝비교 갭업승 {pos} - 갭업패 {neg}  p={binom_p(min(pos,neg),pos+neg):.3f}")

# ── 거래대금 상대순위(같은날 3분위) 재현 ────────────────
print("\n■ 거래대금 같은날 상대순위 3분위 (거래 단위)")
buck=defaultdict(list)
for d in DAYS:
    rs=sorted(BYDAY[d], key=lambda r:r["turnover"])
    n=len(rs)
    if n<3: continue
    for i,r in enumerate(rs):
        q = 0 if i < n/3 else (1 if i < 2*n/3 else 2)
        buck[q].append(r)
for q in (2,1,0):
    g=buck[q]; w=[r["win"] for r in g if r["win"] is not None]
    print(f"  {['하위1/3','중위1/3','상위1/3'][q]}  n={len(g):>3}  기대 {sum(r['ret'] for r in g)/len(g):>+6.2f}%  승률 {100*sum(w)/len(w):.1f}%")
pos=neg=t=0
for d in DAYS:
    rs=sorted(BYDAY[d], key=lambda r:r["turnover"]); n=len(rs)
    if n<3: continue
    hi=rs[-max(1,n//3):]; rest=rs[:-max(1,n//3)]
    hm=sum(r["ret"] for r in hi)/len(hi); rm=sum(r["ret"] for r in rest)/len(rest)
    if hm>rm: pos+=1
    elif hm<rm: neg+=1
    else: t+=1
print(f"  같은날 상위1/3 vs 나머지 부호검정: {pos}승 {neg}패 ({t}무) p={binom_p(min(pos,neg),pos+neg):.4f}")

# ── 민감도: ambiguous=+20 ───────────────────────────────
print("\n■ 민감도 — ambiguous(24건)를 +20% 로 볼 때 (c) 거래대금 큰 순")
for r in ROWS:
    if r["result"]=="ambiguous": r["ret"]=20.0
for K in (1,2,3,5,6):
    dsel=[d for d in DAYS if len(BYDAY[d])>K]
    rng=random.Random(3); evs=[]
    for _ in range(TIE):
        s=[]
        for d in dsel: s+=pick(BYDAY[d], lambda r:r["turnover"], True, K, rng)
        evs.append(agg(s)[0])
    ev=sum(evs)/TIE
    tot=len(dsel)*K
    base=sum(K*sum(x["ret"] for x in BYDAY[d])/len(BYDAY[d]) for d in dsel)/tot
    print(f"    K={K}: {ev-base:+.2f}%p (기대 {ev:+.2f}%)")
