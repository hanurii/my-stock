import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from canslim_lib.minute_bars import validate_minutes


def test_validate_ok():
    # 오름차순(마지막=15:30). 종가 7930=ref, 거래량합 470000 ≈ ref 469000(100%)
    mins = [{"t": "152900", "c": 7920.0, "v": 370000.0},
            {"t": "153000", "c": 7930.0, "v": 100000.0}]
    ok, ce, cov = validate_minutes(mins, ref_close=7930.0, ref_volume=469000.0)
    assert ok and ce < 0.1 and 99 < cov < 102


def test_validate_bad_close():
    mins = [{"t": "153000", "c": 7160.0, "v": 470000.0}]   # 종가 오차 ~9.7%
    ok, ce, cov = validate_minutes(mins, 7930.0, 469000.0)
    assert not ok and ce > 9


def test_validate_low_coverage():
    mins = [{"t": "153000", "c": 7930.0, "v": 100000.0}]   # 거래량 ~21%
    ok, ce, cov = validate_minutes(mins, 7930.0, 469000.0)
    assert not ok and cov < 90


def test_validate_over_coverage():
    mins = [{"t": "153000", "c": 7930.0, "v": 900000.0}]   # 거래량 ~192%(중복계수)
    ok, ce, cov = validate_minutes(mins, 7930.0, 469000.0)
    assert not ok and cov > 115


def test_validate_empty_or_no_ref():
    assert validate_minutes([], 7930.0, 469000.0)[0] is False
    assert validate_minutes([{"t": "153000", "c": 7930.0, "v": 100.0}], None, 469000.0)[0] is False
