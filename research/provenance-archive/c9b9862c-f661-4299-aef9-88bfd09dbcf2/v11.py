import json, random, statistics
from collections import defaultdict
D=json.load(open('C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json',encoding='utf-8'))
R=json.load(open('C:/Users/hanul/playground/my-stock/public/data/market-regime.json',encoding='utf-8'))
reg={x['date']:x['up'] for x in R['series']}
ev=[x for x in D['events'] if x['result'] in ('win','loss')]
cal=sorted(set(x['date'] for x in R['series']))
ci={d:i for i,d in enumerate(cal)}
byday=defaultdict(list)
for x in ev: byday[x['entry_date']].append(x)
days=sorted(byday)
def gain(x):
    return x['gain_at_resolve_pct']/100.0
def sim(cap, slots=6, regime_filter=False, seed=0):
    rnd=random.Random(seed)
    equity=1.0; free=slots; open_pos=[]  # (release_day_index, weight, ret)
    peak=1.0; mdd=0.0; ntr=0; wins=0
    for d in cal:
        i=ci[d]
        # release
        still=[]
        for rel,w,r in open_pos:
            if rel<=i:
                equity+= w*r
                ntr+=1; wins+= (r>0); free+=1
            else: still.append((rel,w,r))
        open_pos=still
        peak=max(peak,equity); mdd=min(mdd,equity/peak-1)
        if d not in byday: continue
        cands=byday[d][:]
        if regime_filter and not reg[cands[0]['scan_date']]: continue
        rnd.shuffle(cands)
        take=min(cap, free, len(cands))
        for x in cands[:take]:
            w=equity/slots
            rel=i+max(1,int(x['days_held']))
            open_pos.append((rel,w,gain(x)))
            free-=1
    for rel,w,r in open_pos:
        equity+=w*r; ntr+=1; wins+=(r>0)
    return equity-1, mdd, ntr, wins/ntr if ntr else 0
for cap in (6,4,3,2):
    for rf in (False,True):
        res=[sim(cap,6,rf,s) for s in range(200)]
        rets=[r[0]*100 for r in res]; dds=[r[1]*100 for r in res]; ns=[r[2] for r in res]; wr=[r[3]*100 for r in res]
        print('하루 최대 %d개  국면필터=%-3s  총수익 %6.1f%% (중앙 %6.1f)  최대낙폭 %6.1f%%  거래 %.0f건  승률 %.1f%%'%(
            cap,'ON' if rf else 'OFF',statistics.mean(rets),statistics.median(rets),statistics.mean(dds),statistics.mean(ns),statistics.mean(wr)))
