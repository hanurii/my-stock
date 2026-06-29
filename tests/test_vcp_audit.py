import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.vcp_audit import (
    volume_ma,
    audit_prior_advance,
    audit_contractions,
    audit_contraction_volumes,
    audit_dry_point,
    audit_breakout,
)


def test_volume_ma_trailing_window():
    vols = [10, 20, 30, 40, 50]
    ma = volume_ma(vols, window=3)
    # i0=10, i1=(10+20)/2=15, i2=(10+20+30)/3=20, i3=(20+30+40)/3=30, i4=40
    assert ma[0] == 10
    assert ma[1] == 15
    assert ma[2] == 20
    assert ma[3] == 30
    assert ma[4] == 40


def test_audit_prior_advance_low_to_basestart():
    # 저점 100(idx2) → 베이스시작 150(idx6): +50%, 4거래일
    closes = [120, 110, 100, 110, 130, 145, 150, 148]
    r = audit_prior_advance(closes, b0=6, lookback=60)
    assert abs(r["value_pct"] - 50.0) < 1e-9
    assert r["days"] == 4
    assert r["low_price"] == 100


def test_audit_contractions_depths_and_shrinking():
    base = [100, 95, 88, 80, 84, 90, 92, 84, 85, 86]  # 고100→저80(-20%), 고92→저84(-8.7%)
    r = audit_contractions(base, zigzag_pct=8.0, mono_tol=1.15)
    assert r["count"] >= 2
    assert r["depths"][0] > r["depths"][-1]
    assert r["shrinking"] is True


def test_audit_contraction_volumes_decreasing_and_below_ma50():
    # 수축 2개: 첫 구간 거래량 MA50의 120%, 둘째 60% → 감소 & 둘째 50일선 하회
    base_vols  = [120, 120, 60, 60]
    base_ma50  = [100, 100, 100, 100]
    swings = [(0, 100.0, "high"), (1, 80.0, "low"), (2, 90.0, "high"), (3, 82.0, "low")]
    r = audit_contraction_volumes(base_vols, base_ma50, swings, mono_tol=1.15)
    assert len(r["per"]) == 2
    assert abs(r["per"][0]["vol_vs_ma50_pct"] - 120.0) < 1e-6
    assert abs(r["per"][1]["vol_vs_ma50_pct"] - 60.0) < 1e-6
    assert r["decreasing"] is True
    assert r["last_below_ma50"] is True


def test_audit_dry_point_min_on_right():
    base_vols  = [100, 90, 80, 40, 70]   # 우측 1/3 ~ 마지막 한두 개
    base_ma50  = [100, 100, 100, 100, 100]
    base_dates = ["d0", "d1", "d2", "d3", "d4"]
    r = audit_dry_point(base_vols, base_ma50, base_dates, right_frac=0.5)
    assert r["min_vol_vs_ma50_pct"] == 40.0
    assert r["date"] == "d3"


def test_audit_breakout_clean_vs_detector():
    # 피벗 100. b1 이후: d0 전일종가95 → d1 종가105(첫돌파·양봉·거래량2배·연장5%)
    series = {
        "dates":  ["d0", "d1", "d2"],
        "closes": [95.0, 105.0, 108.0],
        "opens":  [96.0, 101.0, 107.0],
        "highs":  [97.0, 106.0, 109.0],
        "lows":   [94.0, 100.0, 106.0],
        "volumes":[100.0, 300.0, 120.0],
    }
    ma50 = [150.0, 150.0, 150.0]   # d1 거래량 300/150 = 200%
    params = {"breakout_vol": 1.4, "near": 5.0, "base_vol_cap": 50}
    r = audit_breakout(series, pivot=100.0, b1=0, ma50=ma50, params=params)
    # d1: 첫돌파(전일95≤100), 양봉(105>101), vol 200%≥140%, 연장 5%≤5 → clean
    assert any(c["date"] == "d1" for c in r["clean_candidates"])
    assert r["pass"] is True
    assert not any(c["date"] == "d2" for c in r["clean_candidates"])  # d2 연장 8%>5 → 제외
    assert "d1" in r["detector_flags"]                                # d1 거래량 300≥base×1.4
