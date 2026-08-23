# -*- coding: utf-8 -*-
"""Discriminator tables for actionable+leading cohort."""
import json, os
from statistics import mean, median

SCRATCH = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad"
d = json.load(open(os.path.join(SCRATCH, "events_raw.json"), encoding="utf-8"))
events = d["events"]
entered = [e for e in events if e.get("entered")]

def cell(evs):
    closed = [e for e in evs if e.get("closed")]
    cw = [e for e in closed if e["outcome"] == "win"]
    out = {
        "n_entered": len(evs),
        "n_closed": len(closed),
        "closed_wins": len(cw),
        "closed_win_rate": round(100 * len(cw) / len(closed), 1) if closed else None,
        "closed_avg_net": round(mean([e["net_pct"] for e in closed]), 2) if closed else None,
        "allin_win_rate": round(100 * sum(1 for e in evs if e["net_pct"] > 0) / len(evs), 1) if evs else None,
        "allin_avg_net": round(mean([e["net_pct"] for e in evs]), 2) if evs else None,
        "avg_r10": round(mean([e["r10"] for e in evs]), 2) if evs else None,
        "avg_mfe10": round(mean([e["mfe10"] for e in evs]), 2) if evs else None,
        "avg_mae10": round(mean([e["mae10"] for e in evs]), 2) if evs else None,
        "small_n": len(closed) < 8,
    }
    return out

def table(name, binfn, evs=entered):
    groups = {}
    for e in evs:
        b = binfn(e)
        if b is None:
            continue
        groups.setdefault(b, []).append(e)
    return {name: {str(k): cell(v) for k, v in sorted(groups.items(), key=lambda x: str(x[0]))}}

tables = {}
tables.update(table("a_relvol", lambda e: None if e.get("relvol_entry") is None else ("1_<0.75" if e["relvol_entry"] < 0.75 else "2_0.75-1.5" if e["relvol_entry"] < 1.5 else "3_>=1.5")))
tables.update(table("a_relvol_ge3", lambda e: None if e.get("relvol_entry") is None else (">=3" if e["relvol_entry"] >= 3 else "<3")))
tables.update(table("b_rs", lambda e: None if e.get("rs_event") is None else ("1_<90" if e["rs_event"] < 90 else "2_90-96" if e["rs_event"] < 97 else "3_>=97")))
tables.update(table("c_above52wlow", lambda e: None if e.get("pct_above_52w_low") is None else ("1_<50%" if e["pct_above_52w_low"] < 50 else "2_50-100%" if e["pct_above_52w_low"] < 100 else "3_>=100%")))
tables.update(table("c_r63", lambda e: None if e.get("r63_event") is None else ("1_<15%" if e["r63_event"] < 15 else "2_15-40%" if e["r63_event"] < 40 else "3_>=40%")))
tables.update(table("d_below52whigh", lambda e: None if e.get("pct_below_52w_high") is None else ("1_<5%" if e["pct_below_52w_high"] < 5 else "2_5-15%" if e["pct_below_52w_high"] < 15 else "3_>=15%")))

meds = {}
for k in ("base_depth_pct", "tightness_pct"):
    vals = [e[k] for e in entered if e.get(k) is not None]
    meds[k] = median(vals) if vals else None
tables.update(table("e_base_depth", lambda e: None if e.get("base_depth_pct") is None else ("shallow_<=med%.1f" % meds["base_depth_pct"] if e["base_depth_pct"] <= meds["base_depth_pct"] else "deep_>med")))
tables.update(table("e_tightness", lambda e: None if e.get("tightness_pct") is None else ("tight_<=med%.1f" % meds["tightness_pct"] if e["tightness_pct"] <= meds["tightness_pct"] else "loose_>med")))
tables.update(table("e_num_contractions", lambda e: None if e.get("num_contractions") is None else str(int(e["num_contractions"]))))
tables.update(table("f_gap", lambda e: None if e.get("gap_pct") is None else ("1_<=0%" if e["gap_pct"] <= 0 else "2_0-3%" if e["gap_pct"] <= 3 else "3_>3%")))
tables.update(table("g_regime", lambda e: "up" if e.get("regime_up_entry") else "down"))
tables.update(table("h_sector", lambda e: e.get("sector_short")))
tables.update(table("i_days_to_cross", lambda e: "1_next_day" if e.get("days_to_cross") == 1 else "2_later"))
tables.update(table("x_src", lambda e: e.get("first_src")))
tables.update(table("x_trigger", lambda e: "entry_ready" if e.get("trigger_entry_ready") else "actionable_only"))
tables.update(table("x_month", lambda e: e["entry_date"][:7]))
tables.update(table("x_conf", lambda e: e.get("sector_conf")))

# regime-controlled relvol (July down-regime only)
july = [e for e in entered if not e.get("regime_up_entry")]
tables.update(table("z_relvol_downregime_only", lambda e: None if e.get("relvol_entry") is None else (">=1.5" if e["relvol_entry"] >= 1.5 else "<1.5"), july))

# correlations (spearman-ish rank corr) of features vs r10 / mfe10
def rankcorr(xs, ys):
    n = len(xs)
    if n < 5:
        return None
    def ranks(v):
        s = sorted(range(n), key=lambda i: v[i])
        r = [0] * n
        for rank, i in enumerate(s):
            r[i] = rank
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = mean(rx), mean(ry)
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    den = (sum((rx[i] - mx) ** 2 for i in range(n)) * sum((ry[i] - my) ** 2 for i in range(n))) ** 0.5
    return round(num / den, 2) if den else None

corrs = {}
for feat in ("relvol_entry", "rs_event", "pct_above_52w_low", "r63_event", "pct_below_52w_high",
             "base_depth_pct", "tightness_pct", "gap_pct", "days_to_cross"):
    pairs = [(e[feat], e["r10"], e["mfe10"], e["net_pct"]) for e in entered if e.get(feat) is not None]
    if len(pairs) >= 5:
        xs = [p[0] for p in pairs]
        corrs[feat] = {"n": len(pairs),
                       "vs_r10": rankcorr(xs, [p[1] for p in pairs]),
                       "vs_mfe10": rankcorr(xs, [p[2] for p in pairs]),
                       "vs_net": rankcorr(xs, [p[3] for p in pairs])}

overall = {
    "all": cell(entered),
    "closed_only_note": "closed = +20/-10 hit within data; unresolved marked at last close <= 2026-08-14",
    "n_bothhit_losses": sum(1 for e in entered if e.get("outcome") == "loss_bothhit"),
    "medians": meds,
}

out = {"overall": overall, "tables": tables, "rank_correlations": corrs}
with open(os.path.join(SCRATCH, "agg_tables.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
