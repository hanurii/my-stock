# tests/test_vcp_history.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.vcp_history import replay_vcp, find_breakout_events, post_breakout_outcome, classify


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


def test_post_breakout_outcome_numbers():
    # 돌파일 종가 100, 이후 110(+10%)·95(-5%)·130(+30%)
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
    assert o["gain_since_pct"] == 30.0           # (130-100)/100
    assert o["max_gain_pct"] == 32.0             # 최고가 132
    assert o["max_drawdown_pct"] == -5.0         # 최저종가 95
    assert o["good_breakout"] is True            # -8% 닿기 전 +20%(132) 도달


def test_post_breakout_outcome_missing_date_returns_none():
    s = {"dates": ["d0"], "closes": [100.0], "highs": [100.0], "lows": [100.0], "volumes": [1]}
    assert post_breakout_outcome(s, "zzz") is None


def test_classify_branches():
    assert classify([], [], recent_days=10) == "no_vcp_found"
    # 최근 돌파: 이벤트가 replay 끝에서 days_since<=recent_days
    rep = [{"vcp_detected": False, "status": "breakout"}] * 12
    ev_recent = [{"replay_idx": 9}]              # len-1-9 = 2 <= 10
    assert classify(ev_recent, rep, recent_days=10) == "recent_breakout"
    # 연장: 오래 전 돌파, 이후 새 vcp 없음
    ev_old = [{"replay_idx": 0}]                 # days_since = 11 > 10
    rep_ext = [{"vcp_detected": False, "status": "extended_dummy"}] * 12
    assert classify(ev_old, rep_ext, recent_days=10) == "extended"
    # 재베이스: 오래 전 돌파 후 vcp_detected 재출현 + 마지막 forming
    rep_reb = [{"vcp_detected": False, "status": "breakout"}] * 12
    rep_reb[5] = {"vcp_detected": True, "status": "forming"}
    rep_reb[-1] = {"vcp_detected": False, "status": "forming"}
    assert classify(ev_old, rep_reb, recent_days=10) == "re_basing"


def test_post_breakout_outcome_same_bar_collision_is_conservative():
    # 돌파가 100. 다음 바 high=125(+25%≥목표20), low=90(-10%≤손절8) → 손절 먼저 = False
    s = {"dates": ["d0", "d1"], "closes": [100.0, 120.0],
         "highs": [100.0, 125.0], "lows": [100.0, 90.0], "volumes": [1, 1]}
    o = post_breakout_outcome(s, "d0", stop_pct=8.0, target_pct=20.0)
    assert o["good_breakout"] is False


def test_integration_real_series_produces_event():
    # 선행 상승 후 수렴 수축(25→13→8%) + 거래량 마름 베이스 + 돌파 바.
    # 기존 find-vcp 테스트(_vcp_closes)에서 evaluate_vcp가 vcp_detected+breakout를
    # 내는 것이 확인된 패턴을 그대로 사용한다.
    # _vcp_closes() 패턴과 동일: 2번째 바닥을 78.3으로 낮춰야 zigzag가
    # 3번째 수축(88→80.8, 8.18%)을 찾고 max_final_depth(10%) 조건을 통과함.
    # 브리프 원안(80.8)은 2수축만 생겨 최종 수축 11.11%>10% → vcp_detected=False.
    base = [100, 92, 84, 78, 75, 80, 86, 90,      # -25% 후 회복
            88, 84, 80, 78.3, 82, 86, 88,         # -13% 후 회복 (피벗 88, _vcp_closes와 동일)
            87, 85, 83, 80.8, 84, 86]             # -8.18% 후 피벗 접근
    closes = [60, 70, 80, 95] + base + [89.0]     # 선행상승 + 베이스 + 돌파(89>피벗88)
    n = len(closes)
    highs = [c * 1.005 for c in closes]
    lows = [c * 0.995 for c in closes]
    # 거래량: 베이스 후반 마름 + 돌파 바 급증
    vols = [3000, 3000, 3000, 3000] + [1500] * 7 + [1000] * (len(base) - 7) + [6000]
    assert len(vols) == n
    dates = [f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}" for i in range(n)]
    s = {"dates": dates, "closes": closes, "highs": highs, "lows": lows, "volumes": vols}

    rep = replay_vcp(s, scan_days=8)              # 마지막 8 거래일(돌파 포함)을 as-of
    evs = find_breakout_events(rep, confirm_lookback=5)
    assert len(evs) >= 1                          # 이음새가 실제로 이벤트를 만든다
    assert evs[-1]["date"] == dates[-1]           # 돌파일에 이벤트
