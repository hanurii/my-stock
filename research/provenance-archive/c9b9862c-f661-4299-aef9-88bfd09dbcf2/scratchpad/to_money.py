import json, collections, statistics, random
BASE=r"C:/Users/hanul/playground/my-stock/public/data/"
d=json.load(open(BASE+"backtest-volatility-pilot.json",encoding="utf-8"))
ev=d["events"]; reg=json.load(open(BASE+"market-regime.json",encoding="utf-8"))["series"]
upmap={r["date"]:bool(r["up"]) for r in reg}
P=[dict(day=x["entry_date"],scan=x["scan_date"],code=x["code"],win=1 if x["result"]=="win" else 0,
        res=x["result"],to=x["turnover_eok"],ret=x.get("gain_at_resolve_pct") or 0.0) for x in ev]
byday=collections.defaultdict(list)
for x in P: byday[x["day"]].append(x)
days=[dy for dy in sorted(byday) if len(byday[dy])>=3]
print("### 같은 날 안 거래대금 상·하위 짝비교 (후보 3개 이상인 %d일)"%len(days))
dw=[];dr=[]
for dy in days:
    it=sorted(byday[dy],key=lambda x:-x["to"]); n=len(it); k=max(1,n//3)
    hi=it[:k]; lo=it[-k:]
    dw.append(statistics.mean([x["win"] for x in hi])-statistics.mean([x["win"] for x in lo]))
    dr.append(statistics.mean([x["ret"] for x in hi])-statistics.mean([x["ret"] for x in lo]))
def signtest(v,seed=1):
    m=statistics.mean(v); random.seed(seed); N=5000; c=0
    for _ in range(N):
        if sum(random.choice([1,-1])*x for x in v)/len(v)>=m: c+=1
    return m,(c+1)/(N+1),sum(1 for x in v if x>0),sum(1 for x in v if x<0)
m,p,a,b=signtest(dw); print(" 승률 차(상위1/3 - 하위1/3): %+.1f%%p  부호 %d승%d패  순열 p=%.4f"%(100*m,a,b,p))
m,p,a,b=signtest(dr); print(" 수익률 차: %+.2f%%p  부호 %d승%d패  순열 p=%.4f"%(m,a,b,p))
# 전후반
for lab,sel in (("전반",[x for x in days if x<'2026-03-25']),("후반",[x for x in days if x>='2026-03-25'])):
    idxs=[days.index(x) for x in sel]
    print("  %s(%d일): 승률차 %+.1f%%p, 수익차 %+.2f%%p"%(lab,len(sel),100*statistics.mean([dw[i] for i in idxs]),statistics.mean([dr[i] for i in idxs])))
# 국면별
for lab,f in (("상승일",True),("조정일",False)):
    idxs=[i for i,x in enumerate(days) if upmap[byday[x][0]["scan"]]==f]
    print("  %s(%d일): 승률차 %+.1f%%p, 수익차 %+.2f%%p"%(lab,len(idxs),100*statistics.mean([dw[i] for i in idxs]),statistics.mean([dr[i] for i in idxs])))
