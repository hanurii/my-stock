# -*- coding: utf-8 -*-
"""Daily Minervini trend-template pass matrix, 2020-2026, from .cache/pdata.

Replicates scripts/canslim_lib/trend_template.py evaluate_trend_template (8 criteria)
+ screen_trend_template.py RS percentile (same-win pool, min 100, bankers-round)
+ minervini_filter.py page-eligibility (preferred / foreign 9xxxxx / 50d turnover < 5eok)
+ liveness.py is_halted (last 5 trading-day volumes all zero).

Outputs (scratchpad):
  passmatrix.npz       dates, codes, all_pass, passed_count, rs, tenure10, eligible,
                       present, crit_bits, nhist, idx (adjusted index), open_r/hi_r/lo_r,
                       vol, turnover_eok, turn50_eok, market
  passmatrix_meta.json build stats + validation results + quirks
"""
import json
import sys
import time
from bisect import bisect_right
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"C:\Users\hanul\playground\my-stock")
PDATA = ROOT / ".cache" / "pdata"
SERIES = ROOT / ".cache" / "ohlcv" / "series"
SCRATCH = Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad")

sys.path.insert(0, str(ROOT / "scripts"))
from canslim_lib.trend_template import evaluate_trend_template  # noqa: E402

RS_MIN = 80
MIN_POOL = 100          # MIN_RS_COMPARISON_POOL
MIN_N_TT = 200          # MIN_CLOSES_FOR_TT
W52 = 252
TURN_WIN, TURN_MIN_DAYS, TURN_MIN_EOK = 50, 20, 5.0
HALT_DAYS = 5

MKT = {"KOSPI": 1, "KOSDAQ": 2, "KONEX": 3}


def load_pdata():
    files = sorted(PDATA.glob("price_*.json"))
    dates = [f.stem[6:14] for f in files]
    dates = [f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in dates]
    T = len(files)
    cap = 6000
    code_idx: dict[str, int] = {}
    codes: list[str] = []

    close = np.full((T, cap), np.nan, dtype=np.float64)
    flt = np.full((T, cap), np.nan, dtype=np.float64)
    op = np.full((T, cap), np.nan, dtype=np.float64)
    hi = np.full((T, cap), np.nan, dtype=np.float64)
    lo = np.full((T, cap), np.nan, dtype=np.float64)
    vol = np.full((T, cap), np.nan, dtype=np.float64)
    turn = np.full((T, cap), np.nan, dtype=np.float64)
    mkt = np.zeros((T, cap), dtype=np.uint8)

    q = {"missing_clpr": 0, "nonpos_clpr": 0, "missing_fltRt": 0,
         "flt_minus100": 0, "missing_trqu": 0, "missing_trPrc": 0,
         "other_mrktCtg": 0, "rows_total": 0}
    missing_flt_by_year: dict[str, int] = {}

    t0 = time.time()
    for t, f in enumerate(files):
        d = json.loads(f.read_text(encoding="utf-8"))
        yr = dates[t][:4]
        for code, row in d.items():
            j = code_idx.get(code)
            if j is None:
                j = code_idx[code] = len(codes)
                codes.append(code)
                if j >= cap:
                    raise RuntimeError("grow cap")
            q["rows_total"] += 1
            m = MKT.get(row.get("mrktCtg"))
            if m is None:
                q["other_mrktCtg"] += 1
                m = 3
            mkt[t, j] = m
            cp = row.get("clpr")
            if cp is None:
                q["missing_clpr"] += 1
            else:
                cp = float(cp)
                if cp <= 0:
                    q["nonpos_clpr"] += 1
                    cp = None
            if cp is not None:
                close[t, j] = cp
            fr = row.get("fltRt")
            if fr is None or fr == "" or fr == "-":
                q["missing_fltRt"] += 1
                missing_flt_by_year[yr] = missing_flt_by_year.get(yr, 0) + 1
            else:
                fr = float(fr)
                if fr <= -100.0:
                    q["flt_minus100"] += 1
                flt[t, j] = fr
            for key, arr in (("mkp", op), ("hipr", hi), ("lopr", lo)):
                v = row.get(key)
                if v is not None:
                    arr[t, j] = float(v)
            v = row.get("trqu")
            if v is None:
                q["missing_trqu"] += 1
            else:
                vol[t, j] = float(v)
            v = row.get("trPrc")
            if v is None:
                q["missing_trPrc"] += 1
            else:
                turn[t, j] = float(v)
        if (t + 1) % 200 == 0:
            print(f"  load {t+1}/{T} ({time.time()-t0:.0f}s)", flush=True)

    N = len(codes)
    arrs = dict(close=close[:, :N], flt=flt[:, :N], op=op[:, :N], hi=hi[:, :N],
                lo=lo[:, :N], vol=vol[:, :N], turn=turn[:, :N], mkt=mkt[:, :N])
    q["missing_fltRt_by_year"] = missing_flt_by_year
    return dates, codes, arrs, q


def main():
    print("1) loading pdata ...", flush=True)
    dates, codes, A, quality = load_pdata()
    T, N = A["close"].shape
    print(f"   T={T} days, N={N} codes (raw union)", flush=True)

    # drop pure-KONEX-only codes (never KOSPI/KOSDAQ) — never in universe
    ever_main = ((A["mkt"] == 1) | (A["mkt"] == 2)).any(axis=0)
    dropped_konex_only = int((~ever_main & (A["mkt"] > 0).any(axis=0)).sum())
    keep = np.where(ever_main)[0]
    codes = [codes[j] for j in keep]
    for k in A:
        A[k] = A[k][:, keep]
    N = len(codes)
    print(f"   dropped pure-KONEX codes: {dropped_konex_only} -> N={N}", flush=True)

    present = A["mkt"] > 0
    # rows where mkt present but clpr missing: treat as present with NaN close
    n_present_no_close = int((present & ~np.isfinite(A["close"])).sum())

    # ── per-stock compact computations ──────────────────────────────
    print("2) per-stock adjusted index + criteria 1-7 ...", flush=True)
    idx_g = np.full((T, N), np.nan, dtype=np.float64)     # adjusted index
    crit_bits = np.zeros((T, N), dtype=np.uint8)          # bit0..bit6 = c1..c7
    pc7 = np.zeros((T, N), dtype=np.int8)
    nhist = np.zeros((T, N), dtype=np.int16)
    win_g = np.zeros((T, N), dtype=np.int16)
    ret_g = np.full((T, N), np.nan, dtype=np.float64)     # RS-window return
    halted_g = np.zeros((T, N), dtype=bool)
    turn50_g = np.full((T, N), np.nan, dtype=np.float64)  # 50d avg clpr*trqu (eok)

    flt_fallback_ratio = 0
    t0 = time.time()
    for j in range(N):
        pos = np.where(present[:, j])[0]
        m = len(pos)
        if m == 0:
            continue
        raw = A["close"][pos, j]
        f = A["flt"][pos, j]
        v = A["vol"][pos, j]
        v = np.where(np.isfinite(v), v, 0.0)

        # forward chaining: ratio[i] = 1+f[i]/100 (fltRt of day i vs prev trading day)
        ratio = np.where(np.isfinite(f), 1.0 + f / 100.0, np.nan)
        prev_raw = np.concatenate([[np.nan], raw[:-1]])
        fb = ~np.isfinite(ratio)
        if fb.any():
            with np.errstate(invalid="ignore", divide="ignore"):
                alt = raw / prev_raw
            use = fb & np.isfinite(alt) & (alt > 0)
            ratio[use] = alt[use]
            flt_fallback_ratio += int(use[1:].sum())
        ratio[~np.isfinite(ratio)] = 1.0
        ratio[ratio <= 0] = 1.0   # mirror ohlcv_matrix: zero ratio treated as 1
        ratio[0] = 1.0
        idx = np.cumprod(ratio)
        idx_g[pos, j] = idx

        nh = np.arange(1, m + 1)
        nhist[pos, j] = np.minimum(nh, 32000).astype(np.int16)

        # halted: last HALT_DAYS volumes all zero (needs >= HALT_DAYS entries)
        zero = (v == 0).astype(np.int32)
        cz = np.concatenate([[0], np.cumsum(zero)])
        hz = np.zeros(m, dtype=bool)
        if m >= HALT_DAYS:
            hz[HALT_DAYS - 1:] = (cz[HALT_DAYS:] - cz[:-HALT_DAYS]) == HALT_DAYS
        halted_g[pos, j] = hz

        # 50d avg turnover (raw close * volume, eok), min 20 days else NaN(=pass)
        rawt = np.where(np.isfinite(raw), raw, 0.0) * v
        ct = np.concatenate([[0.0], np.cumsum(rawt)])
        wlen = np.minimum(nh, TURN_WIN)
        avg = (ct[nh] - ct[nh - wlen]) / wlen / 1e8
        avg[nh < TURN_MIN_DAYS] = np.nan
        turn50_g[pos, j] = avg

        if m < MIN_N_TT:
            continue

        cs = np.concatenate([[0.0], np.cumsum(idx)])

        def sma(w):
            out = np.full(m, np.nan)
            out[w - 1:] = (cs[w:] - cs[:-w]) / w
            return out

        s50, s150, s200 = sma(50), sma(150), sma(200)
        s200_off22 = np.full(m, np.nan)
        s200_off22[22:] = s200[:-22]

        ser = pd.Series(idx)
        h52 = ser.rolling(W52, min_periods=1).max().to_numpy()
        l52 = ser.rolling(W52, min_periods=1).min().to_numpy()

        last = idx
        with np.errstate(invalid="ignore"):
            c1 = (last > s150) & (last > s200)
            c2 = s150 > s200
            c3 = s200 > s200_off22
            c4 = (s50 > s150) & (s50 > s200)
            c5 = last > s50
            c6 = (last - l52) / l52 * 100.0 >= 30.0
            c7 = (h52 - last) / h52 * 100.0 <= 25.0
        for arr in (c1, c2, c3, c4, c5, c6, c7):
            arr[~np.isfinite(s200)] = False
        c3[~np.isfinite(s200_off22)] = False

        ok = nh >= MIN_N_TT
        bits = (c1.astype(np.uint8) | (c2.astype(np.uint8) << 1) |
                (c3.astype(np.uint8) << 2) | (c4.astype(np.uint8) << 3) |
                (c5.astype(np.uint8) << 4) | (c6.astype(np.uint8) << 5) |
                (c7.astype(np.uint8) << 6))
        bits[~ok] = 0
        crit_bits[pos, j] = bits
        s = (c1.astype(np.int8) + c2 + c3 + c4 + c5 + c6 + c7).astype(np.int8)
        s[~ok] = 0
        pc7[pos, j] = s

        # RS-window return: win = min(n-1, 252)
        w = np.minimum(nh - 1, W52)
        win_g[pos, j] = w.astype(np.int16)
        r = np.full(m, np.nan)
        if m >= W52 + 1:
            r[W52:] = idx[W52:] / idx[:-W52] - 1.0
        upto = min(m, W52)
        r[:upto] = idx[:upto] / idx[0] - 1.0  # win = i for position i (i<252)
        ret_g[pos, j] = r

        if (j + 1) % 500 == 0:
            print(f"   stock {j+1}/{N} ({time.time()-t0:.0f}s)", flush=True)

    # ── RS per day ──────────────────────────────────────────────────
    print("3) RS percentile per day ...", flush=True)
    rs_g = np.full((T, N), -1, dtype=np.int16)
    main_mkt = (A["mkt"] == 1) | (A["mkt"] == 2)
    pool_sizes_252 = []
    for t in range(T):
        elig = (main_mkt[t] & ~halted_g[t] & (nhist[t] >= MIN_N_TT)
                & np.isfinite(ret_g[t]))
        jj = np.where(elig)[0]
        if len(jj) == 0:
            continue
        wins = win_g[t, jj]
        rets = ret_g[t, jj]
        for w in np.unique(wins):
            sel = wins == w
            pool = np.sort(rets[sel])
            size = len(pool)
            if w == W52:
                pool_sizes_252.append(size)
            if size < MIN_POOL:
                continue
            rank = np.searchsorted(pool, rets[sel], side="left")
            rs = np.clip(np.rint(rank / size * 100.0), 1, 99).astype(np.int16)
            rs_g[t, jj[sel]] = rs

    c8 = rs_g >= RS_MIN
    passed_count = (pc7 + c8.astype(np.int8)).astype(np.int8)
    passed_count[nhist < MIN_N_TT] = 0
    all_pass = (pc7 == 7) & c8 & (nhist >= MIN_N_TT)

    # ── page eligibility ────────────────────────────────────────────
    print("4) eligibility ...", flush=True)
    code_arr = np.array(codes)
    pref = np.array([c[-1] != "0" for c in codes])           # preferred share
    foreign = np.array([c.startswith("9") for c in codes])   # KOSDAQ foreign
    lowliq = np.isfinite(turn50_g) & (turn50_g < TURN_MIN_EOK)
    eligible = (present & main_mkt & ~halted_g
                & ~pref[None, :] & ~foreign[None, :] & ~lowliq)

    # ── tenure10 ────────────────────────────────────────────────────
    ap = all_pass.astype(np.int16)
    cum = np.concatenate([np.zeros((1, N), np.int32), np.cumsum(ap, axis=0)])
    tenure10 = np.zeros((T, N), dtype=np.int8)
    for t in range(T):
        lo_i = max(t - 10, 0)
        tenure10[t] = (cum[t] - cum[lo_i]).astype(np.int8)

    # ── ratios ──────────────────────────────────────────────────────
    with np.errstate(invalid="ignore", divide="ignore"):
        open_r = (A["op"] / A["close"]).astype(np.float32)
        hi_r = (A["hi"] / A["close"]).astype(np.float32)
        lo_r = (A["lo"] / A["close"]).astype(np.float32)
    turnover_eok = np.where(np.isfinite(A["turn"]), A["turn"],
                            np.where(np.isfinite(A["close"]) & np.isfinite(A["vol"]),
                                     A["close"] * A["vol"], np.nan)) / 1e8

    # ── stats ───────────────────────────────────────────────────────
    years = np.array([d[:4] for d in dates])
    per_year = {}
    for y in sorted(set(years)):
        tsel = years == y
        per_year[y] = {
            "trading_days": int(tsel.sum()),
            "all_pass_stockdays": int(all_pass[tsel].sum()),
            "all_pass_eligible_stockdays": int((all_pass & eligible)[tsel].sum()),
            "avg_daily_all_pass": round(float(all_pass[tsel].sum(1).mean()), 1),
            "avg_daily_all_pass_eligible": round(float((all_pass & eligible)[tsel].sum(1).mean()), 1),
        }

    # ═════ VALIDATION ═══════════════════════════════════════════════
    print("5) validation ...", flush=True)
    date_i = {d: i for i, d in enumerate(dates)}
    val = {}

    # (a) vs committed snapshot 2026-08-13
    import subprocess
    out = subprocess.run(["git", "show", "c883ee80:public/data/sepa-trend-candidates.json"],
                         capture_output=True, cwd=ROOT).stdout
    snap = json.loads(out.decode("utf-8"))
    snap_ap = {c["code"]: c for c in snap["candidates"] if c.get("all_pass")}
    snap_all = {c["code"]: c for c in snap["candidates"]}
    t13 = date_i["2026-08-13"]
    mine13 = {codes[j] for j in np.where(all_pass[t13] & eligible[t13])[0]}
    mine13_nofilter = {codes[j] for j in np.where(all_pass[t13])[0]}
    sset = set(snap_ap)
    overlap = mine13 & sset
    diffs = []
    for c in sorted(sset - mine13):
        j = codes.index(c) if c in codes else None
        d = {"code": c, "side": "snapshot_only"}
        if j is None:
            d["why"] = "code not in pdata matrix"
        else:
            bits = int(crit_bits[t13, j])
            fails = [str(k + 1) for k in range(7) if not (bits >> k) & 1]
            d.update(my_rs=int(rs_g[t13, j]), my_pc=int(passed_count[t13, j]),
                     my_crit_fails=fails, my_eligible=bool(eligible[t13, j]),
                     snap_rs=snap_ap[c].get("rs"),
                     lowliq=bool(lowliq[t13, j]), turn50=round(float(turn50_g[t13, j]), 2)
                     if np.isfinite(turn50_g[t13, j]) else None)
        diffs.append(d)
    for c in sorted(mine13 - sset):
        j = codes.index(c)
        d = {"code": c, "side": "mine_only",
             "my_rs": int(rs_g[t13, j]), "my_pc": int(passed_count[t13, j])}
        sc = snap_all.get(c)
        if sc:
            scrit = sc.get("criteria", {})
            sfails = [k for k, v in scrit.items() if not v.get("pass")]
            d.update(snap_rs=sc.get("rs"), snap_pc=sc.get("passed_count"),
                     snap_crit_fails=sfails)
        else:
            d["snap"] = "not in candidates[] (failed/filtered/absent)"
        diffs.append(d)
    # rs agreement on overlap
    rs_diffs = []
    for c in overlap:
        j = codes.index(c)
        rs_diffs.append(abs(int(rs_g[t13, j]) - int(snap_ap[c].get("rs") or 0)))
    val["snapshot_2026_08_13"] = {
        "snapshot_all_pass": len(sset),
        "mine_all_pass_eligible": len(mine13),
        "mine_all_pass_prefilter": len(mine13_nofilter),
        "overlap": len(overlap),
        "jaccard": round(len(overlap) / len(mine13 | sset), 3),
        "rs_absdiff_on_overlap_mean": round(float(np.mean(rs_diffs)), 2) if rs_diffs else None,
        "rs_absdiff_on_overlap_max": int(max(rs_diffs)) if rs_diffs else None,
        "diffs": diffs,
    }

    # (b) oracle evaluate_trend_template on cached series, 3 stocks x 2 dates
    oracle = []
    vdates = ["2026-04-02", "2026-08-13"]
    for code in ["005930", "219130", "007340"]:
        s = json.loads((SERIES / f"{code}.json").read_text(encoding="utf-8"))
        j = codes.index(code)
        for vd in vdates:
            cut = bisect_right(s["dates"], vd)
            closes = [c for c in s["closes"][:cut]]
            ti = date_i[vd]
            my_rs = int(rs_g[ti, j])
            res = evaluate_trend_template(closes, rs=(my_rs if my_rs > 0 else None), rs_min=RS_MIN)
            bits = int(crit_bits[ti, j])
            mine_crit = {str(k + 1): bool((bits >> k) & 1) for k in range(7)}
            mine_crit["8"] = bool(rs_g[ti, j] >= RS_MIN)
            oracle_crit = {k: v["pass"] for k, v in res["criteria"].items()}
            mism = [k for k in oracle_crit if oracle_crit[k] != mine_crit[k]]
            oracle.append({
                "code": code, "date": vd, "oracle_pass": res["pass"],
                "mine_pass": bool(all_pass[ti, j]),
                "oracle_criteria": oracle_crit, "mine_criteria": mine_crit,
                "mismatched_criteria": mism,
                "oracle_n_closes": len(closes),
                "mine_nhist": int(nhist[ti, j]),
            })
    val["oracle_3x2"] = oracle
    val["oracle_criteria_match_rate"] = round(
        sum(8 - len(o["mismatched_criteria"]) for o in oracle) / (len(oracle) * 8), 4)

    # (c) fltRt chaining vs series returns, 005930, 2025-2026
    s = json.loads((SERIES / "005930.json").read_text(encoding="utf-8"))
    j = codes.index("005930")
    sdates = s["dates"]
    scloses = s["closes"]
    common = [d for d in sdates if d in date_i and d >= "2025-01-01"]
    my_idx = np.array([idx_g[date_i[d], j] for d in common])
    se_cl = np.array([scloses[sdates.index(d)] for d in common])
    my_ret = my_idx[1:] / my_idx[:-1] - 1
    se_ret = se_cl[1:] / se_cl[:-1] - 1
    dmax = float(np.nanmax(np.abs(my_ret - se_ret)))
    worst_i = int(np.nanargmax(np.abs(my_ret - se_ret)))
    val["fltRt_chain_005930"] = {
        "n_common_days_2025_2026": len(common),
        "max_abs_daily_return_diff": dmax,
        "worst_date": common[worst_i + 1],
        "mean_abs_diff": float(np.nanmean(np.abs(my_ret - se_ret))),
    }

    # ═════ SAVE ═════════════════════════════════════════════════════
    print("6) saving ...", flush=True)
    np.savez_compressed(
        SCRATCH / "passmatrix.npz",
        dates=np.array(dates), codes=code_arr,
        all_pass=all_pass, passed_count=passed_count,
        rs=rs_g, tenure10=tenure10, eligible=eligible, present=present,
        crit_bits=crit_bits, nhist=nhist,
        idx=idx_g,
        open_r=open_r, hi_r=hi_r, lo_r=lo_r,
        vol=A["vol"].astype(np.float32),
        turnover_eok=turnover_eok.astype(np.float32),
        turn50_eok=turn50_g.astype(np.float32),
        market=A["mkt"],
    )

    quality["present_rows_missing_close"] = n_present_no_close
    quality["flt_fallback_ratio_steps"] = flt_fallback_ratio
    quality["dropped_pure_konex_codes"] = dropped_konex_only
    meta = {
        "built_at": time.strftime("%Y-%m-%d %H:%M"),
        "shape": {"T_days": T, "N_codes": N,
                  "date_range": [dates[0], dates[-1]]},
        "rules": {
            "rs_min": RS_MIN, "rs_pool_min": MIN_POOL,
            "rs_pool": "same-win pool (win=min(n-1,252)); rank=bisect_left; rs=clip(round(rank/size*100),1,99); pool excludes KONEX+halted+n<200",
            "min_closes_for_tt": MIN_N_TT,
            "turnover_rule": "50d avg(raw clpr*trqu)>=5 eok, needs>=20d else pass",
            "liveness": "last 5 trading-day volumes all 0 -> excluded (is_halted mirror)",
            "eligibility": "KOSPI/KOSDAQ + not preferred(last char != '0') + not 9xxxxx + turnover + liveness",
            "all_pass_is_pure_8_criteria": True,
            "tenure10": "count of all_pass among prior 10 global trading days (missing=fail)",
        },
        "rs_pool_252_size_last_day": pool_sizes_252[-1] if pool_sizes_252 else None,
        "per_year": per_year,
        "quality": quality,
        "quirks": [
            "pdata starts 2020-01-02: nhist is truncated for pre-2020 listings -> no evaluation until day 200 of grid (~2020-10-21); RS uses shortened same-win pools until day 253 (~2021-01); first ~1yr of matrix is warm-up, not true history.",
            "RS pool = pdata KOSPI+KOSDAQ (~2,700) vs production FDR listing (~2,520): pdata includes vehicles FDR listing drops; percentiles can shift 1-2 points near the 80 cut.",
            "turnover filter uses raw clpr*trqu; production uses back-adjusted closes*volumes — differs only when corporate action within the 50d window.",
            "manual excluded-codes.json not applied historically (time-invariant file, would be look-ahead).",
            "production cache history starts 2024-12-19 (401d on 2026-08-13); win=252 both sides, but 52w windows identical only when both have >=252d.",
        ],
        "validation": val,
    }
    (SCRATCH / "passmatrix_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"per_year": per_year,
                      "snapshot": {k: v for k, v in val["snapshot_2026_08_13"].items() if k != "diffs"},
                      "oracle_match": val["oracle_criteria_match_rate"],
                      "chain": val["fltRt_chain_005930"]}, ensure_ascii=False, indent=1))
    print("diffs:", json.dumps(val["snapshot_2026_08_13"]["diffs"], ensure_ascii=False, indent=1))
    print("oracle:", json.dumps(oracle, ensure_ascii=False, indent=1))
    print("DONE")


if __name__ == "__main__":
    main()
