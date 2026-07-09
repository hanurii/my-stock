import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from autobuy import vol_curve


def test_window_vol_frac_consistent_with_curve():
    # 최근 5분 비율 = C(t) - C(t-5분)
    wf = vol_curve.window_vol_frac("113000", 5)
    manual = vol_curve.expected_vol_frac("113000") - vol_curve.expected_vol_frac("112500")
    assert wf > 0 and abs(wf - manual) < 1e-9


def test_window_smaller_than_cumulative():
    # 최근 5분 비율은 그 시각까지 누적비율보다 작다
    assert vol_curve.window_vol_frac("133000", 5) < vol_curve.expected_vol_frac("133000")


def test_window_at_open_clamps_positive():
    # 개장 직후엔 5분 창이 09:00 이전으로 안 넘어가고 양수를 반환
    assert vol_curve.window_vol_frac("090300", 5) > 0
