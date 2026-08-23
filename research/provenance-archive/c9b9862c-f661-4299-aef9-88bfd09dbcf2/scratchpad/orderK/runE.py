# -*- coding: utf-8 -*-
import random, math, sys
from collections import defaultdict, Counter
from engine import ROWS, BYDAY, DAYS, RULES, pick, pick_random, agg
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
def bp(k,n):
    if n==0: return 1.0
    return min(1.0, 2*sum(math.comb(n,i) for i in range(0,min(k,n-k)+1))/2**n)

print("■ 하루 진입 건수 분포")
c=Counter(len(BYDAY[d]) for d in DAYS)
cum=0
for k in sorted(c):
    cum+=c[k]
    print(f"  {k:>2}건 {c[k]:>2}일  (누적 {cum}/{len(DAYS)}일, {100*cum/len(DAYS):.0f}%)")
print(f"  7건 이상 = {sum(v for k,v in c.items() if k>=7)}일, 10건 이상 = {sum(v for k,v in c.items() if k>=10)}일")

print("\n■ 상위 규칙끼리 겹침(K=3, 갈리는 날) — 사실상 같은 요인인가")
K=3; dsel=[d for d in DAYS if len(BYDAY[d])>K]
def sel(keyf,desc,seed):
    rng=random.Random(seed); out={}
    for d in dsel: out[d]={id(r) for r in pick(BYDAY[d],keyf,desc,K,rng)}
    return out
S={n:sel(f,dd,7) for n,f,dd in RULES}
base=S["(c) 거래대금 큰 순"]
for n in ["(j) 시가총액 큰 순","(h) ATR 낮은 순","(i) 52주고가에 가까운 순","(g) 피벗에 가까운 순","(e) RS 높은 순"]:
    ov=sum(len(base[d]&S[n][d]) for d in dsel)/ (len(dsel)*K)
    print(f"  거래대금큰순 ∩ {n:<24} {100*ov:.0f}%")

print("\n■ 전멸(그날 산 것 전부 실패) 위험 — 규칙별")
TIE=200
def wipe(keyf,desc,days,K,seed):
    rng=random.Random(seed); tot=0; w=0
    for _ in range(TIE):
        for d in days:
            s=pick(BYDAY[d],keyf,desc,K,rng) if keyf else pick_random(BYDAY[d],K,rng)
            ws=[r["win"] for r in s if r["win"] is not None]
            if not ws: continue
            tot+=1
            if sum(ws)==0: w+=1
    return 100*w/tot
UP=[d for d in DAYS if BYDAY[d][0]["up"]]; DN=[d for d in DAYS if not BYDAY[d][0]["up"]]
print(f"  (상승국면 진입일 {len(UP)}일 / 조정국면 {len(DN)}일)")
for K in (3,6):
    print(f"   K={K}: 무작위 전체 {wipe(None,None,DAYS,K,1):.1f}% | 거래대금큰순 전체 {wipe(lambda r:r['turnover'],True,DAYS,K,2):.1f}%"
          f" | 무작위·상승국면 {wipe(None,None,UP,K,3):.1f}% | 거래대금큰순·상승국면 {wipe(lambda r:r['turnover'],True,UP,K,4):.1f}%"
          f" | 무작위·조정국면 {wipe(None,None,DN,K,5):.1f}%")

print("\n■ 실전 조합: '상승국면 날만 + 거래대금 큰 순 K개' (사후 선택 — 확인용)")
for K in (3,6):
    rng=random.Random(9); ev=[];wr=[]
    for _ in range(TIE):
        s=[]
        for d in UP: s+=pick(BYDAY[d],lambda r:r["turnover"],True,K,rng)
        a=agg(s); ev.append(a[0]); wr.append(a[1])
    rng=random.Random(10); ev2=[];wr2=[]
    for _ in range(TIE):
        s=[]
        for d in UP: s+=pick_random(BYDAY[d],K,rng)
        a=agg(s); ev2.append(a[0]); wr2.append(a[1])
    print(f"   K={K} 상승국면만: 거래대금큰순 기대 {sum(ev)/TIE:+.2f}% 승률 {sum(wr)/TIE:.1f}%  vs 무작위 {sum(ev2)/TIE:+.2f}% {sum(wr2)/TIE:.1f}%"
          f"  (전체무작위 대비 기준선 승률 37~38%)")

print("\n■ '그날 돌파가 많은 날' 자체가 좋은 날인가 (혼잡도)")
for lo,hi,lab in [(1,2,'1~2건'),(3,4,'3~4건'),(5,6,'5~6건'),(7,9,'7~9건'),(10,99,'10건+')]:
    g=[r for d in DAYS if lo<=len(BYDAY[d])<=hi for r in BYDAY[d]]
    w=[r["win"] for r in g if r["win"] is not None]
    print(f"  {lab:<6} 날 {sum(1 for d in DAYS if lo<=len(BYDAY[d])<=hi):>3}일 거래 {len(g):>3}건 기대 {sum(r['ret'] for r in g)/len(g):>+6.2f}% 승률 {100*sum(w)/len(w):.1f}%")
