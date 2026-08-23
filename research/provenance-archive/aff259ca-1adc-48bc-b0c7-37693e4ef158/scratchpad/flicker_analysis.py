# -*- coding: utf-8 -*-
"""
Flicker-passer vs list-regular statistical test.

Hypothesis: "flicker passers (신참, tenure10<=2 at pass-day) fail more often
than list regulars (단골, tenure10>=5)".

Design A: daily equal-weight cohort spread of forward 5/10/20d returns.
Design B: episode-level (first pass-day of a consecutive pass run).
Stratification: year, regime (equal-weight breadth idx vs 20d MA), RS band.
Sensitivity: tenure windows 10/15/20 x newcomer thresholds <=1/<=2/<=3.
Falsification: RS 80-82 floor alone; tenure effect within RS>=90.
Delisting: exclude-truncated vs truncated=-10%.
"""
import json
import numpy as np
from scipy import stats

SP = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad"

z = np.load(SP + r"\passmatrix.npz", allow_pickle=False)
dates = z["dates"]              # (T,) str
codes = z["codes"]              # (N,) str
all_pass = z["all_pass"]        # (T,N) bool  pure 8 criteria
eligible = z["eligible"]        # (T,N) bool  page filter
tenure10_given = z["tenure10"]  # (T,N) int8  built on pure all_pass
rs = z["rs"]                    # (T,N) int16 (-1 unset)
idx = z["idx"]                  # (T,N) float64 adjusted index (NaN if absent)
open_r = z["open_r"]; hi_r = z["hi_r"]; lo_r = z["lo_r"]
present = z["present"]          # (T,N) bool
market = z["market"]            # (T,N) uint8 1=KOSPI 2=KOSDAQ 3=KONEX/other

T, N = all_pass.shape
years = np.array([d[:4] for d in dates])
year_int = years.astype(int)

TEST_COUNT = 0  # count every p-value produced

# ────────────────────────────────────────────────────────────────────
# 0) basics: pass definition, warm-up cut, presence gaps
# ────────────────────────────────────────────────────────────────────
PASS = all_pass & eligible          # the list the user actually sees
PASS_PURE = all_pass                # sensitivity

T_START = 253                       # meta: RS pools shortened until ~2021-01
print("analysis starts:", dates[T_START])

# presence gap check: absent day with later presence
last_present = np.full(N, -1)
first_present = np.full(N, T)
for j in range(N):
    p = np.where(present[:, j])[0]
    if len(p):
        last_present[j] = p[-1]
        first_present[j] = p[0]
# gap days = not present but between first and last presence
span = np.zeros((T, N), dtype=bool)
for j in range(N):
    if last_present[j] >= 0:
        span[first_present[j]:last_present[j] + 1, j] = True
gap_days = int((span & ~present).sum())
print("presence gap stock-days (absent mid-listing):", gap_days)

# ────────────────────────────────────────────────────────────────────
# 1) tenure matrices for W in {10,15,20} on PASS definition
# ────────────────────────────────────────────────────────────────────
def tenure_mat(pass_mat, W):
    ap = pass_mat.astype(np.int32)
    cum = np.concatenate([np.zeros((1, N), np.int32), np.cumsum(ap, axis=0)])
    out = np.zeros((T, N), dtype=np.int16)
    for t in range(T):
        lo_i = max(t - W, 0)
        out[t] = cum[t] - cum[lo_i]
    return out

TEN = {W: tenure_mat(PASS, W) for W in (10, 15, 20)}
TEN_PURE10 = tenure10_given.astype(np.int16)

# check: our W=10 tenure on pure all_pass equals the provided matrix
chk = tenure_mat(PASS_PURE, 10)
assert (chk == TEN_PURE10).all(), "tenure10 recomputation mismatch!"
print("tenure10 recomputation matches provided matrix: OK")

# ────────────────────────────────────────────────────────────────────
# 2) forward returns (5/10/20) with truncation flags
# ────────────────────────────────────────────────────────────────────
HORIZONS = (5, 10, 20)
fwd = {}       # h -> (T,N) float  (NaN = unusable)
trunc = {}     # h -> (T,N) bool   (delisting-truncated; right-edge excluded)
for h in HORIZONS:
    f = np.full((T, N), np.nan)
    tr = np.zeros((T, N), dtype=bool)
    valid_t = T - 1 - h
    f[:valid_t + 1] = idx[h:] / idx[:-h] - 1.0
    # truncated: base idx finite, target NaN, and t+h <= last day of grid,
    # and stock never present again after t (true disappearance)
    base_ok = np.isfinite(idx[:valid_t + 1])
    tgt_nan = ~np.isfinite(idx[h:])
    tr_part = base_ok & tgt_nan
    # distinguish gap (reappears later) from delist: use last_present
    tt = np.arange(valid_t + 1)[:, None]
    is_delist = (tt + h) > last_present[None, :]
    tr[:valid_t + 1] = tr_part & is_delist
    gap_case = tr_part & ~is_delist
    # gap case: carry forward last available idx within (t, t+h]
    gi, gj = np.where(gap_case)
    for a, b in zip(gi, gj):
        seg = idx[a + 1:a + h + 1, b]
        fin = np.where(np.isfinite(seg))[0]
        if len(fin):
            f[a, b] = seg[fin[-1]] / idx[a, b] - 1.0
        else:
            tr[a, b] = True  # no price at all in window -> treat as truncated
    fwd[h] = f
    trunc[h] = tr
    print(f"h={h}: truncated(stock-days, pass days only)="
          f"{int((tr & PASS)[T_START:].sum())}, gap-carried={int(gap_case.sum())}")

# ────────────────────────────────────────────────────────────────────
# 3) breadth (국면) index: equal-weight mean daily return, cumulated
# ────────────────────────────────────────────────────────────────────
main_mkt = (market == 1) | (market == 2)
both = main_mkt[1:] & main_mkt[:-1] & np.isfinite(idx[1:]) & np.isfinite(idx[:-1])
day_ret = np.where(both, idx[1:] / idx[:-1] - 1.0, np.nan)
mean_ret = np.full(T, 0.0)
mean_ret[1:] = np.nanmean(np.where(both, day_ret, np.nan), axis=1)
bidx = np.cumprod(1.0 + mean_ret)
ma20 = np.full(T, np.nan)
cs = np.concatenate([[0.0], np.cumsum(bidx)])
ma20[19:] = (cs[20:] - cs[:-20]) / 20
regime_up = bidx > ma20            # (T,) bool; NaN MA -> False (pre-day-20)
print("regime up-days share (from T_START):",
      round(float(regime_up[T_START:].mean()), 3))

# ────────────────────────────────────────────────────────────────────
# helper stats
# ────────────────────────────────────────────────────────────────────
def nw_se(x, lag):
    """Newey-West (Bartlett) SE of the mean of series x."""
    x = np.asarray(x, float)
    n = len(x)
    e = x - x.mean()
    g0 = np.dot(e, e) / n
    s = g0
    for l in range(1, lag + 1):
        w = 1.0 - l / (lag + 1.0)
        s += 2.0 * w * np.dot(e[l:], e[:-l]) / n
    s = max(s, 1e-18)
    return np.sqrt(s / n)

def tstat_p(mean, se, dfree):
    t = mean / se if se > 0 else np.nan
    p = 2 * stats.t.sf(abs(t), dfree) if np.isfinite(t) else np.nan
    return t, p

def summarize_series(s_days, s_vals, horizon, label):
    """Inference on a daily spread series: every-step subsample t-test + NW."""
    global TEST_COUNT
    s_vals = np.asarray(s_vals, float)
    n = len(s_vals)
    out = {"label": label, "n_days": n,
           "mean_pp": round(float(s_vals.mean() * 100), 3) if n else None}
    if n < 8:
        out["note"] = "too few days"
        return out
    # every-10th (and every-h for h=20) non-overlapping subsample t-test
    for step in sorted({10, max(10, horizon)}):
        pick, last = [], -10**9
        for d, v in zip(s_days, s_vals):
            if d >= last + step:
                pick.append(v); last = d
        pick = np.array(pick)
        if len(pick) >= 5:
            tt, pp = stats.ttest_1samp(pick, 0.0)
            TEST_COUNT += 1
            ci = stats.t.interval(0.95, len(pick) - 1,
                                  loc=pick.mean(),
                                  scale=stats.sem(pick))
            out[f"sub{step}"] = {
                "n": int(len(pick)),
                "mean_pp": round(float(pick.mean() * 100), 3),
                "t": round(float(tt), 2), "p": round(float(pp), 4),
                "ci95_pp": [round(ci[0] * 100, 3), round(ci[1] * 100, 3)]}
    # Newey-West on full series
    se = nw_se(s_vals, horizon)
    t, p = tstat_p(s_vals.mean(), se, n - 1)
    TEST_COUNT += 1
    half = stats.t.ppf(0.975, n - 1) * se
    out["nw"] = {"lag": horizon, "n": n,
                 "mean_pp": round(float(s_vals.mean() * 100), 3),
                 "t": round(float(t), 2), "p": round(float(p), 4),
                 "ci95_pp": [round((s_vals.mean() - half) * 100, 3),
                             round((s_vals.mean() + half) * 100, 3)]}
    return out

# ────────────────────────────────────────────────────────────────────
# 4) DESIGN A: daily cohort spread
# ────────────────────────────────────────────────────────────────────
def design_A(pass_mat, ten, new_thr, reg_thr, h, day_filter=None,
             rs_lo=None, rs_hi=None, trunc_mode="excl"):
    """Return (days, spread, mean_new, mean_reg, n_new, n_reg)."""
    f = fwd[h]; tr = trunc[h]
    days, spread, mn_new, mn_reg, nn, nr = [], [], [], [], [], []
    for t in range(T_START, T - h):
        if day_filter is not None and not day_filter[t]:
            continue
        sel = pass_mat[t]
        if rs_lo is not None:
            sel = sel & (rs[t] >= rs_lo)
        if rs_hi is not None:
            sel = sel & (rs[t] <= rs_hi)
        jj = np.where(sel)[0]
        if len(jj) == 0:
            continue
        te = ten[t, jj]
        r = f[t, jj].copy()
        trm = tr[t, jj]
        if trunc_mode == "excl":
            r[trm] = np.nan
        else:  # worst
            r[trm] = -0.10
        ok = np.isfinite(r)
        newm = ok & (te <= new_thr)
        regm = ok & (te >= reg_thr)
        if newm.sum() == 0 or regm.sum() == 0:
            continue
        a = float(r[newm].mean()); b = float(r[regm].mean())
        days.append(t); spread.append(a - b)
        mn_new.append(a); mn_reg.append(b)
        nn.append(int(newm.sum())); nr.append(int(regm.sum()))
    return (np.array(days), np.array(spread), np.array(mn_new),
            np.array(mn_reg), np.array(nn), np.array(nr))

A_res = {}
for h in HORIZONS:
    for tm in ("excl", "worst"):
        d, s, mn, mr, nn, nr = design_A(PASS, TEN[10], 2, 5, h,
                                        trunc_mode=tm)
        key = f"h{h}_{tm}"
        A_res[key] = summarize_series(d, s, h, f"A spread h={h} trunc={tm}")
        A_res[key]["cohort_means_pp"] = {
            "newcomer": round(float(mn.mean() * 100), 3),
            "regular": round(float(mr.mean() * 100), 3)}
        A_res[key]["avg_daily_n"] = {"newcomer": round(float(nn.mean()), 1),
                                     "regular": round(float(nr.mean()), 1)}

# by year
A_year = {}
for h in (10, 20):
    A_year[h] = {}
    for y in range(2021, 2027):
        yf = year_int == y
        d, s, mn, mr, nn, nr = design_A(PASS, TEN[10], 2, 5, h,
                                        day_filter=yf)
        if len(s) == 0:
            continue
        A_year[h][y] = summarize_series(d, s, h, f"A y{y} h{h}")
        A_year[h][y]["cohort_means_pp"] = {
            "newcomer": round(float(mn.mean() * 100), 3),
            "regular": round(float(mr.mean() * 100), 3)}

# by regime
A_regime = {}
for h in (10, 20):
    A_regime[h] = {}
    for rg, name in ((regime_up, "up"), (~regime_up, "down")):
        d, s, mn, mr, nn, nr = design_A(PASS, TEN[10], 2, 5, h,
                                        day_filter=rg)
        A_regime[h][name] = summarize_series(d, s, h, f"A {name} h{h}")
        A_regime[h][name]["cohort_means_pp"] = {
            "newcomer": round(float(mn.mean() * 100), 3),
            "regular": round(float(mr.mean() * 100), 3)}

# by RS band
A_rs = {}
for h in (10, 20):
    A_rs[h] = {}
    for lo, hi_, name in ((80, 89, "rs80_89"), (90, 99, "rs90p")):
        d, s, mn, mr, nn, nr = design_A(PASS, TEN[10], 2, 5, h,
                                        rs_lo=lo, rs_hi=hi_)
        A_rs[h][name] = summarize_series(d, s, h, f"A {name} h{h}")
        A_rs[h][name]["cohort_means_pp"] = {
            "newcomer": round(float(mn.mean() * 100), 3),
            "regular": round(float(mr.mean() * 100), 3)}

# falsification 1: RS 80-82 vs 83+ (all tenures) — expected ~0
def design_A_rsfloor(h):
    f = fwd[h]; tr = trunc[h]
    days, spread = [], []
    for t in range(T_START, T - h):
        jj = np.where(PASS[t])[0]
        if len(jj) == 0:
            continue
        r = f[t, jj].copy(); r[tr[t, jj]] = np.nan
        ok = np.isfinite(r)
        rsv = rs[t, jj]
        low = ok & (rsv >= 80) & (rsv <= 82)
        hig = ok & (rsv >= 83)
        if low.sum() == 0 or hig.sum() == 0:
            continue
        days.append(t)
        spread.append(float(r[low].mean()) - float(r[hig].mean()))
    return np.array(days), np.array(spread)

A_falsif = {}
for h in (10, 20):
    d, s = design_A_rsfloor(h)
    A_falsif[f"rsfloor_h{h}"] = summarize_series(d, s, h, f"RSfloor h{h}")

# sensitivity: pure all_pass (no eligibility filter)
A_pure = {}
for h in (10, 20):
    d, s, mn, mr, nn, nr = design_A(PASS_PURE, TEN_PURE10, 2, 5, h)
    A_pure[h] = summarize_series(d, s, h, f"A pure h{h}")

# sensitivity grid: W x newcomer threshold (h=10, excl)
A_grid = {}
REG_THR = {10: 5, 15: 8, 20: 10}
for W in (10, 15, 20):
    for nt in (1, 2, 3):
        d, s, mn, mr, nn, nr = design_A(PASS, TEN[W], nt, REG_THR[W], 10)
        A_grid[f"W{W}_new<={nt}"] = {
            "n_days": int(len(s)),
            "mean_spread_pp": round(float(s.mean() * 100), 3) if len(s) else None,
            "nw_t": None}
        if len(s) >= 8:
            se = nw_se(s, 10)
            t, p = tstat_p(s.mean(), se, len(s) - 1)
            TEST_COUNT += 1
            A_grid[f"W{W}_new<={nt}"]["nw_t"] = round(float(t), 2)
            A_grid[f"W{W}_new<={nt}"]["nw_p"] = round(float(p), 4)

print("Design A done")

# ────────────────────────────────────────────────────────────────────
# 5) DESIGN B: episode level
# ────────────────────────────────────────────────────────────────────
def build_episodes(pass_mat):
    """(t0, j) first day of each maximal consecutive pass run, t0>=T_START."""
    eps = []
    pm = pass_mat
    prev = np.zeros(N, dtype=bool)
    starts = pm & np.concatenate([np.zeros((1, N), bool), pm[:-1]]) == False
    # starts: pass today & not pass yesterday
    st = pm & ~np.concatenate([np.zeros((1, N), bool), pm[:-1]])
    ti, jj = np.where(st)
    for a, b in zip(ti, jj):
        if a >= T_START:
            eps.append((a, b))
    return eps

episodes = build_episodes(PASS)
print("episodes (from T_START):", len(episodes))

def trading_rule(t0, j, tp=0.20, sl=-0.10, max_hold=60, cost=0.0034):
    """Entry next-day open after first pass day t0; +20/-10 intraday;
    both-hit=loss; gap fills at open; 60d time exit at close.
    Returns (net_ret, outcome, truncated_flag) or None if no entry possible."""
    te = t0 + 1
    if te >= T:
        return None
    if not (np.isfinite(idx[te, j]) and np.isfinite(open_r[te, j])):
        return None  # no next-day price -> cannot enter
    entry = idx[te, j] * open_r[te, j]
    if not np.isfinite(entry) or entry <= 0:
        return None
    tgt = entry * (1 + tp)
    stp = entry * (1 + sl)
    last_d = min(te + max_hold - 1, T - 1)
    for d in range(te, last_d + 1):
        if not np.isfinite(idx[d, j]):
            # gap or delist: if never present again -> truncated exit at last close
            fut = idx[d:last_d + 1, j]
            if not np.isfinite(fut).any():
                # find last finite close before d
                prev_seg = idx[te:d, j]
                fin = np.where(np.isfinite(prev_seg))[0]
                if len(fin) == 0:
                    return None
                exit_px = prev_seg[fin[-1]]
                return (exit_px / entry - 1 - cost, "delist", True)
            continue
        o = idx[d, j] * open_r[d, j] if np.isfinite(open_r[d, j]) else np.nan
        hi_px = idx[d, j] * hi_r[d, j] if np.isfinite(hi_r[d, j]) else idx[d, j]
        lo_px = idx[d, j] * lo_r[d, j] if np.isfinite(lo_r[d, j]) else idx[d, j]
        if d > te and np.isfinite(o):
            if o <= stp:
                return (o / entry - 1 - cost, "stop_gap", False)
            if o >= tgt:
                return (o / entry - 1 - cost, "target_gap", False)
        hit_s = lo_px <= stp
        hit_t = hi_px >= tgt
        if hit_s and hit_t:
            return (sl - cost, "both_hit_loss", False)
        if hit_s:
            return (sl - cost, "stop", False)
        if hit_t:
            return (tp - cost, "target", False)
    # time exit
    ex = idx[last_d, j]
    if not np.isfinite(ex):
        seg = idx[te:last_d + 1, j]
        fin = np.where(np.isfinite(seg))[0]
        ex = seg[fin[-1]]
    return (ex / entry - 1 - cost, "time_exit", False)

# classify episodes and compute outcomes
rows = []
for (t0, j) in episodes:
    te10 = int(TEN[10][t0, j])
    rec = {"t0": int(t0), "j": int(j), "code": str(codes[j]),
           "year": int(year_int[t0]), "tenure10": te10,
           "rs": int(rs[t0, j]), "regime_up": bool(regime_up[t0]),
           "ten15": int(TEN[15][t0, j]), "ten20": int(TEN[20][t0, j])}
    for h in (10, 20):
        v = fwd[h][t0, j]
        tr_f = bool(trunc[h][t0, j])
        rec[f"fwd{h}"] = float(v) if np.isfinite(v) else None
        rec[f"trunc{h}"] = tr_f
        rec[f"edge{h}"] = (t0 + h) >= T  # right-edge censored
    tr_res = trading_rule(t0, j)
    if tr_res is not None:
        rec["rule_ret"] = float(tr_res[0])
        rec["rule_outcome"] = tr_res[1]
        rec["rule_trunc"] = bool(tr_res[2])
        # right-edge: time-exit with shortened window (unresolved position)
        rec["rule_edge"] = (t0 + 60 > T - 1) and tr_res[1] == "time_exit"
    else:
        rec["rule_ret"] = None
        rec["rule_edge"] = False
    rows.append(rec)

# continuing regulars base: pass & tenure10==10, non-overlapping 10d per code
cont_rows = []
last_pick = {}
for t in range(T_START, T):
    jj = np.where(PASS[t] & (TEN[10][t] == 10))[0]
    for j in jj:
        if t >= last_pick.get(j, -10**9) + 10:
            last_pick[j] = t
            rec = {"t0": int(t), "j": int(j), "code": str(codes[j]),
                   "year": int(year_int[t]), "rs": int(rs[t, j]),
                   "regime_up": bool(regime_up[t])}
            for h in (10, 20):
                v = fwd[h][t, j]
                rec[f"fwd{h}"] = float(v) if np.isfinite(v) else None
                rec[f"trunc{h}"] = bool(trunc[h][t, j])
                rec[f"edge{h}"] = (t + h) >= T
            tr_res = trading_rule(t, j)
            rec["rule_ret"] = float(tr_res[0]) if tr_res else None
            rec["rule_outcome"] = tr_res[1] if tr_res else None
            rec["rule_trunc"] = bool(tr_res[2]) if tr_res else None
            rec["rule_edge"] = (tr_res is not None and t + 60 > T - 1
                                and tr_res[1] == "time_exit")
            cont_rows.append(rec)
print("episode rows:", len(rows), " continuing-regular samples:", len(cont_rows))

def cell(vals_a, vals_b, label):
    """two-sample welch t-test cell with CI of diff (a - b)."""
    global TEST_COUNT
    a = np.array([v for v in vals_a if v is not None and np.isfinite(v)])
    b = np.array([v for v in vals_b if v is not None and np.isfinite(v)])
    out = {"label": label, "n_a": int(len(a)), "n_b": int(len(b))}
    if len(a) < 5 or len(b) < 5:
        out["note"] = "too few obs"
        return out
    out["mean_a_pp"] = round(float(a.mean() * 100), 2)
    out["mean_b_pp"] = round(float(b.mean() * 100), 2)
    out["diff_pp"] = round(float((a.mean() - b.mean()) * 100), 2)
    tt, pp = stats.ttest_ind(a, b, equal_var=False)
    TEST_COUNT += 1
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    dfree = (a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b)) ** 2 / (
        (a.var(ddof=1) / len(a)) ** 2 / (len(a) - 1)
        + (b.var(ddof=1) / len(b)) ** 2 / (len(b) - 1))
    half = stats.t.ppf(0.975, dfree) * se
    d = a.mean() - b.mean()
    out["t"] = round(float(tt), 2); out["p"] = round(float(pp), 4)
    out["ci95_diff_pp"] = [round((d - half) * 100, 2), round((d + half) * 100, 2)]
    # win rate for rule returns (>0)
    return out

def get_vals(rws, key, sel=None, trunc_mode="excl", trunc_key=None,
             edge_key=None):
    out = []
    for r in rws:
        if sel is not None and not sel(r):
            continue
        v = r.get(key)
        if edge_key and r.get(edge_key):
            continue  # right-edge censored: drop from both variants
        if trunc_key and r.get(trunc_key):
            if trunc_mode == "excl":
                continue
            v = -0.10
        if v is None:
            continue
        out.append(v)
    return out

new_sel = lambda r: r["tenure10"] <= 2
reg_sel = lambda r: r["tenure10"] >= 5

B_res = {}
for h in (10, 20):
    for tm in ("excl", "worst"):
        a = get_vals(rows, f"fwd{h}", new_sel, tm, f"trunc{h}", f"edge{h}")
        b = get_vals(rows, f"fwd{h}", reg_sel, tm, f"trunc{h}", f"edge{h}")
        B_res[f"fwd{h}_{tm}"] = cell(a, b, f"B fwd{h} newcomer-vs-returning {tm}")

# vs continuing regulars
for h in (10, 20):
    a = get_vals(rows, f"fwd{h}", new_sel, "excl", f"trunc{h}", f"edge{h}")
    b = get_vals(cont_rows, f"fwd{h}", None, "excl", f"trunc{h}", f"edge{h}")
    B_res[f"fwd{h}_vs_continuing"] = cell(a, b, f"B fwd{h} newcomer-vs-continuing")

# trading rule
def rule_cell(rws_a, rws_b, label, sel_a=None, sel_b=None):
    global TEST_COUNT
    a = [r["rule_ret"] for r in rws_a
         if (sel_a is None or sel_a(r)) and r.get("rule_ret") is not None
         and not r.get("rule_edge")]
    b = [r["rule_ret"] for r in rws_b
         if (sel_b is None or sel_b(r)) and r.get("rule_ret") is not None
         and not r.get("rule_edge")]
    out = cell(a, b, label)
    if len(a) >= 5 and len(b) >= 5:
        aa = np.array(a); bb = np.array(b)
        out["win_a"] = round(float((aa > 0).mean()), 3)
        out["win_b"] = round(float((bb > 0).mean()), 3)
    return out

B_res["rule"] = rule_cell(rows, rows, "B rule newcomer-vs-returning",
                          new_sel, reg_sel)
B_res["rule_vs_continuing"] = rule_cell(rows, cont_rows,
                                        "B rule newcomer-vs-continuing",
                                        new_sel, None)

# outcome distribution for rule
def outcome_dist(rws, sel):
    from collections import Counter
    c = Counter(r["rule_outcome"] for r in rws
                if (sel is None or sel(r)) and r.get("rule_ret") is not None)
    tot = sum(c.values())
    return {k: round(v / tot, 3) for k, v in sorted(c.items())} if tot else {}

B_res["rule_outcomes"] = {
    "newcomer": outcome_dist(rows, new_sel),
    "returning": outcome_dist(rows, reg_sel),
    "continuing": outcome_dist(cont_rows, None)}

# per-year cells
B_year = {}
for y in range(2021, 2027):
    ysel_n = lambda r, y=y: r["year"] == y and r["tenure10"] <= 2
    ysel_r = lambda r, y=y: r["year"] == y and r["tenure10"] >= 5
    a = get_vals(rows, "fwd10", ysel_n, "excl", "trunc10", "edge10")
    b = get_vals(rows, "fwd10", ysel_r, "excl", "trunc10", "edge10")
    B_year[y] = {"fwd10": cell(a, b, f"B y{y} fwd10")}
    B_year[y]["rule"] = rule_cell(rows, rows, f"B y{y} rule", ysel_n, ysel_r)

# regime cells
B_regime = {}
for rg_val, name in ((True, "up"), (False, "down")):
    s_n = lambda r, v=rg_val: r["regime_up"] == v and r["tenure10"] <= 2
    s_r = lambda r, v=rg_val: r["regime_up"] == v and r["tenure10"] >= 5
    a = get_vals(rows, "fwd10", s_n, "excl", "trunc10", "edge10")
    b = get_vals(rows, "fwd10", s_r, "excl", "trunc10", "edge10")
    B_regime[name] = {"fwd10": cell(a, b, f"B regime-{name} fwd10")}
    B_regime[name]["rule"] = rule_cell(rows, rows, f"B regime-{name} rule",
                                       s_n, s_r)

# RS band cells + falsification within RS>=90
B_rs = {}
for lo, hi_, name in ((80, 89, "rs80_89"), (90, 200, "rs90p")):
    s_n = lambda r, lo=lo, hi_=hi_: lo <= r["rs"] <= hi_ and r["tenure10"] <= 2
    s_r = lambda r, lo=lo, hi_=hi_: lo <= r["rs"] <= hi_ and r["tenure10"] >= 5
    a = get_vals(rows, "fwd10", s_n, "excl", "trunc10", "edge10")
    b = get_vals(rows, "fwd10", s_r, "excl", "trunc10", "edge10")
    B_rs[name] = {"fwd10": cell(a, b, f"B {name} fwd10")}
    B_rs[name]["rule"] = rule_cell(rows, rows, f"B {name} rule", s_n, s_r)

# stock-level dedup: first episode per code per year
seen = set()
dedup_rows = []
for r in sorted(rows, key=lambda r: r["t0"]):
    k = (r["code"], r["year"])
    if k in seen:
        continue
    seen.add(k)
    dedup_rows.append(r)
B_dedup = {}
a = get_vals(dedup_rows, "fwd10", new_sel, "excl", "trunc10", "edge10")
b = get_vals(dedup_rows, "fwd10", reg_sel, "excl", "trunc10", "edge10")
B_dedup["fwd10"] = cell(a, b, "B dedup fwd10")
a = get_vals(dedup_rows, "fwd20", new_sel, "excl", "trunc20", "edge20")
b = get_vals(dedup_rows, "fwd20", reg_sel, "excl", "trunc20", "edge20")
B_dedup["fwd20"] = cell(a, b, "B dedup fwd20")
B_dedup["rule"] = rule_cell(dedup_rows, dedup_rows, "B dedup rule",
                            new_sel, reg_sel)

# sensitivity grid on episodes: W x newcomer thr (fwd10 excl)
B_grid = {}
TKEY = {10: "tenure10", 15: "ten15", 20: "ten20"}
for W in (10, 15, 20):
    for nt in (1, 2, 3):
        s_n = lambda r, W=W, nt=nt: r[TKEY[W]] <= nt
        s_r = lambda r, W=W: r[TKEY[W]] >= REG_THR[W]
        a = get_vals(rows, "fwd10", s_n, "excl", "trunc10", "edge10")
        b = get_vals(rows, "fwd10", s_r, "excl", "trunc10", "edge10")
        c = cell(a, b, f"grid W{W} nt{nt}")
        B_grid[f"W{W}_new<={nt}"] = {
            "n_new": c.get("n_a"), "n_reg": c.get("n_b"),
            "diff_pp": c.get("diff_pp"), "p": c.get("p")}

print("Design B done; total tests so far:", TEST_COUNT)

# ────────────────────────────────────────────────────────────────────
# save
# ────────────────────────────────────────────────────────────────────
result = {
    "meta": {
        "built_from": "passmatrix.npz",
        "analysis_start": str(dates[T_START]),
        "pass_definition": "all_pass & eligible (production list); "
                           "sensitivity with pure all_pass included",
        "newcomer": "tenure10 <= 2 at pass-day",
        "regular": "tenure10 >= 5 (3-4 dropped as gray zone)",
        "episodes_total": len(rows),
        "continuing_regular_samples": len(cont_rows),
        "presence_gap_stockdays": gap_days,
        "regime_up_share": round(float(regime_up[T_START:].mean()), 3),
        "total_tests": None,  # filled below
    },
    "design_A": {"headline": A_res, "by_year": {str(h): {str(y): v for y, v in d.items()}
                                               for h, d in A_year.items()},
                 "by_regime": {str(h): d for h, d in A_regime.items()},
                 "by_rs": {str(h): d for h, d in A_rs.items()},
                 "falsification_rsfloor": A_falsif,
                 "pure_allpass_sensitivity": {str(h): v for h, v in A_pure.items()},
                 "grid": A_grid},
    "design_B": {"headline": B_res, "by_year": {str(y): v for y, v in B_year.items()},
                 "by_regime": B_regime, "by_rs": B_rs,
                 "dedup": B_dedup, "grid": B_grid},
}
result["meta"]["total_tests"] = TEST_COUNT

with open(SP + r"\flicker_test.json", "w", encoding="utf-8") as fh:
    json.dump(result, fh, ensure_ascii=False, indent=1)
print("saved. TOTAL TESTS:", TEST_COUNT)
