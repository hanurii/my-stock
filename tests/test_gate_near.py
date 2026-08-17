"""관문 임박(gate_near) 판정 테스트 — screen_trend_template._gate_near_reasons.

실증 근거: 깊은 베이스 VCP가 돌파 전날까지 관문에 걸리는 구조적 충돌
(메가터치·한양이엔지 26-08-07 미스, 네오오토 26-08-14 +20.2% 미스).
⑦(52주고가) 허용 한도 변천: 26-08-11 -40% 허용 → 26-08-12 필수 환원
→ 26-08-17 -35% 재완화(사용자 결정, 네오오토 3번째 사례 계기).
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


# ── ⑦ 52주고가 완화(-35% 이내) ──────────────────────────────────────────────

def test_high52w_only_within_35pct_is_gate_near():
    # -30%: 한도(-35%) 이내 → 임박 + 사유
    r = _result({"7"}, {"high_52w": 10_000})
    assert _gate_near_reasons(r, 7_000) == ["⑦ 52주고가 -30.0%"]


def test_high52w_beyond_35pct_is_not_gate_near():
    # -36%: 한도 밖 → 제외 (한도 없으면 폭락주 오탐 — -40% 시절 40종목 유입 사고)
    r = _result({"7"}, {"high_52w": 10_000})
    assert _gate_near_reasons(r, 6_400) is None


def test_high52w_exact_boundary_is_gate_near():
    # 정확히 -35% (close == high*0.65) 는 이내로 인정
    r = _result({"7"}, {"high_52w": 10_000})
    assert _gate_near_reasons(r, 6_500) == ["⑦ 52주고가 -35.0%"]


def test_high52w_missing_extras_is_not_gate_near():
    r = _result({"7"}, {})
    assert _gate_near_reasons(r, 7_000) is None


def test_neoauto_2026_08_13_case():
    # 실사례: 네오오토 8/13 밤 — 종가 10,260 vs 52주고가 15,570.26 (-34.1%), ⑦만 탈락
    r = _result({"7"}, {"high_52w": 15_570.26})
    assert _gate_near_reasons(r, 10_260.0) == ["⑦ 52주고가 -34.1%"]


def test_megatouch_2026_08_07_case():
    # 실사례: 메가터치 8/7 — ⑦만 탈락 -32.3%
    r = _result({"7"}, {"high_52w": 9_900})
    reasons = _gate_near_reasons(r, 9_900 * 0.677)
    assert reasons == ["⑦ 52주고가 -32.3%"]


# ── 기존 ①⑤ 동작 보존 + 조합 ────────────────────────────────────────────────

def test_ma_only_still_gate_near():
    r = _result({"5"}, {"sma50": 10_000})
    assert _gate_near_reasons(r, 9_000) == ["⑤ 50일선 -10.0%"]


def test_combined_5_and_7_within_limits():
    r = _result({"5", "7"}, {"sma50": 10_000, "high_52w": 13_000})
    assert _gate_near_reasons(r, 9_000) == ["⑤ 50일선 -10.0%", "⑦ 52주고가 -30.8%"]


def test_combined_7_ok_but_5_beyond_limit():
    # 하나라도 근접 한도 밖이면 전체 탈락
    r = _result({"5", "7"}, {"sma50": 12_000, "high_52w": 13_000})
    assert _gate_near_reasons(r, 9_000) is None


def test_non_relaxable_criterion_fails():
    # ⑦+② 탈락: ②는 완화 불가 → None
    r = _result({"2", "7"}, {"high_52w": 10_000})
    assert _gate_near_reasons(r, 7_000) is None


def test_all_pass_returns_none():
    r = _result(set(), {"high_52w": 10_000}, all_pass=True)
    assert _gate_near_reasons(r, 9_000) is None


def test_too_many_fails_returns_none():
    r = _result({"1", "5", "7"}, {"sma150": 9_100, "sma200": 9_000,
                                  "sma50": 9_500, "high_52w": 10_000},
                passed_count=5)
    assert _gate_near_reasons(r, 9_000) is None


def test_tol_constants():
    # 한도 정본: ① -10% · ⑤ -15% · ⑦ -35%
    assert GATE_NEAR_TOL == {"ma150_200": 0.90, "ma50": 0.85, "high52w": 0.65}
