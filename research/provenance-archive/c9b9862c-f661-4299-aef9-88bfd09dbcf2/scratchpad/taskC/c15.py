import json,os,collections,math,sys
import numpy as np
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix
S=os.environ['SCRATCH']
rows=json.load(open(os.path.join(S,'taskC','joinedC2.json'),encoding='utf-8'))
cache={}
def ser(c):
    if c not in cache:
        try: cache[c]=ohlcv_matrix.get_series(c)
        except Exception: cache[c]=None
    return cache[c]
H=[]
for r in rows:
    h=r.get('h10')
    if not h: continue
    s=ser(r['code']); vol=None
    if s:
        try:
            i=s['dates'].index(r['date']); cl=s['closes'][max(0,i-20):i+1]
            rr=[(cl[j]/cl[j-1]-1)*100 for j in range(1,len(cl)) if cl[j-1]]
            if len(rr)>=10:
                m=sum(rr)/len(rr); vol=math.sqrt(sum((x-m)**2 for x in rr)/(len(rr)-1))
        except ValueError: pass
    q=dict(r); q['vol20']=vol; q['is_stop']=1 if h['out']=='stop' else 0
    q['rule_ret']=-10.0 if h['out']=='stop' else (20.0 if h['out']=='target' else h['ret'])
    q['tgt']=1 if h['out']=='target' else 0
    q['d52']=r['mrg_7']-25.0   # 52주고가 대비 % (음수)
    H.append(q)
print('=== 3) ⑦ 52주고가 거리 구간별 (10일창 n=%d) ==='%len(H))
bands=[(-100,-30),(-30,-25),(-25,-20),(-20,-15),(-15,-10),(-10,-5),(-5,0.001)]
print(f"{'52주고가 대비':<14}{'n':>4}{'종목':>5}{'손절률':>8}{'+20%':>7}{'규칙수익':>9}{'평균변동성':>10}")
for lo,hi in bands:
    g=[r for r in H if lo<=r['d52']<hi]
    if not g: continue
    v=[r['vol20'] for r in g if r['vol20']]
    print(f"{f'{lo:.0f}%~{hi:.0f}%':<14}{len(g):>4}{len({r['code'] for r in g}):>5}{100*sum(r['is_stop'] for r in g)/len(g):>8.1f}{100*sum(r['tgt'] for r in g)/len(g):>7.1f}{sum(r['rule_ret'] for r in g)/len(g):>9.2f}{(sum(v)/len(v) if v else float('nan')):>10.2f}")
print()
V=[r for r in H if r['vol20'] is not None]; V.sort(key=lambda r:r['vol20']); h=len(V)//2
print('=== 3b) 변동성 반분 안에서 딥베이스(-20% 초과 하락) vs 얕은 베이스 ===')
for nm,sel in [('저변동',V[:h]),('고변동',V[h:])]:
    deep=[r for r in sel if r['d52']<-20]; sh=[r for r in sel if r['d52']>=-20]
    f=lambda g:(len(g),100*sum(r['is_stop'] for r in g)/len(g),sum(r['rule_ret'] for r in g)/len(g)) if g else (0,float('nan'),float('nan'))
    a=f(deep); b=f(sh)
    print(f"  {nm}: 딥베이스 n={a[0]:>3} 손절 {a[1]:>5.1f}% 수익 {a[2]:>6.2f}%  |  얕은 n={b[0]:>3} 손절 {b[1]:>5.1f}% 수익 {b[2]:>6.2f}%")
print()
print('=== 3c) all_pass=False(⑦ 완화 gate_near 포함) vs True ===')
for k in (True,False):
    g=[r for r in H if r['all_pass']==k]
    if not g: continue
    v=[r['vol20'] for r in g if r['vol20']]
    print(f"  all_pass={k}: n={len(g)} 종목{len({r['code'] for r in g})} 손절 {100*sum(r['is_stop'] for r in g)/len(g):.1f}% 규칙수익 {sum(r['rule_ret'] for r in g)/len(g):+.2f}% 변동성 {sum(v)/len(v):.2f}%")
print()
print('=== 3d) 원장 전체(492, 최종 outcome)로 본 52주고가 거리 ===')
L=[dict(r,d52=r['mrg_7']-25.0) for r in rows if r['outcome']]
for lo,hi in bands:
    g=[r for r in L if lo<=r['d52']<hi]
    if not g: continue
    s=sum(1 for r in g if r['outcome']=='stop'); t=sum(1 for r in g if r['outcome']=='target')
    cr=[r['cur_ret_pct'] for r in g if r['cur_ret_pct'] is not None]
    print(f"  {lo:.0f}%~{hi:.0f}%  n={len(g):>3} 종목{len({r['code'] for r in g}):>3} 손절 {100*s/len(g):>5.1f}% +20% {100*t/len(g):>5.1f}% 현재수익 {sum(cr)/len(cr):>6.2f}%")
