import json,sys
from pathlib import Path
from collections import Counter
MAIN=Path(r"C:\Users\hanul\playground\my-stock"); sys.path.insert(0,str(MAIN/"scripts"))
from canslim_lib import ohlcv_matrix; ohlcv_matrix.SERIES_DIR=MAIN/".cache"/"ohlcv"/"series"
from canslim_lib.pivot_backtest import simulate_pivot_trade
d=json.load(open(MAIN/'public/data/backtest-volatility-pilot.json',encoding='utf-8')); ev=d['events']
vals=sorted(e['atr_pct'] for e in ev); n=len(vals); k=(n-1)*.25; f=int(k)
q1c=vals[f]+(vals[min(f+1,n-1)]-vals[f])*(k-f)
c=Counter()
for e in ev:
    if e['result']!='ambiguous': continue
    s=ohlcv_matrix.get_series(e['code']); i=s['dates'].index(e['entry_date'])
    sim=simulate_pivot_trade(s,i,e['pivot'],20.0,10.0)
    c[(sim['exit_reason'], 'Q1' if e['atr_pct']<=q1c else '나머지')]+=1
print("예외 18건 사유×구간:",dict(c))
# 진입일 -10% 도달(=돌파일 손절)로 예외처리된 건수 전체
c2=Counter()
for e in ev:
    s=ohlcv_matrix.get_series(e['code']); i=s['dates'].index(e['entry_date'])
    sim=simulate_pivot_trade(s,i,e['pivot'],20.0,10.0)
    if sim['exit_reason'] in ('stop_on_breakout_day','both_same_day_breakout'):
        c2['Q1' if e['atr_pct']<=q1c else '나머지']+=1
print("진입일에 ±터치로 예외 판정된 건:",dict(c2))
