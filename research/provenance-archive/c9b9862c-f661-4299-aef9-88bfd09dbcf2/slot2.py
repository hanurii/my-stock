import json, random, statistics
from collections import defaultdict
SP="C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/"
EV0=json.load(open(SP+'feat.json',encoding='utf-8'))
FEE=0.0034
byday=defaultdict(list)
ALLD=sorted({e['entry_date'] for e in EV0}|{e['resolve_date'] for e in EV0})

def prep(mode):
    EV=[dict(e) for e in EV0]
    for e in EV:
        p,en,r=e['pivot'],e['entry_price'],e['result']
        if mode=='pivot':
            ex = p*1.20 if r=='win' else (p*0.90 if r in ('loss','ambiguous') else p*(1+e['gain_at_resolve_pct']/100))
            e['_full']=ex/en-1
        else:  # entry 기준: 승 +20%, 패 -10%
            e['_full']= 0.20 if r=='win' else (-0.10 if r in ('loss','ambiguous') else (p*(1+e['gain_at_resolve_pct']/100))/en-1)
        e['_cut']=e['d1_close']/en-1
        e['_cuttable']=e['days_held']>=1
    return EV

def run(EV, keyfn, slots=6, cut=None, seed=None, sameday=False):
    rnd=random.Random(seed); bd=defaultdict(list)
    for e in EV: bd[e['entry_date']].append(e)
    eq=[1.0]*slots; free=[None]*slots; trades=[]
    for d in ALLD:
        for i in range(slots):
            if free[i] is not None and (free[i]<=d if sameday else free[i]<d): free[i]=None
        for e in sorted(bd.get(d,[]), key=lambda e: keyfn(e,rnd)):
            try: i=free.index(None)
            except ValueError: break
            if cut is not None and e['_cuttable'] and e['d1_ret']<cut:
                r,rd=e['_cut'],e['entry_date']
            else:
                r,rd=e['_full'],e['resolve_date']
            r-=FEE; eq[i]*=(1+r); free[i]=rd; trades.append(r)
    return sum(eq)/slots-1, len(trades)

for mode in ['pivot','entry']:
  for sameday in [False,True]:
    EV=prep(mode)
    lab=f'[{mode} 기준, 같은날재사용={sameday}]'
    base=run(EV, lambda e,r:-e['turnover_eok'], sameday=sameday)
    alpha=run(EV, lambda e,r:e['code'], sameday=sameday)
    rs=run(EV, lambda e,r:-e['rs'], sameday=sameday)
    c2=run(EV, lambda e,r:-e['turnover_eok'], cut=-2, sameday=sameday)
    sims=[run(EV, lambda e,r:r.random(), seed=s, sameday=sameday)[0] for s in range(300)]
    mu=statistics.mean(sims); sd=statistics.pstdev(sims)
    pct=sum(1 for s in sims if s<base[0])/len(sims)
    print(f'{lab} 거래대금순 {base[0]*100:6.1f}%(n={base[1]}) 가나다 {alpha[0]*100:6.1f}% RS순 {rs[0]*100:6.1f}% 컷-2 {c2[0]*100:6.1f}% | 무작위 {mu*100:6.1f}%±{sd*100:.1f} 거래대금순백분위 {pct:.2f}')
