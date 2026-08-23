import json, os, sys, statistics as st, collections
import numpy as np
from scipy import stats
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix
SCR=r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
store=json.load(open(os.path.join(SCR,'percond.json'),encoding='utf-8'))
led=json.load(open('public/data/sepa-buy-rec-ledger.json',encoding='utf-8'))['entries']
cache={}
def ser(c):
    if c not in cache:
        try: cache[c]=ohlcv_matrix.get_series(c)
        except Exception: cache[c]=None
    return cache[c]
H=10; rows=[]
for e in led:
    m=store.get(e['date'],{}).get(e['code'])
    if not m: continue
    s=ser(e['code'])
    if not s: continue
    try: i=s['dates'].index(e['date'])
    except ValueError: continue
    if i+H>=len(s['dates']): continue
    p0=e['rec_price']; w=slice(i+1,i+1+H)
    rows.append({'date':e['date'],'code':e['code'],'name':e['name'],'gm':m['score'],'m6':m['margin']['6']+30,
        'tight':m['label'],'r':(s['closes'][w][-1]/p0-1)*100,'hit':1 if (min(s['lows'][w])/p0-1)*100<=-10 else 0,
        'mfe':(max(s['highs'][w])/p0-1)*100})
print('H=10 n=%d 고유 %d'%(len(rows),len(set(r['code'] for r in rows))))
print('\n[52주저가 대비 상승폭 구간] (고정 10거래일)')
for lo,hi,lab in [(0,50,'~50%'),(50,100,'50~100%'),(100,150,'100~150%'),(150,300,'150~300%'),(300,1e9,'300%+')]:
    b=[r for r in rows if lo<=r['m6']<hi]
    if not b: continue
    k=sum(r['hit'] for r in b); ci=stats.binomtest(k,len(b)).proportion_ci()
    print('  %-10s n=%3d 고유%2d  -10터치 %.1f%% CI[%.0f,%.0f]  수익중앙 %+.2f%%  MFE중앙 %+.2f%%'%(
        lab,len(b),len(set(r['code'] for r in b)),100*k/len(b),100*ci.low,100*ci.high,st.median([r['r'] for r in b]),st.median([r['mfe'] for r in b])))
print('  Spearman m6 vs 터치 rho=%+.3f p=%.4g'%stats.spearmanr([r['m6'] for r in rows],[r['hit'] for r in rows])[:2])
# cluster perm for m6>=150
codes=sorted(set(r['code'] for r in rows)); byc={c:[r for r in rows if r['code']==c] for c in codes}
flat=[r for c in codes for r in byc[c]]
def stat(outs):
    hi=[o for r,o in zip(flat,outs) if r['m6']>=150]; lo=[o for r,o in zip(flat,outs) if r['m6']<150]
    return np.mean(hi)-np.mean(lo)
base=[r['hit'] for r in flat]; obs=stat(base)
rng=np.random.default_rng(9); cnt=0;N=5000
for _ in range(N):
    perm=rng.permutation(len(codes)); new=[]
    for i,cd in enumerate(codes):
        src=byc[codes[perm[i]]]
        for j,r in enumerate(byc[cd]): new.append(src[j%len(src)]['hit'])
    if abs(stat(new))>=abs(obs): cnt+=1
print('  m6>=150%% 터치 차이 %+.1f%%p, 종목블록 순열 p=%.4f'%(100*obs,cnt/N))
# 첫등장만
seen=set(); f=[]
for r in sorted(rows,key=lambda r:(r['date'],r['code'])):
    if r['code'] in seen: continue
    seen.add(r['code']); f.append(r)
hi=[r for r in f if r['m6']>=150]; lo=[r for r in f if r['m6']<150]
print('  첫등장만: >=150%% n=%d 터치 %.0f%% 수익중앙 %+.2f%% | <150%% n=%d 터치 %.0f%% 수익중앙 %+.2f%% Fisher p=%.4f'%(
    len(hi),100*np.mean([r['hit'] for r in hi]),st.median([r['r'] for r in hi]),
    len(lo),100*np.mean([r['hit'] for r in lo]),st.median([r['r'] for r in lo]),
    stats.fisher_exact([[sum(r['hit'] for r in hi),len(hi)-sum(r['hit'] for r in hi)],[sum(r['hit'] for r in lo),len(lo)-sum(r['hit'] for r in lo)]])[1]))
print('\n[가장 빡빡한 조건별 · 고정10일]')
for k,v in collections.Counter(r['tight'] for r in rows).most_common():
    b=[r for r in rows if r['tight']==k]
    print('  %-14s n=%3d 고유%2d 터치 %.1f%% 수익중앙 %+.2f%%'%(k,v,len(set(r['code'] for r in b)),100*np.mean([r['hit'] for r in b]),st.median([r['r'] for r in b])))
