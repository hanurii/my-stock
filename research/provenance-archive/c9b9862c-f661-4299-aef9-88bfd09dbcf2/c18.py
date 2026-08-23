import json,os,collections
S=os.environ['SCRATCH']
rows=json.load(open(os.path.join(S,'taskC','joinedC2.json'),encoding='utf-8'))
L=[r for r in rows if r['outcome']]
z=[r for r in L if r['gm_score']<=0.05]
print('종합점수 0 인 건수:',len(z),'/',len(L), '(%.1f%%)'%(100*len(z)/len(L)))
print(' 그중 tightest 분포:',sorted(collections.Counter(r['tightest'] for r in z).items()))
print(' 0점 손절률 %.1f%%  0점 아닌 것 %.1f%%'%(
  100*sum(1 for r in z if r['outcome']=='stop')/len(z),
  100*sum(1 for r in L if r['outcome']=='stop' and r['gm_score']>0.05)/sum(1 for r in L if r['gm_score']>0.05)))
print()
H=[r for r in rows if r.get('h10')]
for r in H:
    o=r['h10']['out']; r['is_stop']=1 if o=='stop' else 0
    r['rule_ret']=-10.0 if o=='stop' else (20.0 if o=='target' else r['h10']['ret'])
print('=== 참고: 현행 초안 경계(종합 min)로 자른 결과 (10일창) ===')
for lo,hi,lab in [(0,20,'🔴<20'),(20,50,'🟡20~50'),(50,101,'🟢>=50')]:
    g=[r for r in H if lo<=r['gm_score']<hi]
    if not g: continue
    print('  %-9s n=%3d 종목%3d 손절률 %5.1f%%  규칙수익 %+6.2f%%'%(lab,len(g),len({r['code'] for r in g}),
        100*sum(r['is_stop'] for r in g)/len(g), sum(r['rule_ret'] for r in g)/len(g)))
print()
print('=== 참고: ⑦ 단독 경계로 자른 결과 (10일창) ===')
for lo,hi,lab in [(0,20,'⑦<20'),(20,50,'⑦20~50'),(50,101,'⑦>=50')]:
    g=[r for r in H if lo<=r['pct_7']<hi]
    if not g: continue
    print('  %-9s n=%3d 종목%3d 손절률 %5.1f%%  규칙수익 %+6.2f%%'%(lab,len(g),len({r['code'] for r in g}),
        100*sum(r['is_stop'] for r in g)/len(g), sum(r['rule_ret'] for r in g)/len(g)))
