#!/usr/bin/env python3
"""
ETF 메타데이터 자동 갱신 스크립트.

Naver 모바일 API에서 운용보수·AUM·30일 거래대금·상위 종목·수익률 fetch.
의존성 없음 (Python stdlib만 사용).

사용법:
    python scripts/fetch_etf_metrics.py             # 모든 ETF 갱신
    python scripts/fetch_etf_metrics.py --code 091160  # 특정 ETF만
    python scripts/fetch_etf_metrics.py --debug     # 원시 응답 출력
    python scripts/fetch_etf_metrics.py --dry-run   # JSON 저장 안 함

API endpoints (Naver):
- m.stock.naver.com/api/stock/{code}/etfAnalysis  # 운용보수, AUM, top10, YTD
- api.stock.naver.com/chart/domestic/item/{code}/day  # 30일 거래대금
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Windows cp949 콘솔 호환을 위해 UTF-8로 강제
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
ETF_DATA_PATH = ROOT / "public" / "data" / "etf-data.json"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
    "Referer": "https://m.stock.naver.com/",
}


# ─────────────────────────────────────────────────────────
# HTTP
# ─────────────────────────────────────────────────────────

def fetch_json(url: str, timeout: int = 10):
    req = Request(url, headers=HEADERS)
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


# ─────────────────────────────────────────────────────────
# 한국식 금액 문자열 파싱
# ─────────────────────────────────────────────────────────

def parse_korean_money(s):
    """
    "5조 4,924억" → 5_492_400_000_000
    "1,234억" → 123_400_000_000
    "500만" → 5_000_000
    숫자/None → 그대로
    """
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return int(s)
    if not isinstance(s, str):
        return None

    s = s.strip().replace(" ", "")
    if not s:
        return None

    total = 0
    matched = False

    # 조
    m = re.search(r"([\d,\.]+)조", s)
    if m:
        total += float(m.group(1).replace(",", "")) * 1_000_000_000_000
        matched = True

    # 억
    m = re.search(r"([\d,\.]+)억", s)
    if m:
        total += float(m.group(1).replace(",", "")) * 100_000_000
        matched = True

    # 만
    m = re.search(r"([\d,\.]+)만", s)
    if m:
        total += float(m.group(1).replace(",", "")) * 10_000
        matched = True

    if matched:
        return int(total)

    # 단위 표기 없으면 숫자로 시도
    digits = re.sub(r"[^\d.]", "", s)
    if digits:
        try:
            return int(float(digits))
        except ValueError:
            return None
    return None


def parse_pct(value):
    """0.45, "0.45%", "+30.43%" → 0.45 / 30.43"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.replace("%", "").replace(",", "").replace("+", "").strip()
        try:
            return float(s)
        except ValueError:
            return None
    return None


def parse_listed_date(s):
    """20060627 → "2006-06-27" """
    if not s:
        return None
    s = str(s)
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return s


# ─────────────────────────────────────────────────────────
# Naver fetchers
# ─────────────────────────────────────────────────────────

def fetch_etf_analysis(code: str, debug: bool = False) -> dict:
    """ETF 상세 분석 데이터."""
    url = f"https://m.stock.naver.com/api/stock/{code}/etfAnalysis"
    try:
        data = fetch_json(url)
    except (HTTPError, URLError) as e:
        return {"_error": f"etfAnalysis: {e}"}
    except json.JSONDecodeError as e:
        return {"_error": f"etfAnalysis JSON: {e}"}

    if debug:
        print(f"\n[debug] etfAnalysis({code}) keys: {list(data.keys())}")

    out = {}

    # 운용보수
    out["expense_ratio_pct"] = parse_pct(data.get("totalFee"))

    # AUM (시가총액)
    out["aum_krw"] = parse_korean_money(data.get("marketValue"))
    out["nav_total_krw"] = parse_korean_money(data.get("totalNav"))

    # 상장일
    out["listed_date"] = parse_listed_date(data.get("listedDate"))

    # 추종 지수
    out["tracking_index"] = data.get("etfBaseIndex")

    # 추적 오차
    out["tracking_error_pct"] = parse_pct(data.get("chaseErrorRate"))

    # YTD 수익률
    perf = data.get("returnPerformanceList") or []
    for item in perf:
        if item.get("periodTypeCode") == "YTD":
            out["ytd_return_pct"] = parse_pct(item.get("value"))
            break

    # 상위 10 종목
    top10_raw = data.get("etfTop10MajorConstituentAssets") or []
    top10 = []
    for item in top10_raw:
        weight = parse_pct(item.get("etfWeight"))
        name = item.get("itemName")
        item_code = item.get("itemCode")
        if name and weight is not None:
            top10.append({
                "code": item_code,
                "name": name,
                "weight_pct": weight,
            })
    out["top_holdings"] = top10

    return out


def fetch_30day_trading_value(code: str, debug: bool = False) -> int | None:
    """최근 30일 거래대금 누계 (close × volume 합)."""
    end = datetime.now()
    start = end - timedelta(days=50)  # 영업일 30일 확보 위해 여유
    url = (
        f"https://api.stock.naver.com/chart/domestic/item/{code}/day"
        f"?startDateTime={start.strftime('%Y%m%d')}0900"
        f"&endDateTime={end.strftime('%Y%m%d')}1600"
    )
    try:
        data = fetch_json(url)
    except (HTTPError, URLError, json.JSONDecodeError) as e:
        if debug:
            print(f"[debug] chart({code}) error: {e}")
        return None

    if not isinstance(data, list) or not data:
        return None

    # 최근 30개 영업일만
    recent = data[-30:]
    total = 0.0
    for d in recent:
        close = d.get("closePrice")
        vol = d.get("accumulatedTradingVolume")
        if close and vol:
            total += float(close) * float(vol)
    return int(total) if total > 0 else None


# ─────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────

def update_etf(etf: dict, metrics: dict, listed_date_from_api: str | None = None) -> bool:
    """metrics를 etf 객체에 머지. 변경 발생 시 True."""
    changed = False
    fields = [
        "expense_ratio_pct",
        "aum_krw",
        "ytd_return_pct",
        "top_holdings",
        "tracking_error_pct",
    ]
    for f in fields:
        if f in metrics and metrics[f] is not None:
            # top_holdings는 빈 리스트 허용
            if f == "top_holdings" and not metrics[f]:
                continue
            if etf.get(f) != metrics[f]:
                etf[f] = metrics[f]
                changed = True

    # tracking_index 업데이트 (기존이 비어 있을 때만)
    if metrics.get("tracking_index") and not etf.get("tracking_index"):
        etf["tracking_index"] = metrics["tracking_index"]
        changed = True

    # listed_date 업데이트 (기존이 비어 있을 때만)
    if listed_date_from_api and not etf.get("listed_date"):
        etf["listed_date"] = listed_date_from_api
        changed = True

    return changed


def main():
    parser = argparse.ArgumentParser(description="ETF 메트릭 갱신")
    parser.add_argument("--code", help="특정 ETF 종목코드만 갱신")
    parser.add_argument("--debug", action="store_true", help="디버그 출력")
    parser.add_argument("--dry-run", action="store_true", help="JSON 저장 안 함")
    parser.add_argument("--sleep", type=float, default=0.5, help="요청 간 sleep 초")
    args = parser.parse_args()

    if not ETF_DATA_PATH.exists():
        print(f"❌ {ETF_DATA_PATH} 없음", file=sys.stderr)
        sys.exit(1)

    with ETF_DATA_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    codes = [args.code] if args.code else list(data["etfs"].keys())
    print(f"🔍 {len(codes)}개 ETF 갱신 시작 (Naver mobile API)")
    print()

    success = 0
    fail = 0
    today_str = datetime.now().strftime("%Y-%m-%d")

    for code in codes:
        if code not in data["etfs"]:
            print(f"  ⚠️  {code}: etf-data.json에 미등록 — 스킵")
            continue

        etf = data["etfs"][code]
        name = etf.get("name", "?")
        print(f"  📡 {code} {name}", flush=True)

        # 1) etfAnalysis
        analysis = fetch_etf_analysis(code, debug=args.debug)
        if "_error" in analysis:
            print(f"      ✗ analysis: {analysis['_error']}")
            fail += 1
            continue

        # 2) 30일 거래대금
        vol30 = fetch_30day_trading_value(code, debug=args.debug)
        if vol30:
            etf["trading_volume_30d_krw"] = vol30

        # 3) merge
        listed = analysis.get("listed_date")
        changed = update_etf(etf, analysis, listed_date_from_api=listed)
        if vol30:
            changed = True

        if changed:
            etf["metrics_updated_at"] = today_str
            print(f"      ✓ 보수 {analysis.get('expense_ratio_pct')}% · "
                  f"AUM {format_money(analysis.get('aum_krw'))} · "
                  f"YTD {analysis.get('ytd_return_pct')}% · "
                  f"top10 {len(analysis.get('top_holdings', []))}건 · "
                  f"30일거래대금 {format_money(vol30)}")
            success += 1
        else:
            print(f"      — 변경 없음")

        time.sleep(args.sleep)

    if not args.dry_run and success > 0:
        data["data_status"]["metrics_last_refreshed"] = today_str
        data["updated_at"] = today_str
        with ETF_DATA_PATH.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print()
        print(f"✅ {ETF_DATA_PATH.name} 저장 완료")

    print()
    print(f"📊 결과: {success}건 성공 / {fail}건 실패 / 총 {len(codes)}건")


def format_money(amt):
    if amt is None:
        return "—"
    if amt >= 1e12:
        return f"{amt / 1e12:.1f}조"
    if amt >= 1e8:
        return f"{int(amt / 1e8):,}억"
    if amt >= 1e4:
        return f"{int(amt / 1e4):,}만"
    return str(amt)


if __name__ == "__main__":
    main()
