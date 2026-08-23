import json, itertools, math
from math import comb

P = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad\actionable_leading.json"
d = json.load(open(P, encoding="utf-8"))
ev = d["events"]
ent = [e for e in ev if e.get("entered")]
closed = [e for e in ent if e.get("closed")]
unres = [e for e in ent if not e.get("closed")]

print("n_events", len(ev), "entered", len(ent), "closed", len(closed), "unresolved", len(unres))
wins = [e for e in closed if e["outcome"] == "win"]
print("closed wins:", [(e["name"], e["event_open"], e["relvol_entry"], e["regime_up_entry"]) for e in wins])
print("closed win rate:", round(100*len(wins)/len(closed),1), "closed avg net:", round(sum(e["net_pct"] for e in closed)/len(closed),2))
print("allin win rate:", round(100*len(wins)/len(ent),1), "allin avg net:", round(sum(e["net_pct"] for e in ent)/len(ent),2))

def cell(rows):
    c = [e for e in rows if e.get("closed")]
    w = [e for e in c if e["outcome"]=="win"]
    aw = len(w)  # unresolved never counted as win
    out = {
        "n_ent": len(rows), "n_closed": len(c), "wins": len(w),
        "closed_wr": round(100*len(w)/len(c),1) if c else None,
        "closed_avg": round(sum(e["net_pct"] for e in c)/len(c),2) if c else None,
        "allin_avg": round(sum(e["net_pct"] for e in rows)/len(rows),2) if rows else None,
        "codes": sorted(set(e["code"] for e in rows)),
        "entry_dates": sorted(set(e["entry_date"] for e in rows)),
    }
    return out

print("\n--- relvol buckets ---")
for name, lo, hi in [("<0.75", -1, 0.75), ("0.75-1.5", 0.75, 1.5), (">=1.5", 1.5, 999)]:
    rows = [e for e in ent if lo <= e["relvol_entry"] < hi]
    print(name, json.dumps(cell(rows), ensure_ascii=False))

print("\n--- regime ---")
for name, val in [("down", False), ("up", True)]:
    rows = [e for e in ent if e["regime_up_entry"] == val]
    print(name, json.dumps(cell(rows), ensure_ascii=False))

print("\n--- gap ---")
for name, lo, hi in [("<=0", -99, 1e-9), ("0-3", 1e-9, 3), (">3", 3, 99)]:
    rows = [e for e in ent if lo < e["gap_pct"] <= hi] if name=="<=0" else [e for e in ent if lo < e["gap_pct"] <= hi]
    # careful: <=0 means gap<=0
    print(name, json.dumps(cell(rows), ensure_ascii=False))
# redo gap cleanly
print("gap<=0 ", json.dumps(cell([e for e in ent if e["gap_pct"] <= 0]), ensure_ascii=False))
print("gap 0-3", json.dumps(cell([e for e in ent if 0 < e["gap_pct"] <= 3]), ensure_ascii=False))
print("gap >3 ", json.dumps(cell([e for e in ent if e["gap_pct"] > 3]), ensure_ascii=False))

# Fisher exact (hypergeometric, one-sided upper) for k wins in cell of size m out of N closed with K wins total
def fisher_upper(N, K, m, k):
    # P(X >= k), X ~ Hypergeom(N, K, m)
    tot = 0.0
    for x in range(k, min(K, m)+1):
        tot += comb(K, x)*comb(N-K, m-x)/comb(N, m)
    return tot

N, K = len(closed), len(wins)
print("\n--- Fisher one-sided p (closed only, N=%d, K=%d) ---" % (N, K))
c3 = [e for e in closed if e["relvol_entry"] >= 1.5]
print("relvol>=1.5 cell: m=%d k=%d p=%.4f" % (len(c3), sum(1 for e in c3 if e["outcome"]=="win"), fisher_upper(N, K, len(c3), sum(1 for e in c3 if e["outcome"]=="win"))))
c14 = [e for e in closed if e["relvol_entry"] >= 1.4]  # boundary sensitivity: yesti 1.47
print("relvol>=1.4 cell: m=%d k=%d p=%.4f" % (len(c14), sum(1 for e in c14 if e["outcome"]=="win"), fisher_upper(N, K, len(c14), sum(1 for e in c14 if e["outcome"]=="win"))))
cu = [e for e in closed if e["regime_up_entry"]]
print("regime up cell:   m=%d k=%d p=%.4f" % (len(cu), sum(1 for e in cu if e["outcome"]=="win"), fisher_upper(N, K, len(cu), sum(1 for e in cu if e["outcome"]=="win"))))
cg = [e for e in closed if 0 < e["gap_pct"] <= 3]
print("gap 0-3 cell:     m=%d k=%d p=%.4f" % (len(cg), sum(1 for e in cg if e["outcome"]=="win"), fisher_upper(N, K, len(cg), sum(1 for e in cg if e["outcome"]=="win"))))
cm = [e for e in closed if e["sector_conf"]=="medium"]
print("conf=medium cell: m=%d k=%d p=%.4f" % (len(cm), sum(1 for e in cm if e["outcome"]=="win"), fisher_upper(N, K, len(cm), sum(1 for e in cm if e["outcome"]=="win"))))
ca = [e for e in closed if not e["trigger_entry_ready"]]
print("actionable-only:  m=%d k=%d p=%.4f" % (len(ca), sum(1 for e in ca if e["outcome"]=="win"), fisher_upper(N, K, len(ca), sum(1 for e in ca if e["outcome"]=="win"))))

# within-down-regime relvol
dn = [e for e in closed if not e["regime_up_entry"]]
Kd = sum(1 for e in dn if e["outcome"]=="win")
cd = [e for e in dn if e["relvol_entry"] >= 1.5]
print("within-down relvol>=1.5: N=%d K=%d m=%d k=%d p=%.4f" % (len(dn), Kd, len(cd), sum(1 for e in cd if e["outcome"]=="win"), fisher_upper(len(dn), Kd, len(cd), sum(1 for e in cd if e["outcome"]=="win"))))

# loss resolution speed
print("\n--- loss speed (trading-day gap unknown; calendar diff) ---")
losses = [e for e in closed if e["outcome"]=="loss"]
from datetime import date
def pd(s): y,m,dd = s.split("-"); return date(int(y),int(m),int(dd))
fast = [e for e in losses if (pd(e["resolve_date"]) - pd(e["entry_date"])).days <= 1]
print("losses:", len(losses), "resolved within 0-1 calendar days:", len(fast))
for e in losses:
    print(" ", e["name"], e["entry_date"], "->", e["resolve_date"])

# distinct entry-date clusters (independence check)
print("\n--- entry date clustering (closed) ---")
from collections import Counter
cnt = Counter(e["entry_date"] for e in closed)
print(dict(cnt))
print("distinct entry dates among closed:", len(cnt))

# mark-to-market window lengths for unresolved (marked) events
print("\n--- unresolved events: days elapsed entry->2026-08-14 ---")
for e in unres:
    print(" ", e["name"], e["entry_date"], "net", e["net_pct"], "mae10", e["mae10"], "r10_partial", e.get("r10_partial"))

# duplicated codes among entered
print("\n--- entered codes multiplicity ---")
cc = Counter(e["code"] for e in ent)
print({k:v for k,v in cc.items() if v>1})
