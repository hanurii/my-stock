"""규칙 2 법정기한 클램프 → 과거 expected(d_day 음수) 재현 검증."""
import sys
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from datetime import date
from screen_earnings_calendar import estimate_next_earnings

# 시나리오 A: 작년 3Q 분기보고서를 기한(11/14) 뒤인 11/20에 제출한 회사
# + 올해 정상 이력(1월 잠정 포함 → 마스킹될 "유효한 다음 후보" 존재)
filings_a = [
    {"date": "2025-11-20", "title": "분기보고서 (2025.09)"},          # 기한 후 제출
    {"date": "2026-01-28", "title": "연결재무제표기준영업(잠정)실적(공정공시)"},
    {"date": "2026-03-20", "title": "사업보고서 (2025.12)"},
    {"date": "2026-05-12", "title": "분기보고서 (2026.03)"},
    {"date": "2026-08-12", "title": "반기보고서 (2026.06)"},
]

print("=== 시나리오 A: 분기보고서 기한 후 제출 패턴 ===")
for asof in ["2026-11-14", "2026-11-15", "2026-11-16", "2026-11-19", "2026-11-20"]:
    r = estimate_next_earnings(filings_a, asof)
    if r is None:
        print(f"asof {asof}: None")
        continue
    dropped = date.fromisoformat(r["window"][1]) < date.fromisoformat(asof)
    print(f"asof {asof}: expected={r['expected']} d_day={r['d_day']:+d} "
          f"window={r['window']} basis={r['basis']} "
          f"-> main() {'폐기(캘린더 실종)' if dropped else '수록'}")

# 시나리오 B: 잠정실적 2025-08-20 (반기 기한 8/14 뒤) + asof 2026-08-16
filings_b = [
    {"date": "2025-08-20", "title": "연결재무제표기준영업(잠정)실적(공정공시)"},
    {"date": "2025-11-10", "title": "분기보고서 (2025.09)"},
    {"date": "2026-03-20", "title": "사업보고서 (2025.12)"},
    {"date": "2026-05-12", "title": "분기보고서 (2026.03)"},
]
print("\n=== 시나리오 B: 잠정 8/20 패턴 + asof 8/16 ===")
for asof in ["2026-08-15", "2026-08-16", "2026-08-19", "2026-08-20"]:
    r = estimate_next_earnings(filings_b, asof)
    if r is None:
        print(f"asof {asof}: None")
        continue
    dropped = date.fromisoformat(r["window"][1]) < date.fromisoformat(asof)
    print(f"asof {asof}: expected={r['expected']} d_day={r['d_day']:+d} "
          f"window={r['window']} basis={r['basis']} "
          f"-> main() {'폐기(캘린더 실종)' if dropped else '수록'}")

# 대조: 죽은 후보를 손으로 제거하면 무엇이 나와야 했나 (마스킹 확인)
print("\n=== 대조: 시나리오 A에서 11/20 이벤트 제거 시 (마스킹된 후보 확인) ===")
r = estimate_next_earnings([f for f in filings_a if f["date"] != "2025-11-20"],
                           "2026-11-16")
print(r)
