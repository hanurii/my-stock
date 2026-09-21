"""종가 출처 대조기의 «순수 로직» 시험.

이 검사기의 값어치는 「문턱을 결과 보기 전에 박았다」는 데 있다. 그래서 시험도
문턱이 «움직이지 않는지»를 먼저 본다.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_close_source import (  # noqa: E402
    HIT_AT_OR_ABOVE, MISS_BELOW, chain_ok, divergence_rate, verdict,
)


# ── 문턱이 박혀 있는가 ───────────────────────────────────────

def test_문턱이_사전등록값_그대로():
    """결과를 보고 문턱을 옮기면 사전등록이 장식이 된다. 값을 시험이 붙잡는다."""
    assert HIT_AT_OR_ABOVE == 50.0
    assert MISS_BELOW == 20.0


def test_적중과_빗나감_사이에_못가림이_있다():
    """이분법이면 애매한 결과가 한쪽으로 끌려간다."""
    assert MISS_BELOW < HIT_AT_OR_ABOVE


# ── verdict ──────────────────────────────────────────────────

@pytest.mark.parametrize("rate,expect", [
    (93.0, "예측 적중"), (50.0, "예측 적중"), (49.9, "못 가림"),
    (20.0, "못 가림"), (19.9, "예측 빗나감"), (0.0, "예측 빗나감"),
])
def test_판정은_문턱으로만_정해진다(rate, expect):
    assert verdict(rate) == expect


# ── divergence_rate ──────────────────────────────────────────

def test_전부_같으면_0퍼센트():
    r = divergence_rate([(100.0, 100.0), (200.0, 200.0)])
    assert r["bad"] == 0
    assert r["rate"] == pytest.approx(0.0)


def test_전부_다르면_100퍼센트():
    r = divergence_rate([(101.0, 100.0), (202.0, 200.0)])
    assert r["bad"] == 2
    assert r["rate"] == pytest.approx(100.0)


def test_1원_차이도_어긋남으로_센다():
    """0.5 는 부동소수 반올림만 흡수한다. 1원은 진짜 차이다."""
    r = divergence_rate([(10001.0, 10000.0)])
    assert r["bad"] == 1


def test_아주_작은_차이는_안_센다():
    r = divergence_rate([(10000.3, 10000.0)])
    assert r["bad"] == 0


def test_빈_입력에_안_터진다():
    r = divergence_rate([])
    assert r == {"n": 0, "bad": 0, "rate": 0.0, "median_pct": 0.0}


def test_중앙_차이는_퍼센트로_나온다():
    r = divergence_rate([(102.0, 100.0), (101.0, 100.0), (103.0, 100.0)])
    assert r["median_pct"] == pytest.approx(2.0)


def test_같은_것은_중앙값_계산에서_빠진다():
    """어긋난 것들의 크기를 묻는 것이지 전체 평균이 아니다."""
    r = divergence_rate([(100.0, 100.0), (100.0, 100.0), (105.0, 100.0)])
    assert r["bad"] == 1
    assert r["median_pct"] == pytest.approx(5.0)


# ── chain_ok (이 검사기의 «자기 검사») ───────────────────────

def test_기준가_연쇄가_맞으면_어긋남_0():
    """기준가(D) == 종가(D-1). 이게 성립해야 KIS 를 자로 쓸 수 있다."""
    closes = [100.0, 110.0, 120.0]
    bases = [99.0, 100.0, 110.0]
    assert chain_ok(closes, bases) == {"n": 2, "bad": 0}


def test_연쇄가_깨지면_잡아낸다():
    closes = [100.0, 110.0, 120.0]
    bases = [99.0, 105.0, 110.0]      # 105 != 100
    assert chain_ok(closes, bases) == {"n": 2, "bad": 1}


def test_하루치만_있으면_비교할_쌍이_없다():
    assert chain_ok([100.0], [99.0]) == {"n": 0, "bad": 0}


# ── can_judge_yet (당일에 판정하지 않는다) ───────────────────

def test_예측일_당일에는_판정하지_않는다():
    """예측이 「그날 저녁엔 같다가 다음날 갈린다」이므로 당일 0% 는 반증이 아니다."""
    from check_close_source import can_judge_yet
    assert can_judge_yet("20260921", "20260921") is False


def test_다음날이면_판정한다():
    from check_close_source import can_judge_yet
    assert can_judge_yet("20260922", "20260921") is True


def test_예측일_이전이면_판정하지_않는다():
    from check_close_source import can_judge_yet
    assert can_judge_yet("20260918", "20260921") is False
