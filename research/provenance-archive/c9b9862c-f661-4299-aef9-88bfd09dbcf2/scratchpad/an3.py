import json, os, statistics, random, math
from collections import Counter, defaultdict
SCRATCH=os.environ["SCRATCH"]
P=json.load(open(os.path.join(SCRATCH,"panel.json"),encoding="utf-8"))
RULES=P["rules"]; EV=P["events"]
for e in EV:
    e["ff"]={}; e["retk"]={dd["k"]: dd["ret_close"] for dd in e["days"]}
    for ri,r in enumerate(RULES):
        f=None
        for dd in e["days"]:
            if dd["st"][ri]=="violation": f=dd["k"]; break
        e["ff"][r]=f
    f=None
    for dd in e["days"]:
        if any(st=="violation" for st in dd["st"]): f=dd["k"]; break
    e["ff"]["ANY5"]=f
ALL=RULES+["ANY5"]

def binom_p(k,n):
    if n==0: return None
    # two-sided exact sign test vs 0.5
    from math import comb
    tail=sum(comb(n,i) for i in range(0,min(k,n-k)+1))
    return min(1.0, 2*tail/2**n)

print("="*100)
print("[C] 1차 관문 — 같은 진입일 + 같은 보유일차 안에서만 비교 (국면·확장도 착시 차단)")
print("="*100)
for r in ALL:
    strata=[]
    for k in range(1,200):
        R=[e for e in EV if e["K"]>k]
        if not R: break
        byd=defaultdict(list)
        for e in R: byd[e["entry_date"]].append(e)
        for dt,grp in byd.items():
            A=[e for e in grp if e["ff"][r]==k]
            B=[e for e in grp if e["ff"][r] is None or e["ff"][r]>k]
            if A and B: strata.append((dt,k,A,B))
    if not strata:
        print(f"■ {r:26s} 매칭 가능한 (진입일×보유일차) 칸 없음 — 검정 불가"); continue
    dwin=[]; dhold=[]
    for dt,k,A,B in strata:
        wa=sum(1 for e in A if e["result"]=="win")/len(A)
        wb=sum(1 for e in B if e["result"]=="win")/len(B)
        dwin.append(wa-wb)
        dhold.append(statistics.mean(e["ret_hold"] for e in A)-statistics.mean(e["ret_hold"] for e in B))
    nz=[x for x in dwin if x!=0]
    neg=sum(1 for x in nz if x<0)
    p=binom_p(neg,len(nz))
    nz2=[x for x in dhold if x!=0]
    neg2=sum(1 for x in nz2 if x<0)
    p2=binom_p(neg2,len(nz2))
    print(f"■ {r:26s} 칸 {len(strata)}개 (A총 {sum(len(A) for _,_,A,_ in strata)}건)")
    print(f"   +20%도달률 칸평균 차 {statistics.mean(dwin)*100:+.1f}%p | 불리한 칸 {neg}/{len(nz)}  부호검정 p={p:.4f}" if p is not None else "")
    print(f"   끝까지수익률 칸평균 차 {statistics.mean(dhold):+.2f}%p | 불리한 칸 {neg2}/{len(nz2)}  부호검정 p={p2:.4f}" if p2 is not None else "")

print()
print("="*100)
print("[D] 종목 블록 순열검정 (2000회) — 결과(성과)를 종목 블록 단위로 섞어 재계산")
print("    통계량: 보유일차 매칭 +20%도달률 차 (음수일수록 '규칙이 나쁜 걸 잘 골라냄')")
print("="*100)
random.seed(11)
bycode=defaultdict(list)
for e in EV: bycode[e["code"]].append(e)
blocks=[bycode[c] for c in sorted(bycode)]
order=[e for b in blocks for e in b]     # 종목 블록 순서로 늘어놓은 이벤트
sizes=[len(b) for b in blocks]

def stat_matched(assign, r):
    """assign: event id -> outcome dict(result, ret_hold)"""
    num=den=0.0
    for k in range(1,200):
        R=[e for e in EV if e["K"]>k]
        if not R: break
        A=[e for e in R if e["ff"][r]==k]
        B=[e for e in R if e["ff"][r] is None or e["ff"][r]>k]
        if not A or not B: continue
        nA,nB=len(A),len(B); w=nA*nB/(nA+nB)
        wa=sum(1 for e in A if assign[id(e)]=="win")/nA
        wb=sum(1 for e in B if assign[id(e)]=="win")/nB
        num+=w*(wa-wb); den+=w
    return num/den if den else 0.0

real_assign={id(e): e["result"] for e in EV}
for r in ALL:
    obs=stat_matched(real_assign,r)
    cnt=0; N=2000
    for _ in range(N):
        bs=blocks[:]; random.shuffle(bs)
        flat=[e["result"] for b in bs for e in b]
        perm={id(e): flat[i] for i,e in enumerate(order)}
        if stat_matched(perm,r) <= obs: cnt+=1
    p=(cnt+1)/(N+1)
    print(f"■ {r:26s} 관측 {obs*100:+.1f}%p, 순열에서 이만큼 이하 나올 확률 p={p:.4f}")
