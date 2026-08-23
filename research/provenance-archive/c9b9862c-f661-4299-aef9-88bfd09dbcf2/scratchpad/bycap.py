"""규칙 vs 보유 — 시장/시총 구간별"""
import json, pickle, sys, statistics as st
from pathlib import Path
MAIN=Path(r"C:\Users\hanul\playground\my-stock"); SP=Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
sys.path.insert(0,str(MAIN/"scripts"))
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR=MAIN/".cache"/"ohlcv"/"series"; ohlcv_matrix.FOREIGN_PATH=MAIN/".cache"/"ohlcv"/"foreign.json"
P=pickle.load(open(SP/"panel.pkl","rb")); rows=P["rows"]
bt=json.loads((MAIN/"public/data/backtest-volatility-pilot.json").read_text(encoding="utf-8"))
groups={}
for e in bt["events"]:
    if e["gain_at_resolve_pct"] is None: continue
    s=ohlcv_matrix.get_series(e["code"]);
    if not s: continue
    d,c=s["dates"],s["closes"]
    idx=[i for i,x in enumerate(d) if x<="2026-08-21" and c[i]]
    if not idx: continue
    h=(c[idx[-1]]/e["entry_price"]-1)*100
    ed=e["entry_date"]; rec=rows.get(e["code"],{}).get(ed)
    cap=rec[2] if rec else None
    if cap is None: cap=0
    band=("A 10조+" if cap>=100000 else "B 1~10조" if cap>=10000 else "C 3천억~1조" if cap>=3000 else "D 3천억미만")
    groups.setdefault(band,[]).append((e["gain_at_resolve_pct"],h))
    groups.setdefault("시장:"+e["market"],[]).append((e["gain_at_resolve_pct"],h))
print(f"{'구간':<14}{'n':>5}{'규칙평균':>10}{'보유평균':>10}{'보유중앙':>10}{'보유가나음%':>11}")
for k in sorted(groups):
    v=groups[k]; r=[a for a,_ in v]; hh=[b for _,b in v]
    print(f"{k:<14}{len(v):>5}{sum(r)/len(r):>+9.2f}%{sum(hh)/len(hh):>+9.2f}%{st.median(hh):>+9.2f}%{sum(1 for a,b in v if b>a)/len(v)*100:>10.1f}%")
