# -*- coding: utf-8 -*-
import json, collections, math, pickle, random, os
random.seed(20260822)
SP = os.path.dirname(os.path.abspath(__file__))
ROOT = r"C:/Users/hanul/playground/my-stock"
D = pickle.load(open(SP+"/regime_metrics.pkl","rb"))
dates, pos, M, up = D["dates"], D["pos"], D["M"], D["up"]
N=len(dates)
d = json.load(open(ROOT+"/public/data/backtest-volatility-pilot.json", encoding="utf-8"))
events=[x for x in d["events"] if x["result"] in ("win","loss")]

day_n=collections.defaultdict(int); day_w=collections.defaultdict(int)
for e in events:
    day_n[e["entry_date"]]+=1
    day_w[e["entry_date"]]+= 1 if e["result"]=="win" else 0
alldays=sorted(day_n)
updays=[dt for dt in alldays if up[pos[dt]-1]]
print("all entry days",len(alldays),"trades",sum(day_n.values()))
print("uptrend entry days",len(updays),"trades",sum(day_n[x] for x in updays),
      "wins",sum(day_w[x] for x in updays))
dn=[dt for dt in alldays if not up[pos[dt]-1]]
print("correction days",len(dn),"trades",sum(day_n[x] for x in dn),"winrate",
      round(100*sum(day_w[x] for x in dn)/max(1,sum(day_n[x] for x in dn)),1))

def stat_quart(vals, days, q=4):
    """trade-weighted winrate(top quartile) - winrate(bottom quartile)"""
    pairs=sorted(zip(vals,days))
    k=len(pairs)//q
    if k<2: return None
    bot=pairs[:k]; top=pairs[-k:]
    def wr(ps):
        n=sum(day_n[dt] for _,dt in ps); w=sum(day_w[dt] for _,dt in ps)
        return (100*w/n if n else None, n, w)
    a=wr(top); b=wr(bot)
    if a[0] is None or b[0] is None: return None
    return a[0]-b[0], a, b

def run_metric(name, days, nshift_report=False):
    S=M[name]
    lo=0
    while lo<N and S[lo] is None: lo+=1
    ser=S[lo:]
    L=len(ser)
    use=[dt for dt in days if pos[dt]-1>=lo]
    if len(use)<20: return None
    p=[pos[dt]-1-lo for dt in use]
    obs=stat_quart([ser[i] for i in p], use)
    if obs is None: return None
    T=abs(obs[0])
    # 1) day-block permutation (shuffle metric labels across days) 4000x
    vals=[ser[i] for i in p]
    cnt=0; B=4000
    for _ in range(B):
        sh=use[:]; random.shuffle(sh)
        s=stat_quart(vals, sh)
        if s and abs(s[0])>=T-1e-12: cnt+=1
    p_perm=(cnt+1)/(B+1)
    # 2) circular shift of the metric series (preserves autocorrelation)
    cnt2=0; tot=0
    for k in range(1,L):
        sv=[ser[(i+k)%L] for i in p]
        s=stat_quart(sv, use)
        if s is None: continue
        tot+=1
        if abs(s[0])>=T-1e-12: cnt2+=1
    p_shift=(cnt2+1)/(tot+1)
    return dict(name=name, n_days=len(use), diff=obs[0], top=obs[1], bot=obs[2],
                p_perm=p_perm, p_shift=p_shift, nshift=tot)

rows=[]
for name in M:
    for tag,days in (("전체",alldays),("상승국면",updays)):
        r=run_metric(name,days)
        if r: r["tag"]=tag; rows.append(r)
rows.sort(key=lambda r:r["p_perm"])
print("\n=== 36 tests: day-block permutation p  vs  circular-shift p ===")
print(f"{'지표':<16}{'구간':<8}{'일수':>5}{'상위승률':>9}{'하위승률':>9}{'차':>8}{'p(날순열)':>11}{'p(순환이동)':>12}")
for r in rows:
    print(f"{r['name']:<16}{r['tag']:<8}{r['n_days']:>5}{r['top'][0]:>9.1f}{r['bot'][0]:>9.1f}"
          f"{r['diff']:>8.1f}{r['p_perm']:>11.4f}{r['p_shift']:>12.4f}")
json.dump(rows, open(SP+"/rows.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
sig=[r for r in rows if r["p_perm"]<0.05]
print(f"\n날순열 p<0.05: {len(sig)}/36 ; 순환이동 p<0.05: {sum(1 for r in rows if r['p_shift']<0.05)}/36")
print(f"Bonferroni 0.05/36={0.05/36:.5f} 통과(순환이동): {sum(1 for r in rows if r['p_shift']<0.05/36)}")
print("최소 순환이동 p:", min(r['p_shift'] for r in rows), min(rows,key=lambda r:r['p_shift'])['name'])
