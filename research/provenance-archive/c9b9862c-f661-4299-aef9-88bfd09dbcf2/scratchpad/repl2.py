import json, sys
sys.path.insert(0, r"C:/Users/hanul/playground/my-stock/scripts")
from canslim_lib import ohlcv_matrix
from pathlib import Path
ohlcv_matrix.SERIES_DIR = Path(r"C:/Users/hanul/playground/my-stock/.cache/ohlcv/series")
from canslim_lib.pivot_backtest import simulate_pivot_trade

ROOT = r"C:/Users/hanul/playground/my-stock"
d = json.load(open(ROOT + "/public/data/backtest-volatility-pilot.json", encoding="utf-8"))
ev = d["events"]
mismatch=0; ok=0; miss=0
for e in ev:
    s = ohlcv_matrix.get_series(e["code"])
    if not s: miss+=1; continue
    try: b = s["dates"].index(e["entry_date"])
    except ValueError: miss+=1; continue
    r = simulate_pivot_trade(s, b, e["entry_price"], 20.0, 10.0)
    if r["result"]!=e["result"] or r["resolve_date"]!=e["resolve_date"] or abs(r["max_gain_pct"]-e["max_gain_pct"])>0.02:
        mismatch+=1
        if mismatch<=6: print("MM",e["code"],e["entry_date"],e["result"],e["resolve_date"],e["max_gain_pct"],"->",r["result"],r["resolve_date"],r["max_gain_pct"])
    else: ok+=1
print("miss",miss,"mismatch",mismatch,"ok",ok)
