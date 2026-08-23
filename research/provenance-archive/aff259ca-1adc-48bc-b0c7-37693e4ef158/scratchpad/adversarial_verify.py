# -*- coding: utf-8 -*-
import json, itertools, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SP = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad"
rows = json.load(open(SP + r"\enriched_trades.json", encoding="utf-8"))["rows"]

def agg(rs):
    n = len(rs)
    if n == 0:
        return "n=0"
    w = sum(1 for r in rs if r["outcome"] == "win")
    avg = sum(r["net_pct"] for r in rs) / n
    tot = sum(r["net_won"] for r in rs)
    return f"n={n:2d} win={w:2d} wr={100*w/n:5.1f}% avg={avg:+6.2f}% sum={tot:+,.0f}"

def split(rs, keyfn, title):
    print(f"--- {title} ---")
    groups = {}
    for r in rs:
        groups.setdefault(keyfn(r), []).append(r)
    for k in sorted(groups, key=lambda x: str(x)):
        print(f"  {str(k):16s} {agg(groups[k])}")

jul = [r for r in rows if r["month"] == "2026-07"]
aug = [r for r in rows if r["month"] == "2026-08"]
print(f"ALL: {agg(rows)}")
print(f"JUL: {agg(jul)}")
print(f"AUG: {agg(aug)}")

# NOTE: month field is by close_date? check open dates in aug
print("\nAUG rows open_dates:", sorted((r["open_date"], r["name"]) for r in aug))

# (1) split stability by month
for name, sub in [("ALL", rows), ("JUL", jul), ("AUG", aug)]:
    print(f"\n================ {name} ================")
    split(sub, lambda r: r["sector_bucket"], "sector")
    split(sub, lambda r: r["rs_bucket"], "RS")
    split(sub, lambda r: r["relvol_bucket"], "relvol")
    split(sub, lambda r: r["status_bucket"], "status")
    split(sub, lambda r: r["setup"], "setup")
    split(sub, lambda r: r["regime_up"], "regime")
    split(sub, lambda r: (r["relvol_entry"] is not None and r["relvol_entry"] < 1), "relvol<1")

# (2) sector x regime
print("\n================ sector x regime ================")
for sec in sorted(set(r["sector_bucket"] for r in rows)):
    for reg in [True, False]:
        sub = [r for r in rows if r["sector_bucket"] == sec and r["regime_up"] == reg]
        if sub:
            print(f"  {sec:12s} regime_up={reg!s:5s} {agg(sub)}")

print("\nleading x regime:")
for lead in [True, False]:
    for reg in [True, False]:
        sub = [r for r in rows if r["leading"] == lead and r["regime_up"] == reg]
        if sub:
            print(f"  leading={lead!s:5s} regime_up={reg!s:5s} {agg(sub)}")

# leading trades detail
print("\nleading-sector trades detail:")
for r in rows:
    if r["leading"]:
        print(f"  {r['name']:10s} {r['open_date']} net={r['net_pct']:+6.2f} rs={r['displayed_rs']} relvol={r['relvol_entry']} regime_up={r['regime_up']} status={r['status_bucket']}")

# (3) axis overlap: leading, RS>=90, relvol>=1.5
print("\n================ axis overlap ================")
A = set(i for i, r in enumerate(rows) if r["leading"])
B = set(i for i, r in enumerate(rows) if (r["displayed_rs"] or 0) >= 90)
C = set(i for i, r in enumerate(rows) if (r["relvol_entry"] or 0) >= 1.5)
D = set(i for i, r in enumerate(rows) if (r["relvol_entry"] or 99) < 1)
print(f"leading n={len(A)}, RS>=90 n={len(B)}, relvol>=1.5 n={len(C)}, relvol<1 n={len(D)}")
print(f"leading & RS>=90: {len(A & B)}")
print(f"leading & relvol>=1.5: {len(A & C)}")
print(f"RS>=90 & relvol>=1.5: {len(B & C)}")
print(f"all three: {len(A & B & C)}")
print(f"leading & relvol<1: {len(A & D)}")
# also setup-null vs other axes
N = set(i for i, r in enumerate(rows) if r["setup"] is None)
print(f"setup=null n={len(N)}; null & relvol>=1: {len(N & set(i for i,r in enumerate(rows) if (r['relvol_entry'] or 0)>=1))}")
print(f"null trades by month:", sorted(rows[i]["month"] for i in N))
print(f"null trades regime_up:", [rows[i]["regime_up"] for i in N])

# (4) outlier sensitivity
print("\n================ outlier sensitivity ================")
noFF = [r for r in rows if not (r["code"] == "383220")]
best = max(rows, key=lambda r: r["net_pct"])
noBest = [r for r in rows if r is not best]
print(f"best winner: {best['name']} {best['open_date']} {best['net_pct']}")
for name, sub in [("no F&F", noFF), ("no best(타이거일렉 07-10)", noBest)]:
    print(f"\n--- {name} ---")
    split(sub, lambda r: r["sector_bucket"], "sector")
    split(sub, lambda r: (r["relvol_entry"] is not None and r["relvol_entry"] < 1), "relvol<1")
    split(sub, lambda r: r["setup"], "setup")
    split(sub, lambda r: r["regime_up"], "regime")

# extra: relvol<1 within regime (is quiet-volume edge just a regime artifact?)
print("\n================ relvol<1 x regime ================")
for reg in [True, False]:
    for lv in [True, False]:
        sub = [r for r in rows if r["regime_up"] == reg and ((r["relvol_entry"] or 99) < 1) == lv]
        if sub:
            print(f"  regime_up={reg!s:5s} relvol<1={lv!s:5s} {agg(sub)}")

# setup x regime
print("\n================ setup x regime ================")
for su in ["VCP", "3C", None]:
    for reg in [True, False]:
        sub = [r for r in rows if r["setup"] == su and r["regime_up"] == reg]
        if sub:
            print(f"  setup={str(su):5s} regime_up={reg!s:5s} {agg(sub)}")

# setup null in july only
print("\nnull setup july:", agg([r for r in jul if r["setup"] is None]))
print("null setup aug:", agg([r for r in aug if r["setup"] is None]))

# re-entry by month
print("\n================ re-entry x month ================")
for m in ["2026-07", "2026-08"]:
    for re_ in [True, False]:
        sub = [r for r in rows if r["month"] == m and r["is_reentry"] == re_]
        if sub:
            print(f"  {m} reentry={re_!s:5s} {agg(sub)}")

# re-entry x regime
for reg in [True, False]:
    for re_ in [True, False]:
        sub = [r for r in rows if r["regime_up"] == reg and r["is_reentry"] == re_]
        if sub:
            print(f"  regime_up={reg!s:5s} reentry={re_!s:5s} {agg(sub)}")

# adv>=100 x regime
print("\n================ adv>=100 detail ================")
for r in rows:
    if r["adv_bucket"] == ">=100":
        print(f"  {r['name']:12s} {r['open_date']} net={r['net_pct']:+6.2f} regime_up={r['regime_up']} sector={r['sector_bucket']} setup={r['setup']}")
