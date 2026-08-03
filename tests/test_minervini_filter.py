"""minervini_filter — '미너비니가 사지 않는 주식' 3규칙 분류 테스트.

실증 근거(2026-07 손절 공통점 분석): 우선주(GS우·S-Oil우)·외국법인(로스웰)·
저유동성(로스웰 0.67억·빅솔론 2.1억) 이 반복 손절의 공통 프로필이었다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.minervini_filter import (  # noqa: E402
    avg_turnover_eok,
    classify_non_minervini,
    filter_minervini_universe,
)


def _series(closes, volumes, start="2026-01-01"):
    n = len(closes)
    dates = [f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}" for i in range(n)]
    return {"dates": dates, "closes": closes, "volumes": volumes}


def _liquid_series(days=60, price=10_000, vol=200_000):
    # 10,000원 × 200,000주 = 일 20억 → 10억 기준 통과
    return _series([price] * days, [vol] * days)


def _thin_series(days=60, price=1_700, vol=40_000):
    # 로스웰 실측 수준: 1,700원 × 40,000주 ≈ 일 0.68억
    return _series([price] * days, [vol] * days)


def test_common_liquid_stock_not_excluded():
    stock = {"code": "005930", "name": "삼성전자"}
    assert classify_non_minervini(stock, _liquid_series()) == []


def test_preferred_stock_by_code_suffix():
    # KRX 보통주 코드는 끝자리 0, 우선주는 5/7/9 등 — GS우 078935, S-Oil우 010955
    for code, name in [("078935", "GS우"), ("010955", "S-Oil우"), ("005387", "현대차2우B")]:
        reasons = classify_non_minervini({"code": code, "name": name}, _liquid_series())
        assert any(r["rule"] == "preferred_stock" for r in reasons), (code, reasons)


def test_foreign_listing_by_code_prefix():
    reasons = classify_non_minervini({"code": "900260", "name": "로스웰"}, _liquid_series())
    assert any(r["rule"] == "foreign_listing" for r in reasons)


def test_low_liquidity_below_threshold():
    reasons = classify_non_minervini({"code": "093190", "name": "빅솔론"}, _thin_series())
    assert any(r["rule"] == "low_liquidity" for r in reasons)


def test_low_liquidity_respects_custom_threshold():
    # 일 20억 종목도 기준을 30억으로 올리면 저유동성
    reasons = classify_non_minervini(
        {"code": "005930", "name": "삼성전자"}, _liquid_series(), min_turnover_eok=30.0)
    assert any(r["rule"] == "low_liquidity" for r in reasons)


def test_turnover_none_when_series_missing_or_short():
    assert avg_turnover_eok(None) is None
    assert avg_turnover_eok(_series([100] * 5, [10] * 5)) is None  # 20일 미만


def test_missing_series_does_not_exclude_on_liquidity():
    # 시계열이 없으면 유동성 판정 불가 — 저유동성 사유를 붙이지 않는다
    reasons = classify_non_minervini({"code": "005930", "name": "삼성전자"}, None)
    assert reasons == []


def test_asof_cuts_lookahead():
    # asof 이전 구간은 얇고(0.68억) 이후만 두꺼운 시계열 — asof 판정은 저유동성이어야 함
    s = _thin_series(days=60)
    s["closes"] += [10_000] * 60
    s["volumes"] += [200_000] * 60
    s["dates"] = [f"2026-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}" for i in range(120)]
    asof = s["dates"][59]
    reasons = classify_non_minervini({"code": "093190", "name": "빅솔론"}, s, asof=asof)
    assert any(r["rule"] == "low_liquidity" for r in reasons)


def test_filter_universe_partitions_and_annotates():
    universe = [
        {"code": "005930", "name": "삼성전자"},
        {"code": "078935", "name": "GS우"},
        {"code": "900260", "name": "로스웰"},
    ]
    series = {"005930": _liquid_series(), "078935": _liquid_series(), "900260": _thin_series()}
    kept, dropped = filter_minervini_universe(universe, lambda c: series.get(c))
    assert [s["code"] for s in kept] == ["005930"]
    assert sorted(d["code"] for d in dropped) == ["078935", "900260"]
    roswell = next(d for d in dropped if d["code"] == "900260")
    rules = {r["rule"] for r in roswell["exclusion_reasons"]}
    assert rules == {"foreign_listing", "low_liquidity"}
