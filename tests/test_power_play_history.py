# tests/test_power_play_history.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.power_play_history import (
    replay_power_play, find_breakout_events, post_breakout_outcome, classify,
)


def _clean_htf_with_breakout():
    """깔끔한 HTF(조용→+120% 깃대→얕은 깃발) + 물리적 신고가 돌파 봉."""
    quiet = [50 + (i % 2) for i in range(20)]
    pole = [52, 58, 66, 75, 85, 95, 104, 110]
    flag = [108, 106, 105, 104, 103, 105, 106, 107, 106, 105]
    closes = quiet + pole + flag + [112.0]                  # 마지막=돌파 봉
    highs = [c * 1.01 for c in closes[:-1]] + [113.0]
    lows = [c * 0.99 for c in closes[:-1]] + [111.0]
    vols = [800] * 20 + [3000] * 8 + [500] * 10 + [6000]
    dates = [f"d{i}" for i in range(len(closes))]
    return {"dates": dates, "closes": closes, "highs": highs, "lows": lows, "volumes": vols}


def test_replay_returns_one_entry_per_asof_day_with_keys():
    s = _clean_htf_with_breakout()
    rep = replay_power_play(s, scan_days=5)
    assert len(rep) == 5                               # 마지막 5 거래일
    assert rep[-1]["date"] == s["dates"][-1]           # 마지막 as-of = 마지막 날
    assert set(rep[0]) == {"date", "pattern_detected", "status",
                           "pivot_price", "flagpole_gain_pct", "flag_depth_pct"}


def test_find_breakout_events_detects_transition_with_prior_pattern():
    # 합성 replay: d3에 breakout 전환, 직전(d2)에 pattern_detected=true
    rep = [
        {"date": "d0", "pattern_detected": False, "status": "forming", "pivot_price": None, "flagpole_gain_pct": None, "flag_depth_pct": None},
        {"date": "d1", "pattern_detected": True,  "status": "forming", "pivot_price": 110.0, "flagpole_gain_pct": 120.0, "flag_depth_pct": 8.0},
        {"date": "d2", "pattern_detected": True,  "status": "actionable", "pivot_price": 110.0, "flagpole_gain_pct": 120.0, "flag_depth_pct": 8.0},
        {"date": "d3", "pattern_detected": False, "status": "breakout", "pivot_price": 110.0, "flagpole_gain_pct": 120.0, "flag_depth_pct": 8.0},
        {"date": "d4", "pattern_detected": False, "status": "breakout", "pivot_price": 110.0, "flagpole_gain_pct": 120.0, "flag_depth_pct": 8.0},
    ]
    evs = find_breakout_events(rep, confirm_lookback=5)
    assert len(evs) == 1                               # 연속 breakout(d4)은 중복 카운트 안 함
    assert evs[0]["date"] == "d3"
    assert evs[0]["replay_idx"] == 3
    assert evs[0]["confirm_date"] == "d2"              # 가장 가까운 직전 pattern_detected
    assert evs[0]["pivot_price"] == 110.0
    assert evs[0]["flagpole_gain_pct"] == 120.0
    assert evs[0]["flag_depth_pct"] == 8.0


def test_find_breakout_events_skips_breakout_without_prior_pattern():
    rep = [
        {"date": "d0", "pattern_detected": False, "status": "forming", "pivot_price": None, "flagpole_gain_pct": None, "flag_depth_pct": None},
        {"date": "d1", "pattern_detected": False, "status": "breakout", "pivot_price": 50.0, "flagpole_gain_pct": 60.0, "flag_depth_pct": 5.0},
    ]
    assert find_breakout_events(rep, confirm_lookback=5) == []


def test_integration_real_series_produces_event():
    # 실제 evaluate_power_play 를 as-of 리플레이 → 돌파일에 이벤트 1건.
    s = _clean_htf_with_breakout()
    rep = replay_power_play(s, scan_days=4)             # 마지막 4일(돌파 포함)
    evs = find_breakout_events(rep, confirm_lookback=5)
    assert len(evs) >= 1                               # 이음새가 실제 이벤트를 만든다
    assert evs[-1]["date"] == s["dates"][-1]           # 돌파일에 이벤트
    assert evs[-1]["flagpole_gain_pct"] is not None    # 근거 지표 캡처됨


def test_classify_branches():
    assert classify([], [], recent_days=10) == "no_power_play_found"
    # 최근 돌파: 이벤트가 replay 끝에서 days_since<=recent_days
    rep = [{"pattern_detected": False, "status": "breakout"}] * 12
    ev_recent = [{"replay_idx": 9}]                    # len-1-9 = 2 <= 10
    assert classify(ev_recent, rep, recent_days=10) == "recent_breakout"
    # 연장: 오래 전 돌파, 이후 새 패턴 없음
    ev_old = [{"replay_idx": 0}]                       # days_since = 11 > 10
    rep_ext = [{"pattern_detected": False, "status": "extended_dummy"}] * 12
    assert classify(ev_old, rep_ext, recent_days=10) == "extended"
    # 재베이스: 오래 전 돌파 후 pattern_detected 재출현 + 마지막 forming
    rep_reb = [{"pattern_detected": False, "status": "breakout"}] * 12
    rep_reb[5] = {"pattern_detected": True, "status": "forming"}
    rep_reb[-1] = {"pattern_detected": False, "status": "forming"}
    assert classify(ev_old, rep_reb, recent_days=10) == "re_basing"


def test_post_breakout_outcome_is_reused_from_vcp_history():
    from canslim_lib.vcp_history import post_breakout_outcome as _orig
    assert post_breakout_outcome is _orig


def test_post_breakout_outcome_reused_numbers():
    # 재사용한 vcp_history.post_breakout_outcome 가 이 모듈 import 경로로도 동일 동작.
    s = {
        "dates": ["d0", "d1", "d2", "d3"],
        "closes": [100.0, 110.0, 95.0, 130.0],
        "highs":  [100.0, 112.0, 96.0, 132.0],
        "lows":   [100.0, 108.0, 94.0, 128.0],
        "volumes": [1, 1, 1, 1],
    }
    o = post_breakout_outcome(s, "d0", stop_pct=8.0, target_pct=20.0)
    assert o["breakout_close"] == 100.0
    assert o["days_since"] == 3
    assert o["gain_since_pct"] == 30.0
    assert o["max_gain_pct"] == 32.0
    assert o["max_drawdown_pct"] == -5.0
    assert o["good_breakout"] is True


def test_post_breakout_outcome_missing_date_returns_none():
    s = {"dates": ["d0"], "closes": [100.0], "highs": [100.0], "lows": [100.0], "volumes": [1]}
    assert post_breakout_outcome(s, "zzz") is None
