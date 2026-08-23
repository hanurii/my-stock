# -*- coding: utf-8 -*-
import json, random, math
from collections import defaultdict, Counter

random.seed(20260822)
P = r"C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json"
d = json.load(open(P, encoding="utf-8"))
ev = [e for e in d["events"] if e["result"] in ("win", "loss")]
print("resolved events (win/loss):", len(ev), Counter(e["result"] for e in ev))
print("overall winrate: %.4f" % (sum(e["result"] == "win" for e in ev) / len(ev)))

by_date = defaultdict(list)
for e in ev:
    by_date[e["entry_date"]].append(e)

days_all = sorted(by_date)
days = [dt for dt in days_all if len(by_date[dt]) >= 3]
print("total entry_dates:", len(days_all), "| dates with >=3 candidates:", len(days))
print("events on those dates:", sum(len(by_date[dt]) for dt in days))
sizes = Counter(len(by_date[dt]) for dt in days)
print("candidates-per-day distribution (>=3):", dict(sorted(sizes.items())))

K = 2

def w(e):
    return 1 if e["result"] == "win" else 0

def pick_top(cands, key, reverse):
    return sorted(cands, key=lambda e: (key(e), e["code"]), reverse=reverse)[:K]

key_to = lambda e: e["turnover_eok"]

rows = []
for dt in days:
    c = by_date[dt]
    n = len(c)
    day_wr = sum(w(e) for e in c) / n
    top = pick_top(c, key_to, True)
    bot = pick_top(c, key_to, False)
    rows.append(dict(date=dt, n=n, day_wr=day_wr,
                     top_w=sum(w(e) for e in top), bot_w=sum(w(e) for e in bot),
                     top_wr=sum(w(e) for e in top) / K, bot_wr=sum(w(e) for e in bot) / K))

n_days = len(rows)
top_trades = n_days * K
top_wins = sum(r["top_w"] for r in rows)
bot_wins = sum(r["bot_w"] for r in rows)
top_wr = top_wins / top_trades
bot_wr = bot_wins / top_trades
rand_wr = sum(r["day_wr"] for r in rows) / n_days

print()
print("=== same-day head-to-head, criterion = turnover_eok (50d avg turnover) ===")
print("days used: %d  | trades per rule: %d" % (n_days, top_trades))
print("TOP2 (largest turnover) winrate : %.4f (%d/%d)" % (top_wr, top_wins, top_trades))
print("RANDOM2 expected winrate        : %.4f" % rand_wr)
print("BOT2 (smallest turnover) winrate: %.4f (%d/%d)" % (bot_wr, bot_wins, top_trades))
print("monotonic (top > random > bottom):", top_wr > rand_wr > bot_wr)

def sign_test(diffs):
    pos = sum(1 for x in diffs if x > 0)
    neg = sum(1 for x in diffs if x < 0)
    tie = sum(1 for x in diffs if x == 0)
    m = pos + neg
    if m == 0:
        return pos, neg, tie, 1.0
    k = min(pos, neg)
    tail = sum(math.comb(m, i) for i in range(0, k + 1)) / 2 ** m
    return pos, neg, tie, min(1.0, 2 * tail)

tp, tn, tt, tsp = sign_test([r["top_wr"] - r["day_wr"] for r in rows])
bp, bn, bt, bsp = sign_test([r["bot_wr"] - r["day_wr"] for r in rows])
print()
print("sign test TOP2 vs day-average : +%d / -%d / tie %d  p=%.4f" % (tp, tn, tt, tsp))
print("sign test BOT2 vs day-average : +%d / -%d / tie %d  p=%.4f" % (bp, bn, bt, bsp))
tbp, tbn, tbt, tbsp = sign_test([r["top_wr"] - r["bot_wr"] for r in rows])
print("sign test TOP2 vs BOT2        : +%d / -%d / tie %d  p=%.4f" % (tbp, tbn, tbt, tbsp))

B = 2000
sims = []
for _ in range(B):
    tot = 0
    for dt in days:
        tot += sum(w(e) for e in random.sample(by_date[dt], K))
    sims.append(tot / top_trades)
sims.sort()
ge = sum(1 for s in sims if s >= top_wr) / B
le = sum(1 for s in sims if s <= top_wr) / B
p_top_2s = min(1.0, 2 * min(ge, le))
ge_b = sum(1 for s in sims if s >= bot_wr) / B
le_b = sum(1 for s in sims if s <= bot_wr) / B
p_bot_2s = min(1.0, 2 * min(ge_b, le_b))
mean_sim = sum(sims) / B
sd = (sum((s - mean_sim) ** 2 for s in sims) / (B - 1)) ** 0.5
print()
print("bootstrap (B=%d) random-2 winrate: mean %.4f  sd %.4f  p2.5=%.4f p97.5=%.4f"
      % (B, mean_sim, sd, sims[int(.025 * B)], sims[int(.975 * B)]))
print("TOP2 %.4f -> one-sided p(random>=top)=%.4f  two-sided p=%.4f" % (top_wr, ge, p_top_2s))
print("BOT2 %.4f -> one-sided p(random<=bot)=%.4f  two-sided p=%.4f" % (bot_wr, le_b, p_bot_2s))

# within-day pairwise AUC using every event
pairs_win = 0.0
pairs_tot = 0
day_lists = []
for dt in days:
    c = sorted(by_date[dt], key=lambda e: e["turnover_eok"])
    n = len(c)
    rk = [i / (n - 1) for i in range(n)]
    day_lists.append(c)
    res = [w(e) for e in c]
    wr_ = [rk[i] for i in range(n) if res[i]]
    lr_ = [rk[i] for i in range(n) if not res[i]]
    for a in wr_:
        for b in lr_:
            pairs_tot += 1
            if a > b:
                pairs_win += 1
            elif a == b:
                pairs_win += 0.5
obs_auc = pairs_win / pairs_tot
print()
print("within-day pairwise AUC (P winner has higher turnover than loser): %.4f over %d win-loss pairs"
      % (obs_auc, pairs_tot))

Bp = 2000
cnt = 0
for _ in range(Bp):
    pw = 0.0
    pt = 0
    for c in day_lists:
        n = len(c)
        res = [w(e) for e in c]
        random.shuffle(res)
        rk = [i / (n - 1) for i in range(n)]
        wr_ = [rk[i] for i in range(n) if res[i]]
        lr_ = [rk[i] for i in range(n) if not res[i]]
        for a in wr_:
            for b in lr_:
                pt += 1
                if a > b:
                    pw += 1
                elif a == b:
                    pw += 0.5
    if pt and abs(pw / pt - 0.5) >= abs(obs_auc - 0.5):
        cnt += 1
print("permutation two-sided p for AUC: %.4f" % (cnt / Bp))

buck = defaultdict(lambda: [0, 0])
for dt in days:
    c = sorted(by_date[dt], key=lambda e: -e["turnover_eok"])
    n = len(c)
    for i, e in enumerate(c):
        q = min(3, int(4 * i / n))
        buck[q][0] += w(e)
        buck[q][1] += 1
print()
print("winrate by within-day turnover quartile (Q1=largest):")
for q in sorted(buck):
    ww, nn = buck[q]
    print("  Q%d: %.4f (%d/%d)" % (q + 1, ww / nn, ww, nn))

def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")

tg = []
bg = []
ag = []
for dt in days:
    c = by_date[dt]
    for e in pick_top(c, key_to, True):
        tg.append(e["gain_at_resolve_pct"])
    for e in pick_top(c, key_to, False):
        bg.append(e["gain_at_resolve_pct"])
    for e in c:
        ag.append(e["gain_at_resolve_pct"])
print()
print("mean gain_at_resolve_pct: TOP2 %.2f  ALL(random) %.2f  BOT2 %.2f" % (mean(tg), mean(ag), mean(bg)))

allev = sorted(ev, key=lambda e: -e["turnover_eok"])
h = len(allev) // 2
print()
print("[contrast, POOL-WIDE cut = the invalid design] top-half winrate %.4f, bottom-half %.4f"
      % (sum(w(e) for e in allev[:h]) / h, sum(w(e) for e in allev[h:]) / (len(allev) - h)))

sp = []
for dt in days:
    v = [e["turnover_eok"] for e in by_date[dt]]
    sp.append(max(v) / min(v) if min(v) > 0 else float("inf"))
sp.sort()
print("within-day turnover max/min ratio: median %.1fx, p10 %.1fx, p90 %.1fx"
      % (sp[len(sp) // 2], sp[int(.1 * len(sp))], sp[int(.9 * len(sp))]))
