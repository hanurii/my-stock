"""수출 주도 종목 분류 오라클 테스트 — 2026-08-05 SEPA 통과 32종목 기준."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.export_tags import classify, load_config

ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_config(ROOT / "public" / "data" / "export-leading-config.json")


def tag(code, sector, products):
    return classify(code, sector, products, CONFIG)


def test_soil_petroleum_direct():
    t = tag("010950", "석유 정제품 제조업", None)
    assert t and t["category"] == "petroleum" and t["tier"] == "direct"
    assert "석유 정제" in t["basis"]


def test_samc_semiconductor_indirect_override():
    # 실제 KRX Products('세라믹 STF')에 반도체 키워드가 없어 오버라이드로 편입.
    t = tag("252990", "전자부품 제조업", "세라믹 STF(다층 세라믹 기판)")
    assert t and t["category"] == "semiconductor" and t["tier"] == "indirect"


def test_products_keyword_direct_for_manufacturer():
    t = tag("999999", "전자부품 제조업", "반도체 검사장비용 부품")
    assert t and t["category"] == "semiconductor" and t["tier"] == "direct"


def test_gs_holding_indirect_override():
    t = tag("078930", "기타 금융업", None)
    assert t and t["category"] == "petroleum" and t["tier"] == "indirect"
    assert "GS칼텍스" in t["basis"]


def test_newpower_semiconductor_indirect_override():
    t = tag("144960", "특수 목적용 기계 제조업", None)
    assert t and t["category"] == "semiconductor" and t["tier"] == "indirect"


def test_suprema_excluded_despite_ksic():
    assert tag("094840", "통신 및 방송 장비 제조업", None) is None


def test_panocean_excluded_shipping_user():
    assert tag("028670", "해상 운송업", "외항 화물 운송") is None


def test_shinhan_no_match():
    assert tag("055550", "기타 금융업", "금융지주회사") is None


def test_none_inputs_no_crash():
    assert tag("000000", None, None) is None


def test_service_industry_not_auto_matched():
    # 제조업 아닌 업종은 제품명 키워드가 있어도 자동 매칭 금지(오버라이드로만 편입).
    assert tag("017670", "전기 통신업", "이동전화") is None          # 통신사
    assert tag("044450", "해상 운송업", "선박대여") is None          # 해운사
    assert tag("035760", "텔레비전 방송업", "의류, 가전제품, 기타") is None  # 홈쇼핑


def test_shipbuilder_geonjo_counts_as_manufacturer():
    t = tag("999990", "선박 및 보트 건조업", None)
    assert t and t["category"] == "ships" and t["tier"] == "direct"


def test_override_bad_tier_clamped():
    cfg = {"categories": [{"key": "ships", "label": "선박", "keywords": []}],
           "overrides": {"include": {"111111": {"category": "ships", "tier": "간접"}}}}
    t = classify("111111", None, None, cfg)
    assert t and t["tier"] == "indirect"


def test_config_schema():
    keys = {c["key"] for c in CONFIG["categories"]}
    assert len(keys) == 7 and "semiconductor" in keys
