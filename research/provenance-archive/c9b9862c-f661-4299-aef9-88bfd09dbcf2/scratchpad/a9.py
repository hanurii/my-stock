import json, collections, math
import numpy as np
from scipy.stats import chi2 as CHI2
P='C:/Users/hanul/playground/my-stock/'
d=json.load(open(P+'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=[x for x in d['events'] if x['result'] in ('win','loss')]
byday=collections.defaultdict(list)
for x in ev: byday[x['entry_date']].append(x)
days=sorted(k for k in byday if len(byday[k])>=4)
ns=np.array([len(byday[k]) for k in days],float)
ks=np.array([sum(1 for x in byday[k] if x['result']=='win') for k in days],float)
p=ks.sum()/ns.sum()
q=(1-p)**ns
# exact Poisson-binomial for number of wipeout days
dist=np.zeros(1); dist[0]=1
for qi in q:
    nd=np.zeros(len(dist)+1); nd[:-1]+=dist*(1-qi); nd[1:]+=dist*qi; dist=nd
print(f"p={p:.4f} E[wipeout days]={float((np.arange(len(dist))*dist).sum()):.3f}  exact P(>=14)={dist[14:].sum():.3e}  P(>=11)={dist[11:].sum():.3e}")
qs=p**ns
dist2=np.zeros(1); dist2[0]=1
for qi in qs:
    nd=np.zeros(len(dist2)+1); nd[:-1]+=dist2*(1-qi); nd[1:]+=dist2*qi; dist2=nd
print(f"E[sweep days]={float((np.arange(len(dist2))*dist2).sum()):.3f} exact P(>=2)={dist2[2:].sum():.3f}")
# variance ratio of day win rates
r=ks/ns
obsvar=float(((r-r.mean())**2).mean())
expvar=float((p*(1-p)/ns).mean())
print(f"var(day win rate) obs={obsvar:.5f} expected-if-independent={expvar:.5f} ratio={obsvar/expvar:.2f}")
print(f"LR=35.4 -> p (boundary mixture) = {0.5*CHI2.sf(35.4,1):.3e}; chi2 overdisp 145.2/df70 p={CHI2.sf(145.2,70):.3e}")
# excess-vs-independent ratios in the portfolio sim
for tag,wr,act in (("same day",0.391,0.193),("within 1 week",0.424,0.085),(">=14d apart",0.364,0.061),("fully random",0.391,0.049)):
    ind=(1-wr)**6
    print(f"{tag}: winrate {100*wr:.1f}% -> independent wipeout {100*ind:.1f}% vs actual {100*act:.1f}% = {act/ind:.2f}x")
