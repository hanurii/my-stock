import json, collections, statistics, random
BASE=r"C:/Users/hanul/playground/my-stock/public/data/"
d=json.load(open(BASE+"backtest-volatility-pilot.json",encoding="utf-8"))
ev=d["events"]; reg=json.load(open(BASE+"market-regime.json",encoding="utf-8"))["series"]
upmap={r["date"]:bool(r["up"]) for r in reg}
cal=sorted(upmap); idx={dt:i for i,dt in enumerate(cal)}
P=[dict(day=x["entry_date"],scan=x["scan_date"],win=1 if x["result"]=="win" else 0,to=x["turnover_eok"],
        rs=x["rs"],ret=x.get("gain_at_resolve_pct") or 0.0,hold=max(1,x.get("days_held") or 1)) for x in ev]
byday=collections.defaultdict(list)
for x in P: byday[x["day"]].append(x)
days=sorted(byday); lab={dy:upmap[byday[dy][0]["scan"]] for dy in days}
def sim(order,K=6,rf=False,seed=0):
    rnd=random.Random(seed); free=[0]*K; tot=0;n=0;w=0
    for dy in days:
        t=idx[dy]
        if rf and not lab[dy]: continue
        c=byday[dy][:]; rnd.shuffle(c)
        if order=="turnover": c.sort(key=lambda x:-x["to"])
        elif order=="rs": c.sort(key=lambda x:-x["rs"])
        for s in range(K):
            if not c: break
            if free[s]<=t:
                x=c.pop(0); free[s]=t+x["hold"]; tot+=x["ret"]/K; n+=1; w+=x["win"]
    return tot,n,w
R=[sim("random",seed=s)[0] for s in range(1000)]
T=[sim("turnover",seed=s)[0] for s in range(1000)]
E=[sim("random",rf=True,seed=s)[0] for s in range(1000)]
F=[sim("turnover",rf=True,seed=s)[0] for s in range(1000)]
def q(v):
    v2=sorted(v); return v2[25],v2[500],v2[975]
print("슬롯6 누적수익(자본대비 합), 1000시드 [2.5%, 중앙, 97.5%]")
print(" 무작위 순서   : %.1f / %.1f / %.1f"%q(R))
print(" 거래대금 큰순 : %.1f / %.1f / %.1f  → 무작위 분포에서 백분위 %.0f%%"%(*q(T),100*sum(1 for r in R if r<statistics.median(T))/len(R)))
print(" 상승국면만+무작위: %.1f / %.1f / %.1f"%q(E))
print(" 상승국면만+거래대금큰순: %.1f / %.1f / %.1f"%q(F))
print(" 상승국면 필터가 무작위보다 나은 시드 비율: %.1f%%"%(100*sum(1 for a,b in zip(E,R) if a>b)/len(R)))
# 국면 필터 우위의 순열 검정: 국면 라벨을 순환이동시켜 가짜 필터를 만들고 성과 비교
base=statistics.median(E)-statistics.median(R)
random.seed(4); N=1000; c=0
orig=dict(lab)
for _ in range(N):
    sft=random.randrange(len(days))
    fake={days[i]:orig[days[(i+sft)%len(days)]] for i in range(len(days))}
    lab=fake
    v=[sim("random",rf=True,seed=s)[0] for s in range(20)]
    if statistics.median(v)-statistics.median(R)>=base: c+=1
lab=orig
print(" 국면필터 초과성과 %+.1f%%p, 국면라벨 순환이동 순열 p=%.3f"%(base,(c+1)/(N+1)))
