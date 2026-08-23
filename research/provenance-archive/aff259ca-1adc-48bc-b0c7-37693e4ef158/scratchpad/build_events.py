# -*- coding: utf-8 -*-
"""Actionable+leading-sector cohort: events, entries, outcomes, discriminators."""
import json, os, math
from statistics import mean

REPO = r"C:\Users\hanul\playground\my-stock"
SCRATCH = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad"
COST = 0.34          # pct points round-trip
TGT, STP = 0.20, -0.10
WINDOW = 40          # trading days incl. entry day
PIVOT_CLUSTER = 0.03
DATA_END = "2026-08-14"

def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

snaps = load(os.path.join(SCRATCH, "rich_snapshots.json"))["snapshots"]
snaps.sort(key=lambda s: s["date"])
tags = load(os.path.join(REPO, "public/data/sepa-leading-sectors.json"))["tags"]
regime_series = load(os.path.join(REPO, "public/data/market-regime.json"))["series"]
regime_by_date = sorted([(r["date"], bool(r["up"])) for r in regime_series])

def regime_at(date):
    up = None
    for d, u in regime_by_date:
        if d <= date:
            up = u
        else:
            break
    return up

_ohlcv_cache = {}
def ohlcv(code):
    if code in _ohlcv_cache:
        return _ohlcv_cache[code]
    p = os.path.join(REPO, ".cache/ohlcv/series", f"{code}.json")
    if not os.path.exists(p):
        _ohlcv_cache[code] = None
        return None
    d = load(p)
    _ohlcv_cache[code] = d
    return d

def idx_le(dates, date):
    """index of last trading day <= date, or None"""
    lo, hi, ans = 0, len(dates) - 1, None
    while lo <= hi:
        mid = (lo + hi) // 2
        if dates[mid] <= date:
            ans = mid; lo = mid + 1
        else:
            hi = mid - 1
    return ans

# ---------- collect trigger signals per tagged code ----------
signals = {}  # code -> list of {snap_date, src, pivot, rec}
for s in snaps:
    for r in s["records"]:
        code = r["code"]
        if code not in tags:
            continue
        if not (r["status"] == "actionable" or r["entry_ready"]):
            continue
        if r["pivot"] is None or r["pivot"] <= 0:
            continue
        signals.setdefault(code, []).append({"snap_date": s["date"], "src": r["src"], "pivot": r["pivot"], "rec": r})

# ---------- event clustering + simulation ----------
def simulate(ev, series):
    """entry + outcome using pivot-as-of logic. Returns dict or None if no entry."""
    dates, o, h, l, c, v = series["dates"], series["opens"], series["highs"], series["lows"], series["closes"], series["volumes"]
    sigs = ev["signals"]  # sorted by snap_date
    open_date = ev["event_open"]
    # entry scan
    entry_i = None; entry_pivot = None
    start = idx_le(dates, open_date)
    start = 0 if start is None else start + 1
    for i in range(start, len(dates)):
        t = dates[i]
        if t > DATA_END:
            break
        pv = None
        for sg in sigs:
            if sg["snap_date"] < t:
                pv = sg["pivot"]
            else:
                break
        if pv is None:
            continue
        if h[i] >= pv:
            entry_i, entry_pivot = i, pv
            break
    if entry_i is None:
        return None
    fill = max(o[entry_i], entry_pivot)
    tgt, stp = fill * (1 + TGT), fill * (1 + STP)
    outcome = None; res_i = None
    last_i = min(entry_i + WINDOW - 1, len(dates) - 1)
    for i in range(entry_i, last_i + 1):
        hit_t = h[i] >= tgt
        hit_s = l[i] <= stp
        if hit_t and hit_s:
            outcome, res_i = "loss_bothhit", i; break
        if hit_s:
            outcome, res_i = "loss", i; break
        if hit_t:
            outcome, res_i = "win", i; break
    if outcome in ("loss", "loss_bothhit"):
        net = STP * 100 - COST; closed = True
    elif outcome == "win":
        net = TGT * 100 - COST; closed = True
    else:
        outcome = "unresolved_marked"
        net = (c[last_i] / fill - 1) * 100 - COST
        closed = False
        res_i = last_i
    # r10/MFE10/MAE10 (raw path, no stop)
    e10 = min(entry_i + 9, len(dates) - 1)
    r10 = (c[e10] / fill - 1) * 100
    mfe10 = (max(h[entry_i:e10 + 1]) / fill - 1) * 100
    mae10 = (min(l[entry_i:e10 + 1]) / fill - 1) * 100
    # entry-day features
    relvol = None
    if entry_i >= 10:
        w = v[max(0, entry_i - 50):entry_i]
        m = mean(w) if w else None
        if m and m > 0:
            relvol = v[entry_i] / m
    gap = (o[entry_i] / c[entry_i - 1] - 1) * 100 if entry_i >= 1 else None
    fill_prem = (fill / entry_pivot - 1) * 100
    # trading days from event open to entry (exclusive open, inclusive entry)
    days_to_cross = entry_i - start + 1
    return {
        "entry_date": dates[entry_i], "entry_pivot": round(entry_pivot, 2), "fill": round(fill, 2),
        "outcome": outcome, "closed": closed, "resolve_date": dates[res_i],
        "net_pct": round(net, 2), "r10": round(r10, 2), "mfe10": round(mfe10, 2), "mae10": round(mae10, 2),
        "r10_partial": e10 - entry_i < 9,
        "relvol_entry": round(relvol, 2) if relvol is not None else None,
        "gap_pct": round(gap, 2) if gap is not None else None,
        "fill_premium_pct": round(fill_prem, 2),
        "days_to_cross": days_to_cross,
        "regime_up_entry": regime_at(dates[entry_i]),
    }

events = []
n_sig_total = 0
for code, sigs in signals.items():
    sigs.sort(key=lambda x: (x["snap_date"], x["src"]))
    n_sig_total += len(sigs)
    series = ohlcv(code)
    code_events = []
    for sg in sigs:
        attached = False
        for ev in reversed(code_events):
            # resolved strictly before/at this snapshot date?
            sim = ev.get("_sim")
            resolved_by = sim["resolve_date"] if (sim and sim["closed"]) else None
            if resolved_by is not None and resolved_by <= sg["snap_date"]:
                continue
            if abs(sg["pivot"] / ev["latest_pivot"] - 1) <= PIVOT_CLUSTER:
                ev["signals"].append(sg)
                ev["latest_pivot"] = sg["pivot"]
                if series:
                    ev["_sim"] = simulate(ev, series)
                attached = True
                break
        if not attached:
            ev = {"code": code, "event_open": sg["snap_date"], "signals": [sg], "latest_pivot": sg["pivot"]}
            if series:
                ev["_sim"] = simulate(ev, series)
            code_events.append(ev)
    events.extend(code_events)

# ---------- event-open features ----------
out_events = []
for ev in events:
    code = ev["code"]
    first = ev["signals"][0]
    rec = first["rec"]
    series = ohlcv(code)
    tag = tags[code]
    feat = {
        "code": code, "name": rec.get("name") or tag.get("name"),
        "sector_short": tag.get("short"), "sector_rank": tag.get("rank"), "sector_conf": tag.get("confidence"),
        "event_open": ev["event_open"],
        "first_src": first["src"],
        "srcs": sorted({s["src"] for s in ev["signals"]}),
        "first_pivot": round(first["pivot"], 2), "latest_pivot": round(ev["latest_pivot"], 2),
        "n_signals": len(ev["signals"]),
        "trigger_status": rec["status"], "trigger_entry_ready": rec["entry_ready"],
        "rs_event": rec.get("rs"),
        "tightness_pct": rec.get("tightness_pct"),
        "volume_dryup_ratio": rec.get("volume_dryup_ratio"),
        "num_contractions": rec.get("num_contractions"),
        "base_depth_pct": rec.get("base_depth_pct") or rec.get("cup_depth_pct") or rec.get("flag_depth_pct"),
    }
    if series:
        dates = series["dates"]
        i0 = idx_le(dates, ev["event_open"])
        if i0 is not None and i0 >= 1:
            c0 = series["closes"][i0]
            lo52 = min(series["lows"][max(0, i0 - 251):i0 + 1])
            hi52 = max(series["highs"][max(0, i0 - 251):i0 + 1])
            feat["hist_days_52w"] = i0 + 1 - max(0, i0 - 251)
            feat["pct_above_52w_low"] = round((c0 / lo52 - 1) * 100, 1)
            feat["pct_below_52w_high"] = round((1 - c0 / hi52) * 100, 1)
            if i0 >= 63:
                feat["r63_event"] = round((c0 / series["closes"][i0 - 63] - 1) * 100, 1)
            else:
                feat["r63_event"] = None
        sim = ev.get("_sim")
        if sim:
            feat.update(sim)
            feat["entered"] = True
        else:
            feat["entered"] = False
    else:
        feat["entered"] = False
        feat["no_ohlcv"] = True
    out_events.append(feat)

out_events.sort(key=lambda e: (e["event_open"], e["code"]))

entered = [e for e in out_events if e.get("entered")]
closed = [e for e in entered if e.get("closed")]
wins = [e for e in closed if e["outcome"] == "win"]

def summ(evs):
    if not evs:
        return {"n": 0}
    nets = [e["net_pct"] for e in evs]
    w = [e for e in evs if e["net_pct"] > 0]
    return {"n": len(evs), "win_rate": round(100 * len(w) / len(evs), 1), "avg_net": round(mean(nets), 2)}

summary = {
    "n_codes_tagged": len(tags),
    "n_codes_with_signal": len(signals),
    "n_signals": n_sig_total,
    "n_events": len(out_events),
    "n_entered": len(entered),
    "n_no_entry": len(out_events) - len(entered),
    "n_closed": len(closed),
    "n_unresolved_marked": len(entered) - len(closed),
    "closed_only": {"n": len(closed), "win_rate": round(100 * len(wins) / len(closed), 1) if closed else None,
                    "avg_net": round(mean([e["net_pct"] for e in closed]), 2) if closed else None},
    "all_in": summ(entered),
}
print(json.dumps(summary, indent=1))

with open(os.path.join(SCRATCH, "events_raw.json"), "w", encoding="utf-8") as f:
    json.dump({"summary": summary, "events": out_events}, f, ensure_ascii=False, indent=1)
print("wrote events_raw.json")
