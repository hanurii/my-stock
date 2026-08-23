# -*- coding: utf-8 -*-
"""Robustness add-ons:
1) Design A sub10 t-test across ALL 10 offsets (fragility check).
2) Day-clustered episode test: per-start-day spread series + NW.
3) Daily spread series descriptive stats.
"""
import json
import numpy as np
from scipy import stats

SP = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad"
z = np.load(SP + r"\passmatrix.npz")
dates = z["dates"]; codes = z["codes"]
all_pass = z["all_pass"]; eligible = z["eligible"]
rs = z["rs"]; idx = z["idx"]
T, N = all_pass.shape
PASS = all_pass & eligible
T_START = 253

# tenure10 on PASS
ap = PASS.astype(np.int32)
cum = np.concatenate([np.zeros((1, N), np.int32), np.cumsum(ap, axis=0)])
TEN = np.zeros((T, N), dtype=np.int16)
for t in range(T):
    TEN[t] = cum[t] - cum[max(t - 10, 0)]

last_present = np.full(N, -1)
pres = np.isfinite(idx)
for j in range(N):
    p = np.where(pres[:, j])[0]
    if len(p):
        last_present[j] = p[-1]

def fwd_mat(h):
    f = np.full((T, N), np.nan)
    f[:T - h] = idx[h:] / idx[:-h] - 1.0
    return f

def nw_se(x, lag):
    x = np.asarray(x, float); n = len(x)
    e = x - x.mean(); g0 = np.dot(e, e) / n; s = g0
    for l in range(1, lag + 1):
        s += 2.0 * (1 - l / (lag + 1.0)) * np.dot(e[l:], e[:-l]) / n
    return np.sqrt(max(s, 1e-18) / n)

out = {}
for h in (10, 20):
    f = fwd_mat(h)
    days, spread = [], []
    for t in range(T_START, T - h):
        jj = np.where(PASS[t])[0]
        if len(jj) == 0:
            continue
        r = f[t, jj]
        te = TEN[t, jj]
        ok = np.isfinite(r)
        newm = ok & (te <= 2); regm = ok & (te >= 5)
        if newm.sum() == 0 or regm.sum() == 0:
            continue
        days.append(t)
        spread.append(float(r[newm].mean()) - float(r[regm].mean()))
    days = np.array(days); spread = np.array(spread)
    res = {"n_days": int(len(spread)),
           "full_mean_pp": round(float(spread.mean() * 100), 3),
           "daily_std_pp": round(float(spread.std() * 100), 2),
           "offsets": []}
    for off in range(10):
        pick, last = [], -10**9
        for d, v in zip(days, spread):
            if d >= last + 10 and (d - days[0]) % 10 >= 0:
                pass
        # simple stride from offset
        sel = [i for i in range(off, len(spread), 10)]
        pk = spread[sel]
        tt, pp = stats.ttest_1samp(pk, 0.0)
        res["offsets"].append({"offset": off, "n": len(pk),
                               "mean_pp": round(float(pk.mean() * 100), 3),
                               "t": round(float(tt), 2),
                               "p": round(float(pp), 4)})
    means = [o["mean_pp"] for o in res["offsets"]]
    res["offset_mean_range_pp"] = [min(means), max(means)]
    res["offsets_positive"] = sum(1 for m in means if m > 0)
    out[f"A_offsets_h{h}"] = res

# 2) day-clustered episode design: episodes starting same day -> one obs
st = PASS & ~np.concatenate([np.zeros((1, N), bool), PASS[:-1]])
for h in (10, 20):
    f = fwd_mat(h)
    days, spread, nn, nr = [], [], [], []
    for t in range(T_START, T - h):
        jj = np.where(st[t])[0]
        if len(jj) == 0:
            continue
        te = TEN[t, jj]
        r = f[t, jj]
        ok = np.isfinite(r)
        newm = ok & (te <= 2); regm = ok & (te >= 5)
        if newm.sum() == 0 or regm.sum() == 0:
            continue
        days.append(t)
        spread.append(float(r[newm].mean()) - float(r[regm].mean()))
        nn.append(int(newm.sum())); nr.append(int(regm.sum()))
    spread = np.array(spread)
    se = nw_se(spread, h)
    tstat = spread.mean() / se
    p = 2 * stats.t.sf(abs(tstat), len(spread) - 1)
    half = stats.t.ppf(0.975, len(spread) - 1) * se
    out[f"B_dayclustered_h{h}"] = {
        "n_days": int(len(spread)),
        "mean_pp": round(float(spread.mean() * 100), 3),
        "nw_t": round(float(tstat), 2), "nw_p": round(float(p), 4),
        "ci95_pp": [round((spread.mean() - half) * 100, 3),
                    round((spread.mean() + half) * 100, 3)],
        "avg_n_new": round(float(np.mean(nn)), 1),
        "avg_n_reg": round(float(np.mean(nr)), 1)}

# 3) episode class counts
te_start = TEN[st]
ti, jj = np.where(st)
sel = ti >= T_START
tvals = TEN[ti[sel], jj[sel]]
out["episode_tenure_dist"] = {
    "n_total": int(sel.sum()),
    "newcomer<=2": int((tvals <= 2).sum()),
    "gray3_4": int(((tvals >= 3) & (tvals <= 4)).sum()),
    "returning>=5": int((tvals >= 5).sum())}

with open(SP + r"\flicker_check2.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
