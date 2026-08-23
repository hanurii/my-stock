import json, random
from collections import defaultdict
D=json.load(open('C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json',encoding='utf-8'))
R=json.load(open('C:/Users/hanul/playground/my-stock/public/data/market-regime.json',encoding='utf-8'))
reg={x['date']:x['up'] for x in R['series']}
ev=[x for x in D['events'] if x['result'] in ('win','loss')]
random.seed(5)
def test(sub,minn,label):
    byday=defaultdict(list)
    for x in sub: byday[x['entry_date']].append(x)
    ds=[(d,v) for d,v in byday.items() if len(v)>=minn]
    obs=sum(1 for _,v in ds if all(x['result']=='loss' for x in v))
    sizes=[len(v) for _,v in ds]
    pool=[1 if x['result']=='win' else 0 for _,v in ds for x in v]
    # A) free shuffle
    cnt=0;T=5000; tot=0
    for _ in range(T):
        random.shuffle(pool); i=0;z=0
        for n in sizes:
            if sum(pool[i:i+n])==0: z+=1
            i+=n
        tot+=z
        if z>=obs: cnt+=1
    print('%s min%d: 관측 전멸 %d일 / 무작위섞기 평균 %.1f일, p=%.4f'%(label,minn,obs,tot/T,(cnt+1)/(T+1)))
    # B) stock-block shuffle: shuffle stock blocks' outcomes
    bycode=defaultdict(list)
    for _,v in ds:
        for x in v: bycode[x['code']].append(x)
    codes=list(bycode)
    cnt=0; tot=0
    for _ in range(T):
        random.shuffle(pool)
        # assign contiguous chunks to stocks (keeps stock-level clumping of results)
        m={}; i=0
        for c in codes:
            for x in bycode[c]:
                m[id(x)]=pool[i]; i+=1
        z=0
        for _,v in ds:
            if sum(m[id(x)] for x in v)==0: z+=1
        tot+=z
        if z>=obs: cnt+=1
    print('     종목블록 섞기 평균 %.1f일, p=%.4f'%(tot/T,(cnt+1)/(T+1)))
test(ev,4,'전체')
test([x for x in ev if reg[x['scan_date']]],4,'상승국면')
test([x for x in ev if x['entry_date']<'2026-03-25'],4,'전반')
test([x for x in ev if x['entry_date']>='2026-03-25'],4,'후반')
