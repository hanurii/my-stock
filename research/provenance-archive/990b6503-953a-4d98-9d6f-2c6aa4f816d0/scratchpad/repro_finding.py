import sys
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from screen_earnings_calendar import estimate_next_earnings

def show(label, filings, asof):
    r = estimate_next_earnings(filings, asof)
    print(f"--- {label} (asof {asof})")
    if r is None:
        print("    None")
    else:
        print(f"    status={r['status']} expected={r['expected']} window={r['window']} d_day={r['d_day']} basis={r['basis']}")

# ① IR 8/14, 반기보고서 미제출, asof 8/14 (작년 이력만 있어 패턴 미스 가정)
f1 = [
    {"date": "2025-05-15", "title": "분기보고서 (2025.03)"},
    {"date": "2025-08-30", "title": "반기보고서 (2025.06)"},  # 작년 반기: 투영 8/30은 win[8/14,8/21] 밖 -> 미스
    {"date": "2026-05-15", "title": "분기보고서 (2026.03)"},
    {"date": "2026-08-14", "title": "기업설명회(IR) 개최 안내"},
]
show("① IR 8/14 반기 미제출", f1, "2026-08-14")
# 반기 법정기한 = 8/14. expected 가 8/14 를 넘으면 '불가능일'.

# ①-b 더 현실적: IR 8/12, asof 8/13
f1b = [
    {"date": "2025-05-15", "title": "분기보고서 (2025.03)"},
    {"date": "2025-08-30", "title": "반기보고서 (2025.06)"},
    {"date": "2026-05-15", "title": "분기보고서 (2026.03)"},
    {"date": "2026-08-12", "title": "기업설명회(IR) 개최 안내"},
]
show("①b IR 8/12 반기 미제출", f1b, "2026-08-13")

# ② IR 9/30, asof 10/1 — 3Q 시즌 [10/5, 11/14] 와 창 [9/30,10/7] 겹침
f2 = [
    {"date": "2025-11-14", "title": "분기보고서 (2025.09)"},  # 투영 11/14 은 win 밖 -> 패턴 미스
    {"date": "2026-08-14", "title": "반기보고서 (2026.06)"},
    {"date": "2026-09-30", "title": "기업설명회(IR) 개최 안내"},
]
show("② IR 9/30", f2, "2026-10-01")
# 시즌 최속일 10/5 이전 expected 면 '불가능일'.

# ③ IR 12/30 — 창 [12/30, 1/6] 이 내년 1월 시즌 [1/5, 3/31] 과 겹침
f3 = [
    {"date": "2026-03-20", "title": "사업보고서 (2025.12)"},
    {"date": "2026-08-14", "title": "반기보고서 (2026.06)"},
    {"date": "2026-11-13", "title": "분기보고서 (2026.09)"},
    {"date": "2026-12-30", "title": "기업설명회(IR) 개최 안내"},
]
show("③ IR 12/30", f3, "2026-12-30")
# 시즌 최속일 1/5 이전 expected 면 '불가능일'.

# 패턴 히트 경로도 시즌 경계 밖으로 나올 수 있는지: 작년 잠정 8/18 -> win [8/14,8/21] 안 -> expected 8/18 (> 기한 8/14)
f4 = [
    {"date": "2025-08-18", "title": "연결재무제표기준영업(잠정)실적(공정공시)"},  # 작년엔 잠정이 기한 뒤? (드묾) — 히트 경로 확인용
    {"date": "2026-05-15", "title": "분기보고서 (2026.03)"},
    {"date": "2026-08-13", "title": "기업설명회(IR) 개최 안내"},
]
show("④ 패턴히트 8/18 (참고)", f4, "2026-08-14")
