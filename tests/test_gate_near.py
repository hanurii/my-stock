"""관문 임박(gate_near) 판정 테스트 — screen_trend_template._gate_near_reasons.

실증 근거: 깊은 베이스 VCP가 돌파 전날까지 관문에 걸리는 구조적 충돌
(메가터치·한양이엔지 26-08-07 미스, 네오오토 26-08-14 +20.2% 미스).
⑦(52주고가) 허용 한도 변천: 26-08-11 -40% 허용 → 26-08-12 필수 환원
→ 26-08-17 -35% 재완화 → **26-08-21 필수 환원(사용자 결정)**.
재환원 근거: 완화 관문 종목 실전 7건 0승(청산 4건 -413만원), 8/18 손절 6종목이
전부 52주고가 -12~-35% 딥베이스인 반면 승자는 전부 -4% 이내.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from screen_trend_template import GATE_NEAR_TOL, _gate_near_reasons  # noqa: E402


def _result(fails, extras, passed_count=None, all_pass=False):
    criteria = {str(i): {"pass": str(i) not in fails} for i in range(1, 9)}
    return {
        "pass": all_pass,
        "passed_count": passed_count if passed_count is not None else 8 - len(fails),
        "criteria": criteria,
        "extras": extras,
    }


# ── ⑦ 52주고가는 완화 대상이 아님(필수 통과) ────────────────────────────────

def test_high52w_fail_is_never_gate_near():
    # -30%: 한때 -35% 한도로 허용했으나 26-08-21 환원 → 이제는 임박 아님
    r = _result({"7"}, {"high_52w": 10_000})
    assert _gate_near_reasons(r, 7_000) is None


def test_high52w_slightly_outside_25pct_is_not_gate_near():
    # -26%: 미너비니 기준(-25%)을 조금만 벗어나도 제외 — 완화 폭 자체가 없다
    r = _result({"7"}, {"high_52w": 10_000})
    assert _gate_near_reasons(r, 7_400) is None


def test_neoauto_2026_08_13_case_now_excluded():
    # 실사례: 네오오토 8/13 (-34.1%) — 완화 시절엔 포착됐으나 환원 후 미포착(감수한 트레이드오프)
    r = _result({"7"}, {"high_52w": 15_570.26})
    assert _gate_near_reasons(r, 10_260.0) is None


def test_megatouch_2026_08_07_case_now_excluded():
    # 실사례: 메가터치 8/7 (-32.3%) — 8/18 매수 후 -10.1% 손절난 종목. 환원 후 미포착.
    r = _result({"7"}, {"high_52w": 9_900})
    assert _gate_near_reasons(r, 9_900 * 0.677) is None


def test_combined_5_and_7_is_not_gate_near():
    # ⑤는 한도 이내여도 ⑦이 섞이면 전체 탈락
    r = _result({"5", "7"}, {"sma50": 10_000, "high_52w": 13_000})
    assert _gate_near_reasons(r, 9_000) is None


# ── ①⑤ 이평선 근접만 완화 대상 ──────────────────────────────────────────────

def test_ma50_only_within_15pct_is_gate_near():
    r = _result({"5"}, {"sma50": 10_000})
    assert _gate_near_reasons(r, 9_000) == ["⑤ 50일선 -10.0%"]


def test_ma50_beyond_15pct_is_not_gate_near():
    # 한도 없으면 이평선 한참 아래 폭락주도 '임박'이 되는 오탐(적대 검증 26-08-11)
    r = _result({"5"}, {"sma50": 10_000})
    assert _gate_near_reasons(r, 8_400) is None


def test_ma50_exact_boundary_is_gate_near():
    r = _result({"5"}, {"sma50": 10_000})
    assert _gate_near_reasons(r, 8_500) == ["⑤ 50일선 -15.0%"]


def test_hanyang_eng_2026_08_07_case():
    # 실사례: 한양이엔지 8/7 — ①150일선 -0.12%·⑤50일선 -2.3%만 미달(코일 밑바닥)
    r = _result({"1", "5"}, {"sma150": 10_000, "sma200": 9_500, "sma50": 10_230})
    assert _gate_near_reasons(r, 9_988) == ["① 150·200일선 -0.1%", "⑤ 50일선 -2.4%"]


def test_ma150_200_beyond_10pct_is_not_gate_near():
    r = _result({"1"}, {"sma150": 10_000, "sma200": 10_000})
    assert _gate_near_reasons(r, 8_900) is None


def test_ma_missing_extras_is_not_gate_near():
    r = _result({"5"}, {})
    assert _gate_near_reasons(r, 9_000) is None


# ── 공통 가드 ────────────────────────────────────────────────────────────────

def test_non_relaxable_criterion_fails():
    # ②(150MA>200MA)는 완화 불가 → None
    r = _result({"2", "5"}, {"sma50": 10_000})
    assert _gate_near_reasons(r, 9_000) is None


def test_all_pass_returns_none():
    r = _result(set(), {"high_52w": 10_000}, all_pass=True)
    assert _gate_near_reasons(r, 9_000) is None


def test_too_many_fails_returns_none():
    r = _result({"1", "5", "7"}, {"sma150": 9_100, "sma200": 9_000,
                                  "sma50": 9_500, "high_52w": 10_000},
                passed_count=5)
    assert _gate_near_reasons(r, 9_000) is None


def test_no_close_returns_none():
    r = _result({"5"}, {"sma50": 10_000})
    assert _gate_near_reasons(r, None) is None


def test_tol_constants():
    # 한도 정본: ① -10% · ⑤ -15% (⑦은 완화 대상 아님 — 키 자체가 없어야 한다)
    assert GATE_NEAR_TOL == {"ma150_200": 0.90, "ma50": 0.85}
