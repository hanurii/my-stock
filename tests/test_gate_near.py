"""관문 임박(gate_near) 판정 테스트 — screen_trend_template._gate_near_reasons.

**현재 상태: 완화 전면 중단(26-08-21, 사용자 결정) — 미너비니 8조건 전부 필수.**

변천사:
- 26-08-11 도입: ①150·200MA·⑤50MA 근접 + ⑦52주고가 -40%까지 허용.
  계기 = 딥베이스 VCP가 돌파 전날 관문에 걸려 "이미 오른 뒤 등장"하는 구조적 충돌
  (메가터치·한양이엔지 26-08-07 미스, 네오오토 26-08-14 +20.2% 미스).
- 26-08-12 ⑦ 필수 환원(-40%는 40종목 유입) → 26-08-17 ⑦ -35% 재완화
- 26-08-21 ⑦ 필수 환원: 완화 종목 실전 7건 0승(청산 4건 -413만원), 8/18 손절
  6종목 전원이 52주고가 -12~-35% 딥베이스인 반면 승자는 전부 -4% 이내.
- 26-08-21 ①⑤ 완화도 중단(GATE_NEAR_ENABLED=False): "좋은 주식을 놓치는 것보다
  손실을 막는 게 우선". 한양이엔지형(이평선 바로 밑 코일) 미포착은 감수한다.

기계(GATE_NEAR_TOL·_gate_near_reasons)는 남겨두되 스위치만 끈다 — ⑦ 한도가 네 번
뒤집힌 이력이 있어 되살릴 수 있게. 되살릴 때는 GATE_NEAR_ENABLED 만 True 로.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from screen_trend_template import (  # noqa: E402
    GATE_NEAR_ENABLED,
    GATE_NEAR_TOL,
    _gate_near_reasons,
)


def _result(fails, extras, passed_count=None, all_pass=False):
    criteria = {str(i): {"pass": str(i) not in fails} for i in range(1, 9)}
    return {
        "pass": all_pass,
        "passed_count": passed_count if passed_count is not None else 8 - len(fails),
        "criteria": criteria,
        "extras": extras,
    }


# ── 스위치가 꺼져 있다 ───────────────────────────────────────────────────────

def test_gate_near_switch_is_off():
    assert GATE_NEAR_ENABLED is False


def test_preserved_tolerances_are_unchanged():
    """되살릴 때 쓸 한도값은 보존한다(①150·200MA -10% · ⑤50MA -15%).

    ⑦(52주고가)은 26-08-21 환원으로 키 자체가 없다 — 되살려도 ⑦은 완화 대상 아님.
    """
    assert GATE_NEAR_TOL == {"ma150_200": 0.90, "ma50": 0.85}


# ── 어떤 근접도 임박이 되지 않는다 ───────────────────────────────────────────

def test_ma50_near_miss_is_not_gate_near():
    # 완화 시절엔 "⑤ 50일선 -10.0%"로 통과했다
    r = _result({"5"}, {"sma50": 10_000})
    assert _gate_near_reasons(r, 9_000) is None


def test_ma150_200_near_miss_is_not_gate_near():
    r = _result({"1"}, {"sma150": 10_000, "sma200": 10_000})
    assert _gate_near_reasons(r, 9_990) is None


def test_hanyang_eng_2026_08_07_case_now_excluded():
    """실사례: 한양이엔지 8/7 — ①150일선 -0.12%·⑤50일선 -2.3%만 미달.

    완화 도입의 계기였던 종목. 완화 폐지로 이제 미포착 — 감수한 트레이드오프.
    """
    r = _result({"1", "5"}, {"sma150": 10_000, "sma200": 9_500, "sma50": 10_230})
    assert _gate_near_reasons(r, 9_988) is None


def test_high52w_fail_is_not_gate_near():
    # 네오오토 8/13 (-34.1%) · 메가터치 8/7 (-32.3%) 계열 — 26-08-21 환원분
    for high, close in ((15_570.26, 10_260.0), (9_900, 9_900 * 0.677), (10_000, 7_400)):
        assert _gate_near_reasons(_result({"7"}, {"high_52w": high}), close) is None


def test_no_near_miss_combination_can_be_gate_near():
    """근접 정도·조건 조합과 무관하게 항상 None — 8조건 전부 필수."""
    cases = [
        ({"1"}, {"sma150": 10_000, "sma200": 10_000}, 9_999),
        ({"5"}, {"sma50": 10_000}, 9_999),
        ({"1", "5"}, {"sma150": 10_000, "sma200": 9_900, "sma50": 10_000}, 9_999),
        ({"5", "7"}, {"sma50": 10_000, "high_52w": 13_000}, 9_900),
    ]
    for fails, extras, close in cases:
        assert _gate_near_reasons(_result(fails, extras), close) is None


# ── 공통 가드(스위치와 무관하게 유지) ────────────────────────────────────────

def test_all_pass_returns_none():
    r = _result(set(), {"high_52w": 10_000}, all_pass=True)
    assert _gate_near_reasons(r, 9_000) is None


def test_non_relaxable_criterion_returns_none():
    # ②(150MA>200MA)는 애초에 완화 대상이 아니었다
    r = _result({"2", "5"}, {"sma50": 10_000})
    assert _gate_near_reasons(r, 9_000) is None


def test_too_many_fails_returns_none():
    r = _result({"1", "5", "7"}, {"sma150": 9_100, "sma200": 9_000,
                                  "sma50": 9_500, "high_52w": 10_000},
                passed_count=5)
    assert _gate_near_reasons(r, 9_000) is None


def test_no_close_returns_none():
    r = _result({"5"}, {"sma50": 10_000})
    assert _gate_near_reasons(r, None) is None
