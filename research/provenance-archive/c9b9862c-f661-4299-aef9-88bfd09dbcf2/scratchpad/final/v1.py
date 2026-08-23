# -*- coding: utf-8 -*-
import json, random, collections, statistics as st
ROOT='C:/Users/hanul/playground/my-stock/'
j=json.load(open(ROOT+'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
EV=[e for e in j['events'] if e['result'] in ('win','loss')]
REG={p['date']:p['up'] for p in json.load(open(ROOT+'public/data/market-regime.json',encoding='utf-8'))['series']}
FB,FS=0.0014,0.0014+0.002
def net(g): return ((1+g/100)*(1-FS)/(1+FB)-1)*100

def run(events, slots=5, seed=0, regime=False, cost=True, drop=set()):
    byday=collections.defaultdict(list)
    for e in events:
        if id(e) in drop: continue
        if regime and not REG.get(e['scan_date'],True): continue
        byday[e['entry_date']].append(e)
    rnd=random.Random(seed); eq=1.0; held=[]; taken=[]
    alld=sorted(set(list(byday)+[e['resolve_date'] for e in events]))
    contrib=[]
    for d in alld:
        for rd,e,wgt in [h for h in held if h[0]<=d]:
            g=e['gain_at_resolve_pct']; add=wgt*((net(g) if cost else g)/100)
            eq+=add; taken.append(e); contrib.append((add*100,e))
        held=[h for h in held if h[0]>d]
        free=slots-len(held)
        if free>0 and d in byday:
            c=byday[d][:]; rnd.shuffle(c)
            for e in c[:free]: held.append((e['resolve_date'],e,eq/slots))
    return (eq-1)*100, len(taken), contrib

def med(regime=False,cost=True,slots=5,N=300,events=EV,drop=set()):
    rs=[run(events,slots=slots,seed=i,regime=regime,cost=cost,drop=drop) for i in range(N)]
    f=sorted(r[0] for r in rs); n=sorted(r[1] for r in rs)
    return f[N//2], n[N//2], f[N//20], f[N-N//20]

print('=== 재현: 슬롯5 자산곡선(무작위 순서 300회 중앙) ===')
for lab,rg in (('전부매수',False),('상승국면만',True)):
    for cost,tag in ((True,'미래에셋비용'),(False,'무비용')):
        m,n,lo,hi=med(regime=rg,cost=cost)
        print(f'{lab:<8}{tag:<8} {m:+7.1f}%  체결{n:>4}건  5~95%[{lo:+.1f},{hi:+.1f}]')

print()
print('=== 애매 24건을 손절(-10%)로 편입하면 ===')
AMB=[dict(e,result='loss',gain_at_resolve_pct=-10.0) for e in j['events'] if e['result']=='ambiguous']
EV2=EV+AMB
for lab,rg in (('전부매수',False),('상승국면만',True)):
    m,n,lo,hi=med(regime=rg,events=EV2); print(f'{lab:<8} {m:+7.1f}%  체결{n}건')

print()
print('=== 상위 기여거래 제거 민감도(상승국면, 300회) ===')
# 기여도 평균 산출
agg=collections.defaultdict(float)
for i in range(300):
    _,_,c=run(EV,seed=i,regime=True)
    for add,e in c: agg[id(e)]+=add/300
rank=sorted(agg.items(), key=lambda x:-x[1])
byid={id(e):e for e in EV}
for k in (0,1,2,3,5,10):
    drop={r[0] for r in rank[:k]}
    m,n,_,_=med(regime=True,drop=drop)
    names=', '.join(f"{byid[i]['name']}({agg[i]:+.1f}%p)" for i,_ in rank[:k][-1:]) if k else ''
    print(f'상위{k}건 제거 {m:+7.1f}%  체결{n}건  {names}')
print()
tot_pos=sum(v for v in agg.values() if v>0); tot_neg=sum(v for v in agg.values() if v<0)
print('총이익 %+.1f%%p / 총손실 %+.1f%%p / 순 %+.1f%%p (순=총이익의 %.0f%%)'%(tot_pos,tot_neg,tot_pos+tot_neg,100*(tot_pos+tot_neg)/tot_pos))
print('상위5 기여:', ', '.join(f"{byid[i]['name']} {v:+.1f}%p" for i,v in rank[:5]))
