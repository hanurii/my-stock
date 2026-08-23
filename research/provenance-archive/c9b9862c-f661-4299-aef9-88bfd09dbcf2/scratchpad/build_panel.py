import json, sys, os, time
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from canslim_lib import ohlcv_matrix, sell_rules as SR
from canslim_lib.pivot_backtest import truncate_series

ROOT = r"C:\Users\hanul\playground\my-stock"
SCRATCH = os.environ["SCRATCH"]
d = json.load(open(os.path.join(ROOT,"public","data","backtest-volatility-pilot.json"), encoding="utf-8"))
ev = d["events"]

RULES = ["heavy_volume_pullback","consecutive_lower_lows","close_below_ma",
         "weak_days_dominant","breakout_failure"]

def simulate(s, b, pivot):
    T = pivot*1.2; S = pivot*0.9
    highs, lows = s["highs"], s["lows"]
    n = len(s["closes"])
    hi,lo = highs[b], lows[b]
    if hi is not None and hi>=T and lo is not None and lo<=S: return "ambiguous", b
    if hi is not None and hi>=T: return "win", b
    if lo is not None and lo<=S: return "ambiguous", b
    for i in range(b+1,n):
        hi,lo=highs[i],lows[i]
        ht = hi is not None and hi>=T; hs = lo is not None and lo<=S
        if ht and hs: return "ambiguous", i
        if ht: return "win", i
        if hs: return "loss", i
    return "unresolved", n-1

out = []
t0=time.time()
for idx,e in enumerate(ev):
    s = ohlcv_matrix.get_series(e["code"])
    b = s["dates"].index(e["entry_date"])
    pivot = e["pivot"]
    entry_price = max(pivot, s["opens"][b] or pivot)
    res, ri = simulate(s, b, pivot)
    K = ri - b
    T = pivot*1.2; S = pivot*0.9
    exit_price = T if res=="win" else (S if res in ("loss","ambiguous") else s["closes"][ri])
    rec = {
        "code": e["code"], "name": e["name"], "pattern": e["pattern"],
        "entry_date": e["entry_date"], "pivot": pivot, "entry_price": entry_price,
        "rs": e.get("rs"), "result": res, "K": K,
        "resolve_date": s["dates"][ri],
        "ret_hold": round((exit_price/entry_price-1)*100, 3),
        "json_result": e["result"], "json_days": e["days_held"],
        "days": [],
    }
    for k in range(1, K+1):
        asof = s["dates"][b+k]
        ts = truncate_series(s, asof)
        st = {}
        st["heavy_volume_pullback"] = SR.rule_heavy_volume_pullback(ts, b)["status"]
        st["consecutive_lower_lows"] = SR.rule_consecutive_lower_lows(ts, b)["status"]
        st["close_below_ma"] = SR.rule_close_below_ma(ts, b)["status"]
        st["weak_days_dominant"] = SR.rule_weak_days_dominant(ts, b)["status"]
        st["breakout_failure"] = SR.rule_breakout_failure(ts, b, pivot, breakout_confirmed=True, start=b)["status"]
        rec["days"].append({
            "k": k, "date": asof, "close": s["closes"][b+k],
            "ret_close": round((s["closes"][b+k]/entry_price-1)*100, 3),
            "st": [st[r] for r in RULES],
        })
    out.append(rec)
    if idx % 100 == 0:
        print(idx, round(time.time()-t0,1), flush=True)

json.dump({"rules": RULES, "events": out}, open(os.path.join(SCRATCH,"panel.json"),"w",encoding="utf-8"))
print("done", len(out), round(time.time()-t0,1))
print("total day-evals", sum(len(r["days"]) for r in out))
