import json, os, sys
from collections import Counter
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad'
os.chdir('C:/Users/hanul/playground/my-stock')
A=json.load(open(SP+'/asof_scores.json',encoding='utf-8'))
L=json.load(open('public/data/sepa-buy-rec-ledger.json',encoding='utf-8'))
E=L['entries']
print('ledger n',len(E), 'target',L['target_pct'],'stop',L['stop_pct'])
print('date range', min(e['date'] for e in E), max(e['date'] for e in E))

miss=[]; joined=[]
same_day=0
for e in E:
    d=e['date']; c=e['code']
    if d in A and c in A[d] and A[d][c]['score'] is not None:
        same_day+=1
        r=dict(e); r['score']=A[d][c]['score']; r['tightest']=A[d][c]['tightest']
        r['per']=A[d][c]['per']; r['rs_a']=A[d][c]['rs']; r['ret252']=A[d][c]['ret252']
        r['low52']=A[d][c]['low52']; r['high52']=A[d][c]['high52']; r['px_a']=A[d][c]['px']
        r['all_pass']=A[d][c]['all_pass']
        joined.append(r)
    else:
        miss.append((d,c,e['name'], d in A))
print('joined(same-day)',same_day,'missing',len(miss))
print('missing detail:', miss)
json.dump(joined, open(SP+'/joined.json','w'), ensure_ascii=False)

res=[r for r in joined if r.get('resolved')]
print('with resolved', len(res))
closed=[r for r in res if r['resolved'].get('outcome')!='open']
print('closed',len(closed), Counter(r['resolved']['outcome'] for r in closed))
print('open', sum(1 for r in res if r['resolved']['outcome']=='open'))
print('no resolved field', sum(1 for r in joined if not r.get('resolved')))
print('unique codes closed', len(set(r['code'] for r in closed)))
cc=Counter(r['code'] for r in closed)
print('max repeats', cc.most_common(5))
# stop with max_gain>=20
print('stop with maxgain>=20', sum(1 for r in closed if r['resolved']['outcome']=='stop' and r['resolved']['max_gain_pct']>=20))
