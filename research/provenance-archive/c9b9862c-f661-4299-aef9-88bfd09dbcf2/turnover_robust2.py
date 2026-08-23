# -*- coding: utf-8 -*-
import json, random
from collections import defaultdict, Counter

random.seed(31337)
P = r"C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json"
d = json.load(open(P, encoding="utf-8"))
ev = [e for e in d["events"] if e["result"] in ("win", "loss")]
by_date = defaultdict(list)
for e in ev:
    by_date[e["entry_date"]].append(e)
days = [dt for dt in sorted(by_date) if len(by_date[dt]) >= 3]
TO = lambda e: e["turnover_eok"]
def w(e): return 1 if e["result"] == "win" else 0
def pick(c, rev, K=2): return sorted(c, key=lambda e: (TO(e), e["code"]), reverse=rev)[:K]

# 1) concentration: is a handful of repeat names carrying TOP2?
picks = []
for dt in days:
    picks += pick(by_date[dt], True)
cnt = Counter((e["code"], e["name"]) for e in picks)
print("=== TOP2 pick concentration ===")
print("  170 picks -> %d distinct stocks" % len(cnt))
print("  most repeated:", [(nm, c) for (cd, nm), c in cnt.most_common(8)])
wins_by = defaultdict(lambda: [0, 0])
for e in picks:
    wins_by[e["name"]][0] += w(e); wins_by[e["name"]][1] += 1
top_contrib = sorted(wins_by.items(), key=lambda kv: -kv[1][0])[:6]
print("  biggest win contributors:", [(k, "%d/%d" % (v[0], v[1])) for k, v in top_contrib])

# jackknife by stock: drop each stock entirely, recompute
base_days = days
def stat(exclude_code=None, dl=None):
    dl = dl or days
    tw = rw = 0.0; n = 0
    for dt in dl:
        c = [e for e in by_date[dt] if e["code"] != exclude_code]
        if len(c) < 3: continue
        tw += sum(w(e) for e in pick(c, True)); rw += 2 * sum(w(e) for e in c) / len(c); n += 2
    return tw / n, rw / n, n
codes = set(e["code"] for e in picks)
res = []
for cd in codes:
    t, r, n = stat(cd)
    res.append((t - r, cd, n))
res.sort()
name_of = {e["code"]: e["name"] for e in ev}
print("  jackknife-by-stock, 5 most damaging removals:")
for diff, cd, n in res[:5]:
    print("     drop %s %-12s -> diff %+.1f%%p (trades %d)" % (cd, name_of[cd], 100 * diff, n))
print("  jackknife range: %+.1f%%p .. %+.1f%%p" % (100 * res[0][0], 100 * res[-1][0]))

# 2) control for market: same-day AND same-market comparison
print()
print("=== control for market: within-day, within-market pairwise AUC ===")
for mk in ("KOSPI", "KOSDAQ", "ALL(within-market strata)"):
    pw = 0.0; pt = 0
    for dt in days:
        groups = defaultdict(list)
        for e in by_date[dt]:
            groups[e["market"]].append(e)
        for m, c in groups.items():
            if mk in ("KOSPI", "KOSDAQ") and m != mk: continue
            if len(c) < 2: continue
            ws = [e for e in c if w(e)]; ls = [e for e in c if not w(e)]
            for a in ws:
                for b in ls:
                    pt += 1
                    if TO(a) > TO(b): pw += 1
                    elif TO(a) == TO(b): pw += 0.5
    print("  %-26s AUC %.4f over %d win-loss pairs" % (mk, (pw / pt if pt else float('nan')), pt))

# 3) does it depend on how crowded the day is?
print()
print("=== by day crowding ===")
for lo, hi, lab in ((3, 4, "3-4 cands"), (5, 7, "5-7 cands"), (8, 99, "8+ cands")):
    dl = [dt for dt in days if lo <= len(by_date[dt]) <= hi]
    tw = rw = bw = 0.0; n = 0
    for dt in dl:
        c = by_date[dt]
        tw += sum(w(e) for e in pick(c, True)); bw += sum(w(e) for e in pick(c, False))
        rw += 2 * sum(w(e) for e in c) / len(c); n += 2
    print("  %-10s days=%2d trades=%3d TOP %.4f RAND %.4f BOT %.4f (%+.1f%%p)"
          % (lab, len(dl), n, tw / n, rw / n, bw / n, 100 * (tw - rw) / n))

# 4) absolute-threshold version (is it a level effect or a rank effect?)
print()
print("=== absolute turnover level, pooled over ALL 580 resolved trades ===")
qs = sorted(TO(e) for e in ev)
cuts = [qs[int(f * len(qs))] for f in (0.2, 0.4, 0.6, 0.8)]
b = defaultdict(lambda: [0, 0])
for e in ev:
    v = TO(e); i = sum(v >= c for c in cuts)
    b[i][0] += w(e); b[i][1] += 1
labels = ["<%.0f" % cuts[0]] + ["%.0f~%.0f" % (cuts[i], cuts[i + 1]) for i in range(3)] + [">=%.0f" % cuts[3]]
for i in sorted(b):
    ww, nn = b[i]
    print("  quintile %d (%s eok): winrate %.4f (%d/%d)" % (i + 1, labels[i], ww / nn, ww, nn))

# 5) return-side test: mean gain_at_resolve, day-paired sign test
print()
print("=== return-side (gain_at_resolve_pct), day-paired ===")
import math
diffs = []
for dt in days:
    c = by_date[dt]
    t = sum(e["gain_at_resolve_pct"] for e in pick(c, True)) / 2
    r = sum(e["gain_at_resolve_pct"] for e in c) / len(c)
    diffs.append(t - r)
pos = sum(1 for x in diffs if x > 0); neg = sum(1 for x in diffs if x < 0)
m = pos + neg; k = min(pos, neg)
p = min(1.0, 2 * sum(math.comb(m, i) for i in range(k + 1)) / 2 ** m)
print("  per-day mean-return diff TOP2 - day avg: mean %+.2f%%p, +%d/-%d, sign p=%.4f"
      % (sum(diffs) / len(diffs), pos, neg, p))
