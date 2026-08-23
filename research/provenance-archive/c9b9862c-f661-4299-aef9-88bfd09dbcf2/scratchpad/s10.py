import json, random, statistics
from collections import defaultdict
SP="C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/"
EV0=json.load(open(SP+'feat.json',encoding='utf-8'))
FEE=0.0034
ALLD=sorted({e['entry_date'] for e in EV0}|{e['resolve_date'] for e in EV0})
def prep(mode='pivot'):
    EV=[dict(e) for e in EV0]
    for e in EV:
        p,en,r=e['pivot'],e['entry_price'],e['result']
        if mode=='pivot':
            ex=p*1.20 if r=='win' else (p*0.90 if r in('loss','ambiguous') else p*(1+e['gain_at_resolve_pct']/100)); e['_full']=ex/en-1
        else:
            e['_full']=0.20 if r=='win' else (-0.10 if r in('loss','ambiguous') else (p*(1+e['gain_at_resolve_pct']/100))/en-1)
        e['_cut']=e['d1_close']/en-1; e['_cuttable']=e['days_held']>=1
    return EV
def run(EV,seed,cutset,sameday):
    """cutset: 'rule:-2' | set of ids | None"""
    rnd=random.Random(seed); bd=defaultdict(list)
    for e in EV: bd[e['entry_date']].append(e)
    eq=[1.0]*6; free=[None]*6
    for d in ALLD:
        for i in range(6):
            if free[i] is not None and (free[i]<=d if sameday else free[i]<d): free[i]=None
        cs=list(bd.get(d,[])); rnd.shuffle(cs)
        for e in cs:
            try: i=free.index(None)
            except ValueError: break
            eid=e['code']+e['entry_date']
            do_cut = e['_cuttable'] and (cutset is not None and (eid in cutset))
            if do_cut: r,rd=e['_cut'],e['entry_date']
            else: r,rd=e['_full'],e['resolve_date']
            eq[i]*=(1+r-FEE); free[i]=rd
    return sum(eq)/6-1
for mode in ['pivot','entry']:
 for sameday in [False,True]:
    EV=prep(mode)
    bd=defaultdict(list)
    for e in EV: bd[e['entry_date']].append(e)
    realset={e['code']+e['entry_date'] for e in EV if e['_cuttable'] and e['d1_ret']<-2}
    perday={d:sum(1 for e in xs if e['_cuttable'] and e['d1_ret']<-2) for d,xs in bd.items()}
    rr=random.Random(99)
    diffs=[]
    for s in range(300):
        randset=set()
        for d,xs in bd.items():
            c=[e for e in xs if e['_cuttable']]
            k=min(perday[d],len(c))
            if k: randset|={e['code']+e['entry_date'] for e in rr.sample(c,k)}
        diffs.append(run(EV,s,realset,sameday)-run(EV,s,randset,sameday))
    m=statistics.mean(diffs); sd=statistics.pstdev(diffs)
    print(f'{mode:5s} sameday={str(sameday):5s} 컷-2(실제) − 같은날동수무작위컷: 평균 {m*100:+6.1f}%p ± {sd*100:4.1f}  우세비율 {sum(1 for x in diffs if x>0)/len(diffs)*100:.0f}%')
