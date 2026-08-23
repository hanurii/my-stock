import json,os,numpy as np,collections,random
SP = r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
A=json.load(open(os.path.join(SP,'an.json'),encoding='utf-8'))
D=[r for r in A if r['w10'] and r['vol'] is not None]
rng=random.Random(7)
codes=sorted(set(r['code'] for r in D))
bycode=collections.defaultdict(list)
for r in D: bycode[r['code']].append(r)

def cluster_boot(fn, B=4000):
    obs=fn(D); out=[]
    for _ in range(B):
        samp=[]
        for _ in range(len(codes)): samp+=bycode[rng.choice(codes)]
        v=fn(samp)
        if v==v: out.append(v)
    out=np.array(out)
    return obs, np.percentile(out,2.5), np.percentile(out,97.5), float(np.mean(out<=0)), float(np.mean(out>=0))

def gap_green_red(g):
    a=[r for r in g if r['score']>=50]; b=[r for r in g if r['score']<20]
    if not a or not b: return float('nan')
    return sum(1 for r in a if r['w10'][0]=='stop')/len(a)*100 - sum(1 for r in b if r['w10'][0]=='stop')/len(b)*100
o,l,h,pneg,ppos=cluster_boot(gap_green_red)
print(f'[A] G>=50 minus R<20 손절률차 = {o:+.1f}%p  cluster95%CI[{l:+.1f},{h:+.1f}]  P(<=0)={pneg:.3f}')

def volgap(g):
    med=np.median([r['vol'] for r in g])
    a=[r for r in g if r['vol']>med]; b=[r for r in g if r['vol']<=med]
    if not a or not b: return float('nan')
    return sum(1 for r in a if r['w10'][0]=='stop')/len(a)*100 - sum(1 for r in b if r['w10'][0]=='stop')/len(b)*100
o,l,h,pneg,_=cluster_boot(volgap)
print(f'[B] 변동성 상위-하위 손절률차 = {o:+.1f}%p  CI[{l:+.1f},{h:+.1f}]  P(<=0)={pneg:.3f}')

# within-volatility-stratum: does score band still reverse?
print('\n[C] 변동성 4분위 안에서 초안 경계 (손절률%, n)')
vs=sorted(r['vol'] for r in D); q=[np.percentile(vs,p) for p in (25,50,75)]
def qi(v): return 0 if v<=q[0] else 1 if v<=q[1] else 2 if v<=q[2] else 3
hdr='       '+ ' '.join(f'{"Q"+str(i+1):>14s}' for i in range(4)); print(hdr)
for lab,f in [('R<20',lambda x:x<20),('Y20-50',lambda x:20<=x<50),('G>=50',lambda x:x>=50)]:
    cells=[]
    for i in range(4):
        g=[r for r in D if qi(r['vol'])==i and f(r['score'])]
        cells.append(f'{(sum(1 for r in g if r["w10"][0]=="stop")/len(g)*100 if g else float("nan")):5.1f}%(n={len(g):3d})')
    print(f'{lab:7s}'+' '.join(cells))

# raw 10d buy&hold return (no stop rule) -- is the effect real or stop-mechanics?
import sys; sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix
cache={}
def raw(r,H=10):
    c=r['code']
    if c not in cache:
        try: cache[c]=ohlcv_matrix.get_series(c)
        except Exception: cache[c]=None
    s=cache[c]
    if not s: return None
    d=list(s['dates'])
    if r['date'] not in d: return None
    i=d.index(r['date'])
    if i+H>=len(d): return None
    return (s['closes'][i+H]/r['rec_price']-1)*100
for r in D: r['raw10']=raw(r)
R=[r for r in D if r['raw10'] is not None]
print('\n[D] 규칙없는 순수 10일 보유수익 (n=%d)'%len(R))
for i in range(4):
    g=[r for r in R if qi(r['vol'])==i]
    print(f'  변동성Q{i+1} n={len(g):3d} raw={np.mean([x["raw10"] for x in g]):+6.2f}%  중앙값={np.median([x["raw10"] for x in g]):+6.2f}%')
for lab,f in [('R<20',lambda x:x<20),('Y20-50',lambda x:20<=x<50),('G>=50',lambda x:x>=50)]:
    g=[r for r in R if f(r['score'])]
    print(f'  {lab:7s} n={len(g):3d} raw={np.mean([x["raw10"] for x in g]):+6.2f}%  중앙값={np.median([x["raw10"] for x in g]):+6.2f}%')
