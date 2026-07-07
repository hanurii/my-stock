import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from autobuy.replay import replay_day_minutes, _elapsed_frac

CFG = {"SLOTS": 10, "VOL_PACE_MIN": 1.5, "CHASE_MAX_PCT": 3.0, "TARGET_PCT": 20.0,
       "STOP_PCT": 10.0, "MARKET_OPEN": "0905", "NEW_BUY_UNTIL": "1520"}

def bar(t, o, h, l, c, v):
    return {"t": t, "o": o, "h": h, "l": l, "c": c, "v": v}

def test_elapsed_frac():
    assert _elapsed_frac("090000") <= 1e-5 + 1e-6   # 개장=0 근처
    assert abs(_elapsed_frac("153000") - 1.0) < 1e-9  # 마감=1.0
    assert 0.2 < _elapsed_frac("102000") < 0.25       # 10:20 ~ 0.205

def test_buy_on_pivot_cross_with_volume():
    # 피벗 1000, avg50=1000. 09:30(ef≈0.077) 종가 1010(+1%,피벗위·+3%이내),
    # 그 분까지 누적거래량 200 → pace=200/(1000*0.077)=2.6 ≥1.5 → 매수
    cands = [{"code": "A", "name": "에이", "pivot": 1000.0, "pattern": "VCP"}]
    mins = {"A": [bar("093000", 1005, 1012, 1004, 1010, 200)]}
    ev, held = replay_day_minutes(mins, cands, {"A": 1000.0}, CFG)
    buys = [e for e in ev if e["action"] == "buy"]
    assert len(buys) == 1 and buys[0]["code"] == "A" and buys[0]["price"] == 1010
    assert "A" in held

def test_skip_extended_over_3pct():
    cands = [{"code": "A", "name": "에이", "pivot": 1000.0, "pattern": "VCP"}]
    mins = {"A": [bar("093000", 1040, 1045, 1035, 1040, 500)]}  # +4% → extended
    ev, held = replay_day_minutes(mins, cands, {"A": 1000.0}, CFG)
    assert [e for e in ev if e["action"] == "buy"] == [] and "A" not in held

def test_low_volume_no_buy():
    cands = [{"code": "A", "name": "에이", "pivot": 1000.0, "pattern": "VCP"}]
    mins = {"A": [bar("093000", 1005, 1012, 1004, 1010, 50)]}  # pace 낮음
    ev, held = replay_day_minutes(mins, cands, {"A": 1000.0}, CFG)
    assert [e for e in ev if e["action"] == "buy"] == []

def test_exit_target_then_stop_after_entry():
    # 진입(09:30 @1010) 후 10:00 고가 1212(+20% of 1010=1212) → 익절
    cands = [{"code": "A", "name": "에이", "pivot": 1000.0, "pattern": "VCP"}]
    mins = {"A": [bar("093000", 1005, 1012, 1004, 1010, 300),
                  bar("100000", 1100, 1220, 1090, 1200, 100)]}
    ev, held = replay_day_minutes(mins, cands, {"A": 1000.0}, CFG)
    sells = [e for e in ev if e["action"] == "sell"]
    assert len(sells) == 1 and sells[0]["reason"] == "익절" and "A" not in held

def test_stop_hit():
    cands = [{"code": "A", "name": "에이", "pivot": 1000.0, "pattern": "VCP"}]
    mins = {"A": [bar("093000", 1005, 1012, 1004, 1010, 300),
                  bar("100000", 1000, 1005, 900, 905, 100)]}  # 저가 900 ≤ 1010*0.9=909 → 손절
    ev, held = replay_day_minutes(mins, cands, {"A": 1000.0}, CFG)
    sells = [e for e in ev if e["action"] == "sell"]
    assert len(sells) == 1 and sells[0]["reason"] == "손절"

def test_slot_limit_pace_priority():
    cfg = {**CFG, "SLOTS": 1}
    cands = [{"code": "A", "name": "에이", "pivot": 1000.0, "pattern": "VCP"},
             {"code": "B", "name": "비", "pivot": 1000.0, "pattern": "VCP"}]
    mins = {"A": [bar("093000", 1005, 1012, 1004, 1010, 200)],   # pace 2.6
            "B": [bar("093000", 1005, 1012, 1004, 1010, 500)]}   # pace 6.5 (우선)
    ev, held = replay_day_minutes(mins, cands, {"A": 1000.0, "B": 1000.0}, cfg)
    buys = [e for e in ev if e["action"] == "buy"]
    assert len(buys) == 1 and buys[0]["code"] == "B"   # pace 높은 B만
