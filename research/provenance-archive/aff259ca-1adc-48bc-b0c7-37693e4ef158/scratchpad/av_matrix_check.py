# -*- coding: utf-8 -*-
"""Adversarial verify — MATRIX layer.

Independent re-derivation from raw pdata (av_raw.npz):
  * full cross-section of the 8 criteria + RS + eligibility on 3 random dates,
    compared cell-by-cell against passmatrix.npz
  * detailed hand-derivation printout for 2 random stocks on those dates
  * fltRt-chain sanity vs raw closes (corporate-action day behavior)
  * tenure10 internal consistency re-assertion
"""
import numpy as np
import pandas as pd

SP = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad"

z = np.load(SP + r"\passmatrix.npz", allow_pickle=False)
dates = np.array([str(d) for d in z["dates"]])
codes = np.array([str(c) for c in z["codes"]])
Z_ap = z["all_pass"]; Z_rs = z["rs"]; Z_bits = z["crit_bits"]
Z_el = z["eligible"]; Z_pres = z["present"]; Z_nh = z["nhist"]
Z_idx = z["idx"]; Z_t10 = z["tenure10"]; Z_pc = z["passed_count"]

r = np.load(SP + r"\av_raw.npz")
close = r["close"]; flt = r["flt"]; vol = r["vol"]; mkt = r["mkt"]
T, N = close.shape

present = mkt > 0
# ── contiguity of presence (no mid-listing gaps) ────────────────────
first = np.where(present.any(0), present.argmax(0), -1)
last = np.where(present.any(0), T - 1 - present[::-1].argmax(0), -1)
n_days_present = present.sum(0)
contig = (last - first + 1) == n_days_present
print("presence contiguous for all codes:", bool(contig.all()),
      "| non-contig codes:", int((~contig).sum()))
assert contig.all()

print("present mismatch vs npz:", int((present != Z_pres).sum()))

# missing fltRt on present days?
miss_flt = present & ~np.isfinite(flt)
print("present days with missing fltRt:", int(miss_flt.sum()))

# ── my adjusted index (scale-free) ──────────────────────────────────
R = np.where(present & np.isfinite(flt), 1.0 + flt / 100.0, 1.0)
R[R <= 0] = 1.0
IDX = np.cumprod(R, axis=0)
IDXm = np.where(present, IDX, np.nan)

# chain sanity vs npz idx: daily returns must match wherever both defined
with np.errstate(invalid="ignore"):
    my_ret = IDXm[1:] / IDXm[:-1]
    z_ret = np.where(Z_pres[1:] & Z_pres[:-1], Z_idx[1:] / Z_idx[:-1], np.nan)
both = np.isfinite(my_ret) & np.isfinite(z_ret)
dd = np.abs(my_ret[both] - z_ret[both])
print(f"daily-return agreement mine-vs-npz: n={both.sum()}, max abs diff={dd.max():.3e}")

# corporate-action day: raw close ratio != 1+fltRt/100 → idx must follow fltRt
with np.errstate(invalid="ignore"):
    raw_ratio = close[1:] / close[:-1]
ca = both & np.isfinite(raw_ratio) & (np.abs(raw_ratio - my_ret) > 0.05)
ti, jj = np.where(ca)
if len(ti):
    k = 0
    t_, j_ = ti[k] + 1, jj[k]
    print(f"corporate-action example: {codes[j_]} {dates[t_]} raw clpr "
          f"{close[t_-1,j_]:.0f}->{close[t_,j_]:.0f} (ratio {raw_ratio[ti[k],j_]:.3f}) "
          f"fltRt {flt[t_,j_]:+.2f}% -> npz idx ratio {z_ret[ti[k],j_]:.4f} (follows fltRt: "
          f"{abs(z_ret[ti[k],j_]-(1+flt[t_,j_]/100))<1e-9})")
print("corporate-action-like days (>5% divergence raw vs fltRt):", len(ti))

# ── helpers for a full-day evaluation ───────────────────────────────
NH = np.cumsum(present, axis=0)          # nhist at each day (0 if not yet listed)
NH = np.where(present, NH, 0)
print("nhist mismatch vs npz:", int((NH != Z_nh).sum()))

CS = np.cumsum(np.where(present, IDX, 0.0), axis=0)   # cumsum of idx over time
CS0 = np.concatenate([np.zeros((1, N)), CS])

df = pd.DataFrame(IDXm)
H52 = df.rolling(252, min_periods=1).max().to_numpy()
L52 = df.rolling(252, min_periods=1).min().to_numpy()

VZ = np.cumsum(np.where(present, (np.where(np.isfinite(vol), vol, 0.0) == 0), 0), axis=0)
VZ0 = np.concatenate([np.zeros((1, N), int), VZ])

TURN = np.cumsum(np.where(present, np.where(np.isfinite(close), close, 0.0)
                          * np.where(np.isfinite(vol), vol, 0.0), 0.0), axis=0)
TURN0 = np.concatenate([np.zeros((1, N)), TURN])

def sma(t, w):
    out = np.full(N, np.nan)
    ok = NH[t] >= w
    out[ok] = (CS0[t + 1, ok] - CS0[t + 1 - w, ok]) / w
    return out

def eval_day(t):
    """Independent full evaluation of day t. Returns dict of vectors."""
    nh = NH[t]
    lastp = np.where(present[t], IDX[t], np.nan)
    s50, s150, s200 = sma(t, 50), sma(t, 150), sma(t, 200)
    s200_1m = np.full(N, np.nan)
    ok22 = nh >= 222
    s200_1m[ok22] = (CS0[t + 1 - 22, ok22] - CS0[t + 1 - 22 - 200, ok22]) / 200
    h52, l52 = H52[t], L52[t]
    with np.errstate(invalid="ignore"):
        c1 = (lastp > s150) & (lastp > s200)
        c2 = s150 > s200
        c3 = s200 > s200_1m
        c4 = (s50 > s150) & (s50 > s200)
        c5 = lastp > s50
        c6 = (lastp - l52) / l52 * 100.0 >= 30.0
        c7 = (h52 - lastp) / h52 * 100.0 <= 25.0
    crit = np.vstack([c1, c2, c3, c4, c5, c6, c7])
    crit[:, nh < 200] = False
    crit = np.nan_to_num(crit).astype(bool)

    # halted: last 5 present-day volumes all zero
    halted = np.zeros(N, dtype=bool)
    ok5 = nh >= 5
    halted[ok5] = (VZ0[t + 1, ok5] - VZ0[t + 1 - 5, ok5]) == 5

    # RS
    win = np.minimum(nh - 1, 252)
    ret = np.full(N, np.nan)
    okw = present[t] & (nh >= 1)
    for j in np.where(okw)[0]:
        w = win[j]
        if w >= 1:
            ret[j] = IDX[t, j] / IDX[t - w, j] - 1.0
    pool_ok = present[t] & ((mkt[t] == 1) | (mkt[t] == 2)) & ~halted & (nh >= 200) & np.isfinite(ret)
    rs = np.full(N, -1, dtype=int)
    for w in np.unique(win[pool_ok]):
        sel = pool_ok & (win == w)
        pool = np.sort(ret[sel])
        if len(pool) < 100:
            continue
        rank = np.searchsorted(pool, ret[sel], side="left")
        rs[sel] = np.clip(np.rint(rank / len(pool) * 100.0), 1, 99).astype(int)

    ap = crit.all(0) & (rs >= 80) & (nh >= 200)

    # eligibility
    pref = np.array([c[-1] != "0" for c in codes])
    foreign = np.array([c.startswith("9") for c in codes])
    wlen = np.minimum(nh, 50)
    t50 = np.full(N, np.nan)
    okt = nh >= 20
    t50[okt] = (TURN0[t + 1, okt] - TURN0[t + 1 - wlen[okt], okt]) / wlen[okt] / 1e8
    lowliq = np.isfinite(t50) & (t50 < 5.0)
    elig = present[t] & ((mkt[t] == 1) | (mkt[t] == 2)) & ~halted & ~pref & ~foreign & ~lowliq
    return dict(crit=crit, rs=rs, ap=ap, elig=elig, halted=halted, nh=nh,
                s50=s50, s150=s150, s200=s200, s200_1m=s200_1m,
                h52=h52, l52=l52, lastp=lastp, ret=ret, win=win, t50=t50)

rng = np.random.default_rng(42)
pick_t = sorted(rng.choice(np.arange(300, T - 1), 3, replace=False))
print("\nrandom dates:", [dates[t] for t in pick_t])

for t in pick_t:
    e = eval_day(t)
    # compare vs npz
    zbits = Z_bits[t]
    mybits = np.zeros(N, dtype=np.uint8)
    for k in range(7):
        mybits |= (e["crit"][k].astype(np.uint8) << k)
    bit_mm = int((mybits != zbits).sum())
    rs_mm = int((e["rs"] != Z_rs[t]).sum())
    rs_close = int((np.abs(e["rs"] - Z_rs[t]) > 1).sum())
    ap_mm = int((e["ap"] != Z_ap[t]).sum())
    el_mm = int((e["elig"] != Z_el[t]).sum())
    print(f"\n=== {dates[t]} ===")
    print(f" crit-bits mismatches: {bit_mm}/{N} | rs mismatches: {rs_mm} "
          f"(|diff|>1: {rs_close}) | all_pass mismatches: {ap_mm} | eligible mismatches: {el_mm}")
    print(f" my all_pass count {int(e['ap'].sum())} vs npz {int(Z_ap[t].sum())}; "
          f" my pass&elig {int((e['ap'] & e['elig']).sum())} vs npz {int((Z_ap[t] & Z_el[t]).sum())}")
    if ap_mm:
        for j in np.where(e["ap"] != Z_ap[t])[0][:5]:
            print("  AP diff:", codes[j], "mine", e["ap"][j], "npz", Z_ap[t][j],
                  "rs mine/npz", e["rs"][j], Z_rs[t][j])
    if rs_mm:
        jj = np.where(e["rs"] != Z_rs[t])[0]
        print("  rs diffs sample:", [(codes[j], int(e["rs"][j]), int(Z_rs[t][j])) for j in jj[:5]])

# ── detailed hand check: 2 random stocks on the 3 dates ─────────────
t_mid = pick_t[1]
cands = np.where((NH[t_mid] >= 200) & present[t_mid])[0]
j1 = int(rng.choice(cands))
ap_cands = np.where(Z_ap[t_mid])[0]
j2 = int(rng.choice(ap_cands))
print(f"\nrandom stocks: {codes[j1]} (generic), {codes[j2]} (all_pass on {dates[t_mid]})")

for j in (j1, j2):
    print(f"\n--- {codes[j]} ---")
    for t in pick_t:
        if not present[t, j]:
            print(f" {dates[t]}: not listed")
            continue
        e = None
        nh = NH[t, j]
        idxs = IDX[max(0, t - 260):t + 1, j]
        s50 = IDX[t - 49:t + 1, j].mean() if nh >= 50 else np.nan
        s150 = IDX[t - 149:t + 1, j].mean() if nh >= 150 else np.nan
        s200 = IDX[t - 199:t + 1, j].mean() if nh >= 200 else np.nan
        w52lo = max(t - 251, first[j])
        h52 = IDX[w52lo:t + 1, j].max(); l52 = IDX[w52lo:t + 1, j].min()
        lastp = IDX[t, j]
        zb = int(Z_bits[t, j])
        my = [lastp > s150 and lastp > s200, s150 > s200, np.nan, s50 > s150 and s50 > s200,
              lastp > s50, (lastp - l52) / l52 * 100 >= 30, (h52 - lastp) / h52 * 100 <= 25]
        if nh >= 222:
            s200_1m = IDX[t - 221:t - 21, j].mean()
            my[2] = s200 > s200_1m
        else:
            my[2] = False
        if nh < 200:
            my = [False] * 7
        npz_bits = [(zb >> k) & 1 == 1 for k in range(7)]
        agree = all(bool(a) == b for a, b in zip(my, npz_bits))
        print(f" {dates[t]}: nh={nh} close_idx={lastp:.4f} sma50={s50:.4f} sma150={s150:.4f} "
              f"sma200={s200:.4f} 52wH={h52:.4f} 52wL={l52:.4f}")
        print(f"   my c1-7={[bool(x) for x in my]} npz={npz_bits} agree={agree} | "
              f"my_rs_from_fullday(below) npz_rs={int(Z_rs[t,j])} npz_all_pass={bool(Z_ap[t,j])} "
              f"npz_elig={bool(Z_el[t,j])} npz_tenure10={int(Z_t10[t,j])}")

# tenure10 internal consistency (full matrix)
ap_i = Z_ap.astype(np.int32)
cum = np.concatenate([np.zeros((1, N), np.int32), np.cumsum(ap_i, axis=0)])
t10 = np.zeros((T, N), dtype=np.int16)
for t in range(T):
    t10[t] = cum[t] - cum[max(t - 10, 0)]
print("\ntenure10 == recomputed-from-npz-all_pass everywhere:", bool((t10 == Z_t10).all()))
