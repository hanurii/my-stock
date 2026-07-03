import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.sell_rules import avg_volume, find_breakout_index


def make_series(closes, volumes=None, highs=None, lows=None):
    """오름차순 일봉 dict 생성. 기본 고저 = 종가 ±1%, 거래량 1000."""
    n = len(closes)
    d0 = date(2026, 1, 1)
    dates = [(d0 + timedelta(days=i)).isoformat() for i in range(n)]
    return {
        "dates": dates,
        "closes": list(closes),
        "highs": list(highs) if highs else [c * 1.01 for c in closes],
        "lows": list(lows) if lows else [c * 0.99 for c in closes],
        "volumes": list(volumes) if volumes else [1000.0] * n,
    }


# --- avg_volume ---

def test_avg_volume_excludes_current_day():
    vols = [1000.0] * 10 + [9999.0]  # 판정일(마지막)은 평균에서 제외
    assert avg_volume(vols, 10) == 1000.0


def test_avg_volume_none_when_insufficient_sample():
    assert avg_volume([1000.0] * 3, 3) is None  # 직전 3일 < min_days 5


def test_avg_volume_caps_window_at_50():
    vols = [2000.0] * 30 + [1000.0] * 50 + [1.0]
    assert avg_volume(vols, 80) == 1000.0  # 직전 50일만


# --- find_breakout_index ---

def test_find_breakout_detects_pivot_cross():
    closes = [100.0] * 10 + [106.0, 107.0]  # index 10에서 피벗 105 상향 돌파
    s = make_series(closes)
    bi, estimated = find_breakout_index(s, s["dates"][-1], 105.0)
    assert bi == 10
    assert estimated is False


def test_find_breakout_falls_back_to_buy_date_when_no_cross():
    closes = [100.0] * 12  # 피벗 105를 넘은 날 없음
    s = make_series(closes)
    bi, estimated = find_breakout_index(s, s["dates"][5], 105.0)
    assert bi == 5
    assert estimated is True


def test_find_breakout_no_pivot_uses_buy_date():
    s = make_series([100.0] * 12)
    bi, estimated = find_breakout_index(s, s["dates"][7], None)
    assert bi == 7
    assert estimated is True


def test_find_breakout_buy_date_between_trading_days():
    # 매수일이 휴장일이면 그 이전 마지막 거래일을 매수일로 취급
    s = make_series([100.0] * 5)
    bi, estimated = find_breakout_index(s, "2026-12-31", None)
    assert bi == 4  # 마지막 거래일
    assert estimated is True


# --- Rule imports for 규칙 ① ② ③ ---

from canslim_lib.sell_rules import (
    rule_low_volume_breakout,
    rule_heavy_volume_pullback,
    rule_consecutive_lower_closes,
)


# --- 규칙 ① 저거래량 돌파 ---

def test_rule1_violation_below_average_volume():
    vols = [1000.0] * 30 + [800.0]
    s = make_series([100.0] * 31, volumes=vols)
    r = rule_low_volume_breakout(s, 30)
    assert r["status"] == "violation"


def test_rule1_pass_but_weak_between_1x_and_1p5x():
    vols = [1000.0] * 30 + [1200.0]
    s = make_series([100.0] * 31, volumes=vols)
    r = rule_low_volume_breakout(s, 30)
    assert r["status"] == "pass"
    assert "1.5배" in r["detail"]  # 정상 돌파 기준 미달 경고 문구


def test_rule1_pass_strong_volume():
    vols = [1000.0] * 30 + [2100.0]
    s = make_series([100.0] * 31, volumes=vols)
    r = rule_low_volume_breakout(s, 30)
    assert r["status"] == "pass"
    assert "1.5배" not in r["detail"]


def test_rule1_pending_insufficient_history():
    s = make_series([100.0] * 3)
    assert rule_low_volume_breakout(s, 2)["status"] == "pending"


def test_rule1_zero_breakout_volume_is_violation():
    vols = [1000.0] * 30 + [0.0]
    s = make_series([100.0] * 31, volumes=vols)
    assert rule_low_volume_breakout(s, 30)["status"] == "violation"


def test_rule1_none_breakout_volume_is_pending():
    vols = [1000.0] * 30 + [None]
    s = make_series([100.0] * 31, volumes=vols)
    assert rule_low_volume_breakout(s, 30)["status"] == "pending"


# --- 규칙 ② 대량 거래 후퇴 ---

def test_rule2_violation_down_close_on_heavy_volume():
    closes = [100.0] * 30 + [106.0, 103.0]   # 돌파(30) 후 하락 마감
    vols = [1000.0] * 31 + [1800.0]          # 하락일 거래량 1.8배
    s = make_series(closes, volumes=vols)
    r = rule_heavy_volume_pullback(s, 30)
    assert r["status"] == "violation"


def test_rule2_pass_down_close_on_light_volume():
    closes = [100.0] * 30 + [106.0, 103.0]
    vols = [1000.0] * 31 + [900.0]
    s = make_series(closes, volumes=vols)
    assert rule_heavy_volume_pullback(s, 30)["status"] == "pass"


def test_rule2_pass_heavy_volume_but_up_close():
    closes = [100.0] * 30 + [106.0, 109.0]
    vols = [1000.0] * 31 + [3000.0]
    s = make_series(closes, volumes=vols)
    assert rule_heavy_volume_pullback(s, 30)["status"] == "pass"


def test_rule2_pending_no_post_breakout_days():
    s = make_series([100.0] * 31)
    assert rule_heavy_volume_pullback(s, 30)["status"] == "pending"


# --- 규칙 ③ 연속 저저점 (종가 < 전일 저가) ---

def test_rule3_violation_three_consecutive_closes_below_prior_low():
    # 저가 = 종가*0.99. 97<99, 94<96.03, 91<93.06 → 3일 연속
    closes = [100.0] * 30 + [106.0, 97.0, 94.0, 91.0]
    s = make_series(closes)
    r = rule_consecutive_lower_closes(s, 30)
    assert r["status"] == "violation"


def test_rule3_two_day_run_is_pass_with_warning():
    closes = [100.0] * 30 + [106.0, 97.0, 94.0]  # 2일 연속 진행 중
    s = make_series(closes)
    r = rule_consecutive_lower_closes(s, 30)
    assert r["status"] == "pass"
    assert "2일" in r["detail"]


def test_rule3_pass_when_run_broken():
    # 2일 연속 후 반등 → 위반 아님
    closes = [100.0] * 30 + [106.0, 97.0, 94.0, 98.0]
    s = make_series(closes)
    r = rule_consecutive_lower_closes(s, 30)
    assert r["status"] == "pass"
    assert "2일" not in r["detail"]
