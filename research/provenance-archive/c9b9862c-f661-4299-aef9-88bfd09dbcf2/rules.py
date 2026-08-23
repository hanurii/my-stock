exec(open(r'C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/base.py',encoding='utf-8').read())

def gapmid(e):
    g=e["gap_up_pct"]
    return 0 if 0.3<=g<=3.0 else 1   # lower=better
RULES={
 "거래대금큰순":      lambda e: -e["turnover_eok"],
 "거래대금작은순":    lambda e:  e["turnover_eok"],
 "RS높은순":          lambda e: -e["rs"],
 "ATR낮은순(저변동)": lambda e:  e["atr_pct"],
 "ATR높은순":         lambda e: -e["atr_pct"],
 "갭업큰순(먼저돌파)":lambda e: -e["gap_up_pct"],
 "갭업작은순(피벗근접)":lambda e: e["gap_up_pct"],
 "갭0.3~3%우선":      lambda e: (gapmid(e), e["gap_up_pct"]),
 "주가높은순":        lambda e: -e["entry_price"],
 "주가낮은순":        lambda e:  e["entry_price"],
}
def rank(day_events, rule):
    # deterministic tiebreak by code to avoid data-order luck
    return sorted(day_events, key=lambda e:(RULES[rule](e), e["code"]))

def stat_selminusday(rule,K,val,days=None,minday=None):
    """mean over days(n>K) of (mean val of topK - day mean val)"""
    days=days or DAYS
    diffs=[]
    for d in days:
        g=BY[d]
        if len(g)<=K: continue
        if minday and len(g)<minday: continue
        sel=rank(g,rule)[:K]
        dm=sum(val(e) for e in g)/len(g)
        sm=sum(val(e) for e in sel)/K
        diffs.append(sm-dm)
    return (sum(diffs)/len(diffs) if diffs else float('nan')), len(diffs), diffs

def perm_p(rule,K,val,nperm=3000,seed=1,days=None):
    obs,n,_=stat_selminusday(rule,K,val,days)
    rnd=random.Random(seed)
    days=days or DAYS
    cnt=0
    pool=[(BY[d],) for d in days if len(BY[d])>K]
    for _ in range(nperm):
        tot=0.0
        for (g,) in pool:
            idx=list(range(len(g))); rnd.shuffle(idx)
            sel=[g[i] for i in idx[:K]]
            dm=sum(val(e) for e in g)/len(g)
            tot+=sum(val(e) for e in sel)/K-dm
        if abs(tot/len(pool))>=abs(obs)-1e-12: cnt+=1
    return obs,n,(cnt+1)/(nperm+1)
