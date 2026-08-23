import json, statistics as st
from collections import defaultdict
d=json.load(open(r'C:\Users\hanul\playground\my-stock\public\data\backtest-volatility-pilot.json',encoding='utf-8'))
ev=d['events']
res=[e for e in ev if e['result'] in ('win','loss')]
print('resolved', len(res), 'wins', sum(1 for e in res if e['result']=='win'))
byday=defaultdict(list)
for e in res: byday[e['entry_date']].append(e)
print('days total', len(byday))
for k in (3,4):
    days=[dt for dt,v in byday.items() if len(v)>=k]
    wipe=[dt for dt in days if all(x['result']=='loss' for x in byday[dt])]
    sweep=[dt for dt in days if all(x['result']=='win' for x in byday[dt])]
    n_ev=sum(len(byday[dt]) for dt in days)
    n_wipe_ev=sum(len(byday[dt]) for dt in wipe)
    print(f'k>={k}: days={len(days)} events={n_ev} wipeout_days={len(wipe)} wipeout_events={n_wipe_ev} sweep_days={len(sweep)} other_events={n_ev-n_wipe_ev}')
    if k==4:
        print(sorted(wipe))
