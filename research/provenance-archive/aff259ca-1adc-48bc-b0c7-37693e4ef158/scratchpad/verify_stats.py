# -*- coding: utf-8 -*-
"""Adversarial verification of synthesis.md splits on 53 trades."""
import json, random, sys
from scipy.stats import fisher_exact

SP = r"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/aff259ca-1adc-48bc-b0c7-37693e4ef158/scratchpad"
rows = json.load(open(SP + "/enriched_trades.json", encoding="utf-8"))["rows"]
sc = json.load(open(r"C:/Users/hanul/playground/my-stock/public/data/scorecard.json", encoding="utf-8"))["trades"]

out = []
def p(s=""):
    out.append(s)

# ---------- 1. Row cross-check vs scorecard ----------
sc_idx = {(t["code"], t["open_date"]): t for t in sc}
p("== 1. enriched vs scorecard cross-check ==")
p("scorecard n=%d enriched n=%d, key overlap=%d" % (
    len(sc), len(rows), sum(1 for r in rows if (r["code"], r["open_date"]) in sc_idx)))
random.seed(42)
sample = random.sample(rows, 3)
shared = ["name","close_date","month","net_pct","net_won","outcome","setup","avg_buy","hold_days","stop","stop_violation"]
for r in sample:
    t = sc_idx[(r["code"], r["open_date"])]
    diffs = [(f, r.get(f), t.get(f)) for f in shared if r.get(f) != t.get(f)]
    p("  %s %s (%s): %s" % (r["name"], r["open_date"], r["code"], "MATCH" if not diffs else "DIFF %s" % diffs))
# full-field sweep across all 53, not just 3
mism = 0
for r in rows:
    t = sc_idx.get((r["code"], r["open_date"]))
    if t is None:
        mism += 1; continue
    for f in shared:
        if r.get(f) != t.get(f):
            mism += 1
            p("  FULL-SWEEP DIFF %s %s field=%s enriched=%r scorecard=%r" % (r["name"], r["open_date"], f, r.get(f), t.get(f)))
p("full 53-row sweep on %d shared fields: %d mismatches" % (len(shared), mism))
p("")

# ---------- 2. Recompute split tables & Fisher tests ----------
def cell(pred):
    sub = [r for r in rows if pred(r)]
    w = sum(1 for r in sub if r["outcome"] == "win")
    return len(sub), w

def fisher(a_w, a_n, b_w, b_n):
    """two-sided Fisher exact on wins/losses of group a vs b"""
    table = [[a_w, a_n - a_w], [b_w, b_n - b_w]]
    return fisher_exact(table)[1]

wins = sum(1 for r in rows if r["outcome"] == "win")
p("== 2. overall: %d/%d = %.1f%% ==" % (wins, len(rows), 100.0 * wins / len(rows)))
p("")

tests = []  # (label, p-value, cells-note)

def report(label, groups, headline_pair):
    """groups: list of (name, n, w); headline_pair: (idxA, idxB) into groups for the fisher test"""
    p("-- %s --" % label)
    for name, n, w in groups:
        wr = (100.0 * w / n) if n else float("nan")
        p("   %-28s n=%2d  w=%2d  wr=%5.1f%%%s" % (name, n, w, wr, "  [n<5]" if 0 < n < 5 else ""))
    (ai, bi) = headline_pair
    an, aw = groups[ai][1], groups[ai][2]
    bn, bw = groups[bi][1], groups[bi][2]
    if an and bn:
        pv = fisher(aw, an, bw, bn)
        p("   Fisher (%s vs %s): p=%.4f" % (groups[ai][0], groups[bi][0], pv))
        tests.append((label + ": " + groups[ai][0] + " vs " + groups[bi][0], pv))
    p("")
    return

# 1. setup
g = []
for s in ["VCP", "3C", None]:
    n, w = cell(lambda r, s=s: r["setup"] == s)
    g.append((str(s), n, w))
report("(1) setup  [headline: VCP vs null]", g, (0, 2))
# also VCP vs everything-else pooled
n1, w1 = cell(lambda r: r["setup"] == "VCP")
n2, w2 = cell(lambda r: r["setup"] != "VCP")
pv = fisher(w1, n1, w2, n2)
p("   extra: VCP vs non-VCP pooled: %d/%d vs %d/%d p=%.4f" % (w1, n1, w2, n2, pv))
tests.append(("(1) setup: VCP vs non-VCP pooled", pv))
# setup-present vs null
n1, w1 = cell(lambda r: r["setup"] is not None)
n2, w2 = cell(lambda r: r["setup"] is None)
pv = fisher(w1, n1, w2, n2)
p("   extra: any-setup vs null: %d/%d vs %d/%d p=%.4f" % (w1, n1, w2, n2, pv))
tests.append(("(1) setup: any vs null", pv))
p("")

# 2. sector
g = []
for s in ["주도섹터", "금융·보험", "우선주", "방어·내수소비", "기타"]:
    n, w = cell(lambda r, s=s: r["sector_bucket"] == s)
    g.append((s, n, w))
report("(2) sector [headline: fin/ins vs rest]", g, (1, 4))
# pooled 'avoid' bucket (금융+우선주+adv>=100?) — just fin+pref vs rest
n1, w1 = cell(lambda r: r["sector_bucket"] in ("금융·보험", "우선주"))
n2, w2 = cell(lambda r: r["sector_bucket"] not in ("금융·보험", "우선주"))
pv = fisher(w1, n1, w2, n2)
p("   extra: fin+pref pooled vs rest: %d/%d vs %d/%d p=%.4f" % (w1, n1, w2, n2, pv))
tests.append(("(2) sector: fin+pref vs rest", pv))
p("")

# 3. RS
g = []
for s in ["missing", "<80", "80-89", ">=90"]:
    n, w = cell(lambda r, s=s: r["rs_bucket"] == s)
    g.append((s, n, w))
report("(3) RS [headline: 80-89 vs >=90]", g, (2, 3))

# 4. status
g = []
for s in ["breakout", "actionable", "forming", "not_on_page"]:
    n, w = cell(lambda r, s=s: r["status_bucket"] == s)
    g.append((s, n, w))
report("(4) status [headline: forming vs actionable]", g, (2, 1))

# 5. entry_ready
g = []
for lbl, pred in [("true", lambda r: r["entry_ready"] is True),
                  ("false", lambda r: r["entry_ready"] is False),
                  ("missing", lambda r: r["entry_ready"] is None)]:
    n, w = cell(pred)
    g.append((lbl, n, w))
report("(5) entry_ready [headline: false vs true]", g, (1, 0))

# 6. relvol
g = []
for s in ["<1", "1-1.5", "1.5-3", ">=3"]:
    n, w = cell(lambda r, s=s: r["relvol_bucket"] == s)
    g.append((s, n, w))
report("(6) relvol [headline: <1 vs 1-1.5]", g, (0, 1))
n1, w1 = cell(lambda r: r["relvol_entry"] < 1)
n2, w2 = cell(lambda r: r["relvol_entry"] >= 1)
pv = fisher(w1, n1, w2, n2)
p("   extra: <1 vs >=1 pooled: %d/%d (%.1f%%) vs %d/%d (%.1f%%) p=%.4f" % (
    w1, n1, 100.0*w1/n1, w2, n2, 100.0*w2/n2, pv))
tests.append(("(6) relvol: <1 vs >=1 pooled", pv))
p("")

# 7. regime
g = []
for lbl, v in [("up", True), ("down", False)]:
    n, w = cell(lambda r, v=v: r["regime_up"] is v)
    g.append((lbl, n, w))
report("(7) regime [up vs down]", g, (0, 1))

# 8. adv20
g = []
for s in ["<10", "10-100", ">=100"]:
    n, w = cell(lambda r, s=s: r["adv_bucket"] == s)
    g.append((s, n, w))
report("(8) adv20 [>=100 vs <100 pooled below]", g, (2, 0))
n1, w1 = cell(lambda r: r["adv_bucket"] == ">=100")
n2, w2 = cell(lambda r: r["adv_bucket"] != ">=100")
pv = fisher(w1, n1, w2, n2)
p("   extra: >=100 vs <100 pooled: %d/%d vs %d/%d p=%.4f" % (w1, n1, w2, n2, pv))
tests.append(("(8) adv20: >=100 vs rest", pv))
p("")

# 9. month
g = []
for s in ["2026-07", "2026-08"]:
    n, w = cell(lambda r, s=s: r["month"] == s)
    g.append((s, n, w))
report("(9) month [aug vs jul]", g, (1, 0))
# NOTE: month in scorecard = close month? check consistency: synthesis says 39 jul / 14 aug

# 10. reentry
g = []
for lbl, v in [("first", False), ("reentry", True)]:
    n, w = cell(lambda r, v=v: r["is_reentry"] is v)
    g.append((lbl, n, w))
report("(10) reentry [re vs first]", g, (1, 0))
# conditional: win-after-win
# determine first-attempt outcome per code
first_outcome = {}
for r in sorted(rows, key=lambda r: r["open_date"]):
    if r["attempt_no"] == 1:
        first_outcome[r["code"]] = r["outcome"]
re_rows = [r for r in rows if r["is_reentry"]]
waw = [r for r in re_rows if first_outcome.get(r["code"]) == "win"]
wal = [r for r in re_rows if first_outcome.get(r["code"]) == "loss"]
w1 = sum(1 for r in waw if r["outcome"] == "win")
w2 = sum(1 for r in wal if r["outcome"] == "win")
p("   reentry-after-win: %d/%d, reentry-after-loss: %d/%d" % (w1, len(waw), w2, len(wal)))
if waw and wal:
    pv = fisher(w1, len(waw), w2, len(wal))
    p("   Fisher waw vs wal: p=%.4f" % pv)
    tests.append(("(10) reentry: after-win vs after-loss", pv))
pv = fisher(w1, len(waw), wins - w1, len(rows) - len(waw))
p("   Fisher waw vs all-others: p=%.4f" % pv)
tests.append(("(10) reentry: after-win vs all others", pv))
p("")

# 11. price
g = []
for s in ["<5000원", ">=5000원"]:
    n, w = cell(lambda r, s=s: r["price_bucket"] == s)
    g.append((s, n, w))
report("(11) price", g, (0, 1))

# 12. combo
n1, w1 = cell(lambda r: r["combo"])
p("-- (12) combo: n=%d w=%d (untestable)" % (n1, w1))
p("")

# ---------- July-only reruns of the two claims said to survive ----------
jul = [r for r in rows if r["open_date"].startswith("2026-07")]
p("== July-only (by open_date): n=%d ==" % len(jul))
def jcell(pred):
    sub = [r for r in jul if pred(r)]
    return len(sub), sum(1 for r in sub if r["outcome"] == "win")
n1, w1 = jcell(lambda r: r["setup"] == "VCP")
n2, w2 = jcell(lambda r: r["setup"] is None)
p("  VCP: %d/%d (%.1f%%)  null: %d/%d (%.1f%%)  Fisher p=%.4f" % (
    w1, n1, 100.0*w1/n1, w2, n2, 100.0*w2/n2 if n2 else 0, fisher(w1, n1, w2, n2)))
tests.append(("(1jul) setup VCP vs null, july-only", fisher(w1, n1, w2, n2)))
n1, w1 = jcell(lambda r: r["relvol_entry"] < 1)
n2, w2 = jcell(lambda r: r["relvol_entry"] >= 1)
p("  relvol<1: %d/%d (%.1f%%)  >=1: %d/%d (%.1f%%)  Fisher p=%.4f" % (
    w1, n1, 100.0*w1/n1, w2, n2, 100.0*w2/n2, fisher(w1, n1, w2, n2)))
tests.append(("(6jul) relvol <1 vs >=1, july-only", fisher(w1, n1, w2, n2)))
n1, w1 = jcell(lambda r: r["regime_up"])
n2, w2 = jcell(lambda r: not r["regime_up"])
p("  regime up: %d/%d  down: %d/%d  Fisher p=%.4f" % (w1, n1, w2, n2, fisher(w1, n1, w2, n2)))
tests.append(("(7jul) regime july-only", fisher(w1, n1, w2, n2)))
p("")

# ---------- confounding: setup x relvol x regime cross-tabs ----------
p("== confound checks ==")
# is relvol<1 edge just setup edge? VCP-only relvol split
n1, w1 = cell(lambda r: r["setup"] == "VCP" and r["relvol_entry"] < 1)
n2, w2 = cell(lambda r: r["setup"] == "VCP" and r["relvol_entry"] >= 1)
p("  within VCP: relvol<1 %d/%d (%.1f%%) vs >=1 %d/%d (%.1f%%) p=%.4f" % (
    w1, n1, 100.0*w1/n1, w2, n2, 100.0*w2/n2 if n2 else 0, fisher(w1, n1, w2, n2)))
# null-setup relvol distribution
nullr = [r["relvol_entry"] for r in rows if r["setup"] is None]
p("  null-setup relvols: %s" % sorted(nullr))
# regime vs month overlap
aug = [r for r in rows if r["open_date"] >= "2026-08"]
p("  regime_up by open month: jul %d/%d, aug %d/%d" % (
    sum(1 for r in jul if r["regime_up"]), len(jul),
    sum(1 for r in aug if r["regime_up"]), len(aug)))
# month field vs open_date month
mm = sum(1 for r in rows if r["month"] != r["open_date"][:7])
p("  rows where month field != open_date month: %d (month is close-month?)" % mm)
# adv>=100 overlap with sector buckets
big = [r for r in rows if r["adv_bucket"] == ">=100"]
p("  adv>=100 rows: %s" % [(r["name"], r["sector_bucket"], r["outcome"]) for r in big])
p("")

# ---------- multiple comparisons ----------
p("== 3. all Fisher p-values (sorted), ~12 axes tested ==")
tests.sort(key=lambda t: t[1])
m = 12  # axes examined in synthesis
p("Bonferroni alpha for 12 axes: 0.05/12 = %.5f" % (0.05 / m))
# Benjamini-Hochberg on the primary per-axis tests
for label, pv in tests:
    p("   p=%.4f  %s" % (pv, label))
# BH FDR
primary = tests  # treat all as family
srt = sorted(primary, key=lambda t: t[1])
k = len(srt)
bh_sig = []
for i, (label, pv) in enumerate(srt, 1):
    if pv <= 0.10 * i / k:
        bh_sig.append((label, pv))
p("")
p("BH-FDR(q=0.10) survivors (naive, family=%d tests): %s" % (k, [l for l, _ in bh_sig]))

open(SP + "/verify_out.txt", "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))
