import json, sys, os
sys.path.insert(0, r"C:/Users/hanul/playground/my-stock/scripts")
from canslim_lib import ohlcv_matrix
from canslim_lib.pivot_backtest import truncate_series, simulate_pivot_trade

ROOT = r"C:/Users/hanul/playground/my-stock"
d = json.load(open(ROOT + "/public/data/backtest-volatility-pilot.json", encoding="utf-8"))
ev = d["events"]
print("n events", len(ev))

miss = 0
mismatch = 0
ok = 0
for e in ev[:614]:
    s = ohlcv_matrix.get_series(e["code"])
    if not s:
        miss += 1; continue
    try:
        b = s["dates"].index(e["entry_date"])
    except ValueError:
        miss += 1; continue
    r = simulate_pivot_trade(s, b, e["pivot"], 20.0, 10.0)
    if r["result"] != e["result"] or r["resolve_date"] != e["resolve_date"]:
        mismatch += 1
        if mismatch <= 5:
            print("MISMATCH", e["code"], e["entry_date"], e["result"], e["resolve_date"], "->", r["result"], r["resolve_date"])
    else:
        ok += 1
print("miss", miss, "mismatch", mismatch, "ok", ok)
print("last date in a sample series:", s["dates"][-1])
