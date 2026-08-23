import json, statistics as st, random, collections
E=json.load(open("evfull.json",encoding="utf-8"))
R=json.load(open("rulescan.json",encoding="utf-8"))
RULES=["heavy_volume_pullback","consecutive_lower_lows","close_below_ma","weak_days_dominant","breakout_failure"]
# 관측 = (거래, 보유일차 k) — k일 종가에 팔았을 때 대비 계속 보유의 이득(=forward)
obs=[]
for r in R:
    i=r["i"]; e=E[i]; s=e["ser"]; b=e["bi_local"]; P=e["entry_price"]
    for row in r["daily"]:
        k=row["k"]
        if k>=r["days"]: continue      # 그날 이미 결착 → 팔 기회 없음
        sell=(s["closes"][b+k]/P-1)*100
        fwd = r["gain"] - sell
        obs.append({"code":r["code"],"date":s["dates"][b+k],"k":k,"fwd":fwd,
                    **{rid:(row[rid]=="v") for rid in RULES}})
print("관측(거래×보유일) =",len(obs),"고유종목",len(set(o['code'] for o in obs)))
def strat_diff(rows, rid, key):
    g=collections.defaultdict(lambda:[[],[]])
    for o in rows:
        g[o[key]][1 if o[rid] else 0].append(o["fwd"])
    num=den=0; n1=n0=0
    for kk,(a,bl) in g.items():
        if not a or not bl: continue
        w=len(a)+len(bl)
        num += w*(st.mean(bl)-st.mean(a)); den += w
        n1+=len(bl); n0+=len(a)
    return (num/den if den else None), n1, n0
print()
print("계속보유 이득(fwd, %p) — 점등일 vs 비점등일. 음수면 '점등일에 파는 게 이득'")
print("%-24s %7s %7s %10s %10s %10s"%("rule","점등n","비점등n","전체차","보유일차층화","날짜층화"))
for rid in RULES:
    a=[o["fwd"] for o in obs if not o[rid]]; bl=[o["fwd"] for o in obs if o[rid]]
    raw=(st.mean(bl)-st.mean(a)) if a and bl else None
    dk,n1,n0=strat_diff(obs,rid,"k")
    dd,_,_=strat_diff(obs,rid,"date")
    print("%-24s %7d %7d %10.3f %10.3f %10.3f"%(rid,len(bl),len(a),raw,dk,dd))
# 군집 부트스트랩(종목) 2000회 — 보유일차 층화 차이
codes=sorted({o["code"] for o in obs})
bycode=collections.defaultdict(list)
for o in obs: bycode[o["code"]].append(o)
rnd=random.Random(7)
print()
print("종목 군집 부트스트랩 2000회 (보유일차 층화 차이의 95% 구간)")
for rid in RULES:
    ds=[]
    for _ in range(2000):
        samp=[]
        for _ in range(len(codes)): samp+=bycode[rnd.choice(codes)]
        d,_,_=strat_diff(samp,rid,"k")
        if d is not None: ds.append(d)
    ds.sort()
    pt,_,_=strat_diff(obs,rid,"k")
    print("  %-24s %+7.3f  [%+7.3f ~ %+7.3f]  P(차<0)=%.3f"%(rid,pt,ds[int(.025*len(ds))],ds[int(.975*len(ds))],sum(1 for x in ds if x<0)/len(ds)))
