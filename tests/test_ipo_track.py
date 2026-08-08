"""IPO 트랙(신규상장 대체 관문) 평가기 테스트.

설계: docs/superpowers/specs/2026-08-08-ipo-exception-track-design.md
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.ipo_track import evaluate_ipo_track  # noqa: E402


def _uptrend(n: int, start: float = 100.0, end: float = 160.0) -> list[float]:
    step = (end - start) / (n - 1)
    return [start + step * i for i in range(n)]


def test_uptrend_55d_all_pass():
    """마키나락스형 시나리오: 상장 55일 꾸준한 상승 + iRS 90 → 7조건 전부 통과."""
    r = evaluate_ipo_track(_uptrend(55), ipo_rs=90, filter_reasons=[])
    assert r["pass"] is True
    assert r["passed_count"] == 7
    assert r["extras"]["data_days"] == 55
    # 55일이면 lookback 22 · MA 창은 min(50, 55-22)=33 으로 축소돼야 한다
    assert r["extras"]["ma_rising_lookback_used"] == 22
    assert r["extras"]["ma_window_used"] == 33


def test_too_young_fails_all():
    """상장 15일: I7 미달 → 전 조건 fail (평가 자체는 항상 반환)."""
    r = evaluate_ipo_track(_uptrend(15), ipo_rs=95, filter_reasons=[])
    assert r["pass"] is False
    assert r["passed_count"] == 0
    assert all(not v["pass"] for v in r["criteria"].values())


def test_deep_pullback_fails_high_proximity():
    """급등 후 -30% 되밀림: I4(상장 후 최고가 -25% 이내) fail."""
    closes = _uptrend(40, 100, 200) + [200 * (1 - 0.30)] * 5
    r = evaluate_ipo_track(closes, ipo_rs=90, filter_reasons=[])
    assert r["criteria"]["I4"]["pass"] is False
    assert r["pass"] is False


def test_rs_none_and_filter_reasons():
    """iRS 미산출 → I5 fail. 필터 사유 있음 → I6 fail. 필터 미적용(None) → I6 pass."""
    closes = _uptrend(55)
    r = evaluate_ipo_track(closes, ipo_rs=None,
                           filter_reasons=[{"rule": "low_liquidity", "detail": "x"}])
    assert r["criteria"]["I5"]["pass"] is False
    assert r["criteria"]["I6"]["pass"] is False
    r2 = evaluate_ipo_track(closes, ipo_rs=85, filter_reasons=None)
    assert r2["criteria"]["I6"]["pass"] is True
    assert "미적용" in r2["criteria"]["I6"]["detail"]


def test_downtrend_fails_ma_conditions():
    """하락 추세: I1(종가>MA)·I2(MA 상승) fail."""
    closes = _uptrend(55, 160, 100)  # 상장 후 내리막
    r = evaluate_ipo_track(closes, ipo_rs=90, filter_reasons=[])
    assert r["criteria"]["I1"]["pass"] is False
    assert r["criteria"]["I2"]["pass"] is False
