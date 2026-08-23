# -*- coding: utf-8 -*-
"""Threshold-newcomer hypothesis: tenure/streak/RS-floor vs trade outcomes.

Data:
  trend_snaps.json      - nightly sepa-trend-candidates snapshots (last commit per date)
  enriched_trades.json  - 53 closed real trades
  forming_backtest.json - backtest events (forming/control cohorts)
"""
import json, os, math
from datetime import datetime, timezone, timedelta
from scipy.stats import fisher_exact

SCRATCH = os.path.dirname(os.path.abspath(__file__))
KST = timezone(timedelta(hours=9))

snaps = json.load(open(os.path.join(SCRATCH, "trend_snaps.json"), encoding="utf-8"))
for s in snaps:
    s["dt"] = datetime.fromisoformat(s["iso"])

trades = json.load(open(os.path.join(SCRATCH, "enriched_trades.json"), encoding="utf-8"))["rows"]
bt = json.load(open(os.path.join(SCRATCH, "forming_backtest.json"), encoding="utf-8"))


def pre_entry_snaps(entry_date):
    cutoff = datetime.fromisoformat(entry_date + "T09:00:00+09:00")
    return [s for s in snaps if s["dt"] < cutoff]


def compute_tenure(code, entry_date):
    prior = pre_entry_snaps(entry_date)
    n_prior = len(prior)
    window = prior[-10:]
    def rec(s):
        return s["recs"].get(code)  # [rs, pc, all_pass] or None
    t_strict = sum(1 for s in window if (r := rec(s)) and r[2])
    t_loose = sum(1 for s in window if (r := rec(s)) and r[1] is not None and r[1] >= 7)
    # streak: consecutive passes ending at latest pre-entry snapshot (walk all prior)
    streak_s = 0
    for s in reversed(prior):
        r = rec(s)
        if r and r[2]:
            streak_s += 1
        else:
            break
    streak_l = 0
    for s in reversed(prior):
        r = rec(s)
        if r and r[1] is not None and r[1] >= 7:
            streak_l += 1
        else:
            break
    latest = prior[-1] if prior else None
    lr = rec(latest) if latest else None
    rs_latest = lr[0] if lr else None
    latest_allpass = bool(lr and lr[2])
    latest_pc = lr[1] if lr else None
    rs_vals = [r[0] for s in window if (r := rec(s)) and r[0] is not None]
    rs_vol = (max(rs_vals) - min(rs_vals)) if len(rs_vals) >= 2 else None
    rs_trail = [(s["date"], (rec(s)[0] if rec(s) else None),
                 (rec(s)[1] if rec(s) else None)) for s in window]
    return {
        "n_prior_snaps": n_prior, "n_window": len(window),
        "tenure10_strict": t_strict, "tenure10_loose": t_loose,
        "streak_strict": streak_s, "streak_loose": streak_l,
        "latest_allpass": latest_allpass, "latest_passed_count": latest_pc,
        "rs_latest": rs_latest, "rs_vol10": rs_vol,
        "latest_snap_date": latest["date"] if latest else None,
        "rs_trail": rs_trail,
    }


# ---------------- trades ----------------
trade_rows = []
for t in trades:
    c = compute_tenure(t["code"], t["open_date"])
    on_page = t["displayed_status"] != "not_on_page"
    rs_disp = t["displayed_rs"] if t["displayed_rs"] is not None else c["rs_latest"]
    row = {
        "code": t["code"], "name": t["name"], "open_date": t["open_date"],
        "net_pct": t["net_pct"], "win": t["outcome"] == "win",
        "setup": t["setup"], "regime_up": t["regime_up"],
        "relvol_entry": t["relvol_entry"], "displayed_status": t["displayed_status"],
        "on_page": on_page, "rs_display": rs_disp,
        **c,
    }
    row["newcomer"] = (c["latest_allpass"] or on_page) and c["tenure10_strict"] <= 2
    row["newcomer_loose"] = (c["latest_allpass"] or on_page) and c["tenure10_loose"] <= 2
    row["rs_floor"] = rs_disp is not None and rs_disp <= 82
    row["regular"] = c["tenure10_strict"] >= 5
    row["flag_proposed"] = row["newcomer"] or row["rs_floor"]  # tenure<=2 OR rs<=82 (newcomer includes on-page cond)
    row["flag_raw"] = (c["tenure10_strict"] <= 2) or row["rs_floor"]  # literal proposal
    trade_rows.append(row)

# ---------------- backtest events ----------------
entered = [e for e in bt["events"] if e.get("result") == "entered"]
# dedup: first entry per code (keep earliest entry_date; per code across cohorts, note collisions)
entered.sort(key=lambda e: (e["entry_date"], e["event_open_date"]))
seen, bt_rows, dropped_dups = set(), [], 0
for e in entered:
    if e["code"] in seen:
        dropped_dups += 1
        continue
    seen.add(e["code"])
    c = compute_tenure(e["code"], e["entry_date"])
    rs_disp = e.get("rs_open")
    row = {
        "code": e["code"], "name": e["name"], "cohort": e["cohort"],
        "entry_date": e["entry_date"], "net_pct": e["net_pct"],
        "still_open": e["still_open"], "win": (e["net_pct"] is not None and e["net_pct"] > 0),
        "relvol_entry": e.get("rel_vol_entry"), "rs_display": rs_disp,
        "exit_kind": e.get("exit_kind"),
        **c,
    }
    row["newcomer"] = c["tenure10_strict"] <= 2  # events are by construction on the page
    row["newcomer_loose"] = c["tenure10_loose"] <= 2
    row["rs_floor"] = rs_disp is not None and rs_disp <= 82
    row["regular"] = c["tenure10_strict"] >= 5
    row["flag_proposed"] = row["newcomer"] or row["rs_floor"]
    row["flag_raw"] = row["flag_proposed"]
    bt_rows.append(row)

bt_closed = [r for r in bt_rows if not r["still_open"]]


# ---------------- stats helpers ----------------
def grp(rows):
    n = len(rows)
    if n == 0:
        return {"n": 0, "wins": 0, "win_rate": None, "avg_net": None, "sum_net": None}
    wins = sum(1 for r in rows if r["win"])
    nets = [r["net_pct"] for r in rows if r["net_pct"] is not None]
    return {"n": n, "wins": wins, "win_rate": round(100 * wins / n, 1),
            "avg_net": round(sum(nets) / len(nets), 2) if nets else None,
            "sum_net": round(sum(nets), 2) if nets else None}


def fisher(rows_a, rows_b):
    """2x2 win/loss Fisher between two groups."""
    a_w = sum(1 for r in rows_a if r["win"]); a_l = len(rows_a) - a_w
    b_w = sum(1 for r in rows_b if r["win"]); b_l = len(rows_b) - b_w
    if not rows_a or not rows_b:
        return None
    _, p = fisher_exact([[a_w, a_l], [b_w, b_l]])
    return round(p, 4)


def split_report(rows, label):
    out = {"label": label, "n": len(rows)}
    new = [r for r in rows if r["newcomer"]]
    reg = [r for r in rows if r["regular"]]
    mid = [r for r in rows if not r["newcomer"] and not r["regular"]]
    out["newcomer"] = grp(new); out["mid_3_4"] = grp(mid); out["regular_ge5"] = grp(reg)
    out["fisher_new_vs_reg"] = fisher(new, reg)
    out["fisher_new_vs_rest"] = fisher(new, [r for r in rows if not r["newcomer"]])
    # loose defn
    newL = [r for r in rows if r["newcomer_loose"]]
    regL = [r for r in rows if r["tenure10_loose"] >= 5]
    out["newcomer_loose"] = grp(newL); out["regular_loose"] = grp(regL)
    out["fisher_loose"] = fisher(newL, regL)
    # rs buckets
    rs_lo = [r for r in rows if r["rs_display"] is not None and r["rs_display"] <= 82]
    rs_md = [r for r in rows if r["rs_display"] is not None and 83 <= r["rs_display"] <= 89]
    rs_hi = [r for r in rows if r["rs_display"] is not None and r["rs_display"] >= 90]
    out["rs_le82"] = grp(rs_lo); out["rs_83_89"] = grp(rs_md); out["rs_ge90"] = grp(rs_hi)
    out["fisher_rslo_vs_hi"] = fisher(rs_lo, rs_hi)
    # streak buckets
    for lab, lo, hi in [("streak0", 0, 0), ("streak1", 1, 1), ("streak2_4", 2, 4), ("streak_ge5", 5, 999)]:
        out[lab] = grp([r for r in rows if lo <= r["streak_strict"] <= hi])
    # rs volatility
    rv = [r for r in rows if r["rs_vol10"] is not None]
    out["rsvol_ge15"] = grp([r for r in rv if r["rs_vol10"] >= 15])
    out["rsvol_lt15"] = grp([r for r in rv if r["rs_vol10"] < 15])
    return out


def crosstab(rows, cond_name, cond):
    """newcomer effect within strata of another axis."""
    res = {}
    for stratum, pred in cond.items():
        sub = [r for r in rows if pred(r)]
        res[stratum] = {
            "all": grp(sub),
            "newcomer": grp([r for r in sub if r["newcomer"]]),
            "non_newcomer": grp([r for r in sub if not r["newcomer"]]),
        }
    return {cond_name: res}


def flag_eval(rows, flag_key):
    fl = [r for r in rows if r[flag_key]]
    kept = [r for r in rows if not r[flag_key]]
    losses = [r for r in rows if not r["win"]]
    wins = [r for r in rows if r["win"]]
    return {
        "n": len(rows), "n_flagged": len(fl),
        "losses_total": len(losses),
        "losses_flagged": sum(1 for r in losses if r[flag_key]),
        "wins_total": len(wins),
        "wins_flagged": sum(1 for r in wins if r[flag_key]),
        "wins_flagged_names": [f'{r["name"]}({r["open_date" if "open_date" in r else "entry_date"]},{r["net_pct"]:+.1f}%)'
                               for r in wins if r[flag_key]],
        "flagged": grp(fl), "kept": grp(kept),
        "fisher_flag": fisher(fl, kept),
        "net_avoided_sum": round(-sum(r["net_pct"] for r in fl if r["net_pct"] is not None), 2),
    }


def variant_flag(r, ten_thr, rs_thr, op):
    a = (r["tenure10_strict"] <= ten_thr) if ten_thr is not None else None
    b = (r["rs_display"] is not None and r["rs_display"] <= rs_thr) if rs_thr is not None else None
    if a is None: return bool(b)
    if b is None: return bool(a)
    return (a or b) if op == "OR" else (a and b)


def variant_grid(rows):
    out = []
    for ten in [None, 1, 2, 3]:
        for rs in [None, 80, 82, 84]:
            for op in (["OR", "AND"] if ten is not None and rs is not None else ["-"]):
                if ten is None and rs is None:
                    continue
                for r in rows:
                    r["_vf"] = variant_flag(r, ten, rs, op)
                fl = [r for r in rows if r["_vf"]]
                kept = [r for r in rows if not r["_vf"]]
                losses_f = sum(1 for r in fl if not r["win"])
                wins_f = sum(1 for r in fl if r["win"])
                k = grp(kept)
                out.append({
                    "rule": f"tenure10<={ten} {op} rs<={rs}".replace("tenure10<=None ", "").replace(" - rs<=None", "").replace("- ", "").replace(" rs<=None", ""),
                    "ten": ten, "rs": rs, "op": op,
                    "n_flagged": len(fl), "losses_flagged": losses_f, "wins_flagged": wins_f,
                    "kept_n": k["n"], "kept_win_rate": k["win_rate"], "kept_avg_net": k["avg_net"],
                    "avoided_net_sum": round(-sum(r["net_pct"] for r in fl if r["net_pct"] is not None), 2),
                })
    for r in rows:
        r.pop("_vf", None)
    return out


# ---------------- run ----------------
results = {}
results["meta"] = {
    "n_snapshots": len(snaps),
    "snapshot_dates": [s["date"] for s in snaps],
    "note_universe": "08-03부터 스냅샷 유니버스 축소(2485→1346); 파일 부재=all_pass 아님으로 처리",
    "n_trades": len(trade_rows),
    "n_bt_entered_dedup": len(bt_rows), "n_bt_closed": len(bt_closed),
    "bt_dups_dropped": dropped_dups,
    "early_trades_low_history": [f'{r["name"]}({r["open_date"]},n_prior={r["n_prior_snaps"]})'
                                 for r in trade_rows if r["n_prior_snaps"] < 5],
}

results["trades_split"] = split_report(trade_rows, "53 실거래(청산완료)")
results["trades_split_excl_low_history"] = split_report(
    [r for r in trade_rows if r["n_prior_snaps"] >= 5], "실거래(스냅샷 5개 이상 확보분)")
results["bt_closed_split"] = split_report(bt_closed, "백테스트 청산완료(코드당 첫 진입)")
results["bt_forming_closed_split"] = split_report(
    [r for r in bt_closed if r["cohort"] == "forming"], "백테스트 forming 청산완료")

# cross-tabs on trades
results["crosstab_setup"] = crosstab(trade_rows, "setup_null", {
    "setup_null": lambda r: r["setup"] is None,
    "setup_present": lambda r: r["setup"] is not None})
results["crosstab_regime"] = crosstab(trade_rows, "regime", {
    "regime_up": lambda r: r["regime_up"] is True,
    "regime_down": lambda r: r["regime_up"] is False})
results["crosstab_relvol"] = crosstab(trade_rows, "relvol", {
    "relvol_ge1": lambda r: r["relvol_entry"] is not None and r["relvol_entry"] >= 1,
    "relvol_lt1": lambda r: r["relvol_entry"] is not None and r["relvol_entry"] < 1})
# reverse: is newcomer just proxying null-setup/regime?
nn = [r for r in trade_rows if r["newcomer"]]
results["newcomer_composition"] = {
    "n": len(nn),
    "setup_null_share": round(100 * sum(1 for r in nn if r["setup"] is None) / len(nn), 1) if nn else None,
    "regime_down_share": round(100 * sum(1 for r in nn if r["regime_up"] is False) / len(nn), 1) if nn else None,
    "relvol_lt1_share": round(100 * sum(1 for r in nn if (r["relvol_entry"] or 0) < 1) / len(nn), 1) if nn else None,
    "vs_all": {
        "setup_null_share": round(100 * sum(1 for r in trade_rows if r["setup"] is None) / len(trade_rows), 1),
        "regime_down_share": round(100 * sum(1 for r in trade_rows if r["regime_up"] is False) / len(trade_rows), 1),
        "relvol_lt1_share": round(100 * sum(1 for r in trade_rows if (r["relvol_entry"] or 0) < 1) / len(trade_rows), 1),
    },
}

# flag evaluation
results["flag_proposed_trades"] = flag_eval(trade_rows, "flag_raw")
results["flag_proposed_bt_closed"] = flag_eval(bt_closed, "flag_raw")
results["variants_trades"] = variant_grid(trade_rows)
results["variants_bt_closed"] = variant_grid(bt_closed)

# per-trade listing
listing = []
for r in sorted(trade_rows, key=lambda x: x["open_date"]):
    listing.append({k: r[k] for k in
                    ["code", "name", "open_date", "net_pct", "win", "setup", "regime_up",
                     "relvol_entry", "rs_display", "rs_latest", "tenure10_strict",
                     "tenure10_loose", "streak_strict", "streak_loose", "rs_vol10",
                     "n_prior_snaps", "newcomer", "rs_floor", "flag_raw", "rs_trail"]})
results["trades_listing"] = listing

bt_listing = []
for r in sorted(bt_rows, key=lambda x: x["entry_date"]):
    bt_listing.append({k: r[k] for k in
                       ["code", "name", "cohort", "entry_date", "net_pct", "still_open", "win",
                        "rs_display", "rs_latest", "tenure10_strict", "tenure10_loose",
                        "streak_strict", "rs_vol10", "n_prior_snaps", "newcomer", "rs_floor",
                        "flag_raw", "exit_kind"]})
results["bt_listing"] = bt_listing

with open(os.path.join(SCRATCH, "newcomer_raw_results.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=1)

# console summary
print("=== trades split ===")
print(json.dumps(results["trades_split"], ensure_ascii=False, indent=1))
print("=== flag on trades ===")
print(json.dumps(results["flag_proposed_trades"], ensure_ascii=False, indent=1))
print("=== bt closed split ===")
print(json.dumps(results["bt_closed_split"], ensure_ascii=False, indent=1))
print("=== flag on bt closed ===")
print(json.dumps(results["flag_proposed_bt_closed"], ensure_ascii=False, indent=1))
print("=== newcomer composition ===")
print(json.dumps(results["newcomer_composition"], ensure_ascii=False, indent=1))
print("meta:", json.dumps(results["meta"]["early_trades_low_history"], ensure_ascii=False))
