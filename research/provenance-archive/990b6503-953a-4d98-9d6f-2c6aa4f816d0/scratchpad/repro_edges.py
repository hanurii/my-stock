# -*- coding: utf-8 -*-
"""Edge reproductions for estimate_next_earnings after the 1b season-guard fix."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(r"C:\Users\hanul\playground\my-stock\scripts")))
from screen_earnings_calendar import estimate_next_earnings

JAM = "연결재무제표기준영업(잠정)실적(공정공시)"
IR = "기업설명회(IR)개최(안내공시)"


def f(d, t):
    return {"date": d, "title": t}


print("== A. deadline-clamped projection makes exp <= asof and shadows later candidates ==")
# Company filed H1 잠정 late last year (8/20). This year hasn't filed yet.
# asof 8/16: projection c=2026-08-20 > asof, but deadline clamp -> exp = 2026-08-14 (past!).
filings_a = [
    f("2025-08-20", JAM),
    f("2025-11-05", JAM),
    f("2025-11-14", "분기보고서 (2025.09)"),
    f("2026-03-20", "사업보고서 (2025.12)"),
    f("2026-05-14", "분기보고서 (2026.03)"),
]
r = estimate_next_earnings(filings_a, date(2026, 8, 16))
print("asof 2026-08-16 ->", r)

print()
print("== B. zero earnings history + in-season IR (e.g., fresh IPO stock) ==")
filings_b = [f("2026-10-10", IR)]
r = estimate_next_earnings(filings_b, date(2026, 10, 12))
print("asof 2026-10-12 ->", r)

print()
print("== C. late-December IR ahead of Q4 season: boundary of overlap ==")
for ird in ("2026-12-28", "2026-12-29", "2026-12-31"):
    filings_c = [
        f("2026-01-08", JAM),  # last year's Q4 preliminary pattern
        f("2026-03-20", "사업보고서 (2025.12)"),
        f("2026-08-14", "반기보고서 (2026.06)"),
        f("2026-11-13", "분기보고서 (2026.09)"),
        f(ird, IR),
    ]
    r = estimate_next_earnings(filings_c, date.fromisoformat(ird))
    print(f"IR {ird} ->", (r or {}).get("status"), (r or {}).get("expected"), (r or {}).get("basis"))

print()
print("== D. post-annual-report NDR on 3/29 grazes Q1 span start (4/5) ==")
filings_d = [
    f("2025-04-07", JAM),
    f("2025-05-15", "분기보고서 (2025.03)"),
    f("2026-03-20", "사업보고서 (2025.12)"),
    f("2026-03-29", IR),
]
r = estimate_next_earnings(filings_d, date(2026, 3, 30))
print("asof 2026-03-30 ->", r)

print()
print("== E. late filer: report AFTER season end but AFTER the IR -> exhaustion check ==")
filings_e = [
    f("2025-08-04", JAM),
    f("2025-11-14", "분기보고서 (2025.09)"),
    f("2026-03-12", "사업보고서 (2025.12)"),
    f("2026-05-15", "분기보고서 (2026.03)"),
    f("2026-08-12", IR),
    f("2026-08-16", "반기보고서 (2026.06)"),  # filed late, outside season span, after IR
]
r = estimate_next_earnings(filings_e, date(2026, 8, 18))
print("asof 2026-08-18 ->", (r or {}).get("status"), (r or {}).get("expected"), (r or {}).get("basis"))

print()
print("== F. event just BEFORE span start (+5 anchor) then in-season IR ==")
filings_f = [
    f("2025-07-04", JAM),  # last year: preliminary on 7/4 (before span start 7/5)
    f("2025-08-14", "반기보고서 (2025.06)"),
    f("2026-03-20", "사업보고서 (2025.12)"),
    f("2026-05-15", "분기보고서 (2026.03)"),
    f("2026-07-04", JAM),  # this year again 7/4 -- season span [7/5, 8/14] looks 'empty'
    f("2026-07-10", IR),   # post-earnings NDR 6 days after preliminary
]
r = estimate_next_earnings(filings_f, date(2026, 7, 11))
print("asof 2026-07-11 ->", (r or {}).get("status"), (r or {}).get("expected"), (r or {}).get("basis"))
