import json,os,math
from math import comb
P=r"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/cf.json"
rows=json.load(open(P,encoding='utf-8'))
def signtest(w,l):
    n=w+l
    if n==0: return 1.0
    k=min(w,l)
    p=sum(comb(n,i) for i in range(0,k+1))/2**n
    return min(1.0,2*p)

def report(sub,label,basis='gross_pct'):
    w=l=t=0; diffs=[]
    for r in sub:
        a=r[basis]; c=r['cf_pct']
        dd=c-a; diffs.append(dd)
        if dd>1e-9: w+=1
        elif dd<-1e-9: l+=1
        else: t+=1
    diffs.sort()
    med=diffs[len(diffs)//2] if len(diffs)%2 else (diffs[len(diffs)//2-1]+diffs[len(diffs)//2])/2
    print(f"{label:38s} n={len(sub):3d}  hold+20/-10 better {w:3d} / actual better {l:3d} / tie {t}  p={signtest(w,l):.4f}  meandiff={sum(diffs)/len(diffs):+.2f}pp  meddiff={med:+.2f}pp")
    return w,l

print("=== ALL 63 trades: actual exit vs mechanical +20/-10 (gross basis) ===")
report(rows,'ALL 63 (gross)')
report(rows,'ALL 63 (net actual vs gross cf)','net_pct')
print()
wins=[r for r in rows if r['outcome']=='win']
early=[r for r in wins if r['gross_pct']<20]
print('wins',len(wins),'early-exit wins (<+20% gross)',len(early))
report(early,'early-exit WINS only (gross)')
from collections import Counter
print('  cf state breakdown:',Counter(r['cf_state'] for r in early))
print('  cf pct for early wins:')
for r in sorted(early,key=lambda z:z['close_date']):
    print('   ',r['close_date'],r['code'],r['name'][:9].ljust(9),'actual',f"{r['gross_pct']:+6.2f}",'-> cf',f"{r['cf_pct']:+7.2f}",r['cf_state'],r['cf_date'])
print()
losses=[r for r in rows if r['outcome']!='win']
report(losses,'losses/other only (gross)')
print()
print("=== split: opened before vs on/after 2026-08-13 (rule change) ===")
for lab,f in [('open < 2026-08-13',lambda r:r['open_date']<'2026-08-13'),('open >= 2026-08-13',lambda r:r['open_date']>='2026-08-13')]:
    sub=[r for r in rows if f(r)]
    report(sub,lab)
print()
print("=== monthly realized stats recompute (net) ===")
for m in ['2026-07','2026-08']:
    sub=[r for r in rows if r['month']==m]
    W=[r['net_pct'] for r in sub if r['outcome']=='win']; L=[r['net_pct'] for r in sub if r['outcome']!='win']
    aw=sum(W)/len(W); al=abs(sum(L)/len(L))
    print(f"{m}: n={len(sub)} win={len(W)}/{len(sub)}={100*len(W)/len(sub):.1f}%  avgwin={aw:+.2f} avgloss={-al:.2f} payoff={aw/al:.2f} breakeven={100*al/(aw+al):.1f}%  won={sum(r['net_won'] for r in sub):,}")
print()
print("=== August split by rule regime (open date) ===")
for lab,f in [('AUG open<8/13',lambda r:r['month']=='2026-08' and r['open_date']<'2026-08-13'),('AUG open>=8/13',lambda r:r['month']=='2026-08' and r['open_date']>='2026-08-13')]:
    sub=[r for r in rows if f(r)]
    W=[r['net_pct'] for r in sub if r['outcome']=='win']; L=[r['net_pct'] for r in sub if r['outcome']!='win']
    aw=(sum(W)/len(W)) if W else float('nan'); al=abs(sum(L)/len(L)) if L else float('nan')
    print(f"{lab}: n={len(sub)} win={len(W)} ({100*len(W)/len(sub):.1f}%) avgwin={aw:+.2f} avgloss={-al:.2f} won={sum(r['net_won'] for r in sub):,}")
print()
print("=== counterfactual total won (position sized by actual buy notional) ===")
tot_a=0;tot_c=0
for r in rows:
    notion=r['avg_buy']*r['buy_qty']
    tot_a+=r['net_won']
    tot_c+=notion*(r['cf_pct']/100)-notion*0.0034
print(f"actual net total = {tot_a:,.0f} KRW ;  mechanical +20/-10 (gross-0.34% fee) = {tot_c:,.0f} KRW ; diff = {tot_c-tot_a:,.0f}")
# early-exit wins only substitution
tot2=tot_a
for r in early:
    notion=r['avg_buy']*r['buy_qty']
    tot2 += (notion*(r['cf_pct']/100)-notion*0.0034) - r['net_won']
print(f"substitute ONLY the 20 early-exit wins -> {tot2:,.0f} KRW ; diff = {tot2-tot_a:,.0f}")
