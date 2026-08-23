import json, statistics as st
E=json.load(open("evfull.json",encoding="utf-8"))
R=json.load(open("rulescan.json",encoding="utf-8"))
RULES=["heavy_volume_pullback","consecutive_lower_lows","close_below_ma","weak_days_dominant","breakout_failure"]
def firstfire(r,rid,cond):
    e=E[r["i"]];s=e["ser"];b=e["bi_local"];P=e["entry_price"]
    for row in r["daily"]:
        k=row["k"]
        if k>=r["days"]: break
        if row[rid]!="v": continue
        pnl=(s["closes"][b+k]/P-1)*100
        if cond=="any": return k
        if cond=="loss" and pnl<0: return k
        if cond=="profit" and pnl>=0: return k
    return None
def anyfire(r,cond):
    ks=[firstfire(r,rid,cond) for rid in RULES]
    ks=[k for k in ks if k is not None]
    return min(ks) if ks else None
def ev(sel):
    g=[]
    for r in R:
        k=sel(r)
        if k is not None and k<r["days"]:
            e=E[r["i"]];s=e["ser"];b=e["bi_local"];P=e["entry_price"]
            g.append((s["closes"][b+k]/P-1)*100)
        else: g.append(r["gain"])
    return st.mean(g),sum(g)
print(f"기준 현행 EV +1.249")
for cond in ("loss","profit"):
    lab={"loss":"평가손일 때만 규칙청산","profit":"평가익일 때만 규칙청산"}[cond]
    print(f"[{lab}]")
    for rid in RULES:
        m,s2=ev(lambda r,rid=rid: firstfire(r,rid,cond))
        print(f"   {rid:<24} EV {m:+7.3f}")
    m,s2=ev(lambda r: anyfire(r,cond))
    print(f"   {'ANY5':<24} EV {m:+7.3f}")
