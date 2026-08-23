# -*- coding: utf-8 -*-
"""종목 블록 순열 + 전후반 분할 + 전멸률 + 다중검정 보정."""
import json, random, math, sys
from pathlib import Path
from collections import defaultdict
from engine import ROWS, BYDAY, DAYS, RULES, pick, pick_random, agg
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TIE=200; FLIP=5000; BOOT=2000

def sel_prob(days, keyf, desc, K, seed):
    """동점 무작위 파단 평균 선택확률 p_i."""
    rng=random.Random(seed); cnt=defaultdict(int)
    for _ in range(TIE):
        for d in days:
            for r in pick(BYDAY[d], keyf, desc, K, rng): cnt[id(r)]+=1
    return {k: v/TIE for k,v in cnt.items()}

def stat_and_w(days, keyf, desc, K, seed):
    dsel=[d for d in days if len(BYDAY[d])>K]
    P=sel_prob(dsel, keyf, desc, K, seed)
    tot=sum(K for d in dsel)
    W=[]  # (code, w_i*ret_i)
    for d in dsel:
        n=len(BYDAY[d])
        for r in BYDAY[d]:
            w=P.get(id(r),0.0)-K/n
            W.append((r["code"], w*r["ret"]))
    T=sum(x for _,x in W)/tot
    return T, W, tot, dsel

def blockperm_p(W, tot, T, seed=11):
    codes=sorted({c for c,_ in W})
    byc=defaultdict(float)
    for c,v in W: byc[c]+=v
    vals=[byc[c] for c in codes]
    rng=random.Random(seed); ge=0; le=0; null=[]
    for _ in range(FLIP):
        t=sum(v if rng.random()<0.5 else -v for v in vals)/tot
        null.append(t)
        if t>=T: ge+=1
        if t<=T: le+=1
    return min(1.0, 2*min(ge,le)/FLIP), null

def bootstrap_ci(W, tot, seed=13):
    codes=sorted({c for c,_ in W})
    byc=defaultdict(float); cnt=defaultdict(int)
    for c,v in W: byc[c]+=v; cnt[c]+=1
    rng=random.Random(seed); out=[]
    m=len(codes)
    for _ in range(BOOT):
        s=0.0; n=0
        for _ in range(m):
            c=codes[rng.randrange(m)]; s+=byc[c]; n+=cnt[c]
        out.append(s/max(1,n)*(n/tot*tot/max(1,n)) if False else s/tot*(m/m))
    out.sort()
    return out[int(0.025*BOOT)], out[int(0.975*BOOT)], sum(1 for x in out if x<=0)/BOOT

def wipeout(days, keyf, desc, K, seed):
    """상위K가 전부 실패한 날 비율(승 0)."""
    rng=random.Random(seed); tot=0; wipe=0
    for _ in range(TIE):
        for d in days:
            sel=pick(BYDAY[d], keyf, desc, K, rng)
            w=[r["win"] for r in sel if r["win"] is not None]
            if not w: continue
            tot+=1
            if sum(w)==0: wipe+=1
    return 100*wipe/tot

def wipeout_rand(days,K,seed=5):
    rng=random.Random(seed); tot=0; wipe=0
    for _ in range(TIE):
        for d in days:
            sel=pick_random(BYDAY[d],K,rng)
            w=[r["win"] for r in sel if r["win"] is not None]
            if not w: continue
            tot+=1
            if sum(w)==0: wipe+=1
    return 100*wipe/tot

H1=[d for d in DAYS if d < "2026-03-25"]; H2=[d for d in DAYS if d >= "2026-03-25"]
print(f"전반 {len(H1)}일 / 후반 {len(H2)}일  (거래 {sum(len(BYDAY[d]) for d in H1)} / {sum(len(BYDAY[d]) for d in H2)})")

allp=[]
for K in (1,2,3,5,6):
    print(f"\n{'='*100}\n■ K={K}")
    print(f"  {'규칙':<32}{'무작위대비':>10}{'p블록순열':>10}{'부트95%CI':>22}{'p<=0':>7} | {'전반':>8}{'후반':>8} | {'전멸률':>7}(무작위 {wipeout_rand(DAYS,K):.1f}%)")
    for name,keyf,desc in RULES:
        T,W,tot,dsel = stat_and_w(DAYS, keyf, desc, K, seed=hash(name)&0xffff)
        pb,_ = blockperm_p(W,tot,T)
        lo,hi,pneg = bootstrap_ci(W,tot)
        T1 = stat_and_w(H1, keyf, desc, K, seed=1)[0]
        T2 = stat_and_w(H2, keyf, desc, K, seed=2)[0]
        wo = wipeout(DAYS, keyf, desc, K, seed=hash(name)&0xfff)
        allp.append((K,name,pb))
        print(f"  {name:<32}{T:>+9.2f}%p{pb:>10.3f}   [{lo:>+6.2f},{hi:>+6.2f}]%p{pneg:>7.3f} | {T1:>+7.2f}{T2:>+8.2f} | {wo:>6.1f}%")

# 다중검정 보정 (Benjamini-Hochberg, 45개 테스트)
allp.sort(key=lambda x:x[2])
m=len(allp)
print(f"\n■ 다중검정 보정 — 총 {m}개 검정(규칙9 × K5). Bonferroni 문턱 {0.05/m:.5f}")
print(f"  {'순위':>3} {'K':>2} {'규칙':<32}{'p':>8}{'BH q':>8}")
qprev=1.0; rows=[]
for i,(K,name,p) in enumerate(allp[:12],1):
    q=min(qprev, p*m/i); rows.append(q)
    print(f"  {i:>3} {K:>2} {name:<32}{p:>8.3f}{q:>8.3f}")
