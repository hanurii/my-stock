import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.vcp_audit import volume_ma, audit_prior_advance


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
