import json, sys
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from canslim_lib.vcp import evaluate_vcp

s = json.load(open(r"C:\Users\hanul\playground\my-stock\.cache\ohlcv\series\212560.json", encoding="utf-8"))
dates = s["dates"]
keys = ["dates", "opens", "highs", "lows", "closes", "volumes"]

def trunc(asof):
    n = sum(1 for d in dates if d <= asof)
    return {k: s[k][:n] for k in keys}

for asof in ["2026-08-06", "2026-08-12", "2026-08-13", "2026-08-14"]:
    r = evaluate_vcp(trunc(asof))
    print(asof, json.dumps({
        "status": r.get("status"), "entry_ready": r.get("entry_ready"),
        "pivot": r.get("pivot_price"), "pct_to_pivot": r.get("pct_to_pivot"),
        "coil_len": r.get("coil_len"), "coil_dry_mean": r.get("coil_dry_mean"),
        "coil_min_dry": r.get("coil_min_dry"), "num_contractions": r.get("num_contractions"),
        "base_depth": r.get("base_depth_pct"), "reason": r.get("reason"),
    }, ensure_ascii=False))

print("\n--- bars 08-05..08-14 ---")
for d in [x for x in dates if "2026-08-05" <= x <= "2026-08-14"]:
    i = dates.index(d)
    pv = s["volumes"][max(0,i-50):i]
    rv = s["volumes"][i]/(sum(pv)/len(pv))
    print(d, "O", s["opens"][i], "H", s["highs"][i], "L", s["lows"][i], "C", s["closes"][i], "relvol %.2f" % rv)

piv = 10690.29
print("\n--- payoff math from pivot fill %.2f ---" % piv)
lo13 = s["lows"][dates.index("2026-08-13")]
print("08-13 low", lo13, "drawdown %.2f%%" % ((lo13/piv-1)*100))
hi11 = s["highs"][dates.index("2026-08-11")]
print("from 10950.63 fill: drawdown %.2f%%" % ((lo13/hi11-1)*100))
print("stop -5%% level", round(piv*0.95, 2), "hit on 08-13?", lo13 < piv*0.95)
print("stop -10%% level", round(piv*0.90, 2))
for d in ["2026-08-10","2026-08-11","2026-08-12","2026-08-13"]:
    print("  low", d, s["lows"][dates.index(d)], "below -10%?", s["lows"][dates.index(d)] < piv*0.90)
c14 = s["closes"][dates.index("2026-08-14")]
h14 = s["highs"][dates.index("2026-08-14")]
c13 = s["closes"][dates.index("2026-08-13")]
print("08-14 close %.0f (%.2f%% from pivot, %.2f%% day change), high %.0f (%.2f%%)" % (
    c14, (c14/piv-1)*100, (c14/c13-1)*100, h14, (h14/piv-1)*100))

print("\n--- committed 08-14 candidates file entry ---")
cand = json.load(open(r"C:\Users\hanul\playground\my-stock\public\data\sepa-vcp-candidates.json", encoding="utf-8"))
items = cand.get("candidates") or cand.get("items") or cand
if isinstance(items, dict):
    print("keys:", list(cand.keys()))
found = [c for c in (items if isinstance(items, list) else []) if c.get("code") == "212560"]
print(json.dumps(found, ensure_ascii=False)[:800])
