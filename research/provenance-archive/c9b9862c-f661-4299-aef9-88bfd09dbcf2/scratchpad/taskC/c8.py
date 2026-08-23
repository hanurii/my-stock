import json,os,collections
S=os.environ['SCRATCH']
rows=json.load(open(os.path.join(S,'taskC','joinedC2.json'),encoding='utf-8'))
LAB={"1":"① 150·200일선","2":"② 150>200","3":"③ 200일선상승","4":"④ 50일선정렬","5":"⑤ 50일선","6":"⑥ 52주저가","7":"⑦ 52주고가","8":"⑧ RS"}
H=[r for r in rows if r.get('h10')]
for r in H:
    o=r['h10']['out']; r['is_stop']=1 if o=='stop' else 0
    r['rule_ret']=-10.0 if o=='stop' else (20.0 if o=='target' else r['h10']['ret'])
bands=[(0,20),(20,50),(50,100),(100,101)]
print('=== 2b) 조건별 pct 구간 손절률 / 규칙수익 (10일창 n=350, 전체손절률 42.9%) ===')
for k in '12345678':
    print(LAB[k])
    for lo,hi in bands:
        rs=[r for r in H if lo<=r['pct_'+k]<hi]
        if not rs: print(f"   {lo:>3}~{hi:<4} n=  0"); continue
        n=len(rs); s=sum(r['is_stop'] for r in rs); rr=sum(r['rule_ret'] for r in rs)/n
        cd=len({r['code'] for r in rs})
        lab='100(상한)' if lo==100 else f'{lo}~{hi}'
        print(f"   {lab:<9} n={n:>3} 종목{cd:>3}  손절률 {100*s/n:>5.1f}%  규칙수익 {rr:>6.2f}%")
