import json, statistics
from collections import defaultdict
SP="C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/"
EV=json.load(open(SP+'feat.json',encoding='utf-8'))
for e in EV:
    p,en,r=e['pivot'],e['entry_price'],e['result']
    ex=p*1.20 if r=='win' else (p*0.90 if r in('loss','ambiguous') else p*(1+e['gain_at_resolve_pct']/100))
    e['_full']=ex/en-1; e['_cut']=e['d1_close']/en-1; e['_cuttable']=e['days_held']>=1
print('=== 컷 -2 대상의 실제 성격 (반기별) ===')
for lab,f in [('전반(~03-24)',lambda e:e['entry_date']<'2026-03-25'),('후반(03-25~)',lambda e:e['entry_date']>='2026-03-25')]:
    sel=[e for e in EV if f(e) and e['_cuttable'] and e['d1_ret']<-2]
    w=[e for e in sel if e['result']=='win']
    print(f'{lab}: 컷대상 {len(sel)}건 중 실제 승자 {len(w)}건 ({len(w)/len(sel)*100:.1f}%)  컷수익 평균 {statistics.mean(e["_cut"] for e in sel)*100:+.2f}%  보유시 평균 {statistics.mean(e["_full"] for e in sel)*100:+.2f}%  Δ평균 {statistics.mean(e["_cut"]-e["_full"] for e in sel)*100:+.2f}%p')
print()
print('=== 월별 Δ(컷-2) 합 ===')
bym=defaultdict(float); cnt=defaultdict(int)
for e in EV:
    if e['_cuttable'] and e['d1_ret']<-2:
        bym[e['entry_date'][:7]]+= (e['_cut']-e['_full']); cnt[e['entry_date'][:7]]+=1
for m in sorted(bym): print(f'  {m}: {bym[m]*100:+7.1f}%p ({cnt[m]}건)')
print()
print('=== 1일차 종가 규칙: 국면별 ===')
reg={r['date']:r['up'] for r in json.load(open('public/data/market-regime.json',encoding='utf-8'))['series']}
for up in [True,False]:
    sub=[e for e in EV if e['result'] in ('win','loss') and reg.get(e['entry_date'])==up]
    a=[e for e in sub if e['d1_ret']>=0]; b=[e for e in sub if e['d1_ret']<0]
    if a and b:
        print(f'{"상승" if up else "조정"}국면: 1일차+ {sum(1 for x in a if x["result"]=="win")/len(a)*100:.1f}%({len(a)}) vs 1일차- {sum(1 for x in b if x["result"]=="win")/len(b)*100:.1f}%({len(b)})')
