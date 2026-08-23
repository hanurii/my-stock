import json, random, statistics
from collections import defaultdict
SP="C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/"
EV=json.load(open(SP+'feat.json',encoding='utf-8'))
FEE=0.0034
def full_ret(e):
    p,en=e['pivot'],e['entry_price']; r=e['result']
    ex = p*1.20 if r=='win' else (p*0.90 if r in ('loss','ambiguous') else p*(1+e['gain_at_resolve_pct']/100))
    return ex/en-1
for e in EV:
    e['_full']=full_ret(e); e['_cut']=e['d1_close']/e['entry_price']-1
    e['_cuttable']=e['days_held']>=1
DATES=sorted({e['entry_date'] for e in EV})
ALLD=sorted({e['entry_date'] for e in EV} | {e['resolve_date'] for e in EV})
byday=defaultdict(list)
for e in EV: byday[e['entry_date']].append(e)

def run(keyfn, slots=6, cut=None, seed=None):
    rnd=random.Random(seed)
    eq=[1.0]*slots
    free=[None]*slots   # None=free, else date까지 점유
    trades=[]
    for d in ALLD:
        # 만기 해제
        for i in range(slots):
            if free[i] is not None and free[i] < d: free[i]=None
        cands=byday.get(d,[])
        if not cands: continue
        order=sorted(cands, key=lambda e: keyfn(e,rnd))
        for e in order:
            try: i=free.index(None)
            except ValueError: break
            if cut is not None and e['_cuttable'] and e['d1_ret']<cut:
                r=e['_cut']; rd=e['entry_date']
            else:
                r=e['_full']; rd=e['resolve_date']
            r-=FEE
            eq[i]*= (1+r)
            free[i]=rd
            trades.append(r)
    tot=sum(eq)/slots-1
    return tot, len(trades), statistics.mean(trades)

RULES={
 '거래대금 큰 순': lambda e,r: -e['turnover_eok'],
 '거래대금 작은 순': lambda e,r: e['turnover_eok'],
 'RS 높은 순': lambda e,r: -e['rs'],
 '갭업 작은 순': lambda e,r: e['gap_up_pct'],
 'ATR 낮은 순': lambda e,r: e['atr_pct'],
 '가나다(선착순 대용)': lambda e,r: e['code'],
}
print('=== 6슬롯, 컷 없음 ===')
for name,f in RULES.items():
    t,n,m=run(f)
    print(f'{name:16s} 슬롯당누적 {t*100:6.1f}%  거래 {n:4d}  건당 {m*100:+.2f}%')
sims=[run(lambda e,r: r.random(), seed=s) for s in range(300)]
mu=statistics.mean(s[0] for s in sims); sd=statistics.pstdev(s[0] for s in sims)
print(f'{"무작위순서(300회)":16s} 슬롯당누적 {mu*100:6.1f}% ± {sd*100:.1f}  거래 {statistics.mean(s[1] for s in sims):.0f}')
print('  거래대금순 백분위:', sum(1 for s in sims if s[0] < run(RULES['거래대금 큰 순'])[0])/len(sims))

print('\n=== 6슬롯 + 1일차 종가컷 ===')
for cut in [None,1,0,-1,-2,-3,-5]:
    t,n,m = run(RULES['거래대금 큰 순'], cut=cut)
    t2,n2,m2 = run(lambda e,r: e['code'], cut=cut)
    sims=[run(lambda e,r: r.random(), cut=cut, seed=s)[0] for s in range(200)]
    print(f'컷 {str(cut):>4}: 거래대금순 {t*100:6.1f}% (n={n}, 건당 {m*100:+.2f}%) | 가나다순 {t2*100:6.1f}% | 무작위 {statistics.mean(sims)*100:6.1f}%±{statistics.pstdev(sims)*100:.1f}')

print('\n=== 컷 대상 무작위 대조(동수) — 6슬롯, 거래대금순 ===')
def run_randcut(ncut, seed):
    rnd=random.Random(seed)
    cuttable=[e['code']+e['entry_date'] for e in EV if e['_cuttable']]
    pick=set(rnd.sample(cuttable, ncut))
    def keyf(e,r): return -e['turnover_eok']
    eq=[1.0]*6; free=[None]*6; trades=[]
    for d in ALLD:
        for i in range(6):
            if free[i] is not None and free[i]<d: free[i]=None
        for e in sorted(byday.get(d,[]), key=lambda e:-e['turnover_eok']):
            try: i=free.index(None)
            except ValueError: break
            if e['code']+e['entry_date'] in pick:
                r=e['_cut']; rd=e['entry_date']
            else:
                r=e['_full']; rd=e['resolve_date']
            r-=FEE; eq[i]*=(1+r); free[i]=rd; trades.append(r)
    return sum(eq)/6-1, len(trades)
ncut=sum(1 for e in EV if e['_cuttable'] and e['d1_ret']<-2)
real=run(RULES['거래대금 큰 순'], cut=-2)[0]
sims=[run_randcut(ncut, s)[0] for s in range(300)]
mu=statistics.mean(sims); sd=statistics.pstdev(sims)
print(f'컷-2 실제 {real*100:.1f}%  vs 동수무작위컷 {mu*100:.1f}%±{sd*100:.1f}  (백분위 {sum(1 for s in sims if s<real)/len(sims):.3f})')
