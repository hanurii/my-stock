"""실적발표 캘린더 추정 로직 테스트 — screen_earnings_calendar.estimate_next_earnings.

픽스처: F&F(383220)·DN오토모티브(007340)는 실제 DART 공시 이력(2025-07 ~ 2026-08
조회분)을 그대로 옮긴 것. 신한지주(055550)·테스(095610) 등 나머지는 실제 이력의
요지 재구성(날짜 1~3일 단순화) — 검증 대상은 날짜 패턴 구조이지 개별 일자가 아님:
  - F&F: 분기마다 예고 → 잠정 → 정기보고서 3단 패턴이 규칙적
  - DN오토모티브: 예고 없이 잠정 → 정기보고서, 2026-08-10 IR개최 안내
  - 신한지주·테스: 반기보고서 제출 "뒤에" IR개최 안내 —
    사후 설명회(NDR)를 실적발표 예고로 오인하면 안 되는 케이스 (26-08-20 오탐 6건)
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from screen_earnings_calendar import (  # noqa: E402
    HORIZON_DAYS,
    classify_title,
    estimate_next_earnings,
)

YEGO = "결산실적공시예고(안내공시)"
JAMJEONG = "연결재무제표기준영업(잠정)실적(공정공시)"
IR = "기업설명회(IR)개최(안내공시)"


def _f(datestr: str, title: str) -> dict:
    return {"date": f"{datestr[:4]}-{datestr[4:6]}-{datestr[6:]}", "title": title}


# 실제 DART 공시 이력 (rcept_dt / report_nm)
FNF = [  # F&F 383220
    _f("20250723", YEGO),
    _f("20250731", JAMJEONG),
    _f("20250814", "반기보고서 (2025.06)"),
    _f("20251103", YEGO),
    _f("20251110", JAMJEONG),
    _f("20251114", "분기보고서 (2025.09)"),
    _f("20260128", YEGO),
    _f("20260210", JAMJEONG),
    _f("20260318", "사업보고서 (2025.12)"),
    _f("20260424", YEGO),
    _f("20260430", JAMJEONG),
    _f("20260515", "분기보고서 (2026.03)"),
    _f("20260723", YEGO),
    _f("20260731", JAMJEONG),
    _f("20260814", "반기보고서 (2026.06)"),
]

DN_AUTO = [  # DN오토모티브 007340
    _f("20250804", JAMJEONG),
    _f("20250814", "반기보고서 (2025.06)"),
    _f("20251105", JAMJEONG),
    _f("20251114", "분기보고서 (2025.09)"),
    _f("20260309", JAMJEONG),
    _f("20260312", "사업보고서 (2025.12)"),
    _f("20260515", "분기보고서 (2026.03)"),
    _f("20260810", IR),
    _f("20260814", "반기보고서 (2026.06)"),
    _f("20260814", IR),
]


# ── (1) F&F asof 7/28 → 7/23 예고 기반 confirmed, 작년 잠정 패턴 7/31 ──

def test_fnf_confirmed_via_yego():
    r = estimate_next_earnings(FNF, date(2026, 7, 28))
    assert r is not None
    assert r["status"] == "confirmed"
    assert r["expected"] == "2026-07-31"  # 작년 7/31 잠정 패턴이 예고 창 안
    assert r["d_day"] == 3
    assert r["window"][0] <= "2026-07-31" <= r["window"][1]
    assert "7/23" in r["basis"] and "결산실적공시예고" in r["basis"]
    # 마지막 실적 공시 = 1분기 분기보고서
    assert r["last_report"] == {"date": "2026-05-15", "title": "분기보고서 (2026.03)"}


# ── (2) DN오토 asof 8/12 → 8/10 IR (또는 estimated 반기) — expected는 8/14 근처 ──

def test_dnauto_ir_near_half_year_deadline():
    r = estimate_next_earnings(DN_AUTO, date(2026, 8, 12))
    assert r is not None
    # 시즌(반기) 미소진 + 작년 반기 8/14 패턴이 IR 창 안 → confirmed 유지되어야 함
    # (가드가 과잉 억제해 estimated 로 강등되면 회귀)
    assert r["status"] == "confirmed"
    assert "2026-08-13" <= r["expected"] <= "2026-08-15"  # 8/14 근처
    assert r["window"][0] <= "2026-08-14" <= r["window"][1]  # 창이 8/14 포함
    # as-of 안전: 8/14 반기보고서(미래)가 last_report 에 새면 안 됨
    assert r["last_report"] == {"date": "2026-05-15", "title": "분기보고서 (2026.03)"}


# ── (3) DN오토 asof 8/17 → 다음은 ~11/5 (작년 잠정 패턴), 14일 밖이어도 산출 ──

def test_dnauto_next_quarter_estimated():
    r = estimate_next_earnings(DN_AUTO, date(2026, 8, 17))
    assert r is not None
    assert r["status"] == "estimated"  # 8/10 IR 은 8/14 반기보고서로 소진됨
    assert "2026-11-01" <= r["expected"] <= "2026-11-14"
    assert r["expected"] == "2026-11-05"  # 작년 11/5 잠정 패턴
    assert "잠정" in r["basis"]
    assert r["d_day"] == 80
    assert r["d_day"] <= HORIZON_DAYS  # 수록 지평 안 (페이지 14일 컷과 별개)
    assert r["last_report"]["date"] == "2026-08-14"


# ── (4) F&F asof 8/17 → 다음은 11월 초 (작년 11/3 예고·11/10 잠정 패턴) ──

def test_fnf_next_quarter_early_november():
    r = estimate_next_earnings(FNF, date(2026, 8, 17))
    assert r is not None
    assert r["status"] == "estimated"
    assert "2026-11-01" <= r["expected"] <= "2026-11-14"
    assert r["last_report"] == {"date": "2026-08-14", "title": "반기보고서 (2026.06)"}


# ── (5) 공시 이력 없음 → None ──

def test_no_filing_history_returns_none():
    assert estimate_next_earnings([], date(2026, 8, 17)) is None
    # 실적과 무관한 공시만 있어도 None
    noise = [_f("20260701", "주식등의대량보유상황보고서(일반)")]
    assert estimate_next_earnings(noise, date(2026, 8, 17)) is None


# ── 보강: 예고 이후 잠정이 이미 나오면 confirmed 소멸 → 다음 이벤트 추정 ──

def test_yego_consumed_by_subsequent_jamjeong():
    # asof 8/3: 예고(7/23)는 21일 이내지만 잠정(7/31)이 이미 발표됨
    r = estimate_next_earnings(FNF, date(2026, 8, 3))
    assert r is not None
    assert r["status"] == "estimated"
    assert r["expected"] == "2026-08-14"  # 작년 반기보고서 8/14 패턴 (법정기한과 일치)
    assert "반기보고서" in r["basis"]


# ── 보강: 작년 잠정 패턴이 예고 창 밖이면 예고+8 폴백 ──

def test_yego_fallback_plus_8_without_pattern():
    filings = [
        _f("20250910", JAMJEONG),  # 작년 잠정이 9/10 — 예고 창 [7/24, 8/6] 밖
        _f("20260723", YEGO),
    ]
    r = estimate_next_earnings(filings, date(2026, 7, 28))
    assert r is not None
    assert r["status"] == "confirmed"
    assert r["expected"] == "2026-07-31"  # 예고일 7/23 + 8일
    assert r["window"] == ["2026-07-24", "2026-08-06"]


# ── 보강: 공시 폭주 대형주(조회 100건 컷)도 법정기한 폴백은 산출 ──

def test_truncated_history_falls_back_to_legal_deadline():
    # 삼성전자류: 공시가 많아 400일 조회창이 최근 몇 달로 잘림 —
    # 작년 Q3 잠정 패턴이 없어도 분기보고서 기한(11/14)으로 추정해야 함
    filings = [
        _f("20260730", JAMJEONG),
        _f("20260814", "반기보고서 (2026.06)"),
    ]
    r = estimate_next_earnings(filings, date(2026, 8, 17))
    assert r is not None
    assert r["status"] == "estimated"
    assert r["expected"] == "2026-11-16"  # 11/14(토) → 다음 영업일 연장
    assert "기한" in r["basis"] and "분기보고서" in r["basis"]


# ── 보강: 보고서 제출 "뒤" IR = 사후 설명회, 실적발표 예고 아님 ──

SHINHAN = [  # 신한지주 055550 요지 — 반기 8/14 제출 후 8/19 IR(NDR)
    _f("20251024", JAMJEONG),
    _f("20251114", "분기보고서 (2025.09)"),
    _f("20260205", JAMJEONG),
    _f("20260317", "사업보고서 (2025.12)"),
    _f("20260424", JAMJEONG),
    _f("20260515", "분기보고서 (2026.03)"),
    _f("20260725", JAMJEONG),
    _f("20260814", "반기보고서 (2026.06)"),
    _f("20260819", IR),
]


def test_post_report_ir_is_not_upcoming_earnings():
    # 반기 실적이 이미 나온 뒤(시즌 마감 8/14 직후)의 IR은 사후 설명회 —
    # confirmed 로 승격하면 안 되고 다음 분기(작년 10/24 잠정 패턴)로 넘어가야 함
    r = estimate_next_earnings(SHINHAN, date(2026, 8, 20))
    assert r is not None
    assert r["status"] == "estimated"
    assert r["expected"] == "2026-10-26"  # 작년 잠정 10/24 투영이 토요일 → 월요일로
    assert "잠정" in r["basis"]


def test_early_filer_report_then_ir_inside_season():
    # 테스 095610 요지 — 반기를 기한(8/14) 하루 전에 내고 다음날 IR.
    # IR 창이 반기 시즌 창과 겹쳐도 그 시즌 실적이 이미 나왔으면 예고 아님
    tes = [
        _f("20251113", "분기보고서 (2025.09)"),
        _f("20260316", "사업보고서 (2025.12)"),
        _f("20260514", "분기보고서 (2026.03)"),
        _f("20260813", "반기보고서 (2026.06)"),
        _f("20260814", IR),
    ]
    r = estimate_next_earnings(tes, date(2026, 8, 20))
    assert r is not None
    assert r["status"] == "estimated"
    assert r["expected"] == "2026-11-13"  # 작년 분기보고서 11/13 패턴


def test_conference_ir_without_own_pattern_not_confirmed():
    # 무잠정 회사의 여름 콘퍼런스/NDR 참가 IR — 반기 시즌이 미소진이라도
    # 자사 과거 발표일 패턴이 IR 창 안에 없으면 발표 예고 아님(IR+3 폴백 금지)
    filings = [
        _f("20250814", "반기보고서 (2025.06)"),
        _f("20251114", "분기보고서 (2025.09)"),
        _f("20260331", "사업보고서 (2025.12)"),
        _f("20260515", "분기보고서 (2026.03)"),
        _f("20260708", IR),  # 증권사 콘퍼런스 참가 안내
    ]
    r = estimate_next_earnings(filings, date(2026, 7, 9))
    assert r is not None
    assert r["status"] == "estimated"
    assert r["expected"] == "2026-08-14"  # 작년 반기보고서 8/14 패턴


def test_earnings_call_ir_after_jamjeong_not_reconfirmed():
    # 잠정실적 발표 → 며칠 뒤 어닝콜 IR: 시즌 실적이 이미 나왔으므로 예고 아님
    filings = [
        _f("20250725", JAMJEONG),
        _f("20250814", "반기보고서 (2025.06)"),
        _f("20260724", JAMJEONG),
        _f("20260728", IR),
    ]
    r = estimate_next_earnings(filings, date(2026, 7, 29))
    assert r is not None
    assert r["status"] == "estimated"
    assert r["expected"] == "2026-08-14"  # 다음 이벤트 = 반기보고서


def test_year_boundary_ir_heralds_january_season():
    # 연말 IR → 이듬해 1월 4Q 시즌: _season_spans 2개년 처리 + 작년 1월 잠정 투영
    filings = [
        _f("20260105", JAMJEONG),  # 작년 4Q 잠정 1/5
        _f("20260330", "사업보고서 (2025.12)"),
        _f("20260515", "분기보고서 (2026.03)"),
        _f("20260813", "반기보고서 (2026.06)"),
        _f("20261113", "분기보고서 (2026.09)"),
        _f("20261231", IR),
    ]
    r = estimate_next_earnings(filings, date(2027, 1, 2))
    assert r is not None
    assert r["status"] == "confirmed"
    assert r["expected"] == "2027-01-05"  # 작년 잠정 1/5 패턴이 IR 창 안


def test_deadline_weekend_rollforward():
    # 2026-11-14(토) → 실제 3Q 분기보고서 기한은 11/16(월).
    # 기한 당일(asof=11/16)에도 살아 있어야 발표 당일 매수 경고가 유지됨
    filings = [
        _f("20260730", JAMJEONG),
        _f("20260814", "반기보고서 (2026.06)"),
    ]
    r = estimate_next_earnings(filings, date(2026, 11, 16))
    assert r is not None
    assert r["status"] == "estimated"
    assert r["expected"] == "2026-11-16"
    assert r["d_day"] == 0
    assert "기한" in r["basis"]


def test_ir_after_annual_report_still_heralds_q1():
    # 3~4월 코너 핀 고정: 사업보고서(연간) 직후라도 1분기 잠정 시즌(4/5~)과
    # 겹치는 IR은 진짜 발표 예고 — 사후 설명회 가드가 과잉 억제하면 안 됨
    filings = [
        _f("20250407", JAMJEONG),  # 작년 1분기 잠정 4/7
        _f("20250515", "분기보고서 (2025.03)"),
        _f("20260320", "사업보고서 (2025.12)"),
        _f("20260401", IR),
    ]
    r = estimate_next_earnings(filings, date(2026, 4, 2))
    assert r is not None
    assert r["status"] == "confirmed"
    assert r["expected"] == "2026-04-07"  # 작년 잠정 4/7 패턴이 IR 창 안
    assert "IR" in r["basis"]


# ── 보강: 제목 분류 ──

def test_classify_title():
    assert classify_title(YEGO) == "예고"
    assert classify_title(JAMJEONG) == "잠정실적"
    assert classify_title("영업(잠정)실적(공정공시)") == "잠정실적"
    assert classify_title(IR) == "IR"
    assert classify_title("분기보고서 (2026.03)") == "분기보고서"
    assert classify_title("반기보고서 (2026.06)") == "반기보고서"
    assert classify_title("사업보고서 (2025.12)") == "사업보고서"
    assert classify_title("[기재정정]분기보고서 (2026.03)") is None  # 정정 재제출 무시
    assert classify_title("주요사항보고서(유상증자결정)") is None
