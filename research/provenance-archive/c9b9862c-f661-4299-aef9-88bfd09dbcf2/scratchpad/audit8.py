import json, sys, math, statistics, random
from pathlib import Path
from collections import defaultdict
MAIN = Path(r"C:\Users\hanul\playground\my-stock")
sys.path.insert(0,str(MAIN/"scripts"))
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR=MAIN/".cache"/"ohlcv"/"series"
from canslim_lib.pivot_backtest import simulate_pivot_trade
d=json.load(open(MAIN/'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=d['events']
vals=sorted(e['atr_pct'] for e in ev); n=len(vals)
k=(n-1)*.25; f=int(k); q1c=vals[f]+(vals[min(f+1,n-1)]-vals[f])*(k-f)
for e in ev:
    s=ohlcv_matrix.get_series(e['code']); i=s['dates'].index(e['entry_date']); o=s['opens'][i]
    fill=o if (o and o>e['pivot']) else e['pivot']
    sim=simulate_pivot_trade(s,i,fill,20.0,10.0); rr=sim['result']
    if o and o>e['pivot'] and rr=='ambiguous' and sim['exit_reason']=='stop_on_breakout_day': rr='loss'
    e['rF']=rr; e['isQ1']=e['atr_pct']<=q1c
R=[e for e in ev if e['rF'] in ('win','loss')]
byday=defaultdict(list)
for e in R: byday[e['entry_date']].append(e)
pool=[(rows) for rows in byday.values() if any(x['isQ1'] for x in rows) and any(not x['isQ1'] for x in rows)]
pa=na=pb=nb=0; dd=[]
for rows in pool:
    a=[x for x in rows if x['isQ1']]; b=[x for x in rows if not x['isQ1']]
    aw=sum(1 for x in a if x['rF']=='win'); bw=sum(1 for x in b if x['rF']=='win')
    pa+=aw;na+=len(a);pb+=bw;nb+=len(b); dd.append((aw/len(a)-bw/len(b))*100)
obs=pa/na-pb/nb
print(f"[최종] 같은날 매칭({len(pool)}일, 갭업 시가체결 적용)")
print(f"  Q1 {pa}/{na}={pa/na*100:.1f}%   나머지 {pb}/{nb}={pb/nb*100:.1f}%   풀링차 {obs*100:+.1f}%p")
print(f"  일별 차이 평균 {statistics.mean(dd):+.1f}%p  중앙값 {statistics.median(dd):+.1f}%p")
pos=sum(1 for x in dd if x>0); neg=sum(1 for x in dd if x<0)
print(f"  부호 Q1우세 {pos}일 / 열세 {neg}일 / 동률 {len(dd)-pos-neg}일")
random.seed(3); cnt=0; N=30000
for _ in range(N):
    ca=cb=ta=tb=0
    for rows in pool:
        lab=[x['isQ1'] for x in rows]; random.shuffle(lab)
        for x,L in zip(rows,lab):
            w=x['rF']=='win'
            if L: ca+=w; ta+=1
            else: cb+=w; tb+=1
    if (ca/ta-cb/tb)>=obs: cnt+=1
print(f"  같은날 조건부 순열검정 p = {cnt/N:.4f}")
# 부트스트랩 신뢰구간(종목 클러스터)
codes=sorted({e['code'] for e in R}); bycode=defaultdict(list)
for e in R: bycode[e['code']].append(e)
random.seed(5); bs=[]
for _ in range(4000):
    samp=[]
    for _ in range(len(codes)): samp+=bycode[random.choice(codes)]
    a=[x for x in samp if x['isQ1']]; b=[x for x in samp if not x['isQ1']]
    if not a or not b: continue
    bs.append(sum(1 for x in a if x['rF']=='win')/len(a)*100 - sum(1 for x in b if x['rF']=='win')/len(b)*100)
bs.sort()
print(f"\n[부트스트랩] 통제없는 Q1 우위 95% 신뢰구간: {bs[int(.025*len(bs))]:+.1f}%p ~ {bs[int(.975*len(bs))]:+.1f}%p")
