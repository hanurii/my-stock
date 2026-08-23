# -*- coding: utf-8 -*-
import json, random, sys, math
from collections import defaultdict, Counter

random.seed(20260822)
P = r"C:\Users\hanul\playground\my-stock\public\data\backtest-volatility-pilot.json"
d = json.load(open(P, encoding="utf-8"))
ev = [e for e in d["events"] if e["result"] in ("win", "loss")]
print("resolved win/loss events:", len(ev), Counter(e["result"] for e in ev))

by_date = defaultdict(list)
for e in ev:
    by_date[e["entry_date"]].append(e)

days = {k: v for k, v in by_date.items() if len(v) >= 3}
print("all entry_dates:", len(by_date), " days with >=3 candidates:", len(days))
print("events inside those days:", sum(len(v) for v in days.values()))
print("cand-count distribution:", sorted(Counter(len(v) for v in days.values()).items()))

def win(e): return 1.0 if e["result"] == "win" else 0.0

def expected_wins_topk(cands, key, k=2, reverse=True):
    """Exact expected #wins of top-k by `key`, averaging uniformly over ties at the cutoff."""
    vals = sorted({key(c) for c in cands}, reverse=reverse)
    taken = 0; exp = 0.0
    for v in vals:
        grp = [c for c in cands if key(c) == v]
        room = k - taken
        if room <= 0: break
        if len(grp) <= room:
            exp += sum(win(c) for c in grp); taken += len(grp)
        else:
            exp += room * (sum(win(c) for c in grp) / len(grp)); taken = k
    return exp

rows = []
for dt, cands in sorted(days.items()):
    n = len(cands)
    base = sum(win(c) for c in cands) / n          # random-2 expectation == day win rate
    top = expected_wins_topk(cands, lambda c: c["rs"], 2, True) / 2.0
    bot = expected_wins_topk(cands, lambda c: c["rs"], 2, False) / 2.0
    rows.append(dict(date=dt, n=n, base=base, top=top, bot=bot,
                     rs_lo=min(c["rs"] for c in cands), rs_hi=max(c["rs"] for c in cands)))

n_days = len(rows)
top_wr = sum(r["top"] for r in rows) / n_days
bot_wr = sum(r["bot"] for r in rows) / n_days
rnd_wr = sum(r["base"] for r in rows) / n_days
print("\n=== equal-weight-by-day (each day = one 2-pick decision) ===")
print("days used                 :", n_days)
print("trades if top2 each day   :", n_days * 2)
print("TOP2  by RS   win rate    : %.4f" % top_wr)
print("RANDOM2 (day mean)        : %.4f" % rnd_wr)
print("BOT2  by RS   win rate    : %.4f" % bot_wr)
print("top2 - random  = %+.4f pp" % ((top_wr - rnd_wr) * 100))
print("bot2 - random  = %+.4f pp" % ((bot_wr - rnd_wr) * 100))

# ---- sign test on per-day differences ----
def sign_test(diffs):
    pos = sum(1 for x in diffs if x > 1e-12)
    neg = sum(1 for x in diffs if x < -1e-12)
    tie = len(diffs) - pos - neg
    n = pos + neg
    if n == 0: return pos, neg, tie, 1.0
    # two-sided exact binomial
    def C(a, b): return math.comb(a, b)
    k = min(pos, neg)
    tail = sum(C(n, i) for i in range(0, k + 1)) / (2 ** n)
    p = min(1.0, 2 * tail)
    return pos, neg, tie, p

for label, key in (("TOP2", "top"), ("BOT2", "bot")):
    diffs = [r[key] - r["base"] for r in rows]
    pos, neg, tie, p = sign_test(diffs)
    print("\nsign test %s vs random: better days=%d worse days=%d tied days=%d  p=%.4f"
          % (label, pos, neg, tie, p))

# ---- bootstrap: 2000 draws of "random 2 per day" ----
B = 2000
def boot(stat_top):
    ge = 0; le = 0; samples = []
    for _ in range(B):
        s = 0.0
        for dt, cands in days.items():
            pick = random.sample(cands, 2)
            s += (win(pick[0]) + win(pick[1])) / 2.0
        s /= n_days
        samples.append(s)
        if s >= stat_top - 1e-12: ge += 1
        if s <= stat_top + 1e-12: le += 1
    samples.sort()
    return samples, ge, le

samples, ge_top, le_top = boot(top_wr)
p_top_one = (ge_top + 1) / (B + 1)
p_top_two = min(1.0, 2 * min(ge_top + 1, le_top + 1) / (B + 1))
ge_bot = sum(1 for s in samples if s >= bot_wr - 1e-12)
le_bot = sum(1 for s in samples if s <= bot_wr + 1e-12)
p_bot_two = min(1.0, 2 * min(ge_bot + 1, le_bot + 1) / (B + 1))
print("\n=== bootstrap (2000 x random-2-per-day) ===")
print("random-2 mean %.4f  sd %.4f  p2.5%%=%.4f p97.5%%=%.4f"
      % (sum(samples)/B, (sum((x-sum(samples)/B)**2 for x in samples)/B)**.5,
         samples[int(.025*B)], samples[int(.975*B)]))
print("TOP2 %.4f -> one-sided p=%.4f  two-sided p=%.4f" % (top_wr, p_top_one, p_top_two))
print("BOT2 %.4f -> two-sided p=%.4f" % (bot_wr, p_bot_two))

# ---- trade-weighted view (每 trade equal) ----
tw_top = sum(r["top"] * 2 for r in rows) / (2 * n_days)
print("\ntrade-weighted top2 winrate (same as above by construction): %.4f" % tw_top)

# ---- RS buckets, same-day (day-demeaned) ----
def bucket(rs):
    if rs >= 95: return "95+"
    if rs >= 90: return "90-94"
    if rs >= 85: return "85-89"
    if rs >= 80: return "80-84"
    return "<80"

print("\n=== RS buckets ===")
raw = defaultdict(lambda: [0, 0])
dem = defaultdict(list)
for dt, cands in days.items():
    base = sum(win(c) for c in cands) / len(cands)
    for c in cands:
        b = bucket(c["rs"])
        raw[b][0] += win(c); raw[b][1] += 1
        dem[b].append(win(c) - base)
order = ["<80", "80-84", "85-89", "90-94", "95+"]
print("%-7s %5s %8s %10s %8s" % ("bucket", "n", "raw_WR", "vs_dayavg", "se"))
for b in order:
    if raw[b][1] == 0: continue
    n = raw[b][1]; wr = raw[b][0] / n
    ds = dem[b]; m = sum(ds) / len(ds)
    sd = (sum((x - m) ** 2 for x in ds) / (len(ds) - 1)) ** .5 if len(ds) > 1 else float('nan')
    se = sd / len(ds) ** .5
    print("%-7s %5d %7.1f%% %+9.1fpp %7.1fpp" % (b, n, wr * 100, m * 100, se * 100))

# whole-pool raw bucket WR (all 580 resolved, for contrast / calendar illusion check)
raw2 = defaultdict(lambda: [0, 0])
for e in ev:
    b = bucket(e["rs"]); raw2[b][0] += win(e); raw2[b][1] += 1
print("\n(whole pool, NOT same-day — calendar illusion prone)")
for b in order:
    if raw2[b][1] == 0: continue
    print("  %-7s n=%3d WR=%.1f%%" % (b, raw2[b][1], raw2[b][0] / raw2[b][1] * 100))

# ---- how much RS spread is there within a day? ----
spreads = [r["rs_hi"] - r["rs_lo"] for r in rows]
spreads.sort()
print("\nwithin-day RS spread (hi-lo): median %d, p25 %d, p75 %d, zero-spread days %d"
      % (spreads[len(spreads)//2], spreads[len(spreads)//4], spreads[3*len(spreads)//4],
         sum(1 for s in spreads if s == 0)))
tied = sum(1 for r in rows if abs(r["top"] - r["base"]) < 1e-12 and abs(r["bot"] - r["base"]) < 1e-12)
print("days where RS cannot separate at all:", tied)
