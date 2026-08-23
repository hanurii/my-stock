import json, collections, random, statistics
BASE=r"C:/Users/hanul/playground/my-stock/public/data/"
d=json.load(open(BASE+"backtest-volatility-pilot.json",encoding="utf-8"))
ev=d["events"]; reg=json.load(open(BASE+"market-regime.json",encoding="utf-8"))["series"]
upmap={r["date"]:bool(r["up"]) for r in reg}
cal=sorted(upmap); idx={dt:i for i,dt in enumerate(cal)}
P=[]
for x in ev:
    P.append(dict(code=x["code"],name=x["name"],day=x["entry_date"],scan=x["scan_date"],
        win=1 if x["result"]=="win" else 0,res=x["result"],to=x["turnover_eok"],rs=x["rs"],
        ret=x.get("gain_at_resolve_pct") or 0.0,hold=max(1,x.get("days_held") or 1)))
byday=collections.defaultdict(list)
for x in P: byday[x["day"]].append(x)
days=sorted(byday)
print("entry days in calendar:",sum(1 for x in days if x in idx),"/",len(days))

# --- per-trade win rate significance across regime, with day-block (cyclic shift) null ---
lab={dy:upmap[byday[dy][0]["scan"]] for dy in days}
tr_by_day={dy:[y["win"] for y in byday[dy]] for dy in days}
def wr(sel):
    a=[w for dy in sel for w in tr_by_day[dy]]; return 100*sum(a)/len(a)
up=[x for x in days if lab[x]]; dn=[x for x in days if not lab[x]]
obs=wr(up)-wr(dn)
random.seed(9); N=5000; c=0
for _ in range(N):
    s=random.randrange(len(days)); rot=[lab[days[(i+s)%len(days)]] for i in range(len(days))]
    a=[x for x,l in zip(days,rot) if l]; b=[x for x,l in zip(days,rot) if not l]
    if a and b and wr(a)-wr(b)>=obs: c+=1
print("종목당 승률: 상승 %.1f%% vs 조정 %.1f%% (차 %+.1f%%p), 순환이동 p=%.4f"%(wr(up),wr(dn),obs,(c+1)/(N+1)))

# --- slot-constrained portfolio simulation ---
def sim(order, K=6, regime_filter=False, seed=0, weight_by=None):
    rnd=random.Random(seed)
    free=[0]*K   # index of day when slot frees
    total=0.0; n=0; wins=0; rets=[]
    for dy in days:
        if dy not in idx: continue
        t=idx[dy]
        if regime_filter and not lab[dy]: continue
        cand=byday[dy][:]
        if order=="random": rnd.shuffle(cand)
        elif order=="turnover": rnd.shuffle(cand); cand.sort(key=lambda x:-x["to"])
        elif order=="turnover_asc": rnd.shuffle(cand); cand.sort(key=lambda x:x["to"])
        elif order=="rs": rnd.shuffle(cand); cand.sort(key=lambda x:-x["rs"])
        for s in range(K):
            if not cand: break
            if free[s]<=t:
                x=cand.pop(0)
                free[s]=t+x["hold"]
                total+=x["ret"]/K; n+=1; wins+=x["win"]; rets.append(x["ret"])
    return total,n,wins,rets
print()
print("### 슬롯 6칸 포트폴리오 시뮬레이션 (보유기간 점유 반영, 수익=gain_at_resolve_pct, 1/6씩)")
print("정책                        매매수  승률   건당평균   누적(자본대비 합)")
rows=[]
for name,kw in [("① 무작위 순서",dict(order="random")),
                ("② 거래대금 큰 순",dict(order="turnover")),
                ("③ 거래대금 작은 순",dict(order="turnover_asc")),
                ("④ RS 높은 순",dict(order="rs")),
                ("⑤ 상승국면일만+무작위",dict(order="random",regime_filter=True)),
                ("⑥ 상승국면일만+거래대금큰순",dict(order="turnover",regime_filter=True))]:
    tots=[];ns=[];ws=[];pers=[]
    for sd in range(300):
        t,n,w,r=sim(seed=sd,**kw); tots.append(t);ns.append(n);ws.append(w);pers.append(statistics.mean(r))
    print("%-26s %5.1f  %5.1f%%  %+6.2f%%   %+7.1f%%"%(name,statistics.mean(ns),100*statistics.mean(ws)/statistics.mean(ns),statistics.mean(pers),statistics.mean(tots)))
    rows.append((name,statistics.mean(tots),statistics.mean(ns)))

# 전후반
print()
print("### 전후반 분할 (누적 자본대비 합)")
def sim_half(kw,lo,hi,seed):
    global days
    keep=days
    days=[x for x in keep if lo<=x<hi]
    r=sim(seed=seed,**kw); days=keep; return r
for name,kw in [("① 무작위",dict(order="random")),("② 거래대금 큰 순",dict(order="turnover")),
                ("⑤ 상승국면일만",dict(order="random",regime_filter=True))]:
    out=[]
    for lo,hi in (("2000-01-01","2026-03-25"),("2026-03-25","2999-12-31")):
        t=[sim_half(kw,lo,hi,sd)[0] for sd in range(200)]
        nn=[sim_half(kw,lo,hi,sd)[1] for sd in range(1)]
        out.append("%+.1f%% (%d건)"%(statistics.mean(t),nn[0]))
    print("%-16s 전반 %s | 후반 %s"%(name,out[0],out[1]))
