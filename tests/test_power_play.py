import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.power_play import DEFAULT_PARAMS, find_flagpole


def test_default_params_has_required_keys():
    for k in ("lookback_days", "min_flagpole_gain", "max_flagpole_days",
              "pole_vol_mult", "quiet_window", "max_pre_pole_gain",
              "min_flag_days", "max_flag_days", "max_flag_depth",
              "breakout_vol_mult", "near_pivot_pct", "min_total_days"):
        assert k in DEFAULT_PARAMS
    assert DEFAULT_PARAMS["min_flagpole_gain"] == 100.0
    assert DEFAULT_PARAMS["max_flagpole_days"] == 40


def test_find_flagpole_detects_doubling():
    # 저점 50에서 시작해 110까지(+120%) 오른 뒤, 100 근처 고점이 인덱스 5
    highs = [52, 70, 90, 105, 110, 111, 108, 106, 104]
    lows  = [50, 66, 86, 100, 105, 106, 100, 98, 96]
    fp = find_flagpole(highs, lows, max_flagpole_days=40)
    # 구간 최고 고가는 인덱스 5(111)
    assert fp["flag_high_idx"] == 5
    assert fp["flag_high"] == 111
    # 깃대 시작 저점은 50(인덱스 0)
    assert fp["pole_start_low"] == 50
    assert fp["pole_start_idx"] == 0
    # (111-50)/50*100 = 122%
    assert abs(fp["flagpole_gain_pct"] - 122.0) < 1e-6
    assert fp["flagpole_days"] == 5


def test_find_flagpole_respects_window_cap():
    # 아주 오래된 저점(인덱스0=10)은 40일 경계 밖이면 무시되고,
    # 경계 안 최저점만 깃대 시작으로 잡힌다.
    highs = [12] + [40]*45 + [80]   # 고점은 마지막(인덱스46)
    lows  = [10] + [38]*45 + [70]
    fp = find_flagpole(highs, lows, max_flagpole_days=40)
    assert fp["flag_high_idx"] == 46
    # 경계 = 46-40 = 6 이후의 최저 저점(38), 10이 아님
    assert fp["pole_start_low"] == 38
    assert fp["flagpole_days"] <= 40
