import json, random, statistics
from collections import defaultdict
D=json.load(open('C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json',encoding='utf-8'))
R=json.load(open('C:/Users/hanul/playground/my-stock/public/data/market-regime.json',encoding='utf-8'))
reg={x['date']:x['up'] for x in R['series']}
ev=[x for x in D['events'] if x['result'] in ('win','loss')]
cal=sorted(set(x['date'] for x in R['series'])); ci={d:i for i,d in enumerate(cal)}
def sim(sub,cap,slots=6,rf=False,seed=0):
    byday=defaultdict(list)
    for x in sub: byday[x['entry_date']].append(x)
    rnd=random.Random(seed); equity=1.0; free=slots; op=[]; peak=1.0; mdd=0.0; ntr=0
    for d in cal:
        i=ci[d]; still=[]
        for rel,w,r in op:
            if rel<=i: equity+=w*r; ntr+=1; free+=1
            else: still.append((rel,w,r))
        op=still; peak=max(peak,equity); mdd=min(mdd,equity/peak-1)
        if d not in byday: continue
        c=byday[d][:]
        if rf and not reg[c[0]['scan_date']]: continue
        rnd.shuffle(c)
        for x in c[:min(cap,free,len(c))]:
            op.append((i+max(1,int(x['days_held'])), equity/slots, x['gain_at_resolve_pct']/100)); free-=1
    for rel,w,r in op: equity+=w*r; ntr+=1
    return equity-1,mdd,ntr
for lbl,sub in (('전반 2025-11~2026-03-24',[x for x in ev if x['entry_date']<'2026-03-25']),
                ('후반 2026-03-25~08',[x for x in ev if x['entry_date']>='2026-03-25'])):
    for cap in (6,3):
        for rf in (False,True):
            r=[sim(sub,cap,6,rf,s) for s in range(200)]
            print('%s  캡%d 국면필터%-3s  수익 %6.1f%%  낙폭 %6.1f%%  거래 %.0f'%(lbl,cap,'ON' if rf else 'OFF',
                statistics.mean(a[0] for a in r)*100, statistics.mean(a[1] for a in r)*100, statistics.mean(a[2] for a in r)))
