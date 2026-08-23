import sys
from datetime import date
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from screen_earnings_calendar import estimate_next_earnings

# Scenario 1: last-year Q4 preliminary on 1/8, IR notice 2026-12-29, asof 12/29
f1 = [
    {"date": "2026-01-08", "title": "연결재무제표기준영업(잠정)실적(공정공시)"},
    {"date": "2026-12-29", "title": "기업설명회(IR) 개최"},
]
r1 = estimate_next_earnings(f1, date(2026, 12, 29))
print("S1:", r1)

# Scenario 2: annual report 3/20 filed, NDR-style IR 3/29, asof 3/30
f2 = [
    {"date": "2025-04-07", "title": "연결재무제표기준영업(잠정)실적(공정공시)"},
    {"date": "2025-05-15", "title": "분기보고서 (2025.03)"},
    {"date": "2026-03-20", "title": "사업보고서 (2025.12)"},
    {"date": "2026-03-29", "title": "기업설명회(IR) 개최"},
]
r2 = estimate_next_earnings(f2, date(2026, 3, 30))
print("S2:", r2)

# Boundary sweep: IR d days before season start (Q1 season starts 4/5)
for ir_day in range(26, 32):
    f = [
        {"date": "2025-04-07", "title": "연결재무제표기준영업(잠정)실적(공정공시)"},
        {"date": "2026-03-20", "title": "사업보고서 (2025.12)"},
        {"date": f"2026-03-{ir_day}", "title": "기업설명회(IR) 개최"},
    ]
    r = estimate_next_earnings(f, date(2026, 3, ir_day))
    print(f"IR 3/{ir_day}:", r["status"], r.get("expected"), r.get("basis"))
