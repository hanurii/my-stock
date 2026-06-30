import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.cheat import DEFAULT_PARAMS, find_cheat_shelf


def test_default_params_has_required_keys():
    for k in ("lookback_days", "min_total_days", "min_cup_depth", "max_cup_depth",
              "min_cup_days", "min_shelf_pullback", "min_shelf_days", "max_shelf_days",
              "max_shelf_depth", "max_shelf_position", "breakout_vol_mult", "near_pivot_pct"):
        assert k in DEFAULT_PARAMS
    assert DEFAULT_PARAMS["min_cup_depth"] == 12.0
    assert DEFAULT_PARAMS["max_shelf_position"] == 66.0


def test_find_cheat_shelf_anchors_bottom_first():
    # 왼쪽 테두리 100(idx0) → 바닥 70(idx4) → 우측 반등 후 선반 천장 85(idx8),
    # 선반 천장 뒤로 80까지 눌림(>3%) 확인. 피벗은 옛 고점 100이 아니라 85.
    highs = [100, 92, 84, 76, 71, 78, 83, 85, 85, 82, 84]
    lows  = [ 98, 90, 82, 74, 70, 76, 81, 83, 80, 80, 82]
    r = find_cheat_shelf(highs, lows, min_shelf_pullback=3.0)
    assert r["cup_low"] == 70
    assert r["cup_low_idx"] == 4
    assert r["left_rim_high"] == 100
    assert r["left_rim_idx"] == 0
    assert r["shelf_high"] == 85          # 옛 고점 100이 아님(바닥 이후 우측에서만)
    assert r["shelf_high_idx"] in (7, 8)  # 85를 찍은 봉
    assert abs(r["cup_depth_pct"] - 30.0) < 1e-6   # (100-70)/100*100
    assert r["cup_base_days"] == (len(highs) - 1) - 0


def test_find_cheat_shelf_excludes_fresh_breakout_bar():
    # 마지막 바가 우측 신고가 90으로 돌파. 피벗은 돌파봉(90)이 아니라 선반 천장 85.
    highs = [100, 92, 84, 76, 71, 78, 83, 85, 84, 83, 90]
    lows  = [ 98, 90, 82, 74, 70, 76, 81, 83, 80, 81, 88]
    r = find_cheat_shelf(highs, lows, min_shelf_pullback=3.0)
    assert r["shelf_high"] == 85
    assert r["shelf_high_idx"] == 7


def test_find_cheat_shelf_empty_returns_sentinel():
    r = find_cheat_shelf([], [], min_shelf_pullback=3.0)
    assert r["cup_depth_pct"] == 0.0
    assert r["cup_base_days"] == 0
