"""수출 주도 품목 분류 — 설정 키워드 매칭 + 오버라이드.

우선순위: exclude > include > 키워드(direct). 매칭 실패 = None(추측 금지).
자동 키워드 매칭은 업종명이 제조업(조선은 건조업)일 때만 — 품목을 만들지 않고
이용·유통만 하는 회사(통신사·해운사·홈쇼핑·상사)가 제품명 텍스트로 걸리는
오탐 차단. 서비스업 밸류체인 편입은 include 오버라이드로만.
설정: public/data/export-leading-config.json (사용자 직접 관리).
"""
import json
from pathlib import Path

_TIERS = {"direct", "indirect"}


def load_config(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _label(config, key):
    for c in config["categories"]:
        if c["key"] == key:
            return c["label"]
    return key


def classify(code, sector, products, config):
    ov = config.get("overrides", {})
    if code in ov.get("exclude", {}):
        return None
    inc = ov.get("include", {}).get(code)
    if inc:
        tier = inc.get("tier", "indirect")
        return {"category": inc["category"], "label": _label(config, inc["category"]),
                "tier": tier if tier in _TIERS else "indirect",
                "basis": inc.get("reason", "오버라이드")}
    markers = config.get("auto_match_requires", ["제조업", "건조업"])
    if not sector or not any(m in sector for m in markers):
        return None
    text = " ".join(x for x in (sector, products) if x)
    for cat in config["categories"]:
        for kw in cat["keywords"]:
            if kw in text:
                src = "업종" if kw in sector else "주요제품"
                return {"category": cat["key"], "label": cat["label"],
                        "tier": "direct", "basis": f"{src}: …{kw}…"}
    return None
