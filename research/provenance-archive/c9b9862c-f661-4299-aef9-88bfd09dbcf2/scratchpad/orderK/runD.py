# -*- coding: utf-8 -*-
import math, sys
from collections import defaultdict
from engine import ROWS, BYDAY, DAYS
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
def bp(k,n):
    if n==0: return 1.0
    return min(1.0, 2*sum(math.comb(n,i) for i in range(0,min(k,n-k)+1))/2**n)
def terc(day):
    rs=sorted(day,key=lambda r:r["turnover"]); n=len(rs); k=max(1,n//3)
    return rs[-k:], rs[:k], rs
print("■ 부호검정 정의별 재현 시도 (거래대금 같은날 상대순위)")
# 1) 거래단위: 상위1/3 각 건 vs 그날 나머지 평균
p=q=t=0
for d in DAYS:
    day=BYDAY[d]
    if len(day)<3: continue
    hi,lo,rs=terc(day)
    for r in hi:
        others=[x for x in day if x is not r]
        m=sum(x["ret"] for x in others)/len(others)
        if r["ret"]>m: p+=1
        elif r["ret"]<m: q+=1
        else: t+=1
print(f"  ① 거래단위 상위1/3 vs 그날 나머지평균 : {p}승 {q}패 ({t}무) p={bp(min(p,q),p+q):.4f}")
# 2) 날단위 상위1/3 vs 하위1/3
p=q=t=0
for d in DAYS:
    day=BYDAY[d]
    if len(day)<3: continue
    hi,lo,_=terc(day)
    a=sum(x["ret"] for x in hi)/len(hi); b=sum(x["ret"] for x in lo)/len(lo)
    if a>b: p+=1
    elif a<b: q+=1
    else: t+=1
print(f"  ② 날단위 상위1/3 vs 하위1/3         : {p}승 {q}패 ({t}무) p={bp(min(p,q),p+q):.4f}")
# 3) 날단위 상위절반 vs 하위절반
p=q=t=0
for d in DAYS:
    day=BYDAY[d]
    if len(day)<2: continue
    rs=sorted(day,key=lambda r:r["turnover"]); h=len(rs)//2
    a=sum(x["ret"] for x in rs[-h:])/h; b=sum(x["ret"] for x in rs[:h])/h
    if a>b: p+=1
    elif a<b: q+=1
    else: t+=1
print(f"  ③ 날단위 상위절반 vs 하위절반        : {p}승 {q}패 ({t}무) p={bp(min(p,q),p+q):.4f}")
# 4) 거래단위 승/패 대비 (win 기준)
p=q=t=0
for d in DAYS:
    day=[r for r in BYDAY[d] if r["win"] is not None]
    if len(day)<3: continue
    rs=sorted(day,key=lambda r:r["turnover"]); n=len(rs); k=max(1,n//3)
    hi=rs[-k:]; rest=rs[:-k]
    if not rest: continue
    a=sum(x["win"] for x in hi)/len(hi); b=sum(x["win"] for x in rest)/len(rest)
    if a>b: p+=1
    elif a<b: q+=1
    else: t+=1
print(f"  ④ 날단위 상위1/3 승률 vs 나머지 승률  : {p}승 {q}패 ({t}무) p={bp(min(p,q),p+q):.4f}")

print("\n■ 거래대금 5분위 (같은날 상대순위, 거래단위)")
b=defaultdict(list)
for d in DAYS:
    day=BYDAY[d]
    if len(day)<5: continue
    rs=sorted(day,key=lambda r:r["turnover"]); n=len(rs)
    for i,r in enumerate(rs): b[min(4,int(i*5/n))].append(r)
for k in range(5):
    g=b[k]; w=[r["win"] for r in g if r["win"] is not None]
    tv=sorted(r["turnover"] for r in g)
    print(f"  {k+1}분위 n={len(g):>3} 거래대금중앙 {tv[len(tv)//2]:>7.0f}억  기대 {sum(r['ret'] for r in g)/len(g):>+6.2f}%  승률 {100*sum(w)/len(w):.1f}%")

print("\n■ 절대 거래대금 구간(같은날 아님 — 참고)")
band=[(0,20),(20,50),(50,150),(150,500),(500,1e9)]
for lo,hi in band:
    g=[r for r in ROWS if lo<=r["turnover"]<hi]
    if not g: continue
    w=[r["win"] for r in g if r["win"] is not None]
    print(f"  {lo:>4}~{hi if hi<1e8 else '∞':>5}억 n={len(g):>3} 기대 {sum(r['ret'] for r in g)/len(g):>+6.2f}% 승률 {100*sum(w)/len(w):.1f}%")

print("\n■ 국면×거래대금(같은날 상위1/3 여부)")
for up in (True,False):
    for lab,f in [("상위1/3",lambda r:r.get("_t")==2),("나머지",lambda r:r.get("_t")!=2)]:
        pass
for d in DAYS:
    day=BYDAY[d]; rs=sorted(day,key=lambda r:r["turnover"]); n=len(rs)
    for i,r in enumerate(rs): r["_t"]= 2 if (n>=3 and i>=2*n/3) else (0 if n>=3 and i<n/3 else 1)
for up in (True,False):
    for tlab,tv in [("상위1/3",2),("중위",1),("하위1/3",0)]:
        g=[r for r in ROWS if r["up"]==up and r["_t"]==tv]
        w=[r["win"] for r in g if r["win"] is not None]
        if not w: continue
        print(f"  {'상승국면' if up else '조정국면'} {tlab}: n={len(g):>3} 기대 {sum(r['ret'] for r in g)/len(g):>+6.2f}% 승률 {100*sum(w)/len(w):>5.1f}%")
