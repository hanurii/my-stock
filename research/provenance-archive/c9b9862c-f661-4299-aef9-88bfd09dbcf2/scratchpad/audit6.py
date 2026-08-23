import json, sys, math, statistics, random
from pathlib import Path
from collections import Counter, defaultdict
MAIN = Path(r"C:\Users\hanul\playground\my-stock")
d=json.load(open(MAIN/'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=d['events']
R=[e for e in ev if e['result'] in ('win','loss')]
vals=sorted(e['atr_pct'] for e in ev); n=len(vals)
def qq(p):
    k=(n-1)*p; f=int(k); c=min(f+1,n-1); return vals[f]+(vals[c]-vals[f])*(k-f)
q1c=qq(.25)
for e in R: e['isQ1']= e['atr_pct']<=q1c
def wr(rows):
    w=sum(1 for r in rows if r['result']=='win'); t=len(rows)
    return w,t,(round(w/t*100,1) if t else None)

print("=== [E] 월별: Q1 비중 vs 그달 승률 (저변동 셋업 출현 = 국면 신호인가) ===")
xs=[];ys=[]
for m in sorted({e['month'] for e in R}):
    sub=[e for e in R if e['month']==m]
    if len(sub)<8: continue
    share=sum(1 for e in sub if e['isQ1'])/len(sub)*100
    _,_,mr=wr(sub); xs.append(share); ys.append(mr)
    print(f"  {m}  Q1비중 {share:>5.1f}%   그달승률 {mr:>5.1f}%  (n={len(sub)})")
mx,my=statistics.mean(xs),statistics.mean(ys)
r=sum((a-mx)*(b-my) for a,b in zip(xs,ys))/math.sqrt(sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))
print(f"  → 상관 r = {r:.3f} (n={len(xs)}개월)  ※ Q1 비중이 높은 달일수록 전체 승률이 높다")

print("\n=== [F] 변동성을 '그날 대비 상대'로 바꾸면? (시장 국면 성분 제거) ===")
# 월내 ATR 중앙값 대비 상대 순위
bymon=defaultdict(list)
for e in R: bymon[e['month']].append(e)
for m,rows in bymon.items():
    v=sorted(x['atr_pct'] for x in rows)
    cut=v[max(0,len(v)//4-1)] if len(v)>=8 else None
    for x in rows: x['relQ1']= (cut is not None and x['atr_pct']<=cut)
sub=[e for e in R if 'relQ1' in e and len(bymon[e['month']])>=8]
aw,at,ar=wr([e for e in sub if e['relQ1']]); bw,bt,br=wr([e for e in sub if not e['relQ1']])
print(f"  월내 상대 저변동 하위25%: {ar}% (n={at})   나머지: {br}% (n={bt})   차 {ar-br:+.1f}%p")

# 절대 저변동인데 '변동성 큰 달'에 나온 것들만
print("\n=== [G] 절대 vs 상대 분해 ===")
badmon={'2026-02','2026-03','2026-05','2026-07'}
for lab,ms in [("좋은달(12·01·04)",{'2025-12','2026-01','2026-04'}),("나쁜달(02·03·05·07)",badmon)]:
    s=[e for e in R if e['month'] in ms]
    aw,at,ar=wr([e for e in s if e['isQ1']]); bw,bt,br=wr([e for e in s if not e['isQ1']])
    print(f"  {lab:<20} Q1 {str(ar):>5}%(n={at:>3})  나머지 {str(br):>5}%(n={bt:>3})  차 {(ar-br) if ar and br else 0:+.1f}%p")

print("\n=== [H] 최종 요약표: 통제 수준별 Q1 우위 ===")
rows=[]
aw,at,ar=wr([e for e in R if e['isQ1']]); bw,bt,br=wr([e for e in R if not e['isQ1']])
rows.append(("통제 없음 (원본 주장)", ar,at,br,bt, ar-br))
# 갭업 시가체결 결과 재사용
import importlib.util
spec=importlib.util.spec_from_file_location("x",MAIN/"scripts/canslim_lib/pivot_backtest.py")
sys.path.insert(0,str(MAIN/"scripts"))
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR=MAIN/".cache"/"ohlcv"/"series"
from canslim_lib.pivot_backtest import simulate_pivot_trade
F=[]
for e in ev:
    s=ohlcv_matrix.get_series(e['code']); i=s['dates'].index(e['entry_date']); o=s['opens'][i]
    fill=o if (o and o>e['pivot']) else e['pivot']
    sim=simulate_pivot_trade(s,i,fill,20.0,10.0); rr=sim['result']
    if o and o>e['pivot'] and rr=='ambiguous' and sim['exit_reason']=='stop_on_breakout_day': rr='loss'
    if rr in ('win','loss'): F.append(dict(e,result=rr,isQ1=e['atr_pct']<=q1c))
aw,at,ar=wr([e for e in F if e['isQ1']]); bw,bt,br=wr([e for e in F if not e['isQ1']])
rows.append(("+ 갭업 시가체결", ar,at,br,bt, ar-br))
# 예외 최악
W=[dict(e,result=('loss' if e['result'] in ('ambiguous','unresolved') else e['result']),isQ1=e['atr_pct']<=q1c) for e in ev]
aw,at,ar=wr([e for e in W if e['isQ1']]); bw,bt,br=wr([e for e in W if not e['isQ1']])
rows.append(("+ 예외·미결 전부 패배", ar,at,br,bt, ar-br))
# 종목당 1거래
first={}
for e in sorted(R,key=lambda x:x['entry_date']): first.setdefault(e['code'],e)
Fi=list(first.values())
aw,at,ar=wr([e for e in Fi if e['isQ1']]); bw,bt,br=wr([e for e in Fi if not e['isQ1']])
rows.append(("+ 종목당 최초 1거래만", ar,at,br,bt, ar-br))
print(f"  {'통제':<26}{'Q1':>7}{'(n)':>6}{'나머지':>8}{'(n)':>6}{'차이':>9}")
for lab,a,an,b,bn,dd in rows:
    print(f"  {lab:<26}{a:>6}%{an:>6}{b:>7}%{bn:>6}{dd:>+8.1f}%p")
print(f"  {'+ 월 통제(MH 가중)':<26}{'':>6} {'':>6}{'':>7} {'':>6}{'+5.0':>8}%p")
print(f"  {'+ 같은날 매칭(일별평균)':<26}{'':>6} {'':>6}{'':>7} {'':>6}{'+5.9':>8}%p  p=0.17")
