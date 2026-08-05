"""SEPA 후보 종목 수출 주도 품목 태깅 — /sepa 마무리 비차단 스텝.

입력: sepa-{trend,vcp,power-play-all,3c}-candidates.json + sepa-buy-recommendations.json
      + export-leading-config.json + KRX 업종·주요제품(FDR StockListing('KRX-DESC'), 7일 캐시)
출력: public/data/sepa-export-tags.json
실패 시: 이전 산출 유지(비차단) — exit 0 유지, 경고만 출력.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from canslim_lib.export_tags import classify, load_config  # noqa: E402

DATA = ROOT / "public" / "data"
CACHE = ROOT / ".cache" / "krx_desc.json"
CACHE_TTL_DAYS = 7
CANDIDATE_FILES = [
    "sepa-trend-candidates.json", "sepa-vcp-candidates.json",
    "sepa-power-play-all-candidates.json", "sepa-3c-candidates.json",
    "sepa-buy-recommendations.json",
]


def collect_codes():
    codes, names, asof = {}, {}, None
    for fn in CANDIDATE_FILES:
        p = DATA / fn
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        asof = d.get("asof") or asof
        for c in d.get("candidates", []):
            # 트렌드 파일은 전 평가 종목(~1,300)을 담고 있어 8조건 통과분만 —
            # 페이지에 표시되지 않는 종목까지 태깅해 파일이 배로 커지는 것 방지.
            if fn == "sepa-trend-candidates.json" and not c.get("all_pass"):
                continue
            if c.get("code"):
                codes[c["code"]] = True
                names[c["code"]] = c.get("name")
    return list(codes), names, asof


def load_krx_desc():
    if CACHE.exists() and time.time() - CACHE.stat().st_mtime < CACHE_TTL_DAYS * 86400:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    try:
        import FinanceDataReader as fdr
        df = fdr.StockListing("KRX-DESC")
        m = {str(r["Code"]): {"sector": None if r["Sector"] != r["Sector"] else str(r["Sector"]),
                              "products": None if r["Products"] != r["Products"] else str(r["Products"]),
                              "industry": None if r["Industry"] != r["Industry"] else str(r["Industry"])}
             for _, r in df.iterrows()}
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
        return m
    except Exception as e:
        if CACHE.exists():
            print(f"⚠️ KRX 최신 수집 실패({e}) — 캐시 사용")
            return json.loads(CACHE.read_text(encoding="utf-8"))
        raise


def main():
    # 비차단 계약: 어떤 실패든 경고 한 줄 + 이전 산출 유지 + exit 0.
    try:
        config = load_config(DATA / "export-leading-config.json")
        codes, names, asof = collect_codes()
    except Exception as e:
        print(f"⚠️ 설정/후보 파일 오류({e}) — 이전 태그 파일 유지")
        return
    if not codes:
        print("⚠️ 후보 파일에 종목 없음 — 이전 태그 파일 유지")
        return
    try:
        krx = load_krx_desc()
    except Exception as e:
        print(f"⚠️ 업종 정보 없음({e}) — 이전 태그 파일 유지")
        return
    tags = {}
    try:
        for code in codes:
            info = krx.get(code, {})
            # KSIC 세부업종(industry)까지 합쳐 매칭 폭 확보 — sector 는 KOSDAQ 소속부명인 경우 있음
            sector_text = " ".join(x for x in (info.get("sector"), info.get("industry")) if x) or None
            t = classify(code, sector_text, info.get("products"), config)
            if t:
                tags[code] = {"name": names.get(code), **t}
    except Exception as e:
        print(f"⚠️ 분류 오류({e}) — 이전 태그 파일 유지 (설정 스키마 확인 필요)")
        return
    out = {"asof": asof, "config_asof": config.get("asof"), "tags": tags}
    (DATA / "sepa-export-tags.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    by_cat = {}
    for t in tags.values():
        by_cat[t["label"]] = by_cat.get(t["label"], 0) + 1
    print(f"💾 저장: sepa-export-tags.json — {len(tags)}종목 태깅 / 대상 {len(codes)}종목")
    for k, v in sorted(by_cat.items()):
        print(f"   {k}: {v}")


if __name__ == "__main__":
    main()
