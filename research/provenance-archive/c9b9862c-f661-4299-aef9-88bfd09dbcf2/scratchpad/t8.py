import json,os,numpy as np,collections,sys,random
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix
SP = r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
C=json.load(open(os.path.join(SP,'clean.json'),encoding='utf-8'))
cache={}
for r in C:
    c=r['code']
    if c not in cache: cache[c]=ohlcv_matrix.get_series(c)
    s=cache[c]; i=list(s['dates']).index(r['date'])
    r['raw10']=(s['closes'][i+10]/r['rec_price']-1)*100
sr=lambda g: sum(1 for r in g if r['w10'][0]=='stop')/len(g)*100
d7=lambda r: r['pct']['7']/100*20-25
print('[S] ⑦ 단독 컷 (52주고가 -10% 이내 = pct7>=75)')
for lab,f in [('고가 -10% 이내',lambda r: d7(r)>-10),('더 먼 쪽',lambda r: d7(r)<=-10)]:
    g=[r for r in C if f(r)]
    print(f'  {lab:14s} n={len(g):3d} 손절={sr(g):5.1f}% 규칙수익={np.mean([r["w10"][1] for r in g]):+.2f}% 순수10일={np.mean([r["raw10"] for r in g]):+.2f}% 목표={sum(1 for r in g if r["w10"][0]=="target")/len(g)*100:4.1f}%')
vs=sorted(r['vol'] for r in C); q=[np.percentile(vs,p) for p in (25,50,75)]
def qi(v): return 0 if v<=q[0] else 1 if v<=q[1] else 2 if v<=q[2] else 3
print('  변동성층 통제 후 ⑦컷 손절률차:')
num=0;den=0
for i in range(4):
    a=[r for r in C if qi(r['vol'])==i and d7(r)>-10]; b=[r for r in C if qi(r['vol'])==i and d7(r)<=-10]
    if len(a)<3 or len(b)<3: 
        print(f'    Q{i+1} n부족 (a={len(a)},b={len(b)})'); continue
    print(f'    Q{i+1}: 이내 {sr(a):5.1f}%(n={len(a):3d}) vs 먼쪽 {sr(b):5.1f}%(n={len(b):3d}) 차={sr(a)-sr(b):+.1f}%p')
    w=len(a)+len(b); num+=w*(sr(a)-sr(b)); den+=w
print(f'    가중평균 차 = {num/den:+.1f}%p')

print('\n[T] 변동성만으로 자른 실전 규칙 비교 (10일창, 오염제거 n=%d)'%len(C))
for lab,f in [('변동성<2.5% 만 매수',lambda r:r['vol']<2.5),('변동성<3.0%',lambda r:r['vol']<3.0),('변동성<4.0%',lambda r:r['vol']<4.0),('전부',lambda r:True)]:
    g=[r for r in C if f(r)]
    print(f'  {lab:18s} n={len(g):3d}({len(g)/len(C)*100:3.0f}%) 종목={len(set(r["code"] for r in g)):2d} 손절={sr(g):5.1f}% 규칙수익={np.mean([r["w10"][1] for r in g]):+.2f}% 순수={np.mean([r["raw10"] for r in g]):+.2f}%')
