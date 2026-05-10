"""한국 주식 데이터 수집 래퍼.

데이터 소스:
- m.stock.naver.com/api: 종목 리스트, 시총/PER/외인율, 분기/연간 재무, 가격
- query1.finance.yahoo.com: 종가/거래량 시계열 (RS·52주 신고가·시장 추세 계산용)
- opendart.fss.or.kr/api: 확정 재무제표 + 5%룰 대량보유 공시 (기관 매집 추세)

모든 함수는 실패 시 None/빈 리스트를 반환. 호출 측에서 필터링.
"""

from __future__ import annotations

import io
import json
import os
import re
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / ".cache"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
NAVER_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json",
    "Referer": "https://m.stock.naver.com/",
}
YAHOO_HEADERS = {"User-Agent": UA}

NAVER_LIST = "https://m.stock.naver.com/api/stocks/marketValue"
NAVER_API = "https://m.stock.naver.com/api/stock"
YAHOO_API = "https://query1.finance.yahoo.com/v8/finance/chart"
DART_API = "https://opendart.fss.or.kr/api"

EXCLUDE_PATTERN = re.compile(r"스팩|SPAC|리츠|REIT|ETF|ETN|인프라|우B$|우C$|\d우$")


def _http_get_json(url: str, headers: dict[str, str], timeout: int = 10) -> Any | None:
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except (HTTPError, URLError, json.JSONDecodeError, TimeoutError):
        return None


def parse_num(s: Any) -> float:
    """문자열 숫자(콤마/단위 포함)를 float로. 실패 시 0."""
    if s is None or s == "" or s == "-":
        return 0.0
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).replace(",", "")
    m = re.search(r"-?[\d.]+", s)
    return float(m.group(0)) if m else 0.0


def parse_market_cap(s: str) -> float:
    """'33조 7,800억' → 337800 (단위: 억원)."""
    if not s:
        return 0.0
    total = 0.0
    jo = re.search(r"([\d,]+)조", s)
    eok = re.search(r"([\d,]+)억", s)
    if jo:
        total += parse_num(jo.group(1)) * 10000
    if eok:
        total += parse_num(eok.group(1))
    return total


# ── 종목 리스트 ──

def fetch_stock_list(market: str) -> list[dict[str, str]]:
    """m.stock.naver의 시가총액 페이지를 순회해 보통주 종목만 수집.

    market: "KOSPI" 또는 "KOSDAQ"
    """
    out: list[dict[str, str]] = []
    page = 1
    while True:
        url = f"{NAVER_LIST}/{market}?page={page}&pageSize=100"
        data = _http_get_json(url, NAVER_HEADERS)
        if not data:
            break
        stocks = data.get("stocks") or []
        if not stocks:
            break
        for s in stocks:
            if s.get("stockEndType") == "stock":
                name = s.get("stockName", "")
                if EXCLUDE_PATTERN.search(name):
                    continue
                out.append({"code": s.get("itemCode", ""), "name": name, "market": market})
        if len(stocks) < 100:
            break
        page += 1
    return out


# ── Naver: 시총/PER/외인 ──

def fetch_integration(code: str) -> dict[str, Any] | None:
    """integration 엔드포인트로 시총/PER/PBR/배당수익률/외인소진율/현재가 추출."""
    data = _http_get_json(f"{NAVER_API}/{code}/integration", NAVER_HEADERS)
    if not data:
        return None
    infos = data.get("totalInfos") or []
    kv = {i.get("key"): i.get("value") for i in infos}

    market_cap = parse_market_cap(kv.get("시총", "")) if kv.get("시총") else 0.0
    per_str = kv.get("PER", "")
    per = parse_num(per_str) if per_str and per_str != "N/A" else None

    return {
        "market_cap_eok": market_cap,
        "per": per,
        "pbr": parse_num(kv.get("PBR")),
        "dividend_yield": parse_num(kv.get("배당수익률")),
        "foreign_ownership": parse_num(kv.get("외인소진율")),
        "price": parse_num(kv.get("전일")),
    }


def fetch_basic(code: str) -> dict[str, Any] | None:
    """basic 엔드포인트 - 현재가/거래량/유통주식수."""
    return _http_get_json(f"{NAVER_API}/{code}/basic", NAVER_HEADERS)


# ── Naver: 재무제표 (annual + quarter) ──

def _parse_finance(data: dict[str, Any]) -> dict[str, Any] | None:
    fi = data.get("financeInfo") or {}
    periods = fi.get("trTitleList") or []
    rows = fi.get("rowList") or []
    if not periods or not rows:
        return None
    return {"periods": periods, "rows": rows}


def fetch_annual(code: str) -> dict[str, Any] | None:
    """연간 재무 데이터 - financeInfo 구조 그대로 반환."""
    data = _http_get_json(f"{NAVER_API}/{code}/finance/annual", NAVER_HEADERS)
    return _parse_finance(data) if data else None


def fetch_quarter(code: str) -> dict[str, Any] | None:
    """분기 재무 데이터."""
    data = _http_get_json(f"{NAVER_API}/{code}/finance/quarter", NAVER_HEADERS)
    return _parse_finance(data) if data else None


def get_row_values(parsed: dict[str, Any], title: str, only_confirmed: bool = True) -> list[tuple[str, float]]:
    """parsed['rows']에서 title에 해당하는 행을 찾아 (period_key, value) 리스트 반환.

    only_confirmed=True면 isConsensus='N' 기간만 (확정 실적).
    시간 순서대로 정렬해 반환.
    """
    rows = parsed.get("rows") or []
    periods = parsed.get("periods") or []
    if only_confirmed:
        periods = [p for p in periods if p.get("isConsensus") == "N"]

    target = next((r for r in rows if r.get("title") == title), None)
    if not target:
        return []
    cols = target.get("columns") or {}
    out: list[tuple[str, float]] = []
    for p in periods:
        key = p.get("key", "")
        cell = cols.get(key)
        if cell is None:
            continue
        v = parse_num(cell.get("value")) if isinstance(cell, dict) else parse_num(cell)
        out.append((key, v))
    return out


# ── Yahoo Finance: 가격 시계열 ──

def yahoo_symbol(code: str, market: str) -> str:
    """'005930' + 'KOSPI' → '005930.KS'."""
    suffix = "KS" if market == "KOSPI" else "KQ"
    return f"{code}.{suffix}"


def fetch_yahoo_chart(symbol: str, range_: str = "1y", interval: str = "1d") -> dict[str, list] | None:
    """Yahoo Finance 차트 API. closes/volumes/timestamps 리스트 반환."""
    qs = urlencode({"range": range_, "interval": interval})
    url = f"{YAHOO_API}/{symbol}?{qs}"
    data = _http_get_json(url, YAHOO_HEADERS, timeout=15)
    if not data:
        return None
    try:
        result = data["chart"]["result"][0]
        timestamps = result.get("timestamp") or []
        quote = result.get("indicators", {}).get("quote", [{}])[0]
        closes = quote.get("close") or []
        volumes = quote.get("volume") or []
        # null 제거
        clean_t, clean_c, clean_v = [], [], []
        for i, t in enumerate(timestamps):
            c = closes[i] if i < len(closes) else None
            v = volumes[i] if i < len(volumes) else None
            if c is None:
                continue
            clean_t.append(t)
            clean_c.append(float(c))
            clean_v.append(int(v) if v is not None else 0)
        return {"timestamps": clean_t, "closes": clean_c, "volumes": clean_v}
    except (KeyError, IndexError, TypeError):
        return None


# ── DART: 확정 재무제표 (선택적) ──

def dart_get(endpoint: str, params: dict[str, str]) -> list[dict[str, Any]] | None:
    """DART OpenAPI 호출. 'list' 필드를 그대로 반환. 키 없으면 None."""
    api_key = os.environ.get("DART_API_KEY")
    if not api_key:
        return None
    qs = urlencode({**params, "crtfc_key": api_key})
    url = f"{DART_API}/{endpoint}.json?{qs}"
    data = _http_get_json(url, {"User-Agent": UA}, timeout=15)
    if not data:
        return None
    if data.get("status") == "000":
        return data.get("list") or []
    return None


def load_corp_code_map() -> dict[str, str]:
    """DART corpCode.xml ZIP 다운로드 → stock_code → corp_code 매핑.

    캐시 파일은 .cache/dart_corpcode.json. 키 없으면 빈 dict 반환.
    """
    cache_path = CACHE_DIR / "dart_corpcode.json"
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    api_key = os.environ.get("DART_API_KEY")
    if not api_key:
        return {}

    url = f"{DART_API}/corpCode.xml?crtfc_key={api_key}"
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=30) as r:
            zip_bytes = r.read()
    except (HTTPError, URLError, TimeoutError):
        return {}

    out: dict[str, str] = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        xml_name = next((n for n in z.namelist() if n.endswith(".xml")), None)
        if not xml_name:
            return {}
        with z.open(xml_name) as fp:
            tree = ET.parse(fp)
    for el in tree.getroot().findall("list"):
        cc = (el.findtext("corp_code") or "").strip()
        sc = (el.findtext("stock_code") or "").strip()
        if cc and sc and len(sc) == 6:
            out[sc] = cc

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(out), encoding="utf-8")
    return out


def fetch_majorstock_holding(corp_code: str) -> dict[str, Any] | None:
    """DART 5%룰 대량보유 공시(majorstock)로 기관 합산 보유율 + 최근 1년 추세 계산.

    Returns:
      {
        "institutional_pct": float,    # 보고자별 최종 보유율 합산
        "recent_trend": "up"|"flat"|"down",
        "reporters": int,               # 보고자 수
      }
    """
    items = dart_get("majorstock", {"corp_code": corp_code})
    if items is None:
        return None
    if not items:
        return {"institutional_pct": 0.0, "recent_trend": "flat", "reporters": 0}

    # 보고자별 최신 보고일자 + 보유율 추출 (rcept_dt 가장 큰 항목 사용)
    by_reporter: dict[str, dict[str, Any]] = {}
    for it in items:
        reporter = (it.get("repror") or "").strip()
        if not reporter:
            continue
        rcept_dt = (it.get("rcept_dt") or "").strip()  # YYYYMMDD
        try:
            stkrt = float((it.get("stkrt") or "0").replace(",", ""))
        except (ValueError, AttributeError):
            stkrt = 0.0

        existing = by_reporter.get(reporter)
        if existing is None or rcept_dt > existing["rcept_dt"]:
            by_reporter[reporter] = {"rcept_dt": rcept_dt, "stkrt": stkrt}

    institutional_pct = sum(r["stkrt"] for r in by_reporter.values())

    # 최근 1년 변동 합계로 추세 판정
    from datetime import datetime, timedelta
    one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
    recent_change = 0.0
    for it in items:
        rcept_dt = (it.get("rcept_dt") or "").strip()
        if rcept_dt < one_year_ago:
            continue
        try:
            irds = float((it.get("stkqy_irds") or "0").replace(",", ""))
        except (ValueError, AttributeError):
            irds = 0.0
        recent_change += irds

    if recent_change > 0:
        trend = "up"
    elif recent_change < 0:
        trend = "down"
    else:
        trend = "flat"

    return {
        "institutional_pct": institutional_pct,
        "recent_trend": trend,
        "reporters": len(by_reporter),
    }


def sleep(ms: int) -> None:
    time.sleep(ms / 1000)
