import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.cheat_history import (
    replay_cheat, find_breakout_events, post_breakout_outcome, classify,
)


def _rep(*tuples):
    """(status, pattern_detected) 튜플들로 replay 리스트 생성(date=d0..)."""
    return [{"date": f"d{i}", "status": s, "pattern_detected": p,
             "pivot_price": 10.0, "cup_depth_pct": 20.0, "shelf_position_pct": 50.0}
            for i, (s, p) in enumerate(tuples)]


def test_find_breakout_events_catches_confirmed_breakout():
    # forming/actionable(치트 확인) ... 그 뒤 breakout 새 전환 → 이벤트 1건.
    rep = _rep(("forming", False), ("actionable", True), ("actionable", True),
               ("breakout", False), ("breakout", False))
    ev = find_breakout_events(rep, confirm_lookback=5)
    assert len(ev) == 1
    assert ev[0]["date"] == "d3"          # 첫 breakout 전환일
    assert ev[0]["confirm_date"] == "d2"  # 직전 pattern_detected=True 최근일
    assert ev[0]["replay_idx"] == 3


def test_find_breakout_events_requires_confirm():
    # breakout 이지만 직전 confirm_lookback 내 pattern_detected=True 없음 → 이벤트 0.
    rep = _rep(("forming", False), ("forming", False), ("breakout", False))
    assert find_breakout_events(rep, confirm_lookback=5) == []


def test_find_breakout_events_dedup_consecutive():
    # 연속 breakout 은 첫 전환만.
    rep = _rep(("actionable", True), ("breakout", False), ("breakout", False), ("breakout", False))
    ev = find_breakout_events(rep, confirm_lookback=5)
    assert len(ev) == 1 and ev[0]["date"] == "d1"


def test_classify_no_3c_found_when_no_events():
    rep = _rep(("forming", False), ("forming", False))
    assert classify([], rep, recent_days=10) == "no_3c_found"


def test_classify_recent_breakout():
    rep = _rep(*[("forming", False)]*5, ("actionable", True), ("breakout", False))
    ev = find_breakout_events(rep, confirm_lookback=5)
    assert classify(ev, rep, recent_days=10) == "recent_breakout"


def test_classify_extended():
    # 돌파 후 한참(>recent_days) 상승, 새 치트 없음.
    rep = _rep(("actionable", True), ("breakout", False), *[("forming", False)]*15)
    ev = find_breakout_events(rep, confirm_lookback=5)
    assert classify(ev, rep, recent_days=10) == "extended"


def test_classify_re_basing():
    # 돌파 후 새 치트(pattern_detected=True) 재출현 + 마지막 forming/actionable.
    rep = _rep(("actionable", True), ("breakout", False), *[("forming", False)]*12,
               ("actionable", True), ("actionable", True))
    ev = find_breakout_events(rep, confirm_lookback=5)
    assert classify(ev, rep, recent_days=10) == "re_basing"


def test_post_breakout_outcome_numbers():
    # 돌파일 종가 100. 이후 high 130(+30%), 종가 최저 95(-5%), 마지막 종가 120(+20%).
    series = {"dates": ["d0", "d1", "d2", "d3"],
              "closes": [100.0, 110.0, 95.0, 120.0],
              "highs":  [101.0, 130.0, 100.0, 122.0],
              "lows":   [99.0, 108.0, 94.0, 118.0],
              "volumes": [1, 1, 1, 1]}
    o = post_breakout_outcome(series, "d0", stop_pct=8.0, target_pct=20.0)
    assert o["breakout_close"] == 100.0
    assert o["days_since"] == 3
    assert o["gain_since_pct"] == 20.0
    assert o["max_gain_pct"] == 30.0
    assert o["max_drawdown_pct"] == -5.0
    assert o["good_breakout"] is True       # +20% high 도달 전 -8% low 미접촉


def test_post_breakout_outcome_stop_before_target():
    # 먼저 -8% 손절(low 92) 후 나중에 +20% → good_breakout False(손절 먼저).
    series = {"dates": ["d0", "d1", "d2"],
              "closes": [100.0, 95.0, 125.0],
              "highs":  [101.0, 98.0, 130.0],
              "lows":   [99.0, 92.0, 120.0],
              "volumes": [1, 1, 1]}
    o = post_breakout_outcome(series, "d0", stop_pct=8.0, target_pct=20.0)
    assert o["good_breakout"] is False


def test_replay_cheat_shape():
    # 작은 시계열로 replay 가 올바른 길이·키를 내는지(evaluate_cheat 실호출).
    closes = [10 + (i % 3) for i in range(60)]
    series = {"dates": [f"2026-01-{i+1:03d}" for i in range(60)],
              "closes": closes, "highs": [c*1.01 for c in closes],
              "lows": [c*0.99 for c in closes], "volumes": [1000]*60}
    rep = replay_cheat(series, scan_days=10)
    assert len(rep) == 10
    for r in rep:
        assert set(r) >= {"date", "pattern_detected", "status", "pivot_price",
                          "cup_depth_pct", "shelf_position_pct"}
    assert rep[-1]["date"] == "2026-01-060"
