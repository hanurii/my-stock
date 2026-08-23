import sys
from datetime import date
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from screen_earnings_calendar import estimate_next_earnings

JAM = "연결재무제표기준영업(잠정)실적(공정공시)"
IR = "기업설명회(IR)개최(안내공시)"

# 작년 잠정 1/8 이력 + IR 2026-12-30, asof 2026-12-31
filings = [
    {"date": "2026-01-08", "title": JAM},
    {"date": "2026-03-20", "title": "사업보고서 (2025.12)"},
    {"date": "2026-12-30", "title": IR},
]
r = estimate_next_earnings(filings, date(2026, 12, 31))
print("CURRENT CODE:", r["status"], r["expected"], r["window"], "|", r["basis"])
