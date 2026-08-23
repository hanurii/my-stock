# -*- coding: utf-8 -*-
import json, glob, os, statistics as st, collections
B=os.environ['LOCALAPPDATA']+'/Temp/bt5y/'
FEE=lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
raw=[]
for f in sorted(glob.glob(B+'bt_*.json')):
    d=json.load(open(f,encoding='utf-8'))
    ev=d['events']
    print(f"{os.path.basename(f)}: total={len(ev)}  " + str(collections.Counter(e['result'] for e in ev)))
    raw += [e for e in ev if e['result'] in ('win','loss')]
print("raw win/loss:", len(raw))
seen=set(); EV=[]
for e in sorted(raw,key=lambda x:(x['entry_date'],x['code'])):
    k=(e['scan_date'],e['code'],e['pattern'])
    if k not in seen: seen.add(k); EV.append(e)
print("dedup:", len(EV), " removed:", len(raw)-len(EV))
W=[e for e in EV if e['result']=='win']; L=[e for e in EV if e['result']=='loss']
print(f"win {len(W)}  loss {len(L)}  WR {len(W)/len(EV)*100:.2f}%")
print(f"win avg gross {st.mean([e['gain_at_resolve_pct'] for e in W]):+.2f}%  loss avg gross {st.mean([e['gain_at_resolve_pct'] for e in L]):+.2f}%")
print(f"win avg NET   {st.mean([FEE(e['gain_at_resolve_pct']) for e in W]):+.2f}%  loss avg NET {st.mean([FEE(e['gain_at_resolve_pct']) for e in L]):+.2f}%")
print(f"ALL avg gross {st.mean([e['gain_at_resolve_pct'] for e in EV]):+.3f}%  ALL avg NET {st.mean([FEE(e['gain_at_resolve_pct']) for e in EV]):+.3f}%")
rr=abs(st.mean([e['gain_at_resolve_pct'] for e in W])/st.mean([e['gain_at_resolve_pct'] for e in L]))
print(f"payoff ratio (gross) {rr:.3f}  breakeven WR {1/(1+rr)*100:.2f}%")
rrn=abs(st.mean([FEE(e['gain_at_resolve_pct']) for e in W])/st.mean([FEE(e['gain_at_resolve_pct']) for e in L]))
print(f"payoff ratio (net)   {rrn:.3f}  breakeven WR {1/(1+rrn)*100:.2f}%")
print("span:", min(e['entry_date'] for e in EV), "~", max(e['resolve_date'] for e in EV))
print("distinct entry days:", len({e['entry_date'] for e in EV}), " distinct scan days:", len({e['scan_date'] for e in EV}))
# scan->entry gap
g=collections.Counter()
import datetime as dt
for e in EV:
    a=dt.date.fromisoformat(e['scan_date']); b=dt.date.fromisoformat(e['entry_date']); g[(b-a).days]+=1
print("scan->entry calendar-day gap:", dict(sorted(g.items())))
json.dump([{k:e[k] for k in ('code','pattern','scan_date','entry_date','resolve_date','result','gain_at_resolve_pct','rs','market')} for e in EV], open(os.path.dirname(__file__)+'/EV.json','w'), ensure_ascii=False)
