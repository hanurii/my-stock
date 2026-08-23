import json,random
from collections import defaultdict
random.seed(11)
P=r"C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json"
ev=[e for e in json.load(open(P,encoding="utf-8"))["events"] if e["result"] in ("win","loss")]
by=defaultdict(list)
for e in ev: by[e["entry_date"]].append(e)
days=[v for v in by.values() if len(v)>=3]
F='gain_at_resolve_pct'
def sel(items,rev): return sorted(items,key=lambda e:(-e['gap_up_pct'] if rev else e['gap_up_pct']))[:2]
top=[x for it in days for x in sel(it,False)]; bot=[x for it in days for x in sel(it,True)]
mt=sum(e[F] for e in top)/len(top); mb=sum(e[F] for e in bot)/len(bot)
B=2000;sims=[]
for _ in range(B):
    s=[];
    for it in days: s+=random.sample(it,2)
    sims.append(sum(e[F] for e in s)/len(s))
sims.sort()
ge=sum(1 for x in sims if x>=mt); le=sum(1 for x in sims if x<=mt)
print("mean gain_at_resolve TOP2=%.2f%% BOT2=%.2f%% random mean=%.2f%% (p05 %.2f p95 %.2f)"
      %(mt,mb,sum(sims)/B,sims[100],sims[1900]))
print("TOP2 two-sided bootstrap p=%.4f"%(min(1.0,2*min(ge,le)/B)))
