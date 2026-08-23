# -*- coding: utf-8 -*-
import json, random, collections, statistics as st
import FinanceDataReader as fdr
ROOT='C:/Users/hanul/playground/my-stock/'
j=json.load(open(ROOT+'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
EV=[e for e in j['events'] if e['result'] in ('win','loss')]
REG={p['date']:p['up'] for p in json.load(open(ROOT+'public/data/market-regime.json',encoding='utf-8'))['series']}
FB,FS=0.0014,0.0014+0.002
def net(g): return ((1+g/100)*(1-FS)/(1+FB)-1)*100

# 대안 국면: 코스피/코스닥 20일선
alt={}
for sym,lab in (('KS11','kospi20'),('KQ11','kosdaq20')):
    df=fdr.DataReader(sym,'2025-08-01','2026-08-22')
    ma=df['Close'].rolling(20).mean()
    alt[lab]={d.strftime('%Y-%m-%d'): bool(c>m) for d,c,m in zip(df.index,df['Close'],ma) if m==m}

def run(events, slots=5, seed=0, regfn=None, cost=True, sub=None):
    byday=collections.defaultdict(list)
    pool=events if sub is None else sub
    for e in pool:
        if regfn and not regfn(e): continue
        byday[e['entry_date']].append(e)
    rnd=random.Random(seed); eq=1.0; held=[]; taken=0
    alld=sorted(set(list(byday)+[e['resolve_date'] for e in events]))
    for d in alld:
        for rd,e,wgt in [h for h in held if h[0]<=d]:
            eq+=wgt*((net(e['gain_at_resolve_pct']) if cost else e['gain_at_resolve_pct'])/100); taken+=1
        held=[h for h in held if h[0]>d]
        free=slots-len(held)
        if free>0 and d in byday:
            c=byday[d][:]; rnd.shuffle(c)
            for e in c[:free]: held.append((e['resolve_date'],e,eq/slots))
    return (eq-1)*100, taken

def med(regfn=None,N=300,sub=None):
    rs=[run(EV,seed=i,regfn=regfn,sub=sub) for i in range(N)]
    f=sorted(r[0] for r in rs); n=sorted(r[1] for r in rs); return f[N//2],n[N//2]

print('=== 국면 정의를 바꾸면 (슬롯5, 300회 중앙) ===')
defs=[('필터없음', None),
      ('등가중20일선(채택)', lambda e: REG.get(e['scan_date'],True)),
      ('코스피20일선', lambda e: alt['kospi20'].get(e['scan_date'],True)),
      ('코스닥20일선', lambda e: alt['kosdaq20'].get(e['scan_date'],True))]
for lab,fn in defs:
    m,n=med(fn); 
    # 후보 건수 및 건당 순수익
    sel=[e for e in EV if (fn is None or fn(e))]
    print(f'{lab:<18} {m:+7.1f}%  체결{n:>4}건  후보{len(sel):>3}건  건당순 {st.mean(net(x["gain_at_resolve_pct"]) for x in sel):+.2f}%')

print()
print('=== "그냥 덜 사기"와의 대조: 무작위로 후보를 433건→같은 수로 줄인 널 ===')
obs,obsn=med(defs[1][1])
rnd=random.Random(7); res=[]
for k in range(500):
    sub=rnd.sample(EV, 433)          # 국면과 무관하게 같은 후보수만 무작위
    m,_=med(sub=sub,N=1)
    res.append(m)
res.sort()
p=sum(1 for x in res if x>=obs)/len(res)
print('관측(등가중20) %+.1f%% / 무작위 433건 널: 중앙 %+.1f%%, P90 %+.1f%%, P95 %+.1f%% → p=%.3f'%(obs,res[250],res[450],res[475],p))
