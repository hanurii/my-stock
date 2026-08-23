import json, sys
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from canslim_lib.vcp import evaluate_vcp
from canslim_lib.cheat import evaluate_cheat

CODE = "212560"
path = rf"C:\Users\hanul\playground\my-stock\.cache\ohlcv\series\{CODE}.json"
with open(path, encoding="utf-8") as f:
    s = json.load(f)

dates = s["dates"]
keys = ["dates", "opens", "highs", "lows", "closes", "volumes"]

def truncate(asof):
    idxs = [i for i, d in enumerate(dates) if d <= asof]
    n = len(idxs)
    return {k: s[k][:n] for k in keys}

# trading days present in the series between 08-01 and 08-14
tds = [d for d in dates if "2026-08-01" <= d <= "2026-08-14"]
print("trading days:", tds)

print("\n=== VCP as-of ===")
rows = []
for asof in tds:
    ser = truncate(asof)
    last = ser["closes"][-1]
    lastv = ser["volumes"][-1]
    r = evaluate_vcp(ser)
    row = {
        "asof": asof, "close": last, "vol": lastv,
        "status": r.get("status"), "reason": r.get("reason"),
        "detected": r.get("vcp_detected"), "entry_ready": r.get("entry_ready"),
        "pivot": r.get("pivot_price"), "pct_to_pivot": r.get("pct_to_pivot"),
        "num_contractions": r.get("num_contractions"),
        "base_depth": r.get("base_depth_pct"),
        "coil_len": r.get("coil_len"), "coil_dry_mean": r.get("coil_dry_mean"),
        "coil_min_dry": r.get("coil_min_dry"), "coil_range_pct": r.get("coil_range_pct"),
        "dryup": r.get("volume_dryup_ratio"),
    }
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False))

print("\n=== 3C as-of ===")
for asof in [d for d in tds if d >= "2026-08-12"]:
    ser = truncate(asof)
    r = evaluate_cheat(ser)
    print(json.dumps({
        "asof": asof, "status": r.get("status"), "reason": r.get("reason"),
        "detected": r.get("pattern_detected"), "pivot": r.get("pivot_price"),
        "cup_depth": r.get("cup_depth_pct"), "shelf_pos": r.get("shelf_position_pct"),
    }, ensure_ascii=False))

# context: recent bars + relvol
print("\n=== recent bars ===")
import statistics
vols = s["volumes"]
for d in [x for x in dates if "2026-07-25" <= x <= "2026-08-14"]:
    i = dates.index(d)
    ma50 = sum(vols[max(0, i-50):i]) / max(1, len(vols[max(0, i-50):i]))
    print(f"{d} O{s['opens'][i]} H{s['highs'][i]} L{s['lows'][i]} C{s['closes'][i]} V{vols[i]} relvol{vols[i]/ma50:.2f}")

with open(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad\neoauto_asof_rows.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
