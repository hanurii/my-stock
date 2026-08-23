# -*- coding: utf-8 -*-
"""TASK 2: remap reaction day by disclosure timing.

장전/장중 -> reaction = 공시 당일 (same-day bar, metrics recomputed from OHLCV)
장후     -> reaction = 다음 거래일
시각미상  -> keep prior mapping, flag (none expected — KIND coverage 100%)
Writes ec_timing.json and merges into ec_final_v2.json.
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

SCRATCH = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad"
REPO = r"C:\Users\hanul\playground\my-stock"

NEXT_TRADING_AFTER_LAST = "2026-08-18"  # 8/15 금 광복절? -> 8/14 last bar, next 8/18(월)


def classify(hhmm):
    if hhmm is None:
        return "시각미상"
    h, m = int(hhmm[:2]), int(hhmm[3:5])
    v = h * 60 + m
    if v < 9 * 60:
        return "장전"
    if v <= 15 * 60 + 30:
        return "장중"
    return "장후"


def main():
    with open(os.path.join(SCRATCH, "ec_reaction.json"), encoding="utf-8") as f:
        reaction = json.load(f)
    with open(os.path.join(SCRATCH, "timing_raw.json"), encoding="utf-8") as f:
        timing_raw = json.load(f)
    with open(os.path.join(SCRATCH, "ec_final.json"), encoding="utf-8") as f:
        final = json.load(f)

    ec_timing = {}
    stats = {"장전": 0, "장중": 0, "장후": 0, "시각미상": 0}
    newly_observable = []
    still_pending = []
    flags_all = []

    for code, rec in reaction.items():
        name = rec["name"]
        reveal = rec["reveal_date"]
        t = timing_raw.get(code, {}).get("time")
        tclass = classify(t)
        stats[tclass] += 1

        out = {
            "name": name,
            "reveal_date": reveal,
            "reveal_kind": rec["reveal_kind"],
            "time": t,
            "timing_class": tclass,
            "reaction_date_v2": None,
            "reaction_ret": None,
            "reaction_gap": None,
            "reaction_relvol": None,
            "observable_v2": False,
            "flags": [],
        }
        ec_timing[code] = out

        spath = os.path.join(REPO, ".cache", "ohlcv", "series", f"{code}.json")
        with open(spath, encoding="utf-8") as f:
            s = json.load(f)
        dates, opens, closes, vols = s["dates"], s["opens"], s["closes"], s["volumes"]

        def day_metrics(i):
            if i <= 0 or i >= len(dates):
                return None, None, None
            pc = closes[i - 1]
            ret = (closes[i] / pc - 1) * 100 if pc else None
            gap = (opens[i] / pc - 1) * 100 if pc else None
            prior = vols[max(0, i - 50):i]
            mv = sum(prior) / len(prior) if prior else 0
            rv = vols[i] / mv if mv else None
            return ret, gap, rv

        eff = next((i for i, d in enumerate(dates) if d >= reveal), None)
        if eff is None:
            out["flags"].append("no_bar_on_or_after_reveal")
            continue

        if tclass == "시각미상":
            # keep prior mapping (next-day), flag
            out["flags"].append("timing_unknown_keep_prior")
            ri = eff + 1
        elif tclass in ("장전", "장중"):
            ri = eff
            if dates[eff] != reveal:
                out["flags"].append(f"reveal_nontrading_day_shifted_to_{dates[eff]}")
        else:  # 장후
            ri = eff + 1

        if ri < len(dates):
            out["observable_v2"] = True
            out["reaction_date_v2"] = dates[ri]
            r, g, rv = day_metrics(ri)
            out["reaction_ret"] = round(r, 3) if r is not None else None
            out["reaction_gap"] = round(g, 3) if g is not None else None
            out["reaction_relvol"] = round(rv, 3) if rv is not None else None
        else:
            out["reaction_date_v2"] = NEXT_TRADING_AFTER_LAST
            out["flags"].append("reaction_pending")

        if out["flags"]:
            flags_all.append((code, name, out["flags"]))

        # 8/14 filer bookkeeping
        if reveal == "2026-08-14":
            if out["observable_v2"] and not rec["observable"]:
                newly_observable.append((code, name, tclass))
            elif not out["observable_v2"]:
                still_pending.append((code, name, tclass))

    # sanity: same-day ret must equal ec_reaction sameday_ret_pct where both exist
    n_mismatch = 0
    for code, out in ec_timing.items():
        rec = reaction[code]
        if (out["timing_class"] in ("장전", "장중") and out["reaction_ret"] is not None
                and rec["sameday_ret_pct"] is not None
                and out["reaction_date_v2"] is not None and out["reaction_date_v2"] >= rec["reveal_date"]):
            if abs(out["reaction_ret"] - rec["sameday_ret_pct"]) > 0.02:
                n_mismatch += 1
                print(f"MISMATCH {code} {out['name']}: v2 {out['reaction_ret']} vs sameday {rec['sameday_ret_pct']}")
    print(f"sameday sanity mismatches: {n_mismatch}")

    with open(os.path.join(SCRATCH, "ec_timing.json"), "w", encoding="utf-8") as f:
        json.dump(ec_timing, f, ensure_ascii=False, indent=1)

    # ---- merge into ec_final_v2.json ----
    POS = {"서프라이즈", "호실적(YoY)"}
    NEG = {"쇼크", "부진(YoY)"}

    def concord(cls, ret, observable):
        if not observable or ret is None:
            return "—"
        if cls in POS:
            return "✓" if ret >= 8 else ("✗" if ret <= -8 else "·")
        if cls in NEG:
            return "✓" if ret <= -8 else ("✗" if ret >= 8 else "·")
        # 부합/무난: 조용한 반응이 정합
        return "✓" if abs(ret) < 8 else "✗"

    for row in final["rows"]:
        code = row["code"]
        tm = ec_timing.get(code)
        if not tm:
            continue
        row["timing"] = {
            "time": tm["time"],
            "timing_class": tm["timing_class"],
            "reaction_date_v2": tm["reaction_date_v2"],
            "reaction_ret": tm["reaction_ret"],
            "reaction_gap": tm["reaction_gap"],
            "reaction_relvol": tm["reaction_relvol"],
            "observable_v2": tm["observable_v2"],
            "flags": tm["flags"],
        }
        row["concord_v2"] = concord(row["classification"], tm["reaction_ret"], tm["observable_v2"])

    final["timing_note"] = ("발표시각 출처=KIND(상장공시시스템) 공시시각, 92/92 확보. "
                            "장전<09:00, 장중 09:00~15:30, 장후>15:30. "
                            "장전/장중 공시=당일 반응, 장후=다음 거래일 반응.")
    with open(os.path.join(SCRATCH, "ec_final_v2.json"), "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=1)

    print("timing stats:", stats)
    print(f"8/14 filers newly observable (장전/장중): {len(newly_observable)}")
    for c, n, t in newly_observable:
        print("  +", c, n, t)
    print(f"8/14 filers still pending (장후): {len(still_pending)}")
    for c, n, t in still_pending:
        print("  -", c, n, t)
    print("flagged:", flags_all)

    obs_v2 = sum(1 for v in ec_timing.values() if v["observable_v2"])
    print(f"observable_v2 total: {obs_v2}/92")


if __name__ == "__main__":
    main()
