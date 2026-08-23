import json, sys, os
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from canslim_lib import ohlcv_matrix
D = json.load(open(r"C:\Users\hanul\playground\my-stock\public\data\backtest-volatility-pilot.json", encoding="utf-8"))
E = D["events"]
codes = sorted({e["code"] for e in E})
print("codes", len(codes))
miss = []
S = {}
for c in codes:
    s = ohlcv_matrix.get_series(c)
    if s is None:
        miss.append(c); continue
    S[c] = s
print("missing", len(miss), miss[:10])
# check date coverage
import itertools
c0 = codes[0]
print(c0, S[c0]["dates"][0], S[c0]["dates"][-1], len(S[c0]["dates"]))
lens = [len(S[c]["dates"]) for c in S]
print("len min/max", min(lens), max(lens))
# verify entry idx found
bad = 0
for e in E:
    s = S.get(e["code"])
    if s is None: continue
    if e["entry_date"] not in s["dates"]:
        bad += 1
print("entry_date not in series:", bad)
json.dump({"ok":1}, open(os.devnull,"w"))
