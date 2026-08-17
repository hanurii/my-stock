"""screen_buy_recommendations 청산 부담 N/M 순수 계산 테스트.

N = burden_pct = POSITION_KRW ÷ ADV20 × 100 (1,000만원 매수 시 청산 부담률)
M = split_risk_krw = ADV20 × 5% (분할매도 가능성 시작 금액, 원)
밴드: 🟢ok N<5 · 🟡caution 5≤N<30 · 🔴danger N≥30 (경계값은 위 밴드).
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import screen_buy_recommendations as sbr


def _series(closes, vols):
    return {"closes": closes, "volumes": vols}


def test_position_krw_is_real_slot():
    # 실제 슬롯 단위(26-08-17 3,000만→1,000만 정정)를 screener가 그대로 참조
    assert sbr.POSITION_KRW == 10_000_000


def test_adv20_burden_and_m_from_synthetic_series():
    # 앞 30일 거래대금 20억, 최근 20일 5억 → ADV20=5억, ADV50=14억
    closes = [10_000] * 50
    vols = [200_000] * 30 + [50_000] * 20
    f = sbr.liquidity_fields(_series(closes, vols))
    assert f["adv_20d_eok"] == 5.0
    assert f["burden_pct"] == 2.0                      # N = 1,000만/5억 = 2.0%
    assert f["split_risk_krw"] == 25_000_000           # M = 5억×5%
    assert f["liquidity"] == "ok"
    # 구 필드 하위 호환(새 POSITION_KRW로 재계산)
    assert f["adv_50d_eok"] == 14.0
    assert f["position_pct_of_adv"] == 0.7             # 1,000만/14억
    assert f["one_day_exit"] is True


def test_adv20_uses_recent_20_not_50():
    # ADV50이 가리는 최근 유동성 붕괴(대양금속형)를 ADV20이 드러내는지
    closes = [1_000] * 50
    vols = [1_190_000] * 30 + [570_000] * 20          # 11.9억 → 5.7억 붕괴
    f = sbr.liquidity_fields(_series(closes, vols))
    assert f["adv_20d_eok"] == 5.7
    assert f["burden_pct"] == 1.8                      # 1,000만/5.7억 = 1.75 → 1.8
    assert f["adv_50d_eok"] == 9.42                   # 50일 평균은 붕괴를 희석


def test_burden_band_boundaries():
    assert sbr.burden_band(None) is None
    assert sbr.burden_band(0.0) == "ok"
    assert sbr.burden_band(4.9) == "ok"
    assert sbr.burden_band(5.0) == "caution"           # 경계 5.0 → 🟡
    assert sbr.burden_band(29.9) == "caution"
    assert sbr.burden_band(30.0) == "danger"           # 경계 30.0 → 🔴
    assert sbr.burden_band(72.0) == "danger"


def test_band_exact_edge_5_from_series():
    # 거래대금 정확히 2억/일 → N=5.0 → 🟡caution
    f = sbr.liquidity_fields(_series([10_000] * 50, [20_000] * 50))
    assert f["burden_pct"] == 5.0
    assert f["liquidity"] == "caution"
    assert f["split_risk_krw"] == 10_000_000


def test_band_edge_30_after_rounding():
    # 원시 N=29.96% → 반올림 30.0 → 밴드는 표시값(반올림) 기준 🔴danger
    f = sbr.liquidity_fields(_series([1] * 50, [33_377_837] * 50))
    assert f["burden_pct"] == 30.0
    assert f["liquidity"] == "danger"
    assert f["one_day_exit"] is False


def test_m_rounding_to_int_won():
    # ADV20=111,111,111원 → M = 5,555,555.55 → 반올림 정수 5,555,556원
    f = sbr.liquidity_fields(_series([1] * 50, [111_111_111] * 50))
    assert f["split_risk_krw"] == 5_555_556
    assert isinstance(f["split_risk_krw"], int)
    assert f["adv_20d_eok"] == 1.11
    assert f["burden_pct"] == 9.0


def test_short_history_returns_none():
    f = sbr.liquidity_fields(_series([10_000] * 19, [1_000] * 19))
    assert f["adv_20d_eok"] is None and f["burden_pct"] is None
    assert f["split_risk_krw"] is None and f["liquidity"] is None


def test_zero_turnover_is_danger():
    f = sbr.liquidity_fields(_series([10_000] * 50, [0] * 50))
    assert f["adv_20d_eok"] == 0.0
    assert f["burden_pct"] is None
    assert f["split_risk_krw"] == 0
    assert f["liquidity"] == "danger"
