import json, os, sys, glob
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from canslim_lib.trend_template import compute_gate_margin
BY = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad\mine\bydata"
files = {}
for p in sorted(glob.glob(os.path.join(BY,"*.json"))):
    d = json.load(open(p,encoding="utf-8"))
    files[d["data_date"]] = d
dates = sorted(files)

sc = json.load(open(r"C:\Users\hanul\playground\my-stock\public\data\scorecard.json",encoding="utf-8"))
trades = sc["trades"]
rows=[]
for t in trades:
    od = t["open_date"]; code = t["code"]
    prev = [d for d in dates if d < od]
    same = [d for d in dates if d <= od]
    def sc_for(dd):
        if not dd: return None, None, None
        f = files[dd]; rec = f["recs"].get(code)
        if rec is None: return None, None, rec
        gm = compute_gate_margin(rec, rec.get("current_price"), rec.get("rs"), rs_min=80)
        return (gm["score"] if gm else None), gm, rec
    pdd = prev[-1] if prev else None
    sdd = same[-1] if same else None
    sp, gmp, recp = sc_for(pdd)
    ss, gms, recs_ = sc_for(sdd)
    rows.append(dict(code=code,name=t["name"],open_date=od,close_date=t.get("close_date"),
        net=t["net_pct"], outcome=t["outcome"], hold=t.get("hold_days"), setup=t.get("setup"),
        prev_dd=pdd, same_dd=sdd, sp=sp, ss=ss,
        prev_missing=(recp is None), same_missing=(recs_ is None),
        p_tight=(gmp or {}).get("tightest"), p_per={k:v["pct"] for k,v in (gmp or {}).get("per_condition",{}).items()},
        p_allpass=(recp or {}).get("all_pass"), p_rs=(recp or {}).get("rs"),
        s_allpass=(recs_ or {}).get("all_pass"), s_rs=(recs_ or {}).get("rs")))
json.dump(rows, open(os.path.join(os.path.dirname(BY),"trades_mine.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=1)
miss_p = [r for r in rows if r["sp"] is None]
print("n trades", len(rows), "| prev score None:", len(miss_p), "| same None:", sum(1 for r in rows if r["ss"] is None))
for r in miss_p: print("  MISS", r["code"], r["name"], r["open_date"], "prev_dd",r["prev_dd"], "rec_missing",r["prev_missing"])
import collections
lag = collections.Counter()
for r in rows:
    i = dates.index(r["prev_dd"]); j = dates.index(r["same_dd"]) if r["same_dd"] else None
    lag[(j-i) if j is not None else -1]+=1
print("trading-session lag (data_date -> buy date, in available snapshots):", dict(lag))
