import sys, math, random, statistics as s
sys.path.insert(0,'.')
from lib import *
from collections import defaultdict

d, ev = load()
R = resolved(ev)

def binom_p_two(k, n, p=0.5):
    if n==0: return 1.0
    pmf=lambda i: math.comb(n,i)*p**i*(1-p)**(n-i)
    obs=pmf(k)
    return min(1.0, sum(pmf(i) for i in range(n+1) if pmf(i)<=obs*(1+1e-9)))

def rank_test(events, key, k, reverse, label, min_day=2):
    byday=defaultdict(list)
    for e in events: byday[e['scan_date']].append(e)
    days=[]; A=[]; B=[]
    for dte, lst in byday.items():
        if len(lst)<min_day: continue
        srt=sorted(lst, key=key, reverse=reverse)
        top=srt[:k]; rest=srt[k:]
        if not top or not rest: continue
        A+=top; B+=rest
        wa=100*sum(1 for x in top if x['result']=='win')/len(top)
        wb=100*sum(1 for x in rest if x['result']=='win')/len(rest)
        ra=sum(x['gain_at_resolve_pct'] for x in top)/len(top)
        rb=sum(x['gain_at_resolve_pct'] for x in rest)/len(rest)
        days.append((dte, wa-wb, ra-rb))
    pos=sum(1 for x in days if x[1]>0); neg=sum(1 for x in days if x[1]<0); tie=sum(1 for x in days if x[1]==0)
    p=binom_p_two(pos,pos+neg)
    wa=wr(A); wb=wr(B)
    print(f"{label:34s} | 일수 {len(days):3d} (상위우세 {pos:3d}/하위우세 {neg:3d}/동률 {tie:3d}) p={p:.3f} "
          f"| 상위 {wa[0]:.1f}%(n{wa[1]}) 하위 {wb[0]:.1f}%(n{wb[1]}) | 수익차중앙 {s.median(x[2] for x in days):+.2f}%p")
    return dict(label=label,days=len(days),pos=pos,neg=neg,p=p,A=wa,B=wb)

print("=== 같은날 순위 규칙 (슬롯 선택과 직결) ===")
for k in (1,2,3):
    rank_test(R, lambda e: e['rs'], k, True, f"그날 RS 상위{k} vs 나머지")
for k in (1,2,3):
    rank_test(R, lambda e: e['turnover_eok'], k, True, f"그날 거래대금 상위{k} vs 나머지")
for k in (1,2,3):
    rank_test(R, lambda e: -e['atr_pct'], k, True, f"그날 ATR 낮은{k} vs 나머지")
for k in (1,2,3):
    rank_test(R, lambda e: -e['gap_up_pct'], k, True, f"그날 갭업 작은{k} vs 나머지")
for k in (1,2,3):
    rank_test(R, lambda e: -e['overrun_pct'], k, True, f"그날 피벗초과 작은{k} vs 나머지")
