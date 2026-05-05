#!/usr/bin/env python3
"""
한국 상장 ETF 전체 리스트에서 키워드 매칭 ETF 검색 + etf-data.json에 자동 추가.

데이터 소스: finance.naver.com (m.stock에 ETF 전체 리스트 endpoint가 없어 예외 사용)
- 매칭만: python scripts/search_etfs.py 화장품
- 추가까지: python scripts/search_etfs.py 화장품 --add-sector beauty
- 추가 + 메트릭 자동 fetch: python scripts/search_etfs.py 화장품 --add-sector beauty --fetch-metrics
- 다중 키워드: python scripts/search_etfs.py 반도체 HBM 비메모리 --add-sector semiconductor_kr

ETF 분류 코드 (etfTabCode):
  1=국내시장지수 / 2=국내업종/테마 / 3=국내파생 / 4=해외주식 / 5=원자재 / 6=채권 / 7=기타
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
ETF_DATA_PATH = ROOT / "public" / "data" / "etf-data.json"

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
LIST_URL = "https://finance.naver.com/api/sise/etfItemList.nhn?etfType=0"

TAB_CODE_DESC = {
    1: "국내시장지수",
    2: "국내업종/테마",
    3: "국내파생",
    4: "해외주식",
    5: "원자재",
    6: "채권",
    7: "기타",
}

# etfTabCode → geography 매핑
TAB_TO_GEO = {
    1: "한국",
    2: "한국",
    3: "한국",
    4: "해외",
    5: "원자재",
    6: "한국",
    7: "혼합",
}


def fetch_etf_universe() -> list[dict]:
    req = Request(LIST_URL, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=15) as r:
        # finance.naver는 EUC-KR encoded
        raw = r.read()
        try:
            text = raw.decode("euc-kr")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
        data = json.loads(text)
    return data["result"]["etfItemList"]


def fetch_etf_meta(code: str) -> dict | None:
    """단일 ETF 기본 메타 fetch (운용사·추종지수·상장일)."""
    url = f"https://m.stock.naver.com/api/stock/{code}/etfAnalysis"
    req = Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Referer": "https://m.stock.naver.com/",
    })
    try:
        with urlopen(req, timeout=8) as r:
            return json.loads(r.read().decode("utf-8"))
    except (HTTPError, URLError, json.JSONDecodeError):
        return None


def parse_listed_date(s):
    if not s:
        return None
    s = str(s)
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return s


def match_etf(name: str, keywords: list[str]) -> bool:
    name_lower = name.lower()
    return any(kw.lower() in name_lower for kw in keywords)


def main():
    parser = argparse.ArgumentParser(description="키워드로 한국 ETF 검색 + 자동 등록")
    parser.add_argument("keywords", nargs="+", help="검색 키워드 (여러 개 OR 매칭)")
    parser.add_argument("--add-sector", help="매칭 결과를 추가할 섹터 키 (예: beauty)")
    parser.add_argument("--fetch-metrics", action="store_true",
                        help="추가 후 fetch_etf_metrics.py 자동 실행")
    parser.add_argument("--include-tab", type=int, action="append",
                        help="특정 etfTabCode만 (예: --include-tab 2)")
    parser.add_argument("--exclude-tab", type=int, action="append",
                        help="제외할 etfTabCode (예: --exclude-tab 3 = 파생 제외)")
    parser.add_argument("--exclude-keyword", nargs="*", default=[],
                        help="제외 키워드 (예: 레버리지 인버스)")
    args = parser.parse_args()

    # 디폴트: 파생(레버리지/인버스 등)은 제외
    if args.exclude_tab is None:
        args.exclude_tab = [3]
    if not args.exclude_keyword:
        args.exclude_keyword = ["레버리지", "인버스", "선물", "곱버스"]

    print(f"🔍 한국 ETF 전체 리스트 fetch...")
    universe = fetch_etf_universe()
    print(f"   {len(universe)}개 ETF 로드 완료")
    print()

    # 매칭
    matches = []
    for it in universe:
        tab = it.get("etfTabCode")
        if args.include_tab and tab not in args.include_tab:
            continue
        if args.exclude_tab and tab in args.exclude_tab:
            continue
        name = it.get("itemname", "")
        if not match_etf(name, args.keywords):
            continue
        if any(ekw in name for ekw in args.exclude_keyword):
            continue
        matches.append(it)

    if not matches:
        print(f"❌ 매칭 ETF 없음 (키워드: {', '.join(args.keywords)})")
        return

    # 시가총액 내림차순 정렬
    matches.sort(key=lambda x: x.get("marketSum", 0), reverse=True)

    print(f"✅ {len(matches)}개 ETF 매칭 (키워드: {', '.join(args.keywords)})")
    print(f"{'코드':<8} {'이름':<32} {'분류':<14} {'시총':>10} {'거래대금':>12} {'3M수익':>9}")
    print("─" * 95)
    for it in matches:
        tab_desc = TAB_CODE_DESC.get(it.get("etfTabCode"), "기타")
        marketSum = it.get("marketSum", 0)
        amount = it.get("amonut", 0)  # Naver API typo "amonut"
        rate = it.get("threeMonthEarnRate", 0)
        print(f"{it['itemcode']:<8} {it['itemname']:<32} {tab_desc:<14} "
              f"{marketSum:>8,}억 {amount:>10,}백만 {rate:>+8.2f}%")

    if not args.add_sector:
        print()
        print("ℹ️  --add-sector <키>를 추가하면 etf-data.json에 자동 등록")
        return

    # etf-data.json에 추가
    print()
    print(f"📝 섹터 '{args.add_sector}'에 추가 중...")
    if not ETF_DATA_PATH.exists():
        print(f"❌ {ETF_DATA_PATH} 없음")
        sys.exit(1)

    with ETF_DATA_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    sector = next((s for s in data["sectors"] if s["key"] == args.add_sector), None)
    if not sector:
        print(f"❌ 섹터 키 '{args.add_sector}' 없음. etf-data.json에 먼저 sectors[]에 추가 필요.")
        sys.exit(1)

    added = []
    skipped = []
    today = datetime.now().strftime("%Y-%m-%d")

    for it in matches:
        code = it["itemcode"]
        if code in sector["etf_codes"]:
            skipped.append(f"{code} {it['itemname']} (이미 등록)")
            continue
        sector["etf_codes"].append(code)

        # etfs 객체에 stub 추가 (또는 갱신)
        if code in data["etfs"]:
            skipped.append(f"{code} {it['itemname']} (etfs에 이미 존재 → 섹터만 추가)")
            continue

        # 운용사·상장일 fetch (즉시)
        meta = fetch_etf_meta(code)
        manager = meta.get("issuerName") if meta else None
        tracking = meta.get("etfBaseIndex") if meta else None
        listed = parse_listed_date(meta.get("listedDate")) if meta else None
        geo = TAB_TO_GEO.get(it.get("etfTabCode"), "한국")

        data["etfs"][code] = {
            "code": code,
            "name": it["itemname"],
            "manager": manager or "",
            "geography": geo,
            "tracking_index": tracking,
            "listed_date": listed,
            "expense_ratio_pct": None,
            "aum_krw": None,
            "trading_volume_30d_krw": None,
            "ytd_return_pct": None,
            "top_holdings": [],
            "metrics_updated_at": None,
            "notes": f"[{today} 자동 발견] 추종지수 {tracking or '?'}.",
        }
        added.append(f"{code} {it['itemname']}")

    data["updated_at"] = today
    with ETF_DATA_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print()
    if added:
        print(f"➕ 신규 추가 ({len(added)}건):")
        for s in added:
            print(f"   {s}")
    if skipped:
        print(f"⏭  스킵 ({len(skipped)}건):")
        for s in skipped:
            print(f"   {s}")

    print(f"💾 {ETF_DATA_PATH.name} 저장 완료")

    if args.fetch_metrics and added:
        print()
        print(f"🚀 fetch_etf_metrics.py 자동 실행 ({len(added)}건)...")
        for s in added:
            code = s.split()[0]
            print(f"   → {code}")
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "fetch_etf_metrics.py"), "--code", code],
                check=False,
            )


if __name__ == "__main__":
    main()
