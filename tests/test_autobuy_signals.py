import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from autobuy.signals import evaluate_entry
from autobuy.signals import evaluate_exit
from autobuy.signals import is_uptrend

# vol_frac = '평소 이 시각까지 하루 거래량의 몇 %'(장중 곡선 C(t)). 선형 경과시간 아님.
BASE = dict(price=1030.0, pivot=1000.0, acml_vol=600_000, avg50_vol=1_000_000,
            vol_frac=0.2, slots_used=0, slots_max=10, held=False)

def ev(**kw):
    return evaluate_entry(**{**BASE, **kw})

def test_all_conditions_met_buys():
    # pace = 600000/(1000000*0.2)=3.0 (>=1.5 기본문턱=strategy_params.VOL_PACE_MIN), price 1030<=1030(+3%) → buy
    assert ev() == (True, "buy")

def test_below_pivot_skips():
    assert ev(price=990.0)[0] is False and ev(price=990.0)[1] == "below_pivot"

def test_extended_over_3pct_skips():
    assert ev(price=1031.0) == (False, "extended")   # +3.1%
    assert ev(price=1030.0)[0] is True               # 정확히 +3.0% 는 허용

def test_low_volume_skips():
    assert ev(acml_vol=200_000) == (False, "low_volume")  # pace 1.0 < 1.5 문턱

def test_spike_buys_when_cumulative_low():
    # 누적 pace 1.0(<1.5)이지만 단기-창 스파이크 4.0(≥3) → OR 경로로 매수
    assert ev(acml_vol=200_000, spike_pace=4.0) == (True, "buy")

def test_spike_below_min_still_low_volume():
    # 누적 1.0·스파이크 2.0 둘 다 미달 → low_volume
    assert ev(acml_vol=200_000, spike_pace=2.0) == (False, "low_volume")

def test_spike_none_is_cumulative_only():
    # spike_pace 없으면 기존대로(누적만) — 1.0<1.5 → low_volume
    assert ev(acml_vol=200_000, spike_pace=None) == (False, "low_volume")

def test_no_slot_skips():
    assert ev(slots_used=10) == (False, "no_slot")

def test_already_held_skips():
    assert ev(held=True) == (False, "already_held")

def test_zero_baseline_skips():
    assert ev(avg50_vol=0) == (False, "no_baseline")
    assert ev(vol_frac=0) == (False, "no_baseline")

def test_exit_stop():
    assert evaluate_exit(900.0, 1000.0) == (True, "손절")     # -10%
    assert evaluate_exit(901.0, 1000.0) == (False, "보유")    # -9.9%

def test_exit_target():
    assert evaluate_exit(1200.0, 1000.0) == (True, "익절")  # +20%
    assert evaluate_exit(1199.0, 1000.0) == (False, "보유")

def test_exit_hold_between():
    assert evaluate_exit(1050.0, 1000.0) == (False, "보유")

def test_is_uptrend():
    assert is_uptrend([1,2,3,4,5,6,7,8,9,10]*3, ma=20) is True     # 우상향
    assert is_uptrend(list(range(30,0,-1)), ma=20) is False        # 우하향
    assert is_uptrend([100]*10, ma=20) is False                    # 데이터<ma → 판단불가=False(보수)
