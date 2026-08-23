"""일별 리밸런스 등가중 지수(= pit_index.ew 방식) + 엔진 교차검증"""
import json, pickle, sys, statistics as st
from pathlib import Path
MAIN = Path(r"C:\Users\hanul\playground\my-stock")
SP = Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
sys.path.insert(0, str(MAIN / "scripts"))
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR = MAIN/".cache"/"ohlcv"/"series"; ohlcv_matrix.FOREIGN_PATH = MAIN/".cache"/"ohlcv"/"foreign.json"
P = pickle.load(open(SP/"panel.pkl","rb")); dates, rows, meta = P["dates"], P["rows"], P["meta"]
HOLD=[d for d in dates if d>"2025-11-26"]

def ew_index(codes):
    lvl=1.0
    for d in HOLD:
        fs=[rows[c][d][0] for c in codes if rows[c].get(d) and rows[c][d][0] is not None]
        if not fs: continue
        lvl *= 1 + (sum(fs)/len(fs))/100
    return (lvl-1)*100

univ=json.loads((SP/"universe_20251126.json").read_text(encoding="utf-8"))
evl=json.loads((SP/"evaluable_20251126.json").read_text(encoding="utf-8"))
bt=json.loads((MAIN/"public/data/backtest-volatility-pilot.json").read_text(encoding="utf-8"))
btc=sorted({e["code"] for e in bt["events"]})
allc=[c for c in rows if "2025-11-26" in rows[c]]
for lab,cs in (("전종목 2767",allc),("전종목 -제일바이오",[c for c in allc if c!="052670"]),
               ("평가대상 1429(거래대금5억+)",list(evl)),("① 유니버스 291(RS80+)",list(univ)),
               ("② 백테스트 350",btc)):
    print(f"  일별리밸런스 등가중지수 [{lab}] {ew_index(cs):+.2f}%")

print("\n--- 엔진 교차검증: pdata fltRt 연쇄 vs ohlcv 수정주가 종가비 ---")
import random; random.seed(0)
sample=random.sample(list(univ),12)
for c in sample:
    cum=1.0
    for d in HOLD:
        r=rows[c].get(d)
        if r and r[0] is not None: cum*=1+r[0]/100
    a=(cum-1)*100
    s=ohlcv_matrix.get_series(c); dd,cc=s["dates"],s["closes"]
    i0=dd.index("2025-11-26"); i1=max(i for i,x in enumerate(dd) if x<="2026-08-20" and cc[i])
    b=(cc[i1]/cc[i0]-1)*100
    print(f"  {meta[c]['name']:<12} pdata {a:+8.2f}%  ohlcv {b:+8.2f}%  차 {a-b:+.2f}%p")

print("\n--- 전종목 등가중 평균(제일바이오 제외) ---")
def pr(c):
    cum,n=1.0,0
    for d in HOLD:
        r=rows[c].get(d)
        if not r or r[0] is None: continue
        cum*=1+r[0]/100; n+=1
    return ((cum-1)*100) if n else None
v=[pr(c) for c in allc if c!="052670" and pr(c) is not None]
print(f"  n={len(v)} 평균 {sum(v)/len(v):+.2f}% 중앙 {st.median(v):+.2f}%")
