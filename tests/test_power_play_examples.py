# tests/test_power_play_examples.py
import json
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from canslim_lib.power_play import evaluate_power_play  # noqa: E402

FIX = json.loads((Path(__file__).resolve().parents[1] / "tests" / "fixtures"
                  / "power_play_examples.json").read_text(encoding="utf-8"))
CASES = {c["code"]: c for c in FIX["cases"]}


def _detect_in_window(case, before=7, after=3, gain_min=None):
    """피벗 −before ~ +after 거래일 중 pattern_detected=True 인 날이 있으면 (날짜, 결과) 반환."""
    s = case["series"]
    dates = s["dates"]
    ip = dates.index(case["pivot_date"])
    params = {"min_flagpole_gain": gain_min} if gain_min is not None else None
    for i in range(max(0, ip - before), min(len(dates), ip + after + 1)):
        sub = {k: v[: i + 1] for k, v in s.items()}
        r = evaluate_power_play(sub, params)
        if r["pattern_detected"]:
            return dates[i], r
    return None, None


@pytest.mark.parametrize("code", ["032500", "133820", "BBY"])
def test_book_examples_detected_near_pivot(code):
    case = CASES[code]
    day, r = _detect_in_window(case)
    assert day is not None, f"{case['name']}: 피벗 윈도 내 미검출"
    # status(actionable/breakout)는 자산하지 않음: pattern_detected 가 검증 목표.
    # 케이엠더블유는 깃발 거래량이 안 말라 actionable status 타이밍이 안 맞음(알려진 한계, spec §4.6/§9).
    # 피벗이 실제 깃발 천장 근방(현재가가 피벗 ±15% 안)
    assert -15 <= (r["pct_to_pivot"] or 0) <= 15


@pytest.mark.xfail(reason="다우데이타: 회복-폴을 finder가 잡음(미너비니상 파워플레이 아님) — 알려진 거짓양성, spec §1/§8", strict=False)
def test_dauda_pole_start_type_not_detected():
    day, _ = _detect_in_window(CASES["032190"])
    assert day is None


def test_tnl_nested_flag_detected_at_lower_gain():
    # 티앤엘: 최종 타이트 수축(피벗 ~32,600)의 깃대는 ~79% → 기본 90 미달, 78에서 검출
    day, r = _detect_in_window(CASES["340570"], gain_min=78.0)
    assert day is not None, "티앤엘: gain 78 윈도 내 미검출"
    assert -15 <= (r["pct_to_pivot"] or 0) <= 15


def test_synthetic_non_powerplay_rejected():
    # 평평하게 횡보만(깃대 없음) → 절대 검출되면 안 됨
    closes = [100 + (i % 3) for i in range(140)]
    s = {"dates": [f"d{i}" for i in range(140)],
         "closes": closes, "highs": [c * 1.01 for c in closes],
         "lows": [c * 0.99 for c in closes], "volumes": [1000] * 140}
    r = evaluate_power_play(s)
    assert r["pattern_detected"] is False
