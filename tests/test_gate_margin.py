"""관문 여유도(gate margin) 계산 테스트 — canslim_lib.trend_template.compute_gate_margin.

8조건은 통과/탈락 이진 판정이라 "1%p 차이로 겨우 통과"와 "두 배 여유로 통과"가
똑같아 보인다. 조건마다 '여유'를 재고 **가장 빡빡한 조건 하나**로 종합 점수를 낸다.

여유율 = min(실제 여유 ÷ '충분' 기준, 1) × 100  (조건별 단위가 달라 정규화)
종합 점수 = 8조건 여유율의 **최솟값** (제일 약한 고리가 그 종목의 여유다)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.trend_template import (  # noqa: E402
    GATE_MARGIN_REF,
    compute_gate_margin,
    evaluate_trend_template,
)


def _series(**kw):
    """조건별 여유를 직접 지정해 만든 가짜 평가 결과."""
    base = {
        "sma50": 100.0, "sma150": 90.0, "sma200": 80.0,
        "sma200_1m_ago": 76.0, "sma200_5m_ago": 60.0,
        "high_52w": 130.0, "low_52w": 50.0,
    }
    base.update(kw)
    return {
        "pass": True,
        "passed_count": 8,
        "criteria": {str(i): {"pass": True} for i in range(1, 9)},
        "extras": base,
    }


# ── 기준값(정본) ─────────────────────────────────────────────────────────────

def test_reference_margins_are_defined_for_all_eight():
    assert set(GATE_MARGIN_REF) == {str(i) for i in range(1, 9)}
    # ⑦ 52주고가: 기준 -25% → 고가 -5%까지 오면 여유 만점(20%p)
    assert GATE_MARGIN_REF["7"] == 20.0
    # ⑧ RS: 합격선 +10점(RS 90)이면 만점
    assert GATE_MARGIN_REF["8"] == 10.0


# ── 조건별 여유 ──────────────────────────────────────────────────────────────

def test_condition7_margin_is_distance_from_the_25pct_line():
    # 종가 117 vs 52주고가 130 → -10.0% → 기준(-25%)까지 15%p 남음 → 15/20 = 75%
    m = compute_gate_margin(_series(), close=117.0, rs=90, rs_min=80)
    assert m["per_condition"]["7"]["margin"] == 15.0
    assert m["per_condition"]["7"]["pct"] == 75.0


def test_condition7_at_the_line_is_zero_margin():
    # 종가 97.5 = 130 × 0.75 → 정확히 -25% → 여유 0
    m = compute_gate_margin(_series(), close=97.5, rs=90, rs_min=80)
    assert m["per_condition"]["7"]["margin"] == 0.0
    assert m["per_condition"]["7"]["pct"] == 0.0


def test_condition7_far_above_is_capped_at_100():
    # 종가 130(신고가) → 여유 25%p 이지만 기준 20%p 이므로 100% 로 자른다
    m = compute_gate_margin(_series(), close=130.0, rs=99, rs_min=80)
    assert m["per_condition"]["7"]["pct"] == 100.0


def test_condition8_margin_is_rs_above_the_bar():
    m = compute_gate_margin(_series(), close=120.0, rs=84, rs_min=80)
    assert m["per_condition"]["8"]["margin"] == 4.0
    assert m["per_condition"]["8"]["pct"] == 40.0


def test_condition5_margin_is_percent_above_the_50ma():
    # 종가 105 vs 50MA 100 → +5.0% → 기준 5% → 100%
    m = compute_gate_margin(_series(), close=105.0, rs=99, rs_min=80)
    assert m["per_condition"]["5"]["margin"] == 5.0
    assert m["per_condition"]["5"]["pct"] == 100.0


def test_condition1_uses_the_nearer_of_150ma_and_200ma():
    # 종가 99 vs 150MA 90(+10%)·200MA 80(+23.75%) → 더 빡빡한 150MA 기준
    m = compute_gate_margin(_series(), close=99.0, rs=99, rs_min=80)
    assert m["per_condition"]["1"]["margin"] == 10.0


def test_condition3_margin_is_200ma_rise_over_a_month():
    # 200MA 80 vs 한 달 전 76 → +5.26%
    m = compute_gate_margin(_series(), close=120.0, rs=99, rs_min=80)
    assert round(m["per_condition"]["3"]["margin"], 2) == 5.26


# ── 종합: 가장 빡빡한 조건이 점수를 정한다 ───────────────────────────────────

def test_score_is_the_weakest_condition():
    # ⑧ RS 82 → 여유 2점/10 = 20% 로 가장 약함
    m = compute_gate_margin(_series(), close=128.0, rs=82, rs_min=80)
    assert m["score"] == 20.0
    assert m["tightest"] == "8"
    assert "RS" in m["tightest_label"]


def test_tightest_reports_a_readable_detail():
    # 종가 105: ⑤는 +5%(만점)인데 ⑦은 -19.2%로 기준까지 5.8%p → ⑦이 가장 빡빡
    m = compute_gate_margin(_series(), close=105.0, rs=99, rs_min=80)
    assert m["tightest"] == "7"
    assert "52주고가" in m["tightest_label"]
    assert "-19.2%" in m["tightest_detail"]


def test_price_sitting_exactly_on_the_50ma_is_the_weakest_link():
    # 종가 = 50MA → ⑤ 여유 0 → 다른 조건이 아무리 넉넉해도 점수 0
    m = compute_gate_margin(_series(), close=100.0, rs=99, rs_min=80)
    assert m["tightest"] == "5"
    assert m["score"] == 0.0


def test_all_conditions_comfortable_scores_high():
    m = compute_gate_margin(
        _series(sma50=80.0, sma150=70.0, sma200=60.0, sma200_1m_ago=55.0,
                high_52w=125.0, low_52w=40.0),
        close=120.0, rs=95, rs_min=80,
    )
    assert m["score"] >= 75.0


# ── 계산 불가 ────────────────────────────────────────────────────────────────

def test_missing_close_returns_none():
    assert compute_gate_margin(_series(), close=None, rs=90, rs_min=80) is None


def test_missing_extras_returns_none():
    bad = _series()
    bad["extras"]["sma200"] = None
    assert compute_gate_margin(bad, close=120.0, rs=90, rs_min=80) is None


def test_missing_rs_returns_none():
    assert compute_gate_margin(_series(), close=120.0, rs=None, rs_min=80) is None


# ── 실제 평가 결과와 맞물린다 ────────────────────────────────────────────────

def test_works_on_real_evaluate_output():
    # 완만히 오르는 시계열 → 8조건 통과 + 여유 계산 가능
    closes = [100.0 * (1.004 ** i) for i in range(320)]
    r = evaluate_trend_template(closes, rs=90, rs_min=80)
    assert r["pass"] is True
    m = compute_gate_margin(r, close=closes[-1], rs=90, rs_min=80)
    assert m is not None
    assert 0.0 <= m["score"] <= 100.0
    assert m["tightest"] in {str(i) for i in range(1, 9)}
