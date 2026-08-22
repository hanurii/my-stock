"""변동성 파일럿 백테스트의 정확성 부품 테스트.

이 스크립트는 연구용 하네스지만, 결론을 좌우하는 네 가지 수정(entry_ready 게이트·
시점 유니버스·원본 거래대금·ATR 정의)은 틀리면 결과가 통째로 무의미해지므로 고정한다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import backtest_volatility_pilot as bt  # noqa: E402


# ── ATR: 장중 폭과 갭을 담아야 한다 ─────────────────────────────────────────

def _flat_series(n=30, price=1000.0, rng=0.0):
    return {
        "dates": [f"2026-01-{i + 1:02d}" for i in range(n)],
        "closes": [price] * n,
        "highs": [price + rng / 2] * n,
        "lows": [price - rng / 2] * n,
        "opens": [price] * n,
        "volumes": [1000] * n,
    }


def test_atr_of_a_motionless_stock_is_zero():
    assert bt.atr_pct(_flat_series(rng=0.0)) == 0.0


def test_atr_is_daily_range_over_price():
    # 매일 고-저 폭이 50원인 1,000원 종목 → 하루 평균 변동폭 5%
    assert bt.atr_pct(_flat_series(rng=50.0)) == 5.0


def test_atr_counts_the_overnight_gap_not_just_the_intraday_range():
    """종가끼리의 표준편차 대신 ATR 을 쓰는 이유 — 갭이 잡혀야 한다."""
    n = 30
    s = _flat_series(n)
    # 마지막 날만 통째로 +100원 갭업(장중 폭은 0)
    s["closes"][-1] = 1100.0
    s["highs"][-1] = 1100.0
    s["lows"][-1] = 1100.0
    v = bt.atr_pct(s)
    assert v is not None and v > 0.0   # 장중 폭이 0이어도 갭이 변동으로 잡힌다


def test_atr_needs_enough_bars():
    assert bt.atr_pct(_flat_series(n=5)) is None


def test_atr_bands_are_fixed_upfront():
    # 경계는 사후 최적화가 아니라 사전 고정값이어야 한다
    assert bt.atr_band(1.0) == "①조용 <2.5%"
    assert bt.atr_band(2.5) == "②보통 2.5~4%"
    assert bt.atr_band(4.0) == "③큼 4~6%"
    assert bt.atr_band(6.0) == "④매우큼 6%+"
    assert bt.atr_band(None) == "미상"


# ── 거래대금: 미래를 보지 않는다 ────────────────────────────────────────────

def _hist(dates, vals):
    return (list(dates), list(vals))


def test_turnover_ignores_days_after_asof():
    dates = [f"2026-01-{i:02d}" for i in range(1, 31)]
    vals = [10.0] * 25 + [999.0] * 5          # 26일차부터 폭증
    got = bt.avg_turnover_asof(_hist(dates, vals), "2026-01-25", window=25)
    assert got == 10.0                        # 미래의 폭증이 섞이면 안 된다


def test_turnover_uses_only_the_last_window_days():
    dates = [f"2026-01-{i:02d}" for i in range(1, 31)]
    vals = [999.0] * 20 + [10.0] * 10         # 최근 10일만 조용
    got = bt.avg_turnover_asof(_hist(dates, vals), "2026-01-30", window=10)
    assert got == 10.0


def test_turnover_returns_none_when_sample_is_short():
    assert bt.avg_turnover_asof(_hist(["2026-01-01"], [10.0]), "2026-01-01", window=50) is None
    assert bt.avg_turnover_asof(None, "2026-01-01") is None


# ── 진입 게이트: 검출 없이 status 만으로 통과하면 안 된다 ───────────────────

class _FakeResult(dict):
    pass


def test_actionable_without_detection_is_rejected(monkeypatch):
    """기존 백테스트의 3배 부풀림 원인 — status 만 보던 것을 막는다."""
    monkeypatch.setattr(bt, "evaluate_vcp",
                        lambda st: {"status": "actionable", "vcp_detected": False, "pivot_price": 100.0})
    assert bt.detect_entry_ready({}, "VCP") is None


def test_detected_and_actionable_is_accepted(monkeypatch):
    monkeypatch.setattr(bt, "evaluate_vcp",
                        lambda st: {"status": "actionable", "vcp_detected": True, "pivot_price": 100.0})
    assert bt.detect_entry_ready({}, "VCP") == 100.0


def test_already_broken_out_is_rejected(monkeypatch):
    """돌파 뒤 진입은 이 설계(익일 돌파 매수)에서 사후 진입이 되므로 제외."""
    monkeypatch.setattr(bt, "evaluate_vcp",
                        lambda st: {"status": "breakout", "vcp_detected": True, "pivot_price": 100.0})
    assert bt.detect_entry_ready({}, "VCP") is None


def test_pattern_detected_flag_is_used_for_3c_and_power_play(monkeypatch):
    monkeypatch.setattr(bt, "evaluate_cheat",
                        lambda st, p: {"status": "actionable", "pattern_detected": False, "pivot_price": 100.0})
    assert bt.detect_entry_ready({}, "3C") is None
    monkeypatch.setattr(bt, "evaluate_power_play",
                        lambda st: {"status": "actionable", "pattern_detected": True, "pivot_price": 55.0})
    assert bt.detect_entry_ready({}, "PP") == 55.0


def test_detector_exception_is_swallowed(monkeypatch):
    def boom(st):
        raise ValueError("bad series")
    monkeypatch.setattr(bt, "evaluate_vcp", boom)
    assert bt.detect_entry_ready({}, "VCP") is None


# ── 손익비·필터 상수가 현행 규칙과 일치 ─────────────────────────────────────

def test_uses_current_risk_reward_and_liquidity_rules():
    assert (bt.TARGET_PCT, bt.STOP_PCT) == (20.0, 10.0)   # 26-08-13 이후 규칙
    assert bt.MIN_TURNOVER_EOK == 5.0                      # 미너비니 저유동성 컷
    assert bt.RS_MIN == 80


def test_exclude_pattern_drops_non_minervini_names():
    for bad in ("삼성스팩1호", "케이리츠", "TIGER ETF", "미래ETN", "맥쿼리인프라",
                "삼성전자우", "현대차2우B", "대신증권우C"):
        assert bt.EXCLUDE_PATTERN.search(bad), bad
    for ok in ("삼성전자", "아스플로", "골프존홀딩스", "코스맥스엔비티"):
        assert not bt.EXCLUDE_PATTERN.search(ok), ok


# ── 갭업 체결가 보정 (26-08-22, 감사 지적) ──────────────────────────────────
# 익일 시가가 이미 피벗 위면 실제 체결가는 피벗이 아니라 시가다. 피벗으로 계산하면
# 기대값이 일관되게 부풀려진다(실측: 갭업 32.2%, 전체 기대값 +2.16%→+1.48%).

def test_entry_price_is_the_pivot_when_the_open_is_below_it():
    assert bt.entry_price(pivot=1000.0, open_px=980.0) == 1000.0


def test_entry_price_is_the_open_when_it_gaps_above_the_pivot():
    assert bt.entry_price(pivot=1000.0, open_px=1080.0) == 1080.0


def test_entry_price_falls_back_to_the_pivot_when_the_open_is_missing():
    assert bt.entry_price(pivot=1000.0, open_px=None) == 1000.0


# ── 우선주 정규식 누출 (감사 지적: CJ4우(전환) 통과) ────────────────────────

def test_exclude_pattern_catches_convertible_preferred_names():
    for bad in ("CJ4우(전환)", "한화3우B", "대신우(전환)"):
        assert bt.EXCLUDE_PATTERN.search(bad), bad


# ── 룩어헤드 필드는 이름으로 경고 ───────────────────────────────────────────

def test_lookahead_volume_field_is_named_so_nobody_filters_on_it():
    """진입일 '종일' 거래량은 장중엔 알 수 없다. 이걸 필터로 쓰면 과거 69%→41% 붕괴가 재현된다."""
    assert bt.REL_VOL_FIELD.endswith("_LOOKAHEAD_DO_NOT_FILTER")
