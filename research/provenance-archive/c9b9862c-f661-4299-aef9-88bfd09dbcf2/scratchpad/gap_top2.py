import json, random, math
from collections import defaultdict

random.seed(20260822)
P = r"C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json"
d = json.load(open(P, encoding="utf-8"))
ev = [e for e in d["events"] if e["result"] in ("win", "loss")]
print("resolved(win/loss) events:", len(ev))

by_date = defaultdict(list)
for e in ev:
    by_date[e["entry_date"]].append(e)

days = {k: v for k, v in by_date.items() if len(v) >= 3}
print("all entry_dates:", len(by_date), " dates with >=3 candidates:", len(days))
print("candidates on those dates:", sum(len(v) for v in days.values()))
sizes = sorted(len(v) for v in days.values())
print("cands/day: min %d med %d max %d" % (sizes[0], sizes[len(sizes)//2], sizes[-1]))

W = lambda e: 1.0 if e["result"] == "win" else 0.0
KEY = "gap_up_pct"

def expected_wins_pick2(items, reverse):
    """expected #wins among the 2 selected by KEY (reverse=False -> smallest gap),
       exact expectation under uniform random tie-breaking."""
    vals = sorted((-e[KEY] if reverse else e[KEY]) for e in items)
    thr = vals[1]                       # 2nd best value
    key = lambda e: (-e[KEY] if reverse else e[KEY])
    strict = [e for e in items if key(e) < thr]
    tied   = [e for e in items if key(e) == thr]
    k = 2 - len(strict)
    ew = sum(W(e) for e in strict)
    if k > 0:
        ew += k * (sum(W(e) for e in tied) / len(tied))
    return ew

tie_days = 0
top_ew = bot_ew = rnd_ew = 0.0
per_day = []
for dt, items in sorted(days.items()):
    n = len(items)
    day_wr = sum(W(e) for e in items) / n
    t = expected_wins_pick2(items, reverse=False)   # smallest gap  = top2 by rule
    b = expected_wins_pick2(items, reverse=True)    # largest gap   = bottom2
    r = 2 * day_wr                                  # random 2 picks, expectation
    vals = sorted(e[KEY] for e in items)
    if vals[1] == vals[2] or vals[-2] == vals[-3]:
        tie_days += 1
    top_ew += t; bot_ew += b; rnd_ew += r
    per_day.append((dt, n, day_wr, t / 2, b / 2, r / 2))

nd = len(days)
top_wr = top_ew / (2 * nd)
bot_wr = bot_ew / (2 * nd)
rnd_wr = rnd_ew / (2 * nd)
print("\n=== gap_up_pct: pick 2 SMALLEST gap, within-day ===")
print("days=%d  trades=%d" % (nd, 2 * nd))
print("TOP2 (smallest gap)  winrate = %.4f  (%.1f wins / %d)" % (top_wr, top_ew, 2*nd))
print("RANDOM2 (day avg)    winrate = %.4f  (%.1f wins / %d)" % (rnd_wr, rnd_ew, 2*nd))
print("BOT2  (largest gap)  winrate = %.4f  (%.1f wins / %d)" % (bot_wr, bot_ew, 2*nd))
print("monotonic top>rand>bot :", top_wr > rnd_wr > bot_wr)
print("boundary-tie days:", tie_days)

# --- sign test on per-day diff (top2 - day baseline) ---
def sign_test(diffs):
    pos = sum(1 for x in diffs if x > 1e-12)
    neg = sum(1 for x in diffs if x < -1e-12)
    n = pos + neg
    if n == 0:
        return pos, neg, 0, 1.0
    # two-sided exact binomial
    k = min(pos, neg)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return pos, neg, n, min(1.0, 2 * tail)

dt_top = [p[3] - p[5] for p in per_day]
dt_bot = [p[4] - p[5] for p in per_day]
pos, neg, n, p_sign = sign_test(dt_top)
print("\nSIGN TEST top2 vs day-baseline: better %d days, worse %d days, ties %d -> p=%.4f"
      % (pos, neg, nd - n, p_sign))
pos_b, neg_b, n_b, p_sign_b = sign_test(dt_bot)
print("SIGN TEST bot2  vs day-baseline: better %d days, worse %d days, ties %d -> p=%.4f"
      % (pos_b, neg_b, nd - n_b, p_sign_b))

# --- bootstrap: 2000x random 2 picks per day ---
B = 2000
sims = []
day_items = [v for _, v in sorted(days.items())]
for _ in range(B):
    s = 0.0
    for items in day_items:
        a, b2 = random.sample(items, 2)
        s += W(a) + W(b2)
    sims.append(s / (2 * nd))
sims.sort()
ge = sum(1 for s in sims if s >= top_wr - 1e-12)
le = sum(1 for s in sims if s <= top_wr + 1e-12)
p_one = ge / B
p_two = min(1.0, 2 * min(ge, le) / B)
print("\nBOOTSTRAP (%d reps of random-2-per-day):" % B)
print("  random pooled winrate mean=%.4f sd=%.4f  p05=%.4f p95=%.4f"
      % (sum(sims)/B, (sum((x-sum(sims)/B)**2 for x in sims)/B) ** .5, sims[int(.05*B)], sims[int(.95*B)]))
print("  observed TOP2=%.4f -> one-sided p(random>=obs)=%.4f  two-sided p=%.4f" % (top_wr, p_one, p_two))
geb = sum(1 for s in sims if s >= bot_wr - 1e-12); leb = sum(1 for s in sims if s <= bot_wr + 1e-12)
print("  observed BOT2 =%.4f -> two-sided p=%.4f" % (bot_wr, min(1.0, 2*min(geb, leb)/B)))

# --- sanity: pooled (calendar-illusion) view for contrast ---
allsorted = sorted(ev, key=lambda e: e[KEY])
q = len(allsorted)//4
print("\n[contrast, INVALID design] pooled quartile winrates by gap:",
      ["%.3f" % (sum(W(e) for e in allsorted[i*q:(i+1)*q]) / q) for i in range(4)])

# --- gap distribution info ---
gaps = sorted(e[KEY] for e in ev)
print("gap_up_pct: min %.2f p25 %.2f med %.2f p75 %.2f max %.2f, <=0: %d" %
      (gaps[0], gaps[len(gaps)//4], gaps[len(gaps)//2], gaps[3*len(gaps)//4], gaps[-1],
       sum(1 for g in gaps if g <= 0)))
# mean gap of selected groups
sel_t, sel_b = [], []
for dt, items in sorted(days.items()):
    s = sorted(items, key=lambda e: e[KEY])
    sel_t += [e[KEY] for e in s[:2]]; sel_b += [e[KEY] for e in s[-2:]]
print("mean gap top2=%.2f%%  bot2=%.2f%%" % (sum(sel_t)/len(sel_t), sum(sel_b)/len(sel_b)))

# --- secondary: mean gain_at_resolve of picks ---
def pick_metric(reverse, field):
    tot=[]
    for dt, items in sorted(days.items()):
        s = sorted(items, key=lambda e: (-e[KEY] if reverse else e[KEY]))
        tot += [e[field] for e in s[:2]]
    return sum(tot)/len(tot)
print("mean gain_at_resolve: top2=%.2f%% bot2=%.2f%% all=%.2f%%" %
      (pick_metric(False,'gain_at_resolve_pct'), pick_metric(True,'gain_at_resolve_pct'),
       sum(e['gain_at_resolve_pct'] for e in ev)/len(ev)))
