# -*- coding: utf-8 -*-
import json, random
from collections import defaultdict

random.seed(4242)
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

def perm_p_days(dl, B=4000):
    n = 2 * len(dl)
    tw = rw = 0.0
    for dt in dl:
        c = by_date[dt]
        tw += sum(w(e) for e in pick(c, True)); rw += 2 * sum(w(e) for e in c) / len(c)
    obs = (tw - rw) / n
    cnt = 0
    dc = [by_date[dt] for dt in dl]
    for _ in range(B):
        t = r = 0.0
        for c in dc:
            res = [w(e) for e in c]; random.shuffle(res)
            idx = sorted(range(len(c)), key=lambda i: (TO(c[i]), c[i]["code"]), reverse=True)[:2]
            t += sum(res[i] for i in idx); r += 2 * sum(res) / len(c)
        if abs((t - r) / n) >= abs(obs): cnt += 1
    return obs, cnt / B

h = len(days) // 2
print("=== split-half permutation p (B=4000) ===")
o, p = perm_p_days(days[:h]); print("  1st half (%s~%s, %d days): diff %+.1f%%p  perm p=%.4f" % (days[0], days[h-1], h, 100*o, p))
o, p = perm_p_days(days[h:]); print("  2nd half (%s~%s, %d days): diff %+.1f%%p  perm p=%.4f" % (days[h], days[-1], len(days)-h, 100*o, p))
o, p = perm_p_days(days); print("  full     (%d days): diff %+.1f%%p  perm p=%.4f" % (len(days), 100*o, p))

# within-market stratified AUC with permutation p
print()
print("=== within-day x within-market AUC, permutation p (B=4000) ===")
def auc(strata, shuffle=False):
    pw = 0.0; pt = 0
    for c in strata:
        res = [w(e) for e in c]
        if shuffle: random.shuffle(res)
        vals = [TO(e) for e in c]
        wv = [vals[i] for i in range(len(c)) if res[i]]
        lv = [vals[i] for i in range(len(c)) if not res[i]]
        for a in wv:
            for b in lv:
                pt += 1
                if a > b: pw += 1
                elif a == b: pw += 0.5
    return (pw / pt if pt else float('nan')), pt

for mk in ("KOSPI", "KOSDAQ", "BOTH"):
    strata = []
    for dt in days:
        g = defaultdict(list)
        for e in by_date[dt]: g[e["market"]].append(e)
        for m, c in g.items():
            if mk != "BOTH" and m != mk: continue
            if len(c) >= 2: strata.append(c)
    o, pt = auc(strata)
    B = 4000; cnt = 0
    for _ in range(B):
        a, _ = auc(strata, shuffle=True)
        if abs(a - 0.5) >= abs(o - 0.5): cnt += 1
    print("  %-7s AUC %.4f (%d pairs)  perm p=%.4f" % (mk, o, pt, cnt / B))
