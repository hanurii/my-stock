# -*- coding: utf-8 -*-
import json, random, math
from collections import defaultdict, Counter

random.seed(777)
P = r"C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json"
d = json.load(open(P, encoding="utf-8"))
ev = [e for e in d["events"] if e["result"] in ("win", "loss")]
by_date = defaultdict(list)
for e in ev:
    by_date[e["entry_date"]].append(e)
days = [dt for dt in sorted(by_date) if len(by_date[dt]) >= 3]

def w(e):
    return 1 if e["result"] == "win" else 0

def pick(cands, key, reverse, K):
    return sorted(cands, key=lambda e: (key(e), e["code"]), reverse=reverse)[:K]

TO = lambda e: e["turnover_eok"]

def stats(dlist, K=2, key=TO):
    tw = bw = rw = 0.0
    n = 0
    for dt in dlist:
        c = by_date[dt]
        tw += sum(w(e) for e in pick(c, key, True, K))
        bw += sum(w(e) for e in pick(c, key, False, K))
        rw += K * sum(w(e) for e in c) / len(c)
        n += K
    return tw / n, rw / n, bw / n, n

# ---------- 1) K sensitivity ----------
print("=== K sensitivity (top-K by turnover vs random-K) ===")
for K in (1, 2, 3):
    dl = [dt for dt in days if len(by_date[dt]) >= max(3, K + 1)]
    t, r, b, n = stats(dl, K)
    print("  K=%d days=%3d trades=%3d  TOP %.4f | RAND %.4f | BOT %.4f  (diff %+.1f%%p)"
          % (K, len(dl), n, t, r, b, 100 * (t - r)))

# ---------- 2) cluster bootstrap over days (accounts for day sampling) ----------
print()
print("=== cluster bootstrap over days (B=2000), stat = TOP2 winrate - random expectation ===")
base_t, base_r, base_b, _ = stats(days)
diffs = []
tb_diffs = []
B = 2000
for _ in range(B):
    sample = [random.choice(days) for _ in days]
    t, r, b, _n = stats(sample)
    diffs.append(t - r)
    tb_diffs.append(t - b)
diffs.sort()
tb_diffs.sort()
print("  observed TOP2-RAND = %+.4f ; boot CI95 [%+.4f, %+.4f] ; P(diff<=0) = %.4f"
      % (base_t - base_r, diffs[int(.025 * B)], diffs[int(.975 * B)],
         sum(1 for x in diffs if x <= 0) / B))
print("  observed TOP2-BOT2 = %+.4f ; boot CI95 [%+.4f, %+.4f] ; P(diff<=0) = %.4f"
      % (base_t - base_b, tb_diffs[int(.025 * B)], tb_diffs[int(.975 * B)],
         sum(1 for x in tb_diffs if x <= 0) / B))

# ---------- 3) time split-half & per-half ----------
print()
print("=== chronological split-half ===")
h = len(days) // 2
for label, dl in (("1st half " + days[0] + "~" + days[h - 1], days[:h]),
                  ("2nd half " + days[h] + "~" + days[-1], days[h:])):
    t, r, b, n = stats(dl)
    print("  %-28s days=%2d trades=%3d TOP %.4f RAND %.4f BOT %.4f (diff %+.1f%%p)"
          % (label, len(dl), n, t, r, b, 100 * (t - r)))

# ---------- 4) per-month ----------
print()
print("=== per-month (month of entry_date) ===")
bym = defaultdict(list)
for dt in days:
    bym[dt[:7]].append(dt)
pos = neg = 0
for m in sorted(bym):
    t, r, b, n = stats(bym[m])
    if t > r: pos += 1
    elif t < r: neg += 1
    print("  %s days=%2d trades=%3d TOP %.4f RAND %.4f BOT %.4f (diff %+.1f%%p)"
          % (m, len(bym[m]), n, t, r, b, 100 * (t - r)))
print("  months TOP>RAND: %d, TOP<RAND: %d, tie: %d" % (pos, neg, len(bym) - pos - neg))

# ---------- 5) leave-one-month-out ----------
print()
print("=== leave-one-month-out (is it one month carrying it?) ===")
worst = None
for m in sorted(bym):
    dl = [dt for dt in days if dt[:7] != m]
    t, r, b, n = stats(dl)
    line = "  drop %s: TOP %.4f RAND %.4f diff %+.1f%%p (days %d)" % (m, t, r, 100 * (t - r), len(dl))
    print(line)
    if worst is None or (t - r) < worst[1]:
        worst = (m, t - r)
print("  weakest after dropping %s -> diff %+.1f%%p" % (worst[0], 100 * worst[1]))

# ---------- 6) confounder: what does 'largest turnover' actually select? ----------
print()
print("=== what does TOP2 pick look like (composition) ===")
def compo(dl, reverse):
    picks = []
    for dt in dl:
        picks += pick(by_date[dt], TO, reverse, 2)
    print("   market", dict(Counter(e["market"] for e in picks)),
          "| pattern", dict(Counter(e["pattern"] for e in picks)))
    print("   median turnover_eok %.1f | mean rs %.1f | mean atr%% %.2f | mean gap %.2f"
          % (sorted(e["turnover_eok"] for e in picks)[len(picks) // 2],
             sum(e["rs"] for e in picks) / len(picks),
             sum(e["atr_pct"] for e in picks) / len(picks),
             sum(e["gap_up_pct"] for e in picks) / len(picks)))
print(" TOP2:"); compo(days, True)
print(" BOT2:"); compo(days, False)

# ---------- 7) rival same-day rules for calibration (how special is turnover?) ----------
print()
print("=== same-day top2 by other criteria (context for multiple testing) ===")
crits = {
    "turnover_eok": TO,
    "rs": lambda e: e["rs"],
    "-atr_pct": lambda e: -e["atr_pct"],
    "atr_pct": lambda e: e["atr_pct"],
    "-gap_up_pct": lambda e: -e["gap_up_pct"],
    "entry_price": lambda e: e["entry_price"],
    "KOSPI_first": lambda e: 1 if e["market"] == "KOSPI" else 0,
}
# permutation p per criterion: shuffle results within day
def perm_p(key, B=2000):
    obs, r0, _b, n = stats(days, 2, key)
    obs_d = obs - r0
    cnt = 0
    day_c = [by_date[dt] for dt in days]
    for _ in range(B):
        tot = 0.0
        rr = 0.0
        for c in day_c:
            res = [w(e) for e in c]
            random.shuffle(res)
            idx = sorted(range(len(c)), key=lambda i: (key(c[i]), c[i]["code"]), reverse=True)[:2]
            tot += sum(res[i] for i in idx)
            rr += 2 * sum(res) / len(c)
        if abs(tot / n - rr / n) >= abs(obs_d):
            cnt += 1
    return obs, r0, obs_d, cnt / B
for name, k in crits.items():
    o, r0, dd, p = perm_p(k)
    print("  %-14s TOP2 %.4f vs RAND %.4f  diff %+.1f%%p  perm p=%.4f" % (name, o, r0, 100 * dd, p))

# ---------- 8) multiple testing context ----------
print()
print("=== multiple-testing context ===")
p_raw = 0.029
for n_tests in (7, 45):
    print("  Bonferroni with %d tests: q = min(1, %.3f*%d) = %.3f" % (n_tests, p_raw, n_tests, min(1.0, p_raw * n_tests)))
