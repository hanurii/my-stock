import json,os,numpy as np,collections,sys
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix
SP = r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
C=json.load(open(os.path.join(SP,'clean.json'),encoding='utf-8'))
A=json.load(open(os.path.join(SP,'an.json'),encoding='utf-8'))
print('[M] 전체 원장(517)에서 score==0:', sum(1 for r in A if r['score']==0),'/',len(A),
      collections.Counter(r['tightest'] for r in A if r['score']==0))
cache={}
for r in C:
    c=r['code']
    if c not in cache: cache[c]=ohlcv_matrix.get_series(c)
    s=cache[c]; i=list(s['dates']).index(r['date'])
    r['raw10']=(s['closes'][i+10]/r['rec_price']-1)*100
vs=sorted(r['vol'] for r in C); q=[np.percentile(vs,p) for p in (25,50,75)]
def qi(v): return 0 if v<=q[0] else 1 if v<=q[1] else 2 if v<=q[2] else 3
print('\n[N] 변동성 분위별 *종목 수* (반복추천 집중도 점검)')
for i in range(4):
    g=[r for r in C if qi(r['vol'])==i]
    cnt=collections.Counter(r['code'] for r in g)
    print(f'  Q{i+1} n={len(g):3d} 종목={len(cnt):2d} 최다종목비중={max(cnt.values())/len(g)*100:.0f}% 상위3종목={sum(sorted(cnt.values(),reverse=True)[:3])/len(g)*100:.0f}%')
print('\n[O] 종목단위(각 종목 1표, 평균) 변동성 vs 순수10일수익')
byc=collections.defaultdict(list)
for r in C: byc[r['code']].append(r)
pts=[(np.mean([x['vol'] for x in g]), np.mean([x['raw10'] for x in g]), np.mean([1 if x['w10'][0]=='stop' else 0 for x in g])) for g in byc.values()]
pts.sort()
h=len(pts)//2
print(f'  종목 {len(pts)}개 — 저변동 절반: 평균수익={np.mean([p[1] for p in pts[:h]]):+.2f}% 손절률={np.mean([p[2] for p in pts[:h]])*100:.1f}%')
print(f'             고변동 절반: 평균수익={np.mean([p[1] for p in pts[h:]]):+.2f}% 손절률={np.mean([p[2] for p in pts[h:]])*100:.1f}%')
from math import sqrt
a=[p[1] for p in pts[:h]]; b=[p[1] for p in pts[h:]]
se=sqrt(np.var(a,ddof=1)/len(a)+np.var(b,ddof=1)/len(b)); print(f'             수익차={np.mean(b)-np.mean(a):+.2f}%p  t={(np.mean(b)-np.mean(a))/se:.2f}')
print('\n[P] 종합점수도 종목단위로')
pts2=[(np.mean([x['score'] for x in g]), np.mean([x['raw10'] for x in g]), np.mean([1 if x['w10'][0]=='stop' else 0 for x in g])) for g in byc.values()]
pts2.sort(); h2=len(pts2)//2
print(f'  저점수 절반: 수익={np.mean([p[1] for p in pts2[:h2]]):+.2f}% 손절률={np.mean([p[2] for p in pts2[:h2]])*100:.1f}%')
print(f'  고점수 절반: 수익={np.mean([p[1] for p in pts2[h2:]]):+.2f}% 손절률={np.mean([p[2] for p in pts2[h2:]])*100:.1f}%')
print('\n[Q] 변동성-종합점수 상관(관측치/종목단위)')
print('  관측치 spearman:', round(float(np.corrcoef(np.argsort(np.argsort([r['vol'] for r in C])), np.argsort(np.argsort([r['score'] for r in C])))[0,1]),3))
print('  종목단위 spearman:', round(float(np.corrcoef(np.argsort(np.argsort([p[0] for p in pts])), np.argsort(np.argsort([p[1] for p in pts])))[0,1]),3))
print('\n[R] 조건별 pct와 변동성 상관 (관측치)')
for k in '12345678':
    print(f'  {k}: r={np.corrcoef([r["pct"][k] for r in C],[r["vol"] for r in C])[0,1]:+.3f}')
print(f'  min: r={np.corrcoef([r["score"] for r in C],[r["vol"] for r in C])[0,1]:+.3f}')
