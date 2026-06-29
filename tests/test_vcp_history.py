# tests/test_vcp_history.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.vcp_history import replay_vcp, find_breakout_events


def _series(closes):
    return {
        "dates": [f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}" for i in range(len(closes))],
        "closes": closes,
        "highs": [c * 1.01 for c in closes],
        "lows": [c * 0.99 for c in closes],
        "volumes": [1000] * len(closes),
    }


def test_replay_returns_one_entry_per_asof_day_with_keys():
    s = _series([100 + i for i in range(40)])
    rep = replay_vcp(s, scan_days=10)
    assert len(rep) == 10                       # 마지막 10 거래일
    assert rep[-1]["date"] == s["dates"][-1]    # 마지막 as-of = 마지막 날
    assert set(rep[0]) == {"date", "vcp_detected", "status", "pivot_price", "contractions"}


def test_find_breakout_events_detects_transition_with_prior_vcp():
    # 합성 replay: day3에 breakout 전환, 직전(day2)에 vcp_detected=true
    rep = [
        {"date": "d0", "vcp_detected": False, "status": "forming", "pivot_price": None, "contractions": []},
        {"date": "d1", "vcp_detected": True,  "status": "actionable", "pivot_price": 100.0, "contractions": [20.0, 8.0]},
        {"date": "d2", "vcp_detected": True,  "status": "actionable", "pivot_price": 100.0, "contractions": [20.0, 8.0]},
        {"date": "d3", "vcp_detected": False, "status": "breakout", "pivot_price": 100.0, "contractions": [20.0, 8.0]},
        {"date": "d4", "vcp_detected": False, "status": "breakout", "pivot_price": 100.0, "contractions": [20.0, 8.0]},
    ]
    evs = find_breakout_events(rep, confirm_lookback=5)
    assert len(evs) == 1                         # 연속 breakout(d4)은 중복 카운트 안 함
    assert evs[0]["date"] == "d3"
    assert evs[0]["replay_idx"] == 3
    assert evs[0]["confirm_date"] == "d2"        # 가장 가까운 직전 vcp_detected
    assert evs[0]["pivot_price"] == 100.0


def test_find_breakout_events_skips_breakout_without_prior_vcp():
    rep = [
        {"date": "d0", "vcp_detected": False, "status": "forming", "pivot_price": None, "contractions": []},
        {"date": "d1", "vcp_detected": False, "status": "breakout", "pivot_price": 50.0, "contractions": []},
    ]
    assert find_breakout_events(rep, confirm_lookback=5) == []
