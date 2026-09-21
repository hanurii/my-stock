"""전 종목 섹터 분류의 «순수 로직» 시험.

지키려는 것 넷:
  ① 한 업종이 두 묶음에 들어가면 «터진다»(조용히 덮어쓰지 않는다)
  ② 제품설명이 업종을 «이긴다» — KSIC 는 테마를 모른다
  ③ 우선주가 보통주를 물려받는다
  ④ 못 정한 것을 아무 데나 넣지 «않는다»
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_sector_map import (  # noqa: E402
    BUCKETS, INDUSTRY_MAP, PRODUCT_RULES, classify_all, classify_one,
    coverage, inherit_preferred, invert_industry_map,
)

IND2B = invert_industry_map(INDUSTRY_MAP)


# ── 묶음 정의 자체 ───────────────────────────────────────────

def test_모든_업종이_아는_묶음으로_간다():
    """INDUSTRY_MAP 의 키가 BUCKETS 에 없으면 라벨도 프록시도 못 찾는다."""
    for bucket in INDUSTRY_MAP:
        assert bucket in BUCKETS, f"{bucket} 이 BUCKETS 에 없다"


def test_제품규칙의_묶음도_아는_묶음이다():
    for bucket, _ in PRODUCT_RULES:
        assert bucket in BUCKETS, f"{bucket} 이 BUCKETS 에 없다"


def test_한_업종이_두_묶음에_있으면_터진다():
    """조용히 덮어쓰면 어느 쪽이 이겼는지 아무도 모른다."""
    with pytest.raises(ValueError, match="양쪽에 있다"):
        invert_industry_map({"a": ["같은업종"], "b": ["같은업종"]})


def test_업종이_안_겹친다():
    """정본 자체 검사 — 겹치면 위 함수가 터지므로 여기 오면 안 겹친 것이다."""
    assert len(IND2B) == sum(len(v) for v in INDUSTRY_MAP.values())


# ── classify_one ─────────────────────────────────────────────

def test_업종으로_분류된다():
    b, why = classify_one("반도체 제조업", "", IND2B)
    assert b == "semiconductor"
    assert why == "업종"


def test_제품이_업종을_이긴다():
    """한미반도체 꼴 — KSIC 는 「특수 목적용 기계」인데 실제로는 반도체 장비다."""
    b, why = classify_one("특수 목적용 기계 제조업", "반도체 본딩 장비", IND2B)
    assert b == "semiconductor"
    assert why == "제품:semiconductor"


def test_태양광은_반도체가_아니라_전력으로():
    """KSIC 는 태양전지를 「반도체 제조업」에 넣는다. 그런데 시장은 SOXX 가 아니라 TAN 을 따른다."""
    b, why = classify_one("반도체 제조업", "태양광 셀·모듈, PV시스템", IND2B)
    assert b == "electrical"


def test_화장품_용기는_화장품이_아니다():
    """용기·포장은 플라스틱 회사다. 이걸 화장품으로 세면 섹터 신호가 오염된다."""
    b, _ = classify_one("플라스틱제품 제조업", "화장품 용기 제조", IND2B)
    assert b != "cosmetics"


def test_순수지주는_금융이_아니라_지주로():
    """LG·CJ·HD현대 꼴 — KSIC 가 「기타 금융업」으로 보내면 금융 신호가 오염된다."""
    b, why = classify_one("기타 금융업", "지주회사", IND2B)
    assert b == "holding"
    assert "순수지주" in why


def test_사업이_보이는_지주는_지주로_안_간다():
    b, _ = classify_one("기타 금융업", "선박,해양구조물,엔진 제조", IND2B)
    assert b == "shipbuilding"


def test_모르는_업종은_미분류이고_까닭이_남는다():
    b, why = classify_one("듣도보도못한 업종", "", IND2B)
    assert b == "_미분류"
    assert "업종 미등록" in why


def test_둘다_없으면_미분류():
    b, why = classify_one("", "", IND2B)
    assert b == "_미분류"
    assert "둘 다 없음" in why


def test_미분류를_아무_묶음에나_넣지_않는다():
    """「모른다」를 「그 섹터가 아니다」로 바꿔 쓰지 않는다."""
    b, _ = classify_one(None, None, IND2B)
    assert b not in BUCKETS


# ── 우선주 상속 ──────────────────────────────────────────────

def test_우선주가_보통주를_물려받는다():
    out = {"005930": {"bucket": "semiconductor", "why": "업종"},
           "005935": {"bucket": "_미분류", "why": "업종·제품 둘 다 없음"}}
    assert inherit_preferred(out) == 1
    assert out["005935"]["bucket"] == "semiconductor"
    assert "우선주 상속(005930)" in out["005935"]["why"]


def test_보통주도_미분류면_물려줄_것이_없다():
    out = {"005930": {"bucket": "_미분류", "why": "x"},
           "005935": {"bucket": "_미분류", "why": "y"}}
    assert inherit_preferred(out) == 0
    assert out["005935"]["bucket"] == "_미분류"


def test_이미_분류된_종목은_안_건드린다():
    out = {"005930": {"bucket": "semiconductor", "why": "업종"},
           "005935": {"bucket": "healthcare", "why": "업종"}}
    assert inherit_preferred(out) == 0
    assert out["005935"]["bucket"] == "healthcare"


# ── classify_all · coverage ──────────────────────────────────

def test_전체분류가_우선주까지_채운다():
    desc = {"005930": {"industry": "반도체 제조업", "products": "반도체"},
            "005935": {"industry": "", "products": ""}}
    res = classify_all(desc, IND2B)
    assert res["005935"]["bucket"] == "semiconductor"


def test_coverage_가_미분류를_센다():
    res = {"a": {"bucket": "semiconductor"}, "b": {"bucket": "_미분류"}}
    c = coverage(res)
    assert c["total"] == 2
    assert c["classified"] == 1
    assert c["unclassified"] == 1
    assert c["rate"] == pytest.approx(50.0)


def test_coverage_가_빈입력에_안_터진다():
    c = coverage({})
    assert c["total"] == 0
    assert c["rate"] == 0.0
