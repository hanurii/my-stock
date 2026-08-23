import json, sys, random, statistics as st
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')
EV=json.load(open('C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json',encoding='utf-8'))['events']
pit=json.load(open('C:/Users/hanul/AppData/Local/Temp/pit_index.json',encoding='utf-8'))
uppit={dt:bool(u) for dt,u in zip(pit['dates'],pit['up'])}
for i,e in enumerate(EV): e['idx']=i; e['up']=uppit.get(e['scan_date'],False)
CONF=[e for e in EV if e['result'] in ('win','loss')]
BUY,SELL=0.0014,0.0034
def nm(g): return (1+g/100.0)*(1-SELL)/(1+BUY)
NS=300
def sim(pool,seed,slots=5,exclude=frozenset(),track=False):
    rng=random.Random(seed); byday=defaultdict(list)
    for e in pool:
        if e['idx'] in exclude: continue
        byday[e['entry_date']].append(e)
    if not byday: return (0.0,0,{}) if track else (0.0,0)
    alld=sorted(set(byday)|set(e['resolve_date'] for e in pool if e['idx'] not in exclude))
    cash=1.0; op=[]; n=0; contrib=defaultdict(float); taken=[]
    for dt in alld:
        keep=[]
        for rd,inv,g,ix in op:
            if rd<=dt:
                cash+=inv*nm(g); contrib[ix]+=inv*nm(g)-inv
            else: keep.append((rd,inv,g,ix))
        op=keep
        c=byday.get(dt,[])
        if not c: continue
        rng.shuffle(c)
        for e in c:
            if len(op)>=slots: break
            eq=cash+sum(x[1] for x in op); s=min(eq/slots,cash)
            if s<=1e-9: break
            cash-=s; op.append((e['resolve_date'],s,e['gain_at_resolve_pct'],e['idx'])); n+=1; taken.append(e['idx'])
    for rd,inv,g,ix in op:
        cash+=inv*nm(g); contrib[ix]+=inv*nm(g)-inv
    if track: return (cash-1)*100, n, dict(contrib)
    return (cash-1)*100, n
def run(pool,exclude=frozenset(),slots=5,ns=NS):
    rs=[];nt=[]
    for s in range(ns):
        r,t=sim(pool,s,slots=slots,exclude=exclude); rs.append(r); nt.append(t)
    rs_s=sorted(rs)
    return dict(med=st.median(rs), mean=st.mean(rs), p10=rs_s[int(.10*ns)], p90=rs_s[int(.90*ns)],
                pos=100*sum(1 for x in rs if x>0)/ns, ntr=st.median(nt), rs=rs)

ALL=CONF; UP=[e for e in CONF if e['up']]
base_all=run(ALL); base_up=run(UP)
print('=== 재현 (확정 580건, 미래에셋 수수료, 슬롯5, 300회 무작위순서) ===')
print(f"전부매수  : 중앙 {base_all['med']:+.2f}%  평균 {base_all['mean']:+.2f}%  거래 {base_all['ntr']:.0f}건  (보고값 +1.6%)")
print(f"상승국면만: 중앙 {base_up['med']:+.2f}%  평균 {base_up['mean']:+.2f}%  거래 {base_up['ntr']:.0f}건  (보고값 +35.4%)")

# ---- A. 이벤트 풀에서 수익률 상위 k개 제거 (경로 무관) ----
print('\n=== A. 상승국면 풀에서 수익률 상위 k건을 아예 삭제 ===')
upsorted=sorted(UP,key=lambda e:-e['gain_at_resolve_pct'])
print('상위 10건:', [(e['name'].encode('cp949',errors='replace').decode('cp949'),e['entry_date'],round(e['gain_at_resolve_pct'],1)) for e in upsorted[:10]][:5])
for k in [0,1,2,3,5,10,20]:
    ex=frozenset(e['idx'] for e in upsorted[:k])
    r=run(UP,exclude=ex)
    ra=run(ALL,exclude=ex)
    g=[e['gain_at_resolve_pct'] for e in UP if e['idx'] not in ex]
    print(f"k={k:2d} 제거 → 슬롯5 상승국면 중앙 {r['med']:+7.2f}% (평균{r['mean']:+7.2f}, P10 {r['p10']:+7.2f}, 플러스비율 {r['pos']:5.1f}%, {r['ntr']:.0f}건) | 같은 종목 뺀 전부매수 {ra['med']:+7.2f}% | 건당평균 {st.mean(g):+5.2f}%")
