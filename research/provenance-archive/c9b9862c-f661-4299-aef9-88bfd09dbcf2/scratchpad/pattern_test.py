# -*- coding: utf-8 -*-
import json, random, collections, math, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

random.seed(20260822)
D = json.load(open('public/data/backtest-volatility-pilot.json', encoding='utf-8'))
ev = [e for e in D['events'] if e['result'] in ('win', 'loss')]
print("resolved events:", len(ev), " (win/loss only, ambiguous+unresolved dropped)")

cnt = collections.Counter(e['pattern'] for e in ev)
wr  = {p: sum(1 for e in ev if e['pattern'] == p and e['result'] == 'win') / cnt[p] for p in cnt}
print("pool-wide (NOT the test, calendar-confounded):")
for p in ('VCP', '3C', 'PP'):
    print("   %-4s n=%3d  win=%3d  winrate=%.1f%%" % (p, cnt[p], sum(1 for e in ev if e['pattern']==p and e['result']=='win'), 100*wr[p]))

# ---- group by entry_date, keep days with >=3 candidates ----
byday = collections.defaultdict(list)
for e in ev:
    byday[e['entry_date']].append(e)
days = {d: v for d, v in byday.items() if len(v) >= 3}
print("\nentry_dates total=%d, with >=3 resolved candidates=%d, events in those days=%d"
      % (len(byday), len(days), sum(len(v) for v in days.values())))
sz = collections.Counter(len(v) for v in days.values())
print("day-size distribution:", dict(sorted(sz.items())))

def w(e): return 1 if e['result'] == 'win' else 0

def exp_pick2(group):
    """expected wins picking 2 at random (no replacement) from group"""
    n = len(group); s = sum(w(e) for e in group)
    return 2.0 * s / n

def exp_prefer(day, P, prefer=True):
    """expected #wins of the 2 picks when pattern P is ranked first (prefer) or last (avoid),
       ties inside a tier broken uniformly at random -> exact expectation."""
    A = [e for e in day if (e['pattern'] == P) == prefer]   # top tier
    B = [e for e in day if (e['pattern'] == P) != prefer]   # bottom tier
    if len(A) >= 2:
        return exp_pick2(A)
    if len(A) == 1:
        return w(A[0]) + (sum(w(e) for e in B) / len(B))
    return exp_pick2(B)

def sign_test(diffs, tol=1e-12):
    pos = sum(1 for x in diffs if x > tol); neg = sum(1 for x in diffs if x < -tol)
    n = pos + neg
    if n == 0: return pos, neg, 1.0
    k = min(pos, neg)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2**n * 2
    return pos, neg, min(1.0, p)

B = 2000
def bootstrap_p(daylist, observed_total, P, prefer):
    """null: pick 2 uniformly at random each day; p = P(random >= observed)."""
    ge = 0; tot = []
    for _ in range(B):
        s = 0.0
        for day in daylist:
            s += sum(w(e) for e in random.sample(day, 2))
        tot.append(s)
        if s >= observed_total - 1e-9: ge += 1
    return (ge + 1) / (B + 1), sum(tot) / B

print("\n" + "=" * 78)
results = {}
for P in ('VCP', '3C', 'PP'):
    # discriminating days: rule differs from random -> day must contain P AND non-P
    dl = [v for v in days.values()
          if any(e['pattern'] == P for e in v) and any(e['pattern'] != P for e in v)]
    if not dl:
        print("\n[%s] discriminating days = 0" % P); continue
    picks = 2 * len(dl)
    top = sum(exp_prefer(d, P, True) for d in dl)
    bot = sum(exp_prefer(d, P, False) for d in dl)
    rnd = sum(exp_pick2(d) for d in dl)
    dif = [exp_prefer(d, P, True) - exp_pick2(d) for d in dl]
    pos, neg, sp = sign_test(dif)
    bp, bmean = bootstrap_p(dl, top, P, True)
    nP = sum(1 for d in dl for e in d if e['pattern'] == P)
    print("\n[prefer %s]  discriminating days=%d  (%s events in them=%d, %d picks simulated)"
          % (P, len(dl), P, nP, picks))
    print("   top2(=%s first) winrate = %.1f%%   (%.2f wins / %d picks)" % (P, 100*top/picks, top, picks))
    print("   random2        winrate = %.1f%%   (%.2f wins)  [bootstrap mean %.2f]" % (100*rnd/picks, rnd, bmean))
    print("   bottom2(=%s last) winrate = %.1f%%   (%.2f wins)" % (P, 100*bot/picks, bot))
    print("   sign test: days better=%d worse=%d tie=%d  p=%.3f" % (pos, neg, len(dl)-pos-neg, sp))
    print("   bootstrap p (random >= top2) = %.4f" % bp)
    print("   monotonic (top > random > bottom): %s" % (top > rnd > bot))
    results[P] = dict(days=len(dl), n_evt=nP, top=100*top/picks, rnd=100*rnd/picks,
                      bot=100*bot/picks, sign_p=sp, boot_p=bp, picks=picks,
                      mono=bool(top > rnd > bot))

# ---- head-to-head same-day pairwise (matched pairs) ----
print("\n" + "=" * 78)
print("head-to-head, same day, all cross-pattern pairs (matched-pair win comparison)")
pairw = collections.Counter()
for v in days.values():
    for i in range(len(v)):
        for j in range(len(v)):
            if i == j: continue
            a, b = v[i], v[j]
            if a['pattern'] == b['pattern']: continue
            key = tuple(sorted([a['pattern'], b['pattern']]))
            if a['pattern'] == key[0]:
                pairw[(key, w(a), w(b))] += 1
for key in [('3C', 'VCP'), ('PP', 'VCP'), ('3C', 'PP')]:
    a1b0 = pairw[(key, 1, 0)]; a0b1 = pairw[(key, 0, 1)]
    both = pairw[(key, 1, 1)]; none = pairw[(key, 0, 0)]
    n = a1b0 + a0b1
    p = 1.0 if n == 0 else min(1.0, 2*sum(math.comb(n,i) for i in range(0, min(a1b0,a0b1)+1))/2**n)
    print("   %s vs %s : discordant pairs %d-%d (both win %d, both lose %d)  binom p=%.3f"
          % (key[0], key[1], a1b0, a0b1, both, none, p))

# ---- also: day-level mean-diff (P vs non-P on days containing both) ----
print("\nday-level winrate diff (P minus non-P), days containing both:")
for P in ('VCP', '3C', 'PP'):
    ds = []
    for v in days.values():
        A = [e for e in v if e['pattern'] == P]; Bx = [e for e in v if e['pattern'] != P]
        if A and Bx:
            ds.append(sum(map(w, A))/len(A) - sum(map(w, Bx))/len(Bx))
    pos, neg, sp = sign_test(ds)
    print("   %-4s days=%3d  mean diff=%+.1f%%p  sign +%d/-%d  p=%.3f"
          % (P, len(ds), 100*sum(ds)/len(ds), pos, neg, sp))

json.dump(results, open('C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/res.json','w'), indent=1)
