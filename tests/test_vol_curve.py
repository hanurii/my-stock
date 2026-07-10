import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from autobuy import vol_curve


def test_window_vol_frac_at_least_raw_diff():
    # 하한(평균율)만 올리므로 실제 C(t)-C(t-W)보다 작지 않다
    t = "113000"
    raw = vol_curve.expected_vol_frac(t) - vol_curve.expected_vol_frac("112500")
    assert vol_curve.window_vol_frac(t, 5) >= raw - 1e-12


def test_window_vol_frac_no_flat_spot_blowup():
    # 곡선 평탄부(10:00: C(10:00)=C(09:59))에서도 분모가 0에 안 가깝다(아티팩트 방지)
    wf = vol_curve.window_vol_frac("100000", 1)
    assert wf > 1e-3   # 1e-6 클램프에 안 걸리고 평균 분당율(~0.005) 수준


def test_window_smaller_than_cumulative():
    # 최근 5분 비율은 그 시각까지 누적비율보다 작다
    assert vol_curve.window_vol_frac("133000", 5) < vol_curve.expected_vol_frac("133000")


def test_window_at_open_clamps_positive():
    # 개장 직후엔 5분 창이 09:00 이전으로 안 넘어가고 양수를 반환
    assert vol_curve.window_vol_frac("090300", 5) > 0
