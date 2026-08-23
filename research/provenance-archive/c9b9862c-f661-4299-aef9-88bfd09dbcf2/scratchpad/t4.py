import json,os,numpy as np,sys,collections,random
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix
SP = r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
A=json.load(open(os.path.join(SP,'an.json'),encoding='utf-8'))
D=[r for r in A if r['w10'] and r['vol'] is not None]
cache={}
def s_(c):
    if c not in cache: cache[c]=ohlcv_matrix.get_series(c)
    return cache[c]
for r in D:
    s=s_(r['code']); i=list(s['dates']).index(r['date'])
    r['gap']=(r['rec_price']/s['closes'][i]-1)*100
BAD=[r for r in D if abs(r['gap'])>5]
print('가격괴리>5% 관측치',len(BAD),'종목',collections.Counter((r['name'],round(r['gap'])) for r in BAD))
print('그중 10일창 판정:',collections.Counter(r['w10'][0] for r in BAD))
print('그중 점수대:',collections.Counter(('R' if r['score']<20 else 'Y' if r['score']<50 else 'G') for r in BAD))
print('그중 변동성:', np.percentile([r['vol'] for r in BAD],[0,50,100]).round(2))

C=[r for r in D if abs(r['gap'])<=5]
print('\n=== 오염 제거 후 n=%d, 종목=%d ==='%(len(C),len(set(r['code'] for r in C))))
def stat(g):
    if not g: return (0,float('nan'),float('nan'))
    return (len(g), sum(1 for r in g if r['w10'][0]=='stop')/len(g)*100, np.mean([r['w10'][1] for r in g]))
print('-- 초안 경계 --')
for lab,f in [('R<20',lambda x:x<20),('Y20-50',lambda x:20<=x<50),('G>=50',lambda x:x>=50)]:
    g=[r for r in C if f(r['score'])]; n,s,ret=stat(g)
    print(f'  {lab:7s} n={n:4d} 종목={len(set(r["code"] for r in g)):3d} 손절={s:5.1f}% 규칙수익={ret:+.2f}%')
print('-- 변동성 4분위 --')
vs=sorted(r['vol'] for r in C); q=[np.percentile(vs,p) for p in (25,50,75)]
def qi(v,q=q): return 0 if v<=q[0] else 1 if v<=q[1] else 2 if v<=q[2] else 3
for i in range(4):
    g=[r for r in C if qi(r['vol'])==i]; n,s,ret=stat(g)
    print(f'  Q{i+1} n={n:3d} 손절={s:5.1f}% 규칙수익={ret:+.2f}% 순수10일={np.mean([x["raw10"] if "raw10" in x else 0 for x in g]):+.2f}')

rng=random.Random(11)
codes=sorted(set(r['code'] for r in C)); bc=collections.defaultdict(list)
for r in C: bc[r['code']].append(r)
def boot(fn,B=4000):
    obs=fn(C); o=[]
    for _ in range(B):
        s=[]
        for _ in range(len(codes)): s+=bc[rng.choice(codes)]
        v=fn(s)
        if v==v: o.append(v)
    o=np.array(o); return obs,np.percentile(o,2.5),np.percentile(o,97.5),float(np.mean(o<=0))
def gr(g):
    a=[r for r in g if r['score']>=50]; b=[r for r in g if r['score']<20]
    if not a or not b: return float('nan')
    return sum(1 for r in a if r['w10'][0]=='stop')/len(a)*100-sum(1 for r in b if r['w10'][0]=='stop')/len(b)*100
o,l,h,p=boot(gr); print(f'\n[A2 오염제거] G-R 손절률차={o:+.1f}%p CI[{l:+.1f},{h:+.1f}] P(<=0)={p:.3f}')

# 변동성 층 내부에서 G vs R (composition 제거)
print('\n[C2] 변동성 4분위 내 G vs R')
for i in range(4):
    a=[r for r in C if qi(r['vol'])==i and r['score']>=50]; b=[r for r in C if qi(r['vol'])==i and r['score']<20]
    fa=sum(1 for r in a if r['w10'][0]=='stop')/len(a)*100 if a else float('nan')
    fb=sum(1 for r in b if r['w10'][0]=='stop')/len(b)*100 if b else float('nan')
    print(f'  Q{i+1}: G {fa:5.1f}%(n={len(a):3d}) vs R {fb:5.1f}%(n={len(b):3d})  차={fa-fb:+.1f}%p')
# 층내 가중평균 차 (Mantel-Haenszel 식)
def strat_gap(g,q=q):
    num=0;den=0
    for i in range(4):
        a=[r for r in g if qi(r['vol'])==i and r['score']>=50]; b=[r for r in g if qi(r['vol'])==i and r['score']<20]
        if len(a)<3 or len(b)<3: continue
        w=len(a)+len(b)
        num+= w*(sum(1 for r in a if r['w10'][0]=='stop')/len(a)-sum(1 for r in b if r['w10'][0]=='stop')/len(b))*100
        den+= w
    return num/den if den else float('nan')
o,l,h,p=boot(strat_gap); print(f'[C3] 변동성층 통제 후 G-R 차={o:+.1f}%p CI[{l:+.1f},{h:+.1f}] P(<=0)={p:.3f}')
json.dump(C,open(os.path.join(SP,'clean.json'),'w',encoding='utf-8'),ensure_ascii=False)
