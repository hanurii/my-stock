# -*- coding: utf-8 -*-
import json, sys, math, random
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCR=Path(sys.argv[0]).parent
rows=json.loads((SCR/"events_feat3.json").read_text(encoding="utf-8"))
R=[r for r in rows if r["result"] in ("win","loss")]
def wr(g): return sum(1 for x in g if x["result"]=="win")/len(g)*100 if g else float('nan')
def binom(k,n):
    if n==0: return 1.0
    pmf=lambda i: math.comb(n,i)*0.5**n
    o=pmf(k); return min(1.0,sum(pmf(i) for i in range(n+1) if pmf(i)<=o*(1+1e-9)))
def split_med(rows_,key):
    byday=defaultdict(list)
    for r in rows_:
        if r.get(key) is not None: byday[r["scan_date"]].append(r)
    days=[]
    for d,g in byday.items():
        if len(g)<2: continue
        v=sorted(x[key] for x in g)
        med=v[len(v)//2] if len(v)%2 else (v[len(v)//2-1]+v[len(v)//2])/2
        hi=[x for x in g if x[key]>med]; lo=[x for x in g if x[key]<=med]
        if not hi or not lo:
            hi=[x for x in g if x[key]>=med]; lo=[x for x in g if x[key]<med]
        if hi and lo: days.append((d,hi,lo))
    return days
def split_cat(rows_,key,pred):
    byday=defaultdict(list)
    for r in rows_:
        if r.get(key) is not None: byday[r["scan_date"]].append(r)
    days=[]
    for d,g in byday.items():
        hi=[x for x in g if pred(x)]; lo=[x for x in g if not pred(x)]
        if hi and lo: days.append((d,hi,lo))
    return days
def report(name,days,n_iter=4000,seed=13):
    if not days: print(f"{name:<20} (비교 가능한 날 없음)"); return None
    pos=neg=0
    for d,h,l in days:
        x=wr(h)-wr(l)
        if x>0: pos+=1
        elif x<0: neg+=1
    ps=binom(pos,pos+neg)
    rnd=random.Random(seed)
    pools=[([1.0 if x["result"]=="win" else 0.0 for x in h]+[1.0 if x["result"]=="win" else 0.0 for x in l],len(h)) for _,h,l in days]
    def stat(sh):
        hs=ls=0.0;hn=ln=0
        for p,nh in pools:
            q=p[:]
            if sh: rnd.shuffle(q)
            hs+=sum(q[:nh]);hn+=nh;ls+=sum(q[nh:]);ln+=len(q)-nh
        return (hs/hn-ls/ln)*100
    obs=stat(False); c=sum(1 for _ in range(n_iter) if abs(stat(True))>=abs(obs)-1e-9)
    pp=(c+1)/(n_iter+1)
    nh=sum(nh for _,nh in pools); nl=sum(len(p)-nh for p,nh in pools)
    print(f"{name:<20}{len(days):>5}{pos:>5}{neg:>5}{ps:>8.4f}{obs:>9.2f}{pp:>8.4f}{nh:>6}{nl:>6}")
    return dict(days=len(days),pos=pos,neg=neg,p_sign=round(ps,4),diff=round(obs,2),p_perm=round(pp,4))
print("=== 2차 요인 배치: 같은날 비교 ===")
print(f"{'요인':<20}{'날수':>5}{'+':>5}{'-':>5}{'부호p':>8}{'WR차':>9}{'순열p':>8}{'n상':>6}{'n하':>6}")
out={}
CONT=["atr_squeeze","vol_dry_20_50","days_since_52wh","pivot_vs_52wh_pct","close_pos",
      "ret_250d_pct","rsline_vs_high_pct","rsline_20d_pct","rsline_60d_pct","excess_20d_pct","n_prior"]
for k in CONT: out[k]=report(k,split_med(R,k))
out["rsline_newhigh"]=report("rsline_newhigh",split_cat(R,"rsline_newhigh",lambda x:x["rsline_newhigh"]==1))
out["is_repeat"]=report("is_repeat",split_cat(R,"is_repeat",lambda x:x["is_repeat"]==1))
out["prev_loss"]=report("prev_loss(직전손절)",split_cat([r for r in R if r.get("prev_loss") is not None],"prev_loss",lambda x:x["prev_loss"]==1))
(SCR/"gate1c_res.json").write_text(json.dumps(out,ensure_ascii=False,indent=1),encoding="utf-8")
