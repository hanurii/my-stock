# -*- coding: utf-8 -*-
"""1차 관문 보강: 같은날 층화 순열검정(부호검정보다 검정력 큼) — 같은 '같은날' 원칙."""
import json, sys, random
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCR = Path(sys.argv[0]).parent
rows = json.loads((SCR/"events_feat.json").read_text(encoding="utf-8"))
R = [r for r in rows if r["result"] in ("win","loss")]

def split_day_median(rows_, key):
    byday=defaultdict(list)
    for r in rows_:
        if r.get(key) is not None: byday[r["scan_date"]].append(r)
    days=[]
    for d,g in byday.items():
        if len(g)<2: continue
        vals=sorted(x[key] for x in g)
        med=vals[len(vals)//2] if len(vals)%2 else (vals[len(vals)//2-1]+vals[len(vals)//2])/2
        hi=[x for x in g if x[key]>med]; lo=[x for x in g if x[key]<=med]
        if not hi or not lo:
            hi=[x for x in g if x[key]>=med]; lo=[x for x in g if x[key]<med]
        if not hi or not lo: continue
        days.append((hi,lo))
    return days

def split_day_cat(rows_, pred):
    byday=defaultdict(list)
    for r in rows_: byday[r["scan_date"]].append(r)
    days=[]
    for d,g in byday.items():
        hi=[x for x in g if pred(x)]; lo=[x for x in g if not pred(x)]
        if hi and lo: days.append((hi,lo))
    return days

def perm(days, n_iter=4000, seed=11, val=lambda x: 1.0 if x["result"]=="win" else 0.0):
    rnd=random.Random(seed)
    pools=[([val(x) for x in H]+[val(x) for x in L], len(H)) for H,L in days]
    def stat(shuffled=False):
        hs=ls=0.0; hn=ln=0
        for pool,nh in pools:
            p=pool[:]
            if shuffled: rnd.shuffle(p)
            hs+=sum(p[:nh]); hn+=nh; ls+=sum(p[nh:]); ln+=len(p)-nh
        return (hs/hn - ls/ln)*100
    obs=stat(False)
    c=sum(1 for _ in range(n_iter) if abs(stat(True))>=abs(obs)-1e-9)
    n_hi=sum(nh for _,nh in pools); n_lo=sum(len(p)-nh for p,nh in pools)
    return round(obs,2), round((c+1)/(n_iter+1),4), n_hi, n_lo, len(days)

CONT = ["turnover_eok","cap_eok","coil_min_dry","dist_52wh_pct","base_depth","pct_to_pivot",
        "ret_120d_pct","tightness","rs","entry_price","gain_52wl_pct","base_len","ext_50ma_pct",
        "ext_150ma_pct","ext_200ma_pct","ret_5d_pct","ret_20d_pct","ret_60d_pct","atr_pct",
        "gap_up_pct","dryup","n_contractions","coil_len","coil_dry_mean","coil_range_pct"]
print("=== 같은날 층화 순열검정 (승률 기준, 4000회) ===")
print(f"{'요인':<18}{'날수':>6}{'상WR-하WR':>11}{'p':>8}{'n상':>6}{'n하':>6}")
out={}
for k in CONT:
    days=split_day_median(R,k)
    if not days: continue
    o,p,nh,nl,nd=perm(days)
    out[k]=dict(diff=o,p=p,nhi=nh,nlo=nl,ndays=nd)
    print(f"{k:<18}{nd:>6}{o:>11.2f}{p:>8.4f}{nh:>6}{nl:>6}")
print()
for nm,pred in [("pattern_VCP",lambda x:x["pattern"]=="VCP"),
                ("market_KOSPI",lambda x:x["market"]=="KOSPI"),
                ("sector_tagged",lambda x:x.get("sector_short") is not None)]:
    days=split_day_cat(R,pred)
    o,p,nh,nl,nd=perm(days)
    out[nm]=dict(diff=o,p=p,nhi=nh,nlo=nl,ndays=nd)
    print(f"{nm:<18}{nd:>6}{o:>11.2f}{p:>8.4f}{nh:>6}{nl:>6}")
(SCR/"gate1b_res.json").write_text(json.dumps(out,ensure_ascii=False,indent=1),encoding="utf-8")
