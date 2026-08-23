import json, collections, math
d=json.load(open('C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=[x for x in d['events'] if x['result'] in ('win','loss')]
print("resolved trades:", len(ev), "unique stocks:", len(set(x['code'] for x in ev)))
byday=collections.defaultdict(list)
for x in ev: byday[x['entry_date']].append(x)
alldays=sorted(byday)
print("all entry days (resolved>=1):", len(alldays))
for k in (1,2,3,4,5):
    ds=[dt for dt in alldays if len(byday[dt])>=k]
    n=sum(len(byday[dt]) for dt in ds); w=sum(1 for dt in ds for x in byday[dt] if x['result']=='win')
    wipe=sum(1 for dt in ds if all(x['result']=='loss' for x in byday[dt]))
    swp=sum(1 for dt in ds if all(x['result']=='win' for x in byday[dt]))
    print(f"n>={k}: days={len(ds)} trades={n} winrate={100*w/n:.2f}% wipeout_days={wipe} sweep_days={swp}")
# duplicates same stock same day?
dup=0
for dt in alldays:
    c=collections.Counter(x['code'] for x in byday[dt])
    dup+=sum(v-1 for v in c.values() if v>1)
print("same stock twice on same day:", dup)
