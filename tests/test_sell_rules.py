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
