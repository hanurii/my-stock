import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.sell_rules import avg_volume, find_breakout_index, evaluate_accumulation, evaluate_mvp


def make_series(closes, volumes=None, highs=None, lows=None):
    """오름차순 일봉 dict 생성. 기본 고저 = 종가 ±1%, 거래량 1000."""
    n = len(closes)
    d0 = date(2026, 1, 1)
    dates = [(d0 + timedelta(days=i)).isoformat() for i in range(n)]
    return {
        "dates": dates,
        "closes": list(closes),
        "highs": list(highs) if highs else [c * 1.01 for c in closes],
        "lows": list(lows) if lows else [c * 0.99 for c in closes],
        "volumes": list(volumes) if volumes else [1000.0] * n,
    }


# --- avg_volume ---

def test_avg_volume_excludes_current_day():
    vols = [1000.0] * 10 + [9999.0]  # 판정일(마지막)은 평균에서 제외
    assert avg_volume(vols, 10) == 1000.0


def test_avg_volume_none_when_insufficient_sample():
    assert avg_volume([1000.0] * 3, 3) is None  # 직전 3일 < min_days 5


def test_avg_volume_caps_window_at_50():
    vols = [2000.0] * 30 + [1000.0] * 50 + [1.0]
    assert avg_volume(vols, 80) == 1000.0  # 직전 50일만


# --- find_breakout_index ---

def test_find_breakout_detects_pivot_cross():
    closes = [100.0] * 10 + [106.0, 107.0]  # index 10에서 피벗 105 상향 돌파
    s = make_series(closes)
    bi, estimated = find_breakout_index(s, s["dates"][-1], 105.0)
    assert bi == 10
    assert estimated is False


def test_find_breakout_falls_back_to_buy_date_when_no_cross():
    closes = [100.0] * 12  # 피벗 105를 넘은 날 없음
    s = make_series(closes)
    bi, estimated = find_breakout_index(s, s["dates"][5], 105.0)
    assert bi == 5
    assert estimated is True


def test_find_breakout_no_pivot_uses_buy_date():
    s = make_series([100.0] * 12)
    bi, estimated = find_breakout_index(s, s["dates"][7], None)
    assert bi == 7
    assert estimated is True


def test_find_breakout_buy_date_between_trading_days():
    # 매수일이 휴장일이면 그 이전 마지막 거래일을 매수일로 취급
    s = make_series([100.0] * 5)
    bi, estimated = find_breakout_index(s, "2026-12-31", None)
    assert bi == 4  # 마지막 거래일
    assert estimated is True


# --- Rule imports for 규칙 ① ② ③ ---

from canslim_lib.sell_rules import (
    rule_low_volume_breakout,
    rule_heavy_volume_pullback,
    rule_consecutive_lower_lows,
)


# --- 규칙 ① 저거래량 돌파 ---

def test_rule1_violation_below_average_volume():
    vols = [1000.0] * 30 + [800.0]
    s = make_series([100.0] * 31, volumes=vols)
    r = rule_low_volume_breakout(s, 30)
    assert r["status"] == "violation"


def test_rule1_pass_but_weak_between_1x_and_1p5x():
    vols = [1000.0] * 30 + [1200.0]
    s = make_series([100.0] * 31, volumes=vols)
    r = rule_low_volume_breakout(s, 30)
    assert r["status"] == "pass"
    assert "1.5배" in r["detail"]  # 정상 돌파 기준 미달 경고 문구


def test_rule1_pass_strong_volume():
    vols = [1000.0] * 30 + [2100.0]
    s = make_series([100.0] * 31, volumes=vols)
    r = rule_low_volume_breakout(s, 30)
    assert r["status"] == "pass"
    assert "1.5배" not in r["detail"]


def test_rule1_pending_insufficient_history():
    s = make_series([100.0] * 3)
    assert rule_low_volume_breakout(s, 2)["status"] == "pending"


def test_rule1_zero_breakout_volume_is_violation():
    vols = [1000.0] * 30 + [0.0]
    s = make_series([100.0] * 31, volumes=vols)
    assert rule_low_volume_breakout(s, 30)["status"] == "violation"


def test_rule1_none_breakout_volume_is_pending():
    vols = [1000.0] * 30 + [None]
    s = make_series([100.0] * 31, volumes=vols)
    assert rule_low_volume_breakout(s, 30)["status"] == "pending"


# --- 규칙 ② 대량 거래 후퇴 ---

def test_rule2_violation_down_close_on_heavy_volume():
    closes = [100.0] * 30 + [106.0, 103.0]   # 돌파(30) 후 하락 마감
    vols = [1000.0] * 31 + [1800.0]          # 하락일 거래량 1.8배
    s = make_series(closes, volumes=vols)
    r = rule_heavy_volume_pullback(s, 30)
    assert r["status"] == "violation"


def test_rule2_pass_down_close_on_light_volume():
    closes = [100.0] * 30 + [106.0, 103.0]
    vols = [1000.0] * 31 + [900.0]
    s = make_series(closes, volumes=vols)
    assert rule_heavy_volume_pullback(s, 30)["status"] == "pass"


def test_rule2_pass_heavy_volume_but_up_close():
    closes = [100.0] * 30 + [106.0, 109.0]
    vols = [1000.0] * 31 + [3000.0]
    s = make_series(closes, volumes=vols)
    assert rule_heavy_volume_pullback(s, 30)["status"] == "pass"


def test_rule2_pending_no_post_breakout_days():
    s = make_series([100.0] * 31)
    assert rule_heavy_volume_pullback(s, 30)["status"] == "pending"


# --- 규칙 ③ 연속 저저점 (저가 < 전일 저가 + 거래량 ≥ 50일 평균) ---

def test_rule3_violation_three_vol_backed_lower_lows():
    # 저가가 3일 연속 하락 + 각 날 거래량이 50일 평균(1000) 이상
    lows = [99.0] * 50 + [98.0, 97.0, 96.0]          # 마지막 3일 저점경신
    closes = [100.0] * 50 + [99.0, 98.0, 97.0]
    vols = [1000.0] * 50 + [1200.0, 1300.0, 1400.0]  # 거래량 붙음
    s = make_series(closes, volumes=vols, lows=lows)
    r = rule_consecutive_lower_lows(s, 49)
    assert r["status"] == "violation"
    assert "거래량 붙은 저점경신" in r["detail"]


def test_rule3_pass_lower_lows_but_light_volume():
    # 저점경신 3연속이지만 거래량이 평균 미만 → 위반 아님(🟡경고)
    lows = [99.0] * 50 + [98.0, 97.0, 96.0]
    closes = [100.0] * 50 + [99.0, 98.0, 97.0]
    vols = [1000.0] * 50 + [700.0, 800.0, 600.0]     # 거래량 낮음
    s = make_series(closes, volumes=vols, lows=lows)
    r = rule_consecutive_lower_lows(s, 49)
    assert r["status"] == "watch"
    assert "🟡" in r["detail"]


def test_rule3_pass_two_vol_backed_lower_lows():
    # 거래량 붙은 저점경신이 2일뿐 → 위반 아님
    lows = [99.0] * 50 + [98.0, 97.0, 99.5]          # 3일째는 저점경신 아님
    closes = [100.0] * 50 + [99.0, 98.0, 100.0]
    vols = [1000.0] * 50 + [1200.0, 1300.0, 1400.0]
    s = make_series(closes, volumes=vols, lows=lows)
    assert rule_consecutive_lower_lows(s, 49)["status"] == "pass"


def test_rule3_pending_no_post_breakout_days():
    s = make_series([100.0] * 51)
    assert rule_consecutive_lower_lows(s, 50)["status"] == "pending"


# --- 규칙 ④ 이평선 아래 마감 ---

from canslim_lib.sell_rules import (
    rule_close_below_ma,
    rule_weak_days_dominant,
    rule_breakout_failure,
)


def test_rule4_violation_close_below_ma20():
    # 60일 100 유지 → 돌파 106 → 90 급락(20일선 약 100 아래)
    closes = [100.0] * 60 + [106.0, 90.0]
    s = make_series(closes)
    r = rule_close_below_ma(s, 60)
    assert r["status"] == "violation"


def test_rule4_severe_below_ma50_on_heavy_volume():
    closes = [100.0] * 60 + [106.0, 80.0]  # 50일선(약 100)도 하회
    vols = [1000.0] * 61 + [2000.0]        # 대량 거래
    s = make_series(closes, volumes=vols)
    r = rule_close_below_ma(s, 60)
    assert r["status"] == "violation"
    assert "심각" in r["detail"]


def test_rule4_pass_holds_above_ma20():
    closes = [100.0] * 60 + [106.0, 107.0, 108.0]
    s = make_series(closes)
    assert rule_close_below_ma(s, 60)["status"] == "pass"


def test_rule4_detail_shows_days_after_breakout():
    closes = [100.0] * 60 + [106.0, 90.0]  # 돌파(60) 다음 날(61) 20일선 이탈
    s = make_series(closes)
    r = rule_close_below_ma(s, 60)
    assert r["status"] == "violation"
    assert "돌파 1거래일째" in r["detail"]


def test_rule4_pending_no_post_breakout_days():
    closes = [100.0] * 61
    s = make_series(closes)
    assert rule_close_below_ma(s, 60)["status"] == "pending"


# --- 규칙 ⑤ 하락일·나쁜 마감 우세 (통합) ---

def test_rule5_pending_under_five_days():
    closes = [100.0] * 30 + [106.0, 105.0, 104.0]  # 경과 2일
    s = make_series(closes)
    assert rule_weak_days_dominant(s, 30)["status"] == "pending"


def test_rule5_violation_more_down_days():
    # 경과 6일: 하락 4 · 상승 2
    closes = [100.0] * 30 + [106.0, 104.0, 102.0, 103.0, 101.0, 99.0, 100.0]
    s = make_series(closes)
    r = rule_weak_days_dominant(s, 30)
    assert r["status"] == "violation"


def test_rule5_violation_more_bad_closes():
    # 종가는 계속 오르는데(하락일 0) 매일 일중 고점에서 크게 밀려 하단 마감
    closes = [100.0] * 30 + [106.0 + i for i in range(7)]
    highs = [c * 1.01 for c in closes[:31]] + [c + 10 for c in closes[31:]]
    lows = [c * 0.99 for c in closes[:31]] + [c - 0.5 for c in closes[31:]]
    s = make_series(closes, highs=highs, lows=lows)
    r = rule_weak_days_dominant(s, 30)
    assert r["status"] == "violation"


def test_rule5_pass_up_days_dominant():
    # 경과 6일 모두 상승, 기본 고저(±1%)면 종가=중간값이라 나쁜/좋은 마감 모두 0
    closes = [100.0] * 30 + [106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0]
    s = make_series(closes)
    assert rule_weak_days_dominant(s, 30)["status"] == "pass"


# --- 규칙 ⑥ 돌파 실패 (스쿼트 + 거래량 비대칭 통합) ---

def test_rule6_violation_volume_backed_break_ignores_grace():
    # 돌파 다음 날 피벗 아래로 되밀림 + 거래량 > 돌파일 → 유예 무시 위반
    closes = [100.0] * 30 + [106.0, 103.0]
    vols = [1000.0] * 30 + [500.0, 900.0]   # 돌파일 500 < 되밀림일 900
    s = make_series(closes, volumes=vols)
    r = rule_breakout_failure(s, 30, 105.0)
    assert r["status"] == "violation"
    assert "거래량 동반" in r["detail"]


def test_rule6_pass_quiet_squat_within_grace():
    # 조용한 스쿼트(거래량 ≤ 돌파일) + 유예(10거래일) 이내 → 관찰중(pass)
    closes = [100.0] * 30 + [106.0, 103.0]
    vols = [1000.0] * 30 + [2000.0, 800.0]  # 되밀림일 800 < 돌파일 2000
    s = make_series(closes, volumes=vols)
    r = rule_breakout_failure(s, 30, 105.0)
    assert r["status"] == "watch"
    assert "관찰중" in r["detail"]


def test_rule6_violation_quiet_squat_past_grace():
    # 조용한 스쿼트인데 유예(10거래일) 초과도 피벗 아래 → 위반
    closes = [100.0] * 30 + [106.0] + [103.0] * 12  # 돌파 후 12일 내내 아래
    vols = [1000.0] * 30 + [2000.0] + [800.0] * 12
    s = make_series(closes, volumes=vols)
    r = rule_breakout_failure(s, 30, 105.0)
    assert r["status"] == "violation"
    assert "유예 초과" in r["detail"]


def test_rule6_pass_reversal_recovery():
    # 스쿼트 후 최근 종가가 피벗 위로 복귀 → pass
    closes = [100.0] * 30 + [106.0, 103.0, 107.0]
    vols = [1000.0] * 30 + [2000.0, 800.0, 900.0]
    s = make_series(closes, volumes=vols)
    r = rule_breakout_failure(s, 30, 105.0)
    assert r["status"] == "pass"
    assert "회복" in r["detail"]


def test_rule6_pass_holds_above_pivot():
    closes = [100.0] * 30 + [106.0, 107.0]
    s = make_series(closes)
    assert rule_breakout_failure(s, 30, 105.0)["status"] == "pass"


def test_rule6_na_without_pivot():
    s = make_series([100.0] * 32)
    assert rule_breakout_failure(s, 30, None)["status"] == "na"


def test_rule6_na_when_breakout_not_confirmed():
    closes = [100.0] * 30 + [101.0, 102.0]  # 피벗 105 미돌파
    s = make_series(closes)
    r = rule_breakout_failure(s, 30, 105.0, breakout_confirmed=False)
    assert r["status"] == "na"


def test_find_breakout_detects_intraday_cross():
    # 종가는 피벗 아래여도 장중 고가가 피벗을 넘었으면 돌파일로 인정 (고가 기준)
    closes = [100.0] * 10 + [103.0, 102.0]
    highs = [c * 1.01 for c in closes[:10]] + [106.0, 103.5]
    s = make_series(closes, highs=highs)
    bi, estimated = find_breakout_index(s, s["dates"][-1], 105.0)
    assert bi == 10
    assert estimated is False


def test_evaluate_holding_intraday_squat_flow():
    # 장중 돌파(고가 106>피벗 105) 후 당일 조용히 아래 마감 → 돌파 확인 + 관찰중(pass)
    closes = [100.0] * 60 + [103.0]
    highs = [c * 1.01 for c in closes[:60]] + [106.0]
    s = make_series(closes, highs=highs)
    r = evaluate_holding(s, s["dates"][60], 103.0, -4.0, pivot_price=105.0)
    assert r["breakout_date_estimated"] is False
    assert r["rules"][5]["status"] == "watch"
    assert "관찰중" in r["rules"][5]["detail"]


# --- evaluate_holding ---

from canslim_lib.sell_rules import evaluate_holding


def _clean_series():
    """위반 없는 시나리오: 대량 거래 돌파 후 얕은 상승 유지."""
    closes = [100.0] * 60 + [106.0, 107.0, 108.0]
    vols = [1000.0] * 60 + [2000.0, 900.0, 900.0]
    return make_series(closes, volumes=vols)


def test_evaluate_holding_hold_when_clean():
    s = _clean_series()
    r = evaluate_holding(s, s["dates"][60], 106.0, -4.0, pivot_price=105.0)
    assert r["signal"] == "hold"
    assert r["violation_count"] == 0
    assert r["breakout_date"] == s["dates"][60]
    assert r["breakout_date_estimated"] is False
    assert len(r["rules"]) == 6


def test_evaluate_holding_early_sell_counts_violations():
    # 저거래량 돌파(①) + 피벗 아래 복귀(⑥) → 위반 2건
    closes = [100.0] * 60 + [106.0, 103.0]
    vols = [1000.0] * 60 + [800.0, 900.0]
    s = make_series(closes, volumes=vols)
    r = evaluate_holding(s, s["dates"][60], 106.0, -4.0, pivot_price=105.0)
    assert r["signal"] == "early_sell"
    assert r["violation_count"] == 2


def test_evaluate_holding_stop_loss_overrides_rules():
    # 현재가 95 <= 손절가 106*0.96=101.76 → 위반과 무관하게 손절 신호
    closes = [100.0] * 60 + [106.0, 95.0]
    s = make_series(closes)
    r = evaluate_holding(s, s["dates"][60], 106.0, -4.0, pivot_price=105.0)
    assert r["signal"] == "stop_loss"
    assert r["stop_price"] == 101.76


def test_evaluate_holding_estimated_breakout_without_pivot():
    s = _clean_series()
    r = evaluate_holding(s, s["dates"][60], 106.0, -4.0, pivot_price=None)
    assert r["breakout_date_estimated"] is True
    assert r["rules"][5]["status"] == "na"  # 스쿼트는 피벗 없어 판정 불가


def test_evaluate_holding_pct_to_stop_sign():
    s = _clean_series()
    r = evaluate_holding(s, s["dates"][60], 106.0, -4.0, pivot_price=105.0)
    # 현재가 108 > 손절가 101.76 → 음수(여유)
    assert r["pct_to_stop"] < 0


def test_evaluate_holding_uncrossed_pivot_squat_na():
    # 피벗이 한 번도 돌파된 적 없으면 돌파일=매수일 추정 + 스쿼트 판정 불가
    closes = [100.0] * 60 + [101.0, 102.0]
    s = make_series(closes)
    r = evaluate_holding(s, s["dates"][60], 101.0, -4.0, pivot_price=200.0)
    assert r["breakout_date_estimated"] is True
    assert r["rules"][5]["status"] == "na"


# --- evaluate_accumulation: 매집 신호 3종 ---

def test_accum_up_days_and_quality_met():
    # 돌파(30) 후 상승 우세 + 상단 마감 우세
    closes = [100.0] * 31 + [102.0, 104.0, 103.5, 106.0]
    highs = [c * 1.005 for c in closes]           # 종가가 고저 중간보다 위(좋은 마감)
    lows = [c * 0.98 for c in closes]
    s = make_series(closes, highs=highs, lows=lows)
    r = evaluate_accumulation(s, 30)
    ids = {x["id"]: x["status"] for x in r["signals"]}
    assert ids["up_days_dominant"] == "met"       # 상승 3 · 하락 1
    assert ids["quality_closes"] == "met"
    assert r["elapsed"] == 4 and r["window"] == "D+4/15"


def test_accum_up_streak_7_met_and_window_locks_at_15():
    # 돌파 후 8일 연속 상승 → streak met, 16일 이상이면 창 고정("15일 완료")
    closes = [100.0] * 31 + [100.0 + i for i in range(1, 20)]
    s = make_series(closes)
    r = evaluate_accumulation(s, 30)
    ids = {x["id"]: x["status"] for x in r["signals"]}
    assert ids["up_streak_7"] == "met"
    assert r["window"] == "15일 완료"


def test_accum_window_computation_capped_at_first_15_days():
    # 첫 15일은 전부 하락(상승 0·하락 15), 그 뒤 16일은 전부 상승.
    # 창이 첫 15일로 고정되면 up_days_dominant=unmet. 캡이 없으면(전체 집계) met으로 뒤집힘.
    closes = ([100.0] * 31
              + [100.0 - i for i in range(1, 16)]     # idx31..45: 99→85 (15일 하락)
              + [85.0 + i for i in range(1, 17)])     # idx46..61: 86→101 (16일 상승)
    s = make_series(closes)
    r = evaluate_accumulation(s, 30)
    up = next(x for x in r["signals"] if x["id"] == "up_days_dominant")
    assert up["status"] == "unmet"
    assert "상승 0" in up["detail"]        # 캡 제거 시 '상승 16 · 하락 15'로 met → 실패
    assert r["window"] == "15일 완료"


def test_accum_pending_when_no_post_breakout_days():
    s = make_series([100.0] * 31)
    r = evaluate_accumulation(s, 30)
    assert all(x["status"] == "pending" for x in r["signals"])


def test_accum_tight_day_not_counted_as_bad_close():
    # 종가가 중간값보다 '아래'(진짜 나쁜 마감 후보)지만 일중 변동폭 <1% (tight)
    # → tight 가드로만 나쁜 마감서 제외됨(대칭 고저의 tie 규칙과 무관).
    closes = [100.0] * 31 + [100.0, 100.0, 100.0]
    highs = [c * 1.01 for c in closes[:31]] + [100.6, 100.6, 100.6]
    lows = [c * 0.99 for c in closes[:31]] + [99.8, 99.8, 99.8]   # mid=100.2 > close 100, range 0.8/100=0.008<1%
    s = make_series(closes, highs=highs, lows=lows)
    r = evaluate_accumulation(s, 30)
    q = next(x for x in r["signals"] if x["id"] == "quality_closes")
    assert "나쁜 0" in q["detail"]   # 가드 제거 시 '나쁜 3'이 되어 실패


# --- evaluate_mvp: M·V·P 감별 ---

def _mvp_series():
    # 직전 15일 거래량 1000, 돌파 후 15일: 12일 상승 + 거래량 2000(2배) + 최고 종가 +25%
    pre = [100.0] * 16                     # index 0..15 (bi=15)
    post_up = [100.0 + 2 * (i + 1) for i in range(12)]   # 12일 상승 → 최고 +24~
    post = post_up + [post_up[-1] - 1, post_up[-1] - 2, post_up[-1] + 3]  # 3일 혼합, 마지막 신고가
    closes = pre + post
    vols = [1000.0] * 16 + [2000.0] * 15
    return make_series(closes, volumes=vols), 15


def test_mvp_yes_when_all_three_met():
    s, bi = _mvp_series()
    r = evaluate_mvp(s, bi)
    assert r["status"] == "yes"
    assert r["m"]["ok"] and r["v"]["ok"] and r["p"]["ok"]


def test_mvp_pending_before_15_days():
    closes = [100.0] * 16 + [101.0, 102.0, 103.0]   # bi=15, 경과 3일
    s = make_series(closes)
    r = evaluate_mvp(s, 15)
    assert r["status"] == "pending"
    assert r["m"]["ok"] is None


def test_mvp_no_when_price_short():
    # M·V 충족해도 P<20%면 no
    pre = [100.0] * 16
    post = [100.0 + 0.5 * (i + 1) for i in range(15)]   # 최고 +7.5%
    s = make_series(pre + post, volumes=[1000.0] * 16 + [2000.0] * 15)
    r = evaluate_mvp(s, 15)
    assert r["status"] == "no"
    assert r["p"]["ok"] is False
