# -*- coding: utf-8 -*-
"""Adversarial verify — STATS layer. Independent recomputation from passmatrix.npz.

1) Design A h10 daily spread (mean, NW p, n_days)
2) Design B fwd10 episode cell newcomer(<=2) vs returning(>=5): means, Welch t, n
3) episode counts / truncation counts / excl-vs-worst
4) year signs, regime cells, RS band cells (B fwd10)
5) day-clustered episode spread NW (h10)
6) newcomer vs continuing (tenure10==10, >=10d spacing per code)
7) EXTRA: direct returning-vs-continuing test (md's actual claim)
8) trading-rule reimplementation: headline cell
"""
import numpy as np
from scipy import stats

SP = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad"
z = np.load(SP + r"\passmatrix.npz", allow_pickle=False)
dates = np.array([str(d) for d in z["dates"]])
codes = np.array([str(c) for c in z["codes"]])
ap = z["all_pass"]; el = z["eligible"]; rs = z["rs"]; idx = z["idx"]
open_r = z["open_r"]; hi_r = z["hi_r"]; lo_r = z["lo_r"]
T, N = ap.shape
PASS = ap & el
T0 = 253
years = np.array([int(d[:4]) for d in dates])

pres = np.isfinite(idx)
last_present = np.full(N, -1)
for j in range(N):
    p = np.where(pres[:, j])[0]
    if len(p):
        last_present[j] = p[-1]

# tenure10 on PASS
cum = np.concatenate([np.zeros((1, N), np.int32), np.cumsum(PASS.astype(np.int32), 0)])
TEN = np.zeros((T, N), np.int16)
for t in range(T):
    TEN[t] = cum[t] - cum[max(t - 10, 0)]

# regime (breadth equal-weight cum return vs its 20MA) — same construction
mkt = z["market"]
main = (mkt == 1) | (mkt == 2)
both = main[1:] & main[:-1] & pres[1:] & pres[:-1]
with np.errstate(invalid="ignore"):
    dr = np.where(both, idx[1:] / idx[:-1] - 1.0, np.nan)
mean_ret = np.zeros(T)
mean_ret[1:] = np.nanmean(dr, axis=1)
bidx = np.cumprod(1 + mean_ret)
ma20 = np.full(T, np.nan)
cs = np.concatenate([[0.0], np.cumsum(bidx)])
ma20[19:] = (cs[20:] - cs[:-20]) / 20
regime_up = bidx > ma20

def fwd(h):
    f = np.full((T, N), np.nan)
    f[:T - h] = idx[h:] / idx[:-h] - 1.0
    return f

F10, F20 = fwd(10), fwd(20)

def nw_se(x, lag):
    x = np.asarray(x, float); n = len(x)
    e = x - x.mean(); s = np.dot(e, e) / n
    for l in range(1, lag + 1):
        s += 2 * (1 - l / (lag + 1)) * np.dot(e[l:], e[:-l]) / n
    return np.sqrt(max(s, 1e-18) / n)

# ── 1) Design A h10 ────────────────────────────────────────────────
days, spread = [], []
for t in range(T0, T - 10):
    jj = np.where(PASS[t])[0]
    if not len(jj):
        continue
    r = F10[t, jj]; te = TEN[t, jj]
    ok = np.isfinite(r)
    nm = ok & (te <= 2); rm = ok & (te >= 5)
    if nm.sum() == 0 or rm.sum() == 0:
        continue
    days.append(t); spread.append(r[nm].mean() - r[rm].mean())
spread = np.array(spread)
se = nw_se(spread, 10)
tstat = spread.mean() / se
p = 2 * stats.t.sf(abs(tstat), len(spread) - 1)
print(f"[A h10] n_days={len(spread)} mean={spread.mean()*100:+.3f}pp NW t={tstat:.2f} p={p:.4f}"
      f"  (claimed: 1358, +0.242, p=0.459)")

# ── 2-3) Design B episodes ─────────────────────────────────────────
st = PASS & ~np.concatenate([np.zeros((1, N), bool), PASS[:-1]])
ti, jj = np.where(st)
sel = ti >= T0
ti, jj = ti[sel], jj[sel]
te = TEN[ti, jj]
print(f"[B episodes] total={len(ti)} new={(te<=2).sum()} gray={((te>=3)&(te<=4)).sum()} "
      f"ret={(te>=5).sum()}  (claimed 19924/11080/2363/6481)")

def cellB(F, h, sel_a, sel_b, label, trunc_mode="excl"):
    va, vb = [], []
    for arr, s in ((va, sel_a), (vb, sel_b)):
        for t, j in zip(ti[s], jj[s]):
            if t + h >= T:
                continue
            v = F[t, j]
            if not np.isfinite(v):
                if t + h > last_present[j]:      # delist-truncated
                    if trunc_mode == "worst":
                        arr.append(-0.10)
                    continue
                continue
            arr.append(v)
    a, b = np.array(va), np.array(vb)
    tt, pp = stats.ttest_ind(a, b, equal_var=False)
    print(f"[{label}] n={len(a)}/{len(b)} mean_a={a.mean()*100:+.2f} mean_b={b.mean()*100:+.2f} "
          f"diff={(a.mean()-b.mean())*100:+.2f}pp t={tt:.2f} p={pp:.4f}")
    return a, b

new_m = te <= 2
ret_m = te >= 5
a, b = cellB(F10, 10, new_m, ret_m, "B fwd10 excl")
cellB(F10, 10, new_m, ret_m, "B fwd10 worst", "worst")
cellB(F20, 20, new_m, ret_m, "B fwd20 excl")

# truncation counts among pass-days
tr10 = 0; tr20 = 0
for t in range(T0, T - 10):
    jj2 = np.where(PASS[t])[0]
    for j in jj2:
        if not np.isfinite(F10[t, j]) and t + 10 > last_present[j]:
            tr10 += 1
for t in range(T0, T - 20):
    jj2 = np.where(PASS[t])[0]
    for j in jj2:
        if not np.isfinite(F20[t, j]) and t + 20 > last_present[j]:
            tr20 += 1
tot_passdays = int(PASS[T0:].sum())
print(f"[trunc] h10={tr10} h20={tr20} of pass-days={tot_passdays} "
      f"({tr10/tot_passdays*100:.3f}% / {tr20/tot_passdays*100:.3f}%)  (claimed 32 / 251)")

# ── 4) year / regime / rs cells (B fwd10) ──────────────────────────
print("\n[B fwd10 by year] (claimed +0.50/+1.67/+0.56/+0.39/+0.41/+1.74)")
ep_year = years[ti]
for y in range(2021, 2027):
    cellB(F10, 10, new_m & (ep_year == y), ret_m & (ep_year == y), f"y{y}")
print("\n[B fwd10 by regime] (claimed up +0.56 p=.092 / down +0.88 p=.038)")
ep_up = regime_up[ti]
cellB(F10, 10, new_m & ep_up, ret_m & ep_up, "regime up")
cellB(F10, 10, new_m & ~ep_up, ret_m & ~ep_up, "regime down")
print("\n[B fwd10 by RS] (claimed 80-89 +0.69 p=.040 / 90+ +0.64 p=.13)")
ep_rs = rs[ti, jj]
cellB(F10, 10, new_m & (ep_rs <= 89), ret_m & (ep_rs <= 89), "rs80-89")
cellB(F10, 10, new_m & (ep_rs >= 90), ret_m & (ep_rs >= 90), "rs90+")

# ── 5) day-clustered NW ────────────────────────────────────────────
dd, sp2 = [], []
for t in range(T0, T - 10):
    jj2 = np.where(st[t])[0]
    if not len(jj2):
        continue
    r = F10[t, jj2]; tt_ = TEN[t, jj2]
    ok = np.isfinite(r)
    nm = ok & (tt_ <= 2); rm = ok & (tt_ >= 5)
    if nm.sum() == 0 or rm.sum() == 0:
        continue
    dd.append(t); sp2.append(r[nm].mean() - r[rm].mean())
sp2 = np.array(sp2)
se2 = nw_se(sp2, 10)
t2 = sp2.mean() / se2
p2 = 2 * stats.t.sf(abs(t2), len(sp2) - 1)
print(f"\n[B day-clustered h10] n_days={len(sp2)} mean={sp2.mean()*100:+.3f}pp t={t2:.2f} "
      f"p={p2:.4f}  (claimed 1222, +1.039, p=0.0045)")

# ── 6) continuing regulars ─────────────────────────────────────────
cont = []
lastpick = {}
for t in range(T0, T):
    for j in np.where(PASS[t] & (TEN[t] == 10))[0]:
        if t >= lastpick.get(j, -999) + 10:
            lastpick[j] = t
            cont.append((t, j))
cvals = [F10[t, j] for t, j in cont if t + 10 < T and np.isfinite(F10[t, j])]
cvals = np.array(cvals)
tt3, pp3 = stats.ttest_ind(a, cvals, equal_var=False)
print(f"[B new vs continuing] n={len(a)}/{len(cvals)} mean_new={a.mean()*100:+.2f} "
      f"mean_cont={cvals.mean()*100:+.2f} diff={(a.mean()-cvals.mean())*100:+.2f}pp p={pp3:.4f}"
      f"  (claimed +0.51 vs +0.45, diff +0.06, p=0.81)")

# 7) EXTRA: returning vs continuing directly
tt4, pp4 = stats.ttest_ind(b, cvals, equal_var=False)
print(f"[EXTRA ret vs cont] mean_ret={b.mean()*100:+.2f} mean_cont={cvals.mean()*100:+.2f} "
      f"diff={(b.mean()-cvals.mean())*100:+.2f}pp t={tt4:.2f} p={pp4:.4f}")

# ── 8) trading rule (independent reimplementation) ─────────────────
def rule(t0, j, tp=0.20, sl=-0.10, hold=60, cost=0.0034):
    te_ = t0 + 1
    if te_ >= T or not (np.isfinite(idx[te_, j]) and np.isfinite(open_r[te_, j])):
        return None
    entry = idx[te_, j] * open_r[te_, j]
    if not np.isfinite(entry) or entry <= 0:
        return None
    tgt, stp = entry * (1 + tp), entry * (1 + sl)
    last_d = min(te_ + hold - 1, T - 1)
    for d in range(te_, last_d + 1):
        if not np.isfinite(idx[d, j]):
            fut = idx[d:last_d + 1, j]
            if not np.isfinite(fut).any():
                seg = idx[te_:d, j]
                fin = np.where(np.isfinite(seg))[0]
                if not len(fin):
                    return None
                return (seg[fin[-1]] / entry - 1 - cost, "delist")
            continue
        o = idx[d, j] * open_r[d, j] if np.isfinite(open_r[d, j]) else np.nan
        hp = idx[d, j] * hi_r[d, j] if np.isfinite(hi_r[d, j]) else idx[d, j]
        lp = idx[d, j] * lo_r[d, j] if np.isfinite(lo_r[d, j]) else idx[d, j]
        if d > te_ and np.isfinite(o):
            if o <= stp:
                return (o / entry - 1 - cost, "stop_gap")
            if o >= tgt:
                return (o / entry - 1 - cost, "target_gap")
        hs, ht = lp <= stp, hp >= tgt
        if hs:
            return (sl - cost, "stop")     # both-hit counts as loss too
        if ht:
            return (tp - cost, "target")
    ex = idx[last_d, j]
    if not np.isfinite(ex):
        seg = idx[te_:last_d + 1, j]
        fin = np.where(np.isfinite(seg))[0]
        ex = seg[fin[-1]]
    return (ex / entry - 1 - cost, "time")

ra, rb = [], []
for m_, arr in ((new_m, ra), (ret_m, rb)):
    for t, j in zip(ti[m_], jj[m_]):
        res = rule(t, j)
        if res is None:
            continue
        if res[1] == "time" and t + 60 > T - 1:
            continue  # right-edge unresolved
        arr.append(res[0])
ra, rb = np.array(ra), np.array(rb)
tt5, pp5 = stats.ttest_ind(ra, rb, equal_var=False)
print(f"\n[rule cell] n={len(ra)}/{len(rb)} mean_new={ra.mean()*100:+.2f} mean_ret={rb.mean()*100:+.2f} "
      f"diff={(ra.mean()-rb.mean())*100:+.2f}pp p={pp5:.4f} win_new={(ra>0).mean():.3f} "
      f"win_ret={(rb>0).mean():.3f}  (claimed -0.37/-0.94 diff +0.56 p=0.020 win .353/.339)")
EOF_MARKER = None
