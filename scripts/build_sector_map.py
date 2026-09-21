"""전 종목 섹터 분류 — 표준산업분류(KSIC) + 제품설명으로 모든 상장 종목에 섹터를 붙인다.

왜 있나:
  주도 섹터 9개(`leading-sectors-config.json`)는 «테마»다. 사용자가 손으로 고른 것이라
  모든 종목에 붙지 않는다(26-09-21 실측: 감시 57종목 중 41종목이 태그 밖).
  장전 브리핑이 말을 걸려면 «모든» 종목에 붙는 축이 따로 있어야 한다.

  테마와 업종은 다른 축이다. 둘 다 쓴다 — 업종은 「빠짐없이」, 테마는 「날카롭게」.

무엇이 정본인가:
  · 업종 원자료  `.cache/krx_desc.json` (KRX 제공, 2,871종목, industry 96.0% · products 95.6%)
  · 묶음 정의    이 파일의 BUCKETS — 미국 ETF 와 1:1 로 대응되게 잘랐다
  · 교정 규칙    이 파일의 PRODUCT_RULES

🚨 KSIC 는 «테마»를 모른다. 반도체 장비회사가 「특수 목적용 기계 제조업」에 들어가
  일반 기계와 섞인다(한미반도체·원익IPS 등). 그래서 제품설명 키워드로 «교정»한다.
  교정은 업종보다 «세다» — 제품이 구체적이기 때문이다.

⚠️ 억지로 채우지 않는다. 업종도 제품설명도 없는 종목(114개)은 `_미분류` 로 남는다.
  「분류 못 했다」와 「그 섹터가 아니다」는 다르다.

산출: public/data/sector-map.json
실행: python -X utf8 scripts/build_sector_map.py [--save] [--sample 20]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

DESC_FILE = ROOT / ".cache" / "krx_desc.json"
OUT_FILE = ROOT / "public" / "data" / "sector-map.json"

# ── 묶음 정의 ────────────────────────────────────────────────
# 자르는 기준은 «미국에 대응 ETF 가 있는가» 다. 없으면 브리핑에서 못 쓴다.
# proxy 가 None 인 묶음은 「한국 내수라 미국 대응이 없다」는 뜻이고 그렇게 표시된다.
BUCKETS = {
    "semiconductor":    {"label": "반도체",            "proxy": ["SOXX", "MU", "NVDA", "AMAT", "LRCX"]},
    "it_hardware":      {"label": "IT하드웨어·전자부품",  "proxy": ["XLK", "AAPL", "DELL"]},
    "software_internet": {"label": "소프트웨어·인터넷",   "proxy": ["IGV", "MSFT", "GOOGL"]},
    "battery":          {"label": "이차전지",          "proxy": ["LIT", "ALB"]},
    "electrical":       {"label": "전기장비·전력",       "proxy": ["GRID", "GEV", "VRT", "ETN", "PWR", "TAN"]},
    "holding":          {"label": "순수지주회사",        "proxy": []},
    "machinery":        {"label": "기계·산업재",        "proxy": ["XLI", "CAT", "DE"]},
    "aerospace_defense": {"label": "항공우주·방산",      "proxy": ["ITA", "LMT", "RTX", "NOC"]},
    "shipbuilding":     {"label": "조선",             "proxy": []},
    "materials":        {"label": "소재·화학·철강",      "proxy": ["XLB", "DOW", "NUE"]},
    "energy":           {"label": "에너지·정유",        "proxy": ["XLE", "XOM", "CVX"]},
    "healthcare":       {"label": "헬스케어·제약·바이오",  "proxy": ["XLV", "XBI", "LLY"]},
    "consumer_disc":    {"label": "경기소비재",         "proxy": ["XLY", "AMZN", "NKE"]},
    "consumer_staples": {"label": "필수소비재",         "proxy": ["XLP", "PG", "KO"]},
    "cosmetics":        {"label": "화장품",            "proxy": ["EL", "ULTA", "COTY"]},
    "financials":       {"label": "금융",             "proxy": ["XLF", "JPM", "BAC"]},
    "communication":    {"label": "커뮤니케이션·미디어",   "proxy": ["XLC", "NFLX", "DIS"]},
    "utilities":        {"label": "유틸리티",          "proxy": ["XLU", "NEE"]},
    "construction":     {"label": "건설·부동산",        "proxy": ["XLRE", "PAVE"]},
    "transport":        {"label": "운송",             "proxy": ["IYT", "UNP", "FDX"]},
    "auto":             {"label": "자동차·부품",        "proxy": ["CARZ", "GM", "F", "APTV"]},
}

# ── 업종 → 묶음 ──────────────────────────────────────────────
# KSIC 업종명 그대로 적는다. 여기 «없는» 업종이 나오면 미분류로 가고 보고된다.
INDUSTRY_MAP: dict[str, list[str]] = {
    "semiconductor": ["반도체 제조업"],
    "it_hardware": [
        "전자부품 제조업", "통신 및 방송 장비 제조업", "컴퓨터 및 주변장치 제조업",
        "측정, 시험, 항해, 제어 및 기타 정밀기기 제조업; 광학기기 제외",
        "영상 및 음향기기 제조업", "사진장비 및 광학기기 제조업", "가정용 기기 제조업",
        "마그네틱 및 광학 매체 제조업", "기록매체 복제업",
    ],
    "software_internet": [
        "소프트웨어 개발 및 공급업", "컴퓨터 프로그래밍, 시스템 통합 및 관리업",
        "자료처리, 호스팅, 포털 및 기타 인터넷 정보매개 서비스업", "기타 정보 서비스업",
    ],
    "battery": ["일차전지 및 이차전지 제조업"],
    "electrical": [
        "전동기, 발전기 및 전기 변환 · 공급 · 제어 장치 제조업", "절연선 및 케이블 제조업",
        "기타 전기장비 제조업", "전구 및 조명장치 제조업",
    ],
    "machinery": [
        "특수 목적용 기계 제조업", "일반 목적용 기계 제조업", "기타 금속 가공제품 제조업",
        "구조용 금속제품, 탱크 및 증기발생기 제조업", "기계장비 및 관련 물품 도매업",
        "금속 주조업", "산업용 기계 및 장비 임대업", "그외 기타 운송장비 제조업",
        "기타 사업지원 서비스업", "사업시설 유지·관리 서비스업", "경비, 경호 및 탐정업",
        "폐기물 처리업", "해체, 선별 및 원료 재생업", "그외 기타 제품 제조업",
        "악기 제조업", "귀금속 및 장신용품 제조업", "개인 및 가정용품 수리업",
    ],
    "aerospace_defense": ["항공기,우주선 및 부품 제조업", "무기 및 총포탄 제조업"],
    "shipbuilding": ["선박 및 보트 건조업"],
    "materials": [
        "기타 화학제품 제조업", "기초 화학물질 제조업", "1차 철강 제조업", "1차 비철금속 제조업",
        "플라스틱제품 제조업", "화학섬유 제조업", "합성고무 및 플라스틱 물질 제조업",
        "고무제품 제조업", "시멘트, 석회, 플라스터 및 그 제품 제조업", "기타 비금속 광물제품 제조업",
        "펄프, 종이 및 판지 제조업", "골판지, 종이 상자 및 종이용기 제조업",
        "기타 종이 및 판지 제품 제조업", "비료, 농약 및 살균, 살충제 제조업",
        "내화, 비내화 요업제품 제조업", "유리 및 유리제품 제조업", "제재 및 목재 가공업",
        "나무제품 제조업", "직물직조 및 직물제품 제조업", "방적 및 가공사 제조업",
        "기타 섬유제품 제조업", "섬유제품 염색, 정리 및 마무리 가공업",
        "인쇄 및 인쇄관련 산업", "상품 종합 도매업", "기타 전문 도매업", "상품 중개업",
        "건축자재, 철물 및 난방장치 도매업", "산업용 농·축산물 및 동·식물 도매업",
    ],
    "energy": ["석유 정제품 제조업", "연료용 가스 제조 및 배관공급업", "연료 소매업"],
    "healthcare": [
        "의약품 제조업", "의료용 기기 제조업", "기초 의약물질 제조업",
        "의료용품 및 기타 의약 관련제품 제조업", "자연과학 및 공학 연구개발업",
        "기타 과학기술 서비스업",
    ],
    "consumer_disc": [
        "봉제의복 제조업", "종합 소매업", "섬유, 의복, 신발 및 가죽제품 소매업",
        "가구 제조업", "가죽, 가방 및 유사제품 제조업", "의복 액세서리 제조업",
        "신발 및 신발 부분품 제조업", "편조의복 제조업", "무점포 소매업",
        "기타 상품 전문 소매업", "기타 생활용품 소매업", "가전제품 및 정보통신장비 소매업",
        "생활용품 도매업", "운동 및 경기용구 제조업", "스포츠 서비스업",
        "유원지 및 기타 오락관련 서비스업", "여행사 및 기타 여행보조 서비스업",
        "일반 및 생활 숙박시설 운영업", "일반 교습 학원", "교육지원 서비스업",
        "초등 교육기관", "기타 교육기관", "그외 기타 개인 서비스업",
        "개인 및 가정용품 임대업", "전문디자인업",
    ],
    "consumer_staples": [
        "기타 식품 제조업", "알코올음료 제조업", "동물용 사료 및 조제식품 제조업",
        "곡물가공품, 전분 및 전분제품 제조업", "도축, 육류 가공 및 저장 처리업",
        "수산물 가공 및 저장 처리업", "과실, 채소 가공 및 저장 처리업",
        "동·식물성 유지 및 낙농제품 제조업", "비알코올음료 및 얼음 제조업",
        "음·식료품 및 담배 도매업", "음·식료품 및 담배 소매업", "담배 제조업",
        "작물 재배업", "어로 어업", "떡, 빵 및 과자류 제조업",
        "도시락 및 식사용 조리식품 제조업",
    ],
    "financials": [
        "기타 금융업", "금융 지원 서비스업", "신탁업 및 집합투자업", "보험업",
        "은행 및 저축기관", "재 보험업", "보험 및 연금관련 서비스업",
        "회사 본부 및 경영 컨설팅 서비스업", "그외 기타 전문, 과학 및 기술 서비스업",
        "기타 전문 서비스업", "시장조사 및 여론조사업",
    ],
    "communication": [
        "영화, 비디오물, 방송프로그램 제작 및 배급업", "광고업", "전기 통신업",
        "텔레비전 방송업", "서적, 잡지 및 기타 인쇄물 출판업", "오디오물 출판 및 원판 녹음업",
        "창작 및 예술관련 서비스업", "영상·오디오물 제공 서비스업",
    ],
    "utilities": ["전기업", "증기, 냉·온수 및 공기조절 공급업"],
    "construction": [
        "건물 건설업", "토목 건설업", "부동산 임대 및 공급업",
        "건축기술, 엔지니어링 및 관련 기술 서비스업", "전기 및 통신 공사업",
        "실내건축 및 건축마무리 공사업", "기반조성 및 시설물 축조관련 전문공사업",
        "건물설비 설치 공사업",
    ],
    "transport": [
        "도로 화물 운송업", "해상 운송업", "항공 여객 운송업", "육상 여객 운송업",
        "기타 운송관련 서비스업", "운송장비 임대업",
    ],
    "auto": [
        "자동차 신품 부품 제조업", "자동차용 엔진 및 자동차 제조업", "자동차 판매업",
        "자동차 부품 및 내장품 판매업", "자동차 차체나 트레일러 제조업",
        "자동차 재제조 부품 제조업",
    ],
}

# ── 제품설명 교정 규칙 ───────────────────────────────────────
# 업종이 못 가르는 것을 제품이 가른다. «위에서부터» 먼저 맞는 것을 쓴다(순서가 뜻을 가진다).
# 🚨 두 가지를 조심한다:
#   ① 「반도체 장비」와 「반도체를 «쓰는» 제품」이 다르다 → 장비·소재 낱말을 같이 본다
#   ② 「화장품 용기」는 화장품이 아니라 플라스틱이다 → 용기·포장은 뺀다
PRODUCT_RULES: list[tuple[str, str]] = [
    ("cosmetics", r"화장품(?!.*(용기|포장|케이스))|기초화장|색조화장|마스크팩|스킨케어"),
    ("semiconductor", r"반도체|웨이퍼|포토레지스트|식각|증착|CMP|프로브카드|패키징|"
                      r"디스플레이\s*제조|OLED\s*장비|TFT-LCD\s*(검사|제조)"),
    ("battery", r"이차전지|2차전지|리튬이온|양극재|음극재|전해액|분리막|배터리\s*(소재|장비|팩)"),
    ("aerospace_defense", r"방산|군수|미사일|탄약|자주포|장갑차|전투기|군용|우주발사체|위성체"),
    ("shipbuilding", r"선박\s*(건조|블록|기자재)|조선기자재|LNG선|해양플랜트|해양구조물"),
    # 태양광은 KSIC 가 「반도체 제조업」으로 보낸다(태양전지가 반도체라서). 그런데 시장에서
    # 태양광은 SOXX 가 아니라 TAN 을 따라간다 — 반도체 규칙 «앞»에 둘 수 없으니 여기서 잡는다.
    ("electrical", r"태양광|태양전지|변압기|배전반|전력\s*(기기|설비|변환)|초고압|차단기|전선\s*(케이블)?"),
    ("healthcare", r"신약|바이오\s*(시밀러|의약품)|임상|항체|백신|진단키트|세포치료|CDMO|CMO"),
]


# ── 순수 로직 (시험 대상) ────────────────────────────────────

def invert_industry_map(m: dict[str, list[str]]) -> dict[str, str]:
    """묶음→업종목록 을 업종→묶음 으로 뒤집는다. 한 업종이 두 묶음에 있으면 «터뜨린다»."""
    out: dict[str, str] = {}
    for bucket, inds in m.items():
        for i in inds:
            if i in out and out[i] != bucket:
                raise ValueError(f"업종 「{i}」가 {out[i]} 와 {bucket} 양쪽에 있다")
            out[i] = bucket
    return out


# 제품설명이 «이것뿐»인 회사는 순수지주회사다. KSIC 는 이들을 「기타 금융업」으로 보내는데
# (LG·CJ·HD현대가 그렇다) 금융 묶음에 섞이면 금융 섹터 신호가 오염된다.
# 「모르겠다」가 아니라 「지주회사라서 사업이 안 보인다」 — 그렇게 따로 적는다.
HOLDING_ONLY = re.compile(r"^[\s,]*(지주\s*회사|지주\s*사업|경영\s*자문\s*및\s*지주\s*사업|"
                          r"회사본부[,\s]*지주회사\s*및\s*경영컨설팅\s*서비스업)[\s,.]*$")


def classify_one(industry: str | None, products: str | None,
                 ind2b: dict[str, str]) -> tuple[str, str]:
    """한 종목의 (묶음, 근거). 못 정하면 ('_미분류', 까닭).

    순서가 뜻을 가진다: 제품 규칙 → 순수지주 → 업종 → 미분류.
    제품이 업종보다 «세다» — KSIC 는 테마를 모르기 때문이다.
    """
    prod = (products or "").strip()
    for bucket, pat in PRODUCT_RULES:
        if prod and re.search(pat, prod):
            return bucket, f"제품:{bucket}"
    if prod and HOLDING_ONLY.match(prod):
        return "holding", "순수지주(사업 안 보임)"
    ind = (industry or "").strip()
    if ind and ind in ind2b:
        return ind2b[ind], "업종"
    if ind:
        return "_미분류", f"업종 미등록:{ind}"
    return "_미분류", "업종·제품 둘 다 없음"


def inherit_preferred(out: dict[str, dict]) -> int:
    """우선주에 보통주의 묶음을 물려준다. 몇 건 물려줬는지 돌려준다.

    우선주는 KRX 가 업종·제품을 «안 준다»(26-09-21 실측: 미분류 114 중 114 가 우선주).
    그런데 우선주는 보통주와 «같은 회사»다 — 섹터가 다를 수 없다.
    한국 종목코드 관례상 보통주는 끝자리가 0 이고 우선주는 5·7 등이다.
    """
    n = 0
    for code, r in out.items():
        if r["bucket"] != "_미분류":
            continue
        base = code[:5] + "0"
        b = out.get(base)
        if b and b["bucket"] != "_미분류":
            r["bucket"] = b["bucket"]
            r["why"] = f"우선주 상속({base})"
            n += 1
    return n


def classify_all(desc: dict, ind2b: dict[str, str]) -> dict[str, dict]:
    out = {}
    for code, v in desc.items():
        b, why = classify_one(v.get("industry"), v.get("products"), ind2b)
        out[code] = {"bucket": b, "why": why,
                     "industry": v.get("industry") or "", "products": v.get("products") or ""}
    inherit_preferred(out)
    return out


def coverage(res: dict[str, dict]) -> dict:
    c = Counter(r["bucket"] for r in res.values())
    n = len(res)
    un = c.get("_미분류", 0)
    return {"total": n, "classified": n - un, "unclassified": un,
            "rate": (n - un) / n * 100 if n else 0.0, "by_bucket": dict(c)}


# ── 실행 ─────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="전 종목 섹터 분류")
    ap.add_argument("--save", action="store_true", help="public/data/sector-map.json 에 저장")
    ap.add_argument("--sample", type=int, default=0, help="묶음마다 표본 몇 개를 보여줄지")
    a = ap.parse_args()

    desc = json.loads(DESC_FILE.read_text(encoding="utf-8"))
    ind2b = invert_industry_map(INDUSTRY_MAP)
    res = classify_all(desc, ind2b)
    cov = coverage(res)

    print(f"종목 {cov['total']} · 분류됨 {cov['classified']} ({cov['rate']:.1f}퍼센트) "
          f"· 미분류 {cov['unclassified']}")
    print()
    print("묶음            종목수   미국 대응")
    for b, n in sorted(cov["by_bucket"].items(), key=lambda x: -x[1]):
        if b == "_미분류":
            continue
        cfg = BUCKETS.get(b, {})
        px = ", ".join(cfg.get("proxy") or []) or "(없음)"
        print(f"{cfg.get('label', b)[:14]:14s} {n:6d}   {px[:44]}")
    print(f"{'_미분류':14s} {cov['by_bucket'].get('_미분류', 0):6d}")

    print()
    print("제품설명 교정으로 «업종과 다르게» 간 종목:")
    moved = [(c, r) for c, r in res.items() if r["why"].startswith("제품:")]
    mc = Counter(r["why"] for _, r in moved)
    for w, n in mc.most_common():
        print(f"   {w:22s} {n}")
    print(f"   합계 {len(moved)}")

    print()
    print("미분류 까닭:")
    for w, n in Counter(r["why"] for r in res.values()
                        if r["bucket"] == "_미분류").most_common(10):
        print(f"   {n:5d}  {w[:70]}")

    if a.sample:
        print()
        for b in BUCKETS:
            ex = [(c, r) for c, r in res.items() if r["bucket"] == b][:a.sample]
            if not ex:
                continue
            print(f"[{BUCKETS[b]['label']}]")
            for c, r in ex:
                print(f"   {c}  {r['products'][:56]}")

    if a.save:
        payload = {
            "asof": f"{datetime.now():%Y-%m-%d}",
            "note": ("전 종목 섹터 분류. 축이 «둘»이다 — 이 파일은 «업종»(빠짐없이), "
                     "leading-sectors-config.json 은 «테마»(날카롭게). 섞어 읽지 않는다."),
            "source": ".cache/krx_desc.json (KRX)",
            "buckets": BUCKETS,
            "coverage": cov,
            "assignments": {c: {"bucket": r["bucket"], "why": r["why"]} for c, r in res.items()},
        }
        tmp = OUT_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        json.loads(tmp.read_text(encoding="utf-8"))
        tmp.replace(OUT_FILE)
        print(f"\n저장 {OUT_FILE}")


if __name__ == "__main__":
    main()
