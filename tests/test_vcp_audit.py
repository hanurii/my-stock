import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.vcp_audit import (
    volume_ma,
    audit_prior_advance,
    audit_contractions,
    audit_contraction_volumes,
    audit_dry_point,
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
