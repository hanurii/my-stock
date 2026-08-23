import json,os,numpy as np,collections,random
SP = r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
C=json.load(open(os.path.join(SP,'clean.json'),encoding='utf-8'))
print('pct8 분포', collections.Counter(round(r['pct']['8']) for r in C).most_common(8))
print('rs 분포', np.percentile([r['rs'] for r in C],[0,10,50,90,100]))
print('score==0 건수', sum(1 for r in C if r['score']==0), '/', len(C))
print(' 그 병목', collections.Counter(r['tightest'] for r in C if r['score']==0))
sr=lambda g: sum(1 for r in g if r['w10'][0]=='stop')/len(g)*100 if g else float('nan')
z=[r for r in C if r['score']==0]; nz=[r for r in C if r['score']>0]
print(f' score=0 손절={sr(z):.1f}%(n={len(z)}) vs >0 손절={sr(nz):.1f}%(n={len(nz)})')

rng=random.Random(23); codes=sorted(set(r['code'] for r in C))
bc=collections.defaultdict(list)
for r in C: bc[r['code']].append(r)
def boot(fn,B=4000):
    obs=fn(C); o=[]
    for _ in range(B):
        s=[]
        for _ in range(len(codes)): s+=bc[rng.choice(codes)]
        v=fn(s)
        if v==v: o.append(v)
    o=np.array(o); return obs,np.percentile(o,2.5),np.percentile(o,97.5),float(np.mean(o>=0)),float(np.mean(o<=0))

vs=sorted(r['vol'] for r in C); q=[np.percentile(vs,p) for p in (25,50,75)]
def qi(v): return 0 if v<=q[0] else 1 if v<=q[1] else 2 if v<=q[2] else 3

# 변동성 축의 순수수익 차 (규칙 제거)
def volraw(g):
    m=np.median([r['vol'] for r in g])
    a=[r for r in g if r['vol']>m]; b=[r for r in g if r['vol']<=m]
    if len(a)<5 or len(b)<5: return float('nan')
    return np.mean([r['raw10'] for r in a])-np.mean([r['raw10'] for r in b])
import sys; sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix
cache={}
for r in C:
    c=r['code']
    if c not in cache: cache[c]=ohlcv_matrix.get_series(c)
    s=cache[c]; i=list(s['dates']).index(r['date'])
    r['raw10']=(s['closes'][i+10]/r['rec_price']-1)*100
o,l,h,pp,pn=boot(volraw)
print(f'\n[J] 변동성 상위-하위 *순수10일수익* 차 = {o:+.2f}%p CI[{l:+.2f},{h:+.2f}] P(>=0)={pp:.3f}')
def volstop(g):
    m=np.median([r['vol'] for r in g]); a=[r for r in g if r['vol']>m]; b=[r for r in g if r['vol']<=m]
    if len(a)<5 or len(b)<5: return float('nan')
    return sr(a)-sr(b)
o,l,h,pp,pn=boot(volstop); print(f'[J2] 변동성 상위-하위 손절률차 = {o:+.1f}%p CI[{l:+.1f},{h:+.1f}] P(<=0)={pn:.3f}')

# 7 cohort, volatility controlled
def coh7(g):
    num=0;den=0
    for i in range(4):
        a=[r for r in g if qi(r['vol'])==i and r['tightest']=='7']; b=[r for r in g if qi(r['vol'])==i and r['tightest']!='7']
        if len(a)<3 or len(b)<3: continue
        w=len(a)+len(b); num+=w*(sr(a)-sr(b)); den+=w
    return num/den if den else float('nan')
def coh7raw(g):
    a=[r for r in g if r['tightest']=='7']; b=[r for r in g if r['tightest']!='7']
    if len(a)<5 or len(b)<5: return float('nan')
    return sr(a)-sr(b)
o,l,h,pp,pn=boot(coh7raw); print(f'\n[K] ⑦병목 코호트 손절률차(통제전)={o:+.1f}%p CI[{l:+.1f},{h:+.1f}] P(<=0)={pn:.3f}  (본페로니 기준 .006)')
o,l,h,pp,pn=boot(coh7);   print(f'[K2] ⑦병목 변동성층 통제후={o:+.1f}%p CI[{l:+.1f},{h:+.1f}] P(<=0)={pn:.3f}')
def coh6(g):
    a=[r for r in g if r['tightest']=='6']; b=[r for r in g if r['tightest']!='6']
    if len(a)<5 or len(b)<5: return float('nan')
    return sr(a)-sr(b)
o,l,h,pp,pn=boot(coh6); print(f'[K3] ⑥병목 코호트 손절률차(통제전)={o:+.1f}%p CI[{l:+.1f},{h:+.1f}] P(>=0)={pp:.3f}')

# 20-day window replication of the draft boundary
A=json.load(open(os.path.join(SP,'an.json'),encoding='utf-8'))
gaps={r['code']+r['date']:None for r in C}
W=[r for r in A if r['w20'] and r['vol'] is not None and (r['code']+r['date']) in gaps]
sr20=lambda g: sum(1 for r in g if r['w20'][0]=='stop')/len(g)*100 if g else float('nan')
print(f'\n[L] 20일창 (오염제거 n={len(W)})')
for lab,f in [('R<20',lambda x:x<20),('Y20-50',lambda x:20<=x<50),('G>=50',lambda x:x>=50)]:
    g=[r for r in W if f(r['score'])]
    print(f'  {lab:7s} n={len(g):3d} 손절={sr20(g):5.1f}% 규칙수익={np.mean([r["w20"][1] for r in g]):+.2f}%')
for i in range(4):
    g=[r for r in W if qi(r['vol'])==i]
    print(f'  변동성Q{i+1} n={len(g):3d} 손절={sr20(g):5.1f}% 규칙수익={np.mean([r["w20"][1] for r in g]):+.2f}%')
