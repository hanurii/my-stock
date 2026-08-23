import json, sys, statistics
from pathlib import Path
from collections import Counter, defaultdict
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
MAIN = Path(r"C:\Users\hanul\playground\my-stock")
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR = MAIN/".cache"/"ohlcv"/"series"
from canslim_lib.pivot_backtest import simulate_pivot_trade

d=json.load(open(MAIN/'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=d['events']
vals=sorted(e['atr_pct'] for e in ev); n=len(vals)
def qq(p):
    k=(n-1)*p; f=int(k); c=min(f+1,n-1); return vals[f]+(vals[c]-vals[f])*(k-f)
q1,q2,q3=qq(.25),qq(.5),qq(.75)
def band(v): return "Q1" if v<=q1 else "Q2" if v<=q2 else "Q3" if v<=q3 else "Q4"
for e in ev: e['Q']=band(e['atr_pct'])

def summ(rows, key='result'):
    c=Counter(r[key] for r in rows); w,l=c['win'],c['loss']; res=w+l
    return (len(rows), w, l, c['ambiguous'], c['unresolved'],
            round(w/res*100,1) if res else None,
            round((w*20-l*10)/res,2) if res else None)
def show(title, rows_by):
    print(f"\n{title}")
    print(f"  {'구간':<22}{'n':>4}{'승':>5}{'패':>5}{'예외':>5}{'미결':>5}{'승률':>7}{'기대값':>8}")
    for k,rows in rows_by:
        t=summ(rows)
        print(f"  {k:<22}{t[0]:>4}{t[1]:>5}{t[2]:>5}{t[3]:>5}{t[4]:>5}{str(t[5]):>7}{str(t[6]):>8}")
byQ=lambda rows: [(k,[e for e in rows if e['Q']==k]) for k in ("Q1","Q2","Q3","Q4")]

show("[0] 원본 재현", byQ(ev))

# ── (1) 갭업 시가체결 재계산 ───────────────────────────────
for e in ev:
    s=ohlcv_matrix.get_series(e['code'])
    i=s['dates'].index(e['entry_date'])
    o=s['opens'][i]
    fill = o if (o and o>e['pivot']) else e['pivot']
    e['fill']=fill; e['gap_up']= bool(o and o>e['pivot'])
    sim=simulate_pivot_trade(s,i,fill,20.0,10.0)
    r=sim['result']
    # 시가체결이면 진입일 손절은 명백한 패배(개장부터 보유) — ambiguous 로 봐주지 않음
    if e['gap_up'] and r=='ambiguous' and sim['exit_reason']=='stop_on_breakout_day':
        r='loss'
    e['result_fill']=r
show("[1] 갭업=시가체결 재계산", [(k,[e for e in v]) for k,v in byQ(ev)])
print("  (위 표는 원본 result 기준 — 아래가 시가체결 결과)")
for e in ev: e['_o']=e['result']; e['result']=e['result_fill']
show("[1b] 갭업=시가체결 결과", byQ(ev))
print("  전체:",summ(ev))
for e in ev: e['result']=e['_o']

# ── (2) 예외 18건 최악가정 ─────────────────────────────────
print("\n[2] 예외(ambiguous) 18건 분포 및 최악가정")
print("  사분위 분포:",Counter(e['Q'] for e in ev if e['result']=='ambiguous'))
print("  사유:",Counter(ohlcv_matrix and '' for e in [] ) or "")
for e in ev: e['_w']= 'loss' if e['result']=='ambiguous' else e['result']
tmp=[dict(e,result=e['_w']) for e in ev]
show("  예외=전부 패배(최악)", byQ(tmp))
tmp=[dict(e,result=('win' if e['result']=='ambiguous' else e['result'])) for e in ev]
show("  예외=전부 승리(최선)", byQ(tmp))

# ── (3) 미결 10건 ─────────────────────────────────────────
print("\n[3] 미결(unresolved) 10건 사분위:",Counter(e['Q'] for e in ev if e['result']=='unresolved'))
tmp=[dict(e,result=('loss' if e['result'] in('unresolved','ambiguous') else e['result'])) for e in ev]
show("  미결+예외 전부 패배(절대최악)", byQ(tmp))
tmp=[dict(e,result=('win' if e['result'] in('unresolved','ambiguous') else e['result'])) for e in ev]
show("  미결+예외 전부 승리(절대최선)", byQ(tmp))

# ── (4) 규모 통제: 거래대금 3분위 안에서 ATR 2분할 ────────
tv=sorted(e['turnover_eok'] for e in ev)
t1,t2=tv[len(tv)//3],tv[2*len(tv)//3]
print(f"\n[4] 거래대금 3분위 경계: {t1:.0f}억 / {t2:.0f}억")
med=statistics.median([e['atr_pct'] for e in ev])
print(f"    ATR 중앙값 {med:.2f}%  |  ATR-거래대금 상관(스피어만 근사):")
import math
def spearman(a,b):
    ra={v:i for i,v in enumerate(sorted(set(a)))}
    def rank(x):
        s=sorted(range(len(x)),key=lambda i:x[i]); r=[0]*len(x)
        for j,i in enumerate(s): r[i]=j
        return r
    ra_,rb_=rank(a),rank(b); m=len(a)
    ma,mb=sum(ra_)/m,sum(rb_)/m
    num=sum((ra_[i]-ma)*(rb_[i]-mb) for i in range(m))
    den=math.sqrt(sum((ra_[i]-ma)**2 for i in range(m))*sum((rb_[i]-mb)**2 for i in range(m)))
    return num/den
print(f"    rho(ATR, 거래대금) = {spearman([e['atr_pct'] for e in ev],[e['turnover_eok'] for e in ev]):.3f}")
for label,lo,hi in [("소형(거래대금 하위1/3)",-1,t1),("중형",t1,t2),("대형(상위1/3)",t2,1e18)]:
    sub=[e for e in ev if lo<e['turnover_eok']<=hi]
    rows=[("  저ATR(중앙값이하)",[e for e in sub if e['atr_pct']<=med]),
          ("  고ATR(중앙값초과)",[e for e in sub if e['atr_pct']>med])]
    show(f"  {label}  n={len(sub)}", rows)
