# -*- coding: utf-8 -*-
"""Build ec_reaction.json: H1-results reveal date + market reaction per code."""
import json, subprocess, sys, os

SCRATCH = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad"
REPO = r"C:\Users\hanul\playground\my-stock"

# 1. Target codes from HEAD version of earnings calendar
raw = subprocess.run(
    ["git", "show", "HEAD:public/data/sepa-earnings-calendar.json"],
    cwd=REPO, capture_output=True, check=True
).stdout.decode("utf-8")
cal = json.loads(raw)
by_code = cal["byCode"]
codes = list(by_code.keys())

WIN_LO, WIN_HI = "2026-07-01", "2026-08-17"
LAST_BAR = "2026-08-14"

out = {}
issues = []
n_obs = n_notyet = 0

for code in codes:
    name = by_code[code].get("name")
    rec = {
        "name": name, "reveal_date": None, "reveal_kind": None,
        "observable": False, "reaction_date": None,
        "day_ret_pct": None, "gap_pct": None, "relvol": None,
        "sameday_ret_pct": None,
    }
    out[code] = rec

    # --- reveal date from cached filing list ---
    cpath = os.path.join(REPO, ".cache", "earnings_calendar", f"{code}.json")
    if not os.path.exists(cpath):
        issues.append(f"{code} {name}: no earnings_calendar cache")
        continue
    with open(cpath, encoding="utf-8") as f:
        filings = json.load(f).get("filings", [])

    in_win = [fl for fl in filings if WIN_LO <= fl["date"] <= WIN_HI]
    prelim = sorted(fl["date"] for fl in in_win if "영업(잠정)실적" in fl["title"])
    if prelim:
        rec["reveal_date"] = prelim[0]
        rec["reveal_kind"] = "잠정"
    else:
        half = sorted(fl["date"] for fl in in_win if "반기보고서" in fl["title"])
        if half:
            rec["reveal_date"] = half[0]
            rec["reveal_kind"] = "반기보고서"
        else:
            issues.append(f"{code} {name}: no reveal filing in window")
            continue

    reveal = rec["reveal_date"]

    # --- price series ---
    spath = os.path.join(REPO, ".cache", "ohlcv", "series", f"{code}.json")
    if not os.path.exists(spath):
        issues.append(f"{code} {name}: no ohlcv series")
        continue
    with open(spath, encoding="utf-8") as f:
        s = json.load(f)
    dates, opens, closes, vols = s["dates"], s["opens"], s["closes"], s["volumes"]

    def day_metrics(i):
        """(day_ret_pct, gap_pct, relvol) for bar index i vs prev close & prior-50 vol."""
        if i <= 0 or i >= len(dates):
            return None, None, None
        pc = closes[i - 1]
        ret = (closes[i] / pc - 1) * 100 if pc else None
        gap = (opens[i] / pc - 1) * 100 if pc else None
        prior = vols[max(0, i - 50):i]
        mv = sum(prior) / len(prior) if prior else 0
        rv = vols[i] / mv if mv else None
        return ret, gap, rv

    # effective reveal trading day = first bar with date >= reveal
    eff = next((i for i, d in enumerate(dates) if d >= reveal), None)

    if eff is not None and dates[eff] != reveal and reveal <= LAST_BAR:
        # reveal fell on a non-trading day; effective day is next trading day
        pass

    # same-day figures (on effective reveal trading day, if data exists)
    if eff is not None:
        sd_ret, sd_gap, sd_rv = day_metrics(eff)
        rec["sameday_ret_pct"] = round(sd_ret, 3) if sd_ret is not None else None
    else:
        sd_ret = sd_gap = sd_rv = None
        issues.append(f"{code} {name}: reveal {reveal} after last bar {dates[-1]}")

    eff_date = dates[eff] if eff is not None else None

    if eff_date is not None and eff_date < LAST_BAR:
        # reaction day = first trading day after effective reveal day
        ri = eff + 1
        if ri < len(dates):
            rec["observable"] = True
            rec["reaction_date"] = dates[ri]
            r, g, rv = day_metrics(ri)
            rec["day_ret_pct"] = round(r, 3) if r is not None else None
            rec["gap_pct"] = round(g, 3) if g is not None else None
            rec["relvol"] = round(rv, 3) if rv is not None else None
        else:
            issues.append(f"{code} {name}: no bar after eff reveal {eff_date}")
    elif eff_date == LAST_BAR:
        # 8/14 filer: reaction day 8/18 not yet arrived — record 8/14 same-day figures
        rec["observable"] = False
        rec["reaction_date"] = None
        rec["day_ret_pct"] = round(sd_ret, 3) if sd_ret is not None else None
        rec["gap_pct"] = round(sd_gap, 3) if sd_gap is not None else None
        rec["relvol"] = round(sd_rv, 3) if sd_rv is not None else None

    if rec["observable"]:
        n_obs += 1
    elif rec["reveal_date"]:
        n_notyet += 1

with open(os.path.join(SCRATCH, "ec_reaction.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

# summary (cp949-safe-ish: keep to ascii + korean via stdout utf8 reconfig)
sys.stdout.reconfigure(encoding="utf-8")
kinds = {}
for c, r in out.items():
    kinds[r["reveal_kind"]] = kinds.get(r["reveal_kind"], 0) + 1
print(f"total={len(out)} observable={n_obs} not_yet={n_notyet} kinds={kinds}")
rd = {}
for c, r in out.items():
    if r["reveal_date"]:
        rd[r["reveal_date"]] = rd.get(r["reveal_date"], 0) + 1
print("reveal date histogram:", dict(sorted(rd.items())))
print("issues:", len(issues))
for m in issues:
    print(" -", m)
