import json,os,collections
S=os.environ['SCRATCH']
rows=json.load(open(os.path.join(S,'taskC','joinedC2.json'),encoding='utf-8'))
L=[dict(r,d52=r['mrg_7']-25.0) for r in rows if r['outcome']]
deep=[r for r in L if r['d52']<-25]
print('=== 원장 딥베이스(52주고가 -25%% 초과) 건수 '+str(len(deep)))
for r in sorted(deep,key=lambda x:x['date']):
    print(f"  {r['date']} {r['name']:<12} 고가대비 {r['d52']:>6.1f}%  tightest {r['tightest']}  종합{r['gm_score']:>5.1f}  결과 {r['outcome']:<7} 현재 {r['cur_ret_pct']}  MFE {r['max_gain_pct']}")
print()
# ⑦ tightest 이면서 손절난 대표 사례
g=[r for r in L if r['tightest']=='7']
byc=collections.defaultdict(list)
for r in g: byc[r['code']].append(r)
print('=== 7이 병목인 종목수 '+str(len(byc)))
for c,v in sorted(byc.items(),key=lambda kv:-len(kv[1]))[:20]:
    s=sum(1 for r in v if r['outcome']=='stop'); t=sum(1 for r in v if r['outcome']=='target')
    print(f"  {v[0]['name']:<14} n={len(v):>2} 손절{s} +20%{t}  고가대비중앙 {sorted(r['d52'] for r in v)[len(v)//2]:>6.1f}%")
