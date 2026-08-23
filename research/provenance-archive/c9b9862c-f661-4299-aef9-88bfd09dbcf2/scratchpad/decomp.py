import json, collections, random, statistics
from math import comb
BASE=r"C:/Users/hanul/playground/my-stock/public/data/"
d=json.load(open(BASE+"backtest-volatility-pilot.json",encoding="utf-8"))
ev=d["events"]; reg=json.load(open(BASE+"market-regime.json",encoding="utf-8"))["series"]
upmap={r["date"]:bool(r["up"]) for r in reg}
P=[dict(code=x["code"],day=x["entry_date"],scan=x["scan_date"],win=1 if x["result"]=="win" else 0,
        res=x["result"],to=x["turnover_eok"],ret=x.get("gain_at_resolve_pct")) for x in ev]
byday=collections.defaultdict(list)
for x in P: byday[x["day"]].append(x)
days=sorted(byday); lab={dy:upmap[byday[dy][0]["scan"]] for dy in days}
def rw(n,w,K):
    k=min(K,n)
    if w==0: return 1.0
    if n-w<k: return 0.0
    return comb(n-w,k)/comb(n,k)

up=[dy for dy in days if lab[dy]]; dn=[dy for dy in days if not lab[dy]]
def stat(sel):
    n=[len(byday[x]) for x in sel]; tr=[y for x in sel for y in byday[x]]
    wr=100*sum(y["win"] for y in tr)/len(tr)
    return len(sel),statistics.mean(n),statistics.median(n),len(tr),wr
print("### 후보 수·승률 (스캔일 국면)")
print(" 상승: 날 %d, 하루평균후보 %.2f, 중앙값 %.1f, 거래 %d, 종목당승률 %.1f%%"%stat(up))
print(" 조정: 날 %d, 하루평균후보 %.2f, 중앙값 %.1f, 거래 %d, 종목당승률 %.1f%%"%stat(dn))

# 기계적 성분: 같은 승률(전체 37%) 가정, 각 날의 후보수만 반영한 기대 전멸률
pg=sum(y["win"] for y in P)/len(P)
print()
print("### 전멸률 분해 (K=6): 실제 vs '승률 동일·후보수만 반영' 기대")
for K in (3,6):
    def mech(sel):
        v=[]
        for dy in sel:
            n=len(byday[dy]); k=min(K,n); v.append((1-pg)**k)
        return 100*statistics.mean(v)
    def act(sel): return 100*statistics.mean([rw(len(byday[dy]),sum(y['win'] for y in byday[dy]),K) for dy in sel])
    print(f" K={K}  실제: 상승 {act(up):.1f}% vs 조정 {act(dn):.1f}% (차 {act(dn)-act(up):+.1f}%p)")
    print(f"        기계(후보수만): 상승 {mech(up):.1f}% vs 조정 {mech(dn):.1f}% (차 {mech(dn)-mech(up):+.1f}%p)")
    # 승률만 반영(후보수 동일 가정: 각 국면 평균 후보수를 6으로 고정)
    wu=sum(y['win'] for x in up for y in byday[x])/sum(len(byday[x]) for x in up)
    wd=sum(y['win'] for x in dn for y in byday[x])/sum(len(byday[x]) for x in dn)
    print(f"        승률만(K개 독립): 상승 {(100*(1-wu)**K):.1f}% vs 조정 {(100*(1-wd)**K):.1f}% (차 {100*((1-wd)**K-(1-wu)**K):+.1f}%p)")

print()
print("### 후보수를 맞춘 비교: 후보 n>=K 인 날만")
for K in (3,6):
    su=[x for x in up if len(byday[x])>=K]; sd=[x for x in dn if len(byday[x])>=K]
    f=lambda sel:100*statistics.mean([rw(len(byday[dy]),sum(y['win'] for y in byday[dy]),K) for dy in sel])
    print(f" K={K}: 상승 {len(su)}일 {f(su):.1f}% vs 조정 {len(sd)}일 {f(sd):.1f}% (차 {f(sd)-f(su):+.1f}%p)")
    # permutation on labels within this restricted set
    vals=[rw(len(byday[dy]),sum(y['win'] for y in byday[dy]),K) for dy in su+sd]
    labs=[1]*len(su)+[0]*len(sd); obs=statistics.mean(vals[len(su):])-statistics.mean(vals[:len(su)])
    random.seed(5);N=5000;c=0
    for _ in range(N):
        sh=labs[:]; random.shuffle(sh)
        a=[v for v,l in zip(vals,sh) if l];b=[v for v,l in zip(vals,sh) if not l]
        if statistics.mean(b)-statistics.mean(a)>=obs: c+=1
    print(f"       순열 p={(c+1)/(N+1):.4f}")

print()
print("### 시계열 블록(연속 10거래일) 부트스트랩으로 국면 차 재검정 (K=6)")
K=6
vals={dy:rw(len(byday[dy]),sum(y['win'] for y in byday[dy]),K) for dy in days}
obs=statistics.mean([vals[x] for x in dn])-statistics.mean([vals[x] for x in up])
random.seed(6); N=3000; c=0; B=10
nb=len(days)//B+1
for _ in range(N):
    # 라벨을 블록 단위로 회전(순환 이동) -> 국면의 지속성 보존
    sh=[]
    shift=random.randrange(len(days))
    rot=[lab[days[(i+shift)%len(days)]] for i in range(len(days))]
    a=[vals[d0] for d0,l in zip(days,rot) if l]; b=[vals[d0] for d0,l in zip(days,rot) if not l]
    if a and b and statistics.mean(b)-statistics.mean(a)>=obs: c+=1
print(f" 관측 {100*obs:+.1f}%p, 순환이동(국면 지속성 보존) p={(c+1)/(N+1):.4f}")
