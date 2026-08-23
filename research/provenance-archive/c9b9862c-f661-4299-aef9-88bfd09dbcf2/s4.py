import json, random, statistics
from collections import defaultdict
SP="C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/"
EV=json.load(open(SP+'feat.json',encoding='utf-8'))
FEE=0.0034
for e in EV:
    p,en,r=e['pivot'],e['entry_price'],e['result']
    ex = p*1.20 if r=='win' else (p*0.90 if r in ('loss','ambiguous') else p*(1+e['gain_at_resolve_pct']/100))
    e['_full']=ex/en-1; e['_cut']=e['d1_close']/en-1; e['_cuttable']=e['days_held']>=1
    e['_delta']=e['_cut']-e['_full']
C=[e for e in EV if e['_cuttable']]
byday=defaultdict(list)
for e in C: byday[e['entry_date']].append(e)
print('=== 컷의 금전 효과: Δ = (1일차 종가청산) − (끝까지 보유), 컷대상만 ===')
rnd=random.Random(11)
for cut in [1,0,-1,-2,-3,-5]:
    sel=[e for e in C if e['d1_ret']<cut]
    tot=sum(e['_delta'] for e in sel)
    per=tot/len(EV)  # 전체 1건당 기여
    # 같은날 동수 무작위 컷 순열 (3000회)
    perday={d:sum(1 for e in xs if e['d1_ret']<cut) for d,xs in byday.items()}
    sims=[]
    for _ in range(3000):
        s=0.0
        for d,xs in byday.items():
            k=perday[d]
            if k: s+=sum(e['_delta'] for e in rnd.sample(xs,k))
        sims.append(s)
    mu=statistics.mean(sims); sd=statistics.pstdev(sims)
    pv=sum(1 for s in sims if s>=tot)/len(sims)
    print(f'컷 {cut:>3}: 대상 {len(sel):3d}건  Δ합 {tot*100:+7.1f}%p (1건당기여 {per*100:+.3f}%p) | 같은날동수무작위 {mu*100:+.1f}±{sd*100:.1f}  p={pv:.4f}')
print()
print('=== 전후반 분할(진입일 2026-03-25 기준) — 컷 -2 ===')
for lab,f in [('전반', lambda e: e['entry_date']<'2026-03-25'), ('후반', lambda e: e['entry_date']>='2026-03-25')]:
    sub=[e for e in EV if f(e)]
    subC=[e for e in sub if e['_cuttable'] and e['d1_ret']<-2]
    resid=[e for e in sub if e['result'] in ('win','loss')]
    a=[e for e in resid if e['d1_ret']>=0]; b=[e for e in resid if e['d1_ret']<0]
    wa=sum(1 for x in a if x['result']=='win')/len(a)*100 if a else 0
    wb=sum(1 for x in b if x['result']=='win')/len(b)*100 if b else 0
    tot=sum(e['_delta'] for e in subC)
    print(f'{lab}: n={len(sub)} 승률 1일차+ {wa:.1f}%({len(a)}) vs 1일차- {wb:.1f}%({len(b)}) | 컷-2 Δ합 {tot*100:+.1f}%p, 1건당기여 {tot/len(sub)*100:+.3f}%p')
print()
print('=== 종목 블록 부트스트랩 (컷 -2 의 1건당 기여) ===')
bycode=defaultdict(list)
for e in EV: bycode[e['code']].append(e)
codes=list(bycode)
def stat(sample_codes):
    tot=0.0; n=0
    for c in sample_codes:
        for e in bycode[c]:
            n+=1
            if e['_cuttable'] and e['d1_ret']<-2: tot+=e['_delta']
    return tot/n if n else 0
obs=stat(codes)
bs=[stat([rnd.choice(codes) for _ in codes]) for _ in range(2000)]
lo,hi=sorted(bs)[50], sorted(bs)[1949]
print(f'관측 {obs*100:+.3f}%p, 종목블록 부트스트랩 95%CI [{lo*100:+.3f}, {hi*100:+.3f}]')
