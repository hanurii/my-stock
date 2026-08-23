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
def qq(p):
    k=(n-1)*p; f=int(k); c=min(f+1,n-1); return vals[f]+(vals[c]-vals[f])*(k-f)
q1c,q2c,q3c=qq(.25),qq(.5),qq(.75)
def band(v): return "Q1" if v<=q1c else "Q2" if v<=q2c else "Q3" if v<=q3c else "Q4"

# 갭업 시가체결로 결과·보유일 재계산
for e in ev:
    s=ohlcv_matrix.get_series(e['code']); i=s['dates'].index(e['entry_date']); o=s['opens'][i]
    fill=o if (o and o>e['pivot']) else e['pivot']
    sim=simulate_pivot_trade(s,i,fill,20.0,10.0); rr=sim['result']
    if o and o>e['pivot'] and rr=='ambiguous' and sim['exit_reason']=='stop_on_breakout_day': rr='loss'
    e['rF']=rr; e['dF']=sim.get('days_held'); e['Q']=band(e['atr_pct'])

print("=== [I] 자본 효율: 기대값 ÷ 보유일 (갭업 시가체결 기준) ===")
print(f"  {'구간':<6}{'승률':>7}{'기대값/거래':>12}{'평균보유일':>10}{'일당 기대값':>12}")
for k in ("Q1","Q2","Q3","Q4"):
    rows=[e for e in ev if e['Q']==k and e['rF'] in ('win','loss')]
    w=sum(1 for r in rows if r['rF']=='win'); l=len(rows)-w
    evv=(w*20-l*10)/len(rows)
    dh=statistics.mean([r['dF'] for r in rows if r['dF'] is not None])
    print(f"  {k:<6}{w/len(rows)*100:>6.1f}%{evv:>+11.2f}%{dh:>10.1f}{evv/dh:>+11.3f}%")

print("\n=== [J] 두 보정 동시 적용: 갭업 시가체결 + 월 통제 ===")
R=[e for e in ev if e['rF'] in ('win','loss')]
bymon=defaultdict(list)
for e in R: bymon[e['month']].append(e)
diffs=[];W=[];mhn=mhd=0
for m in sorted(bymon):
    a=[e for e in bymon[m] if e['Q']=='Q1']; b=[e for e in bymon[m] if e['Q']!='Q1']
    if len(a)<3 or len(b)<3: continue
    aw=sum(1 for x in a if x['rF']=='win'); bw=sum(1 for x in b if x['rF']=='win')
    ar,br=aw/len(a)*100,bw/len(b)*100
    diffs.append(ar-br); W.append(len(a)+len(b))
    N=len(a)+len(b); mhn+=aw*(len(b)-bw)/N; mhd+=(len(a)-aw)*bw/N
    print(f"  {m}: Q1 {ar:>5.1f}%(n={len(a):>3})  나머지 {br:>5.1f}%(n={len(b):>3})  차 {ar-br:+.1f}%p")
print(f"  → 표본가중 월내 차이 {sum(x*w for x,w in zip(diffs,W))/sum(W):+.1f}%p   MH 승산비 {mhn/mhd:.2f}")

print("\n=== [K] 남는 결론: 저변동 셋업의 '수' 자체가 국면 신호인가 ===")
# 스캔일 기준: 그 주의 Q1 진입 비중 → 다음 주 전체 승률
byw=defaultdict(list)
for e in R:
    import datetime as dt
    y,w_,_=dt.date.fromisoformat(e['entry_date']).isocalendar(); byw[(y,w_)].append(e)
ks=sorted(byw)
xs=[];ys=[]
for i in range(len(ks)-1):
    cur,nxt=byw[ks[i]],byw[ks[i+1]]
    if len(cur)<5 or len(nxt)<5: continue
    xs.append(sum(1 for e in cur if e['Q']=='Q1')/len(cur)*100)
    ys.append(sum(1 for e in nxt if e['rF']=='win')/len(nxt)*100)
if len(xs)>4:
    mx,my=statistics.mean(xs),statistics.mean(ys)
    rr=sum((a-mx)*(b-my) for a,b in zip(xs,ys))/math.sqrt(sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))
    print(f"  이번주 Q1비중 → 다음주 승률 상관 r={rr:.3f} (n={len(xs)}주)  ※예측력 여부")
print(f"  동시점 상관(월 단위)은 r=0.444 였음 — 동행일 뿐 선행이 아니면 타이밍에 못 씀")
