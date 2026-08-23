# -*- coding: utf-8 -*-
"""Reproduce the test-lens finding about test_dnauto_ir_near_half_year_deadline."""
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(r"C:\Users\hanul\playground\my-stock")
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from test_earnings_calendar import DN_AUTO, IR  # noqa: E402
import screen_earnings_calendar as m  # noqa: E402

# (1) Current behavior asof 8/12
r = m.estimate_next_earnings(DN_AUTO, date(2026, 8, 12))
print("CURRENT asof 8/12:", r["status"], r["expected"], r["window"], "|", r["basis"])

# (2) Simulate guard over-suppression: IR rejected -> falls through to rule 2.
#     Equivalent to removing the IR filing (rule 1b is the only IR consumer).
dn_no_ir = [f for f in DN_AUTO if f["title"] != IR]
r2 = m.estimate_next_earnings(dn_no_ir, date(2026, 8, 12))
print("SUPPRESSED-GUARD asof 8/12:", r2["status"], r2["expected"], r2["window"], "|", r2["basis"])

# Would the existing test's assertions pass on the suppressed result?
checks = [
    r2 is not None,
    r2["status"] in ("confirmed", "estimated"),
    "2026-08-13" <= r2["expected"] <= "2026-08-15",
    r2["window"][0] <= "2026-08-14" <= r2["window"][1],
    r2["last_report"] == {"date": "2026-05-15", "title": "분기보고서 (2026.03)"},
]
print("existing-test assertions on suppressed result:", checks, "ALL PASS" if all(checks) else "FAIL")

# (3) Simulate the hypothesized bad tightening in-place:
#     heralds requires season window end >= IR + 7 (i.e., IR window fully inside season).
src_path = ROOT / "scripts" / "screen_earnings_calendar.py"
src = src_path.read_text(encoding="utf-8")
old = "            not (s > win[1] or e < win[0])                    # IR 창과 시즌 창이 겹치고\n"
new = "            not (s > win[1] or e < win[0]) and e >= win[1]     # BAD TIGHTENING\n"
assert old in src, "guard line not found"
bad_src = src.replace(old, new)

import types
bad = types.ModuleType("bad_mod")
bad.__dict__["__file__"] = str(src_path)
exec(compile(bad_src, str(src_path), "exec"), bad.__dict__)

rb = bad.estimate_next_earnings(DN_AUTO, date(2026, 8, 12))
print("BAD-GUARD DN asof 8/12:", rb["status"], rb["expected"], rb["window"], "|", rb["basis"])

# April corner-pin test under the bad guard
def _f(datestr, title):
    return {"date": f"{datestr[:4]}-{datestr[4:6]}-{datestr[6:]}", "title": title}

JAMJEONG = "연결재무제표기준영업(잠정)실적(공정공시)"
april = [
    _f("20250407", JAMJEONG),
    _f("20250515", "분기보고서 (2025.03)"),
    _f("20260320", "사업보고서 (2025.12)"),
    _f("20260401", IR),
]
ra = bad.estimate_next_earnings(april, date(2026, 4, 2))
print("BAD-GUARD April asof 4/2:", ra["status"], ra["expected"], "|", ra["basis"])
april_ok = ra["status"] == "confirmed" and ra["expected"] == "2026-04-07" and "IR" in ra["basis"]
print("April corner-pin still green under bad guard:", april_ok)

# And the DN test assertions under the bad guard:
checks_bad = [
    rb is not None,
    rb["status"] in ("confirmed", "estimated"),
    "2026-08-13" <= rb["expected"] <= "2026-08-15",
    rb["window"][0] <= "2026-08-14" <= rb["window"][1],
    rb["last_report"] == {"date": "2026-05-15", "title": "분기보고서 (2026.03)"},
]
print("DN test assertions under bad guard:", checks_bad, "ALL PASS" if all(checks_bad) else "FAIL")
print("regression visible? status changed:", r["status"], "->", rb["status"])
