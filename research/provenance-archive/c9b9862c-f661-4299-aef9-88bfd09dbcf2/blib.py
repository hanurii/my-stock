import json, math, random, statistics as st, bisect
from collections import defaultdict

ROOT = "C:/Users/hanul/playground/my-stock/"

def bload():
    d = json.load(open(ROOT+"public/data/backtest-volatility-pilot.json", encoding="utf-8"))
    ev = d["events"]
    reg = json.load(open(ROOT+"public/data/market-regime.json", encoding="utf-8"))["series"]
    reg_dates = sorted(r["date"] for r in reg)
    regmap = {r["date"]: r["up"] for r in reg}
    for e in ev:
        sd = e["scan_date"]
        i = bisect.bisect_right(reg_dates, sd) - 1
        e["regime_up"] = regmap[reg_dates[i]] if i >= 0 else None
        e["overrun_pct"] = (e["entry_price"]/e["pivot"] - 1)*100 if e["pivot"] else None
    # 같은날 거래대금 순위 백분위 (결착건 기준)
    byday = defaultdict(list)
    for e in ev: byday[e["scan_date"]].append(e)
    for dte, lst in byday.items():
        n=len(lst)
        srt = sorted(lst, key=lambda x: x["turnover_eok"])
        for i,e in enumerate(srt):
            e["to_pct"] = i/(n-1) if n>1 else None
            e["to_rank"] = n-i   # 1 = 그날 거래대금 1위
            e["day_n"] = n
    return d, ev

def resolved(ev): return [e for e in ev if e["result"] in ("win","loss")]

def wr(sub):
    r=[e for e in sub if e["result"] in ("win","loss")]
    if not r: return (None,0)
    return (100.0*sum(1 for e in r if e["result"]=="win")/len(r), len(r))

def realized(sub):
    r=[e for e in sub if e["result"] in ("win","loss")]
    if not r: return (None,0)
    return (sum(e["gain_at_resolve_pct"] for e in r)/len(r), len(r))

def binom_p_two(k,n,p=0.5):
    if n==0: return 1.0
    pmf=lambda i: math.comb(n,i)*p**i*(1-p)**(n-i)
    obs=pmf(k)
    return min(1.0, sum(pmf(i) for i in range(n+1) if pmf(i)<=obs*(1+1e-9)))
