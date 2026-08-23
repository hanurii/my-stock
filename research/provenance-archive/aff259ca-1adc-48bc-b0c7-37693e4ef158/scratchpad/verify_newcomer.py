# -*- coding: utf-8 -*-
"""Adversarial verification of the threshold-newcomer flag conclusion."""
import subprocess, json, sys, math, io
from collections import defaultdict, Counter
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = r"C:/Users/hanul/playground/my-stock"
SCRATCH = r"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/aff259ca-1adc-48bc-b0c7-37693e4ef158/scratchpad"

def fisher_two_sided(a, b, c, d):
    """2x2: [[a,b],[c,d]] rows=groups, cols=win/loss. Two-sided Fisher exact."""
    n = a + b + c + d
    r1, c1 = a + b, a + c
    from math import comb
    denom = comb(n, r1)
    def p_a(x):
        if x < 0 or x > r1 or c1 - x < 0 or c1 - x > (n - r1):
            return 0.0
        return comb(c1, x) * comb(n - c1, r1 - x) / denom
    p_obs = p_a(a)
    lo = max(0, r1 + c1 - n); hi = min(r1, c1)
    return sum(p_a(x) for x in range(lo, hi + 1) if p_a(x) <= p_obs * (1 + 1e-9))

# ---- 1. snapshots from git ----
log = subprocess.run(["git", "-C", REPO, "log", "--format=%H %cI",
                      "--", "public/data/sepa-trend-candidates.json"],
                     capture_output=True, text=True).stdout.strip().splitlines()
by_date = {}
for line in log:
    sha, iso = line.split()
    date = iso[:10]
    if date not in by_date:  # log is newest-first; first seen = last commit that date
        by_date[date] = (sha, iso)
snap_dates = sorted(by_date)
print(f"snapshots: {len(snap_dates)}  {snap_dates[0]}..{snap_dates[-1]}")

snaps = {}  # date -> {code: (rs, passed_count, all_pass)}
for date in snap_dates:
    sha, iso = by_date[date]
    raw = subprocess.run(["git", "-C", REPO, "show",
                          f"{sha}:public/data/sepa-trend-candidates.json"],
                         capture_output=True).stdout
    d = json.loads(raw.decode("utf-8"))
    snaps[date] = {c["code"]: (c.get("rs"), c.get("passed_count"), bool(c.get("all_pass")))
                   for c in d["candidates"]}
print("snapshot sizes:", {d: len(snaps[d]) for d in snap_dates})

# ---- 2. trades ----
enr = json.load(open(f"{SCRATCH}/enriched_trades.json", encoding="utf-8"))["rows"]
flagj = json.load(open(f"{SCRATCH}/newcomer_flag.json", encoding="utf-8"))
listing = flagj["trades_listing"]
print("enriched n:", len(enr), " listing n:", len(listing))

# scorecard sanity: net_pct match
sc = json.load(open(f"{REPO}/public/data/scorecard.json", encoding="utf-8"))
sct = [t for t in sc.get("trades", sc if isinstance(sc, list) else [])]
print("scorecard trades:", len(sct), "closed:",
      sum(1 for t in sct if t.get("close_date") or t.get("status") in (None, "closed")))

# ---- 3. recompute tenure per trade ----
def prior_snap_dates(open_date):
    # snapshot committed strictly before open_date 09:00 KST; commits are evening,
    # except a couple of 08:2x morning commits (kept-last-per-date handles those)
    cutoff = open_date + "T09:00:00"
    res = []
    for d in snap_dates:
        sha, iso = by_date[d]
        if iso[:19] < cutoff:
            res.append(d)
    return res

recomp = []
mismatch = []
for t in enr:
    code, od = t["code"], t["open_date"]
    prior = prior_snap_dates(od)
    n_prior = len(prior)
    last10 = prior[-10:]
    ten_s = sum(1 for d in last10 if code in snaps[d] and snaps[d][code][2])
    ten_l = sum(1 for d in last10 if code in snaps[d] and (snaps[d][code][1] or 0) >= 7)
    # streak: consecutive all_pass ending at immediately preceding snapshot
    streak = 0
    for d in reversed(prior):
        if code in snaps[d] and snaps[d][code][2]:
            streak += 1
        else:
            break
    rs_latest = snaps[prior[-1]][code][0] if prior and code in snaps[prior[-1]] else None
    rs_vals = [snaps[d][code][0] for d in last10 if code in snaps[d] and snaps[d][code][0] is not None]
    rs_vol = (max(rs_vals) - min(rs_vals)) if len(rs_vals) >= 2 else None
    newcomer = ten_s <= 2
    rs_floor = (t["displayed_rs"] is not None and t["displayed_rs"] <= 82)
    row = dict(code=code, name=t["name"], open_date=od, net_pct=t["net_pct"],
               win=t["outcome"] == "win", setup=t["setup"], regime_up=t["regime_up"],
               relvol=t["relvol_entry"], rs_disp=t["displayed_rs"], rs_latest=rs_latest,
               ten_s=ten_s, ten_l=ten_l, streak=streak, rs_vol=rs_vol,
               n_prior=n_prior, newcomer=newcomer, rs_floor=rs_floor,
               flag=newcomer or rs_floor)
    recomp.append(row)
    # compare to listing
    match = [l for l in listing if l["code"] == code and l["open_date"] == od]
    if match:
        l = match[0]
        for a, b in [("ten_s", "tenure10_strict"), ("ten_l", "tenure10_loose"),
                     ("streak", "streak_strict"), ("n_prior", "n_prior_snaps"),
                     ("newcomer", "newcomer"), ("rs_floor", "rs_floor"),
                     ("flag", "flag_raw"), ("rs_latest", "rs_latest")]:
            if row[a] != l.get(b):
                mismatch.append((t["name"], od, a, row[a], l.get(b)))
    else:
        mismatch.append((t["name"], od, "NO_LISTING_MATCH", None, None))

print("\n--- per-trade recompute vs listing mismatches:", len(mismatch))
for m in mismatch:
    print("  ", m)

def cell(rows):
    n = len(rows); w = sum(1 for r in rows if r["win"])
    s = sum(r["net_pct"] for r in rows)
    return dict(n=n, wins=w, win_rate=round(100 * w / n, 1) if n else None,
                avg=round(s / n, 2) if n else None, sum=round(s, 2))

def show(label, rows):
    c = cell(rows)
    print(f"  {label:38s} n={c['n']:3d} wins={c['wins']:2d} wr={c['win_rate']}% avg={c['avg']} sum={c['sum']}")
    return c

# ---- 4. headline splits ----
print("\n=== (1) headline split reproduction (all 53) ===")
newc = [r for r in recomp if r["ten_s"] <= 2]
mid = [r for r in recomp if 3 <= r["ten_s"] <= 4]
reg = [r for r in recomp if r["ten_s"] >= 5]
c_n = show("newcomer ten<=2", newc)
c_m = show("mid 3-4", mid)
c_r = show("regular >=5", reg)
p_nr = fisher_two_sided(c_n["wins"], c_n["n"] - c_n["wins"], c_r["wins"], c_r["n"] - c_r["wins"])
rest = [r for r in recomp if r["ten_s"] > 2]
c_rest = cell(rest)
p_nrest = fisher_two_sided(c_n["wins"], c_n["n"] - c_n["wins"], c_rest["wins"], c_rest["n"] - c_rest["wins"])
print(f"  fisher new vs reg: {p_nr:.4f} (file: {flagj['trades_split']['fisher_new_vs_reg']})")
print(f"  fisher new vs rest: {p_nrest:.4f} (file: {flagj['trades_split']['fisher_new_vs_rest']})")

print("\n=== (3) sample integrity ===")
print("unique codes: newcomer", len(set(r['code'] for r in newc)), "of", len(newc),
      "| mid", len(set(r['code'] for r in mid)), "of", len(mid),
      "| regular", len(set(r['code'] for r in reg)), "of", len(reg))
print("newcomer open-date clusters:", Counter(r['open_date'] for r in newc))
print("newcomer month:", Counter(r['open_date'][:7] for r in newc))
print("all-trades month:", Counter(r['open_date'][:7] for r in recomp))
lowhist = [r for r in newc if r["n_prior"] < 5]
print("newcomers with n_prior<5 (mechanical):", [(r['name'], r['open_date']) for r in lowhist])

ANCH = {("F&F".replace('&','&'),), }
def is_anchor(r):
    return (r["code"], r["open_date"]) in {("007700", "2026-07-31"), ("009190", "2026-08-13")} or \
           (r["name"] in ("F&F", "대양금속") and r["open_date"] in ("2026-07-31", "2026-08-13"))

anchors = [r for r in recomp if is_anchor(r)]
print("anchors found:", [(r['name'], r['open_date'], r['net_pct']) for r in anchors])

print("\n--- newcomer cell excluding anchors ---")
newc_x = [r for r in newc if not is_anchor(r)]
c_nx = show("newcomer excl anchors", newc_x)
p = fisher_two_sided(c_nx["wins"], c_nx["n"] - c_nx["wins"], c_r["wins"], c_r["n"] - c_r["wins"])
print(f"  fisher (excl-anchor newcomer vs regular): {p:.4f}")

print("\n--- newcomer cell excluding anchors AND low-history (n_prior<5) ---")
newc_xx = [r for r in newc_x if r["n_prior"] >= 5]
c_nxx = show("newcomer excl anchors+lowhist", newc_xx)
if c_nxx["n"]:
    p = fisher_two_sided(c_nxx["wins"], c_nxx["n"] - c_nxx["wins"], c_r["wins"], c_r["n"] - c_r["wins"])
    print(f"  fisher vs regular: {p:.4f}")
    print("  members:", [(r['name'], r['open_date'], r['net_pct']) for r in newc_xx])

print("\n--- proposed flag (ten<=2 OR rs<=82) excluding anchors ---")
flg = [r for r in recomp if r["flag"]]
kept = [r for r in recomp if not r["flag"]]
c_f = show("flagged (all)", flg); c_k = show("kept (all)", kept)
p = fisher_two_sided(c_f["wins"], c_f["n"] - c_f["wins"], c_k["wins"], c_k["n"] - c_k["wins"])
print(f"  fisher: {p:.4f} (file {flagj['flag_proposed_trades']['fisher_flag']})")
flg_x = [r for r in flg if not is_anchor(r)]
c_fx = show("flagged excl anchors", flg_x)
p = fisher_two_sided(c_fx["wins"], c_fx["n"] - c_fx["wins"], c_k["wins"], c_k["n"] - c_k["wins"])
print(f"  fisher excl anchors: {p:.4f}")
anch_share = sum(r['net_pct'] for r in anchors)
print(f"  anchors' share of avoided sum: {abs(anch_share):.2f} of {abs(sum(r['net_pct'] for r in flg)):.2f} "
      f"({100*abs(anch_share)/abs(sum(r['net_pct'] for r in flg)):.0f}%)")

print("\n--- precision variant ten<=1 AND rs<=84 ---")
prec = [r for r in recomp if r["ten_s"] <= 1 and r["rs_disp"] is not None and r["rs_disp"] <= 84]
c_p = show("ten<=1 AND rs<=84", prec)
print("  members:", [(r['name'], r['open_date'], r['net_pct']) for r in prec])
prec_x = [r for r in prec if not is_anchor(r)]
c_px = show("  same excl anchors", prec_x)
kept_p = [r for r in recomp if r not in prec]
c_kp = cell(kept_p)
if c_px["n"]:
    p = fisher_two_sided(c_px["wins"], c_px["n"] - c_px["wins"], c_kp["wins"], c_kp["n"] - c_kp["wins"])
    print(f"  fisher excl anchors vs kept: {p:.4f}")
p_full = fisher_two_sided(c_p["wins"], c_p["n"] - c_p["wins"], c_kp["wins"], c_kp["n"] - c_kp["wins"])
print(f"  fisher full vs kept: {p_full:.4f}")
# how special is 4-6 straight losses given base loss rate?
base_loss = 34 / 53
print(f"  P(4 straight losses at base loss rate {base_loss:.2f}) = {base_loss**4:.3f}; 6 straight = {base_loss**6:.3f}")

print("\n=== (2) confound cross-tabs ===")
def xtab(label, rowsel):
    sub = [r for r in recomp if rowsel(r)]
    nc = [r for r in sub if r["newcomer"]]; nn = [r for r in sub if not r["newcomer"]]
    print(f"  [{label}] n={len(sub)}")
    cn = show("   newcomer", nc) if nc else None
    cm = show("   non-newcomer", nn) if nn else None
    if nc and nn:
        p = fisher_two_sided(cn["wins"], cn["n"]-cn["wins"], cm["wins"], cm["n"]-cm["wins"])
        print(f"    fisher: {p:.4f}")
    return nc, nn

xtab("setup present", lambda r: r["setup"] is not None)
xtab("setup null", lambda r: r["setup"] is None)
xtab("regime_down", lambda r: not r["regime_up"])
xtab("relvol<1", lambda r: r["relvol"] is not None and r["relvol"] < 1)
xtab("VCP only", lambda r: r["setup"] == "VCP")
xtab("July only", lambda r: r["open_date"][:7] == "2026-07")
xtab("August only", lambda r: r["open_date"][:7] == "2026-08")
xtab("July only, n_prior>=5", lambda r: r["open_date"][:7] == "2026-07" and r["n_prior"] >= 5)
xtab("VCP only, n_prior>=5", lambda r: r["setup"] == "VCP" and r["n_prior"] >= 5)
xtab("VCP only, excl anchors", lambda r: r["setup"] == "VCP" and not is_anchor(r))
xtab("July excl anchors n_prior>=5", lambda r: r["open_date"][:7] == "2026-07" and r["n_prior"] >= 5 and not is_anchor(r))

print("\n=== newcomer composition vs overall ===")
for lab, sel in [("setup_null", lambda r: r["setup"] is None),
                 ("regime_down", lambda r: not r["regime_up"]),
                 ("relvol<1", lambda r: r["relvol"] is not None and r["relvol"] < 1),
                 ("July", lambda r: r["open_date"][:7] == "2026-07")]:
    a = 100 * sum(1 for r in newc if sel(r)) / len(newc)
    b = 100 * sum(1 for r in recomp if sel(r)) / len(recomp)
    print(f"  {lab}: newcomer {a:.0f}% vs all {b:.0f}%")

print("\n=== (4) multiple comparisons ===")
variants = flagj.get("variants_trades", [])
print(f"variants tested in file: {len(variants)}")
# recompute fisher for every variant, find min p
ps = []
for v in variants:
    ten, rs, op = v["ten"], v["rs"], v["op"]
    def hit(r):
        t_ok = (ten is not None and r["ten_s"] <= ten)
        r_ok = (rs is not None and r["rs_disp"] is not None and r["rs_disp"] <= rs)
        if op == "OR": return t_ok or r_ok
        if op == "AND": return t_ok and r_ok
        return t_ok if ten is not None else r_ok
    f = [r for r in recomp if hit(r)]; k = [r for r in recomp if not hit(r)]
    if f and k:
        cf, ck = cell(f), cell(k)
        p = fisher_two_sided(cf["wins"], cf["n"]-cf["wins"], ck["wins"], ck["n"]-ck["wins"])
        ps.append((v["rule"], cf["n"], cf["wins"], p))
        if cf["n"] != v["n_flagged"]:
            print(f"  !! n_flagged mismatch {v['rule']}: mine {cf['n']} vs file {v['n_flagged']}")
ps.sort(key=lambda x: x[3])
print("  best (smallest p) variants:")
for rule, n, w, p in ps[:5]:
    print(f"    {rule:28s} n={n} wins={w} p={p:.4f}  bonferroni x{len(ps)} -> {min(1, p*len(ps)):.3f}")

# count all fisher tests reported anywhere in file
import re
raw = json.dumps(flagj)
nfish = len(re.findall(r'"fisher', raw))
print(f"  fisher-labelled results reported in file: {nfish}")

print("\n=== extra: loss-size structure ===")
stops = [r for r in recomp if not r["win"]]
near_stop = [r for r in stops if -6.5 <= r["net_pct"] <= -4.2]
print(f"losses n={len(stops)}, within stop-band -4.2..-6.5%: {len(near_stop)}")
print("newcomer losses:", [(r['name'], r['net_pct']) for r in newc if not r['win']])
