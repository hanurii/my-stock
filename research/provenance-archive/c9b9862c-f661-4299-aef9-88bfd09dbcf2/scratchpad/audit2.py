import json, sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
MAIN = Path(r"C:\Users\hanul\playground\my-stock")
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR = MAIN/".cache"/"ohlcv"/"series"
ohlcv_matrix.FOREIGN_PATH = MAIN/".cache"/"ohlcv"/"foreign.json"
from canslim_lib.pivot_backtest import simulate_pivot_trade

d=json.load(open(MAIN/'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=d['events']
vals=sorted(e['atr_pct'] for e in ev); n=len(vals)
def q(p):
    k=(n-1)*p; f=int(k); c=min(f+1,n-1); return vals[f]+(vals[c]-vals[f])*(k-f)
q1,q2,q3=q(.25),q(.5),q(.75)
def band(v):
    return "Q1" if v<=q1 else "Q2" if v<=q2 else "Q3" if v<=q3 else "Q4"

print("=== Q1 최저 ATR 20건 (동결/데이터 이상 점검) ===")
for e in sorted(ev,key=lambda x:x['atr_pct'])[:20]:
    print(f"  {e['code']} {e['name'][:10]:<11} atr={e['atr_pct']:>5.2f} 거래대금={e['turnover_eok']:>8.1f}억 "
          f"진입={e['entry_date']} {e['result']:<10} relvol={e['rel_vol_entry']} pivot={e['pivot']}")

# --- 갭업 분석 ---
cal = ohlcv_matrix.get_series("005930")["dates"]
cidx={dt:i for i,dt in enumerate(cal)}
gap=[]; miss=0
for e in ev:
    s=ohlcv_matrix.get_series(e['code'])
    if not s or e['entry_date'] not in s['dates']:
        miss+=1; e['open_entry']=None; continue
    i=s['dates'].index(e['entry_date'])
    o=s['opens'][i]; e['idx']=i
    e['open_entry']=o
    e['gap_pct']=(o/e['pivot']-1)*100 if o else None
    # 스캔일→진입일 달력 간격
    a=cidx.get(e['scan_date']); b=cidx.get(e['entry_date'])
    e['cal_gap']= (b-a) if (a is not None and b is not None) else None
print("\nseries 못찾음:",miss)
gaps=[e['gap_pct'] for e in ev if e.get('gap_pct') is not None]
up=[e for e in ev if e.get('gap_pct') is not None and e['gap_pct']>0]
print(f"갭업(시가>피벗) {len(up)}건 / {len(gaps)}건 = {len(up)/len(gaps)*100:.1f}%")
import statistics
print(f"  갭업분 초과폭 중앙값 {statistics.median([e['gap_pct'] for e in up]):.2f}%  평균 {statistics.mean([e['gap_pct'] for e in up]):.2f}%  최대 {max(e['gap_pct'] for e in up):.1f}%")
from collections import Counter
print("  갭업 사분위 분포:", Counter(band(e['atr_pct']) for e in up))
print("  스캔→진입 달력간격 분포:", Counter(e.get('cal_gap') for e in ev))
json.dump([{k:v for k,v in e.items()} for e in ev], open(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad\ev.json","w",encoding="utf-8"))
