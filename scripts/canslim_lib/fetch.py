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
import random
import re
import time
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests as _requests
from requests.adapters import HTTPAdapter

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


# ── HTTP Session (keep-alive) ──────────────────────────────────
# requests.Session 한 개를 프로세스 전체에서 재사용해 TLS handshake 비용 절약.
# 워커 모드는 프로세스 분리 → 각 워커가 자기 세션을 가짐 (스레드 안전성 불요).
_session = _requests.Session()
_adapter = HTTPAdapter(pool_connections=8, pool_maxsize=16, max_retries=0)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)

# 호스트별 마지막 요청 시각 — politeness delay 계산용
_LAST_REQUEST_AT: dict[str, float] = {}

# 요청 간 최소 간격 (호스트별, 초). 환경변수 CANSLIM_REQ_DELAY 로 override.
_MIN_INTERVAL = float(os.environ.get("CANSLIM_REQ_DELAY", "0.15"))


def _politeness_wait(host: str) -> None:
    last = _LAST_REQUEST_AT.get(host, 0.0)
    elapsed = time.time() - last
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)


def _http_get_json(url: str, headers: dict[str, str], timeout: int = 10,
                   max_retries: int = 3) -> Any | None:
    """JSON GET — politeness delay + 자동 재시도 (exponential backoff).

    재시도 트리거: 네트워크 오류, JSON 디코드 실패, 5xx 서버에러.
    HTTP 4xx (404 등) 는 재시도 안 함 (영속 실패).
    """
    host = url.split("/")[2] if "://" in url else "default"
    _politeness_wait(host)

    for attempt in range(max_retries + 1):
        retry = False
        try:
            resp = _session.get(url, headers=headers, timeout=timeout)
            _LAST_REQUEST_AT[host] = time.time()
            status = resp.status_code
            if 400 <= status < 500:
                return None  # 4xx 영속 실패
            if 200 <= status < 300:
                try:
                    return resp.json()
                except ValueError:
                    retry = True  # JSON 디코드 실패 → 재시도
            else:
                retry = True  # 5xx → 재시도
        except (_requests.RequestException, OSError):
            _LAST_REQUEST_AT[host] = time.time()
            retry = True

        if retry and attempt < max_retries:
            # 재시도 backoff (지터 추가해 동시 워커가 동기화되어 함께 재시도하는 thundering herd 방지)
            backoff = (2 ** attempt) * 0.5 + random.uniform(0, 0.3)
            time.sleep(backoff)
        elif not retry:
            return None
    return None


def _http_get_bytes(url: str, headers: dict[str, str], timeout: int = 15) -> bytes | None:
    """바이너리 GET (corpCode.xml, document.xml ZIP) — 세션 keep-alive 만 사용. 재시도 없음."""
    host = url.split("/")[2] if "://" in url else "default"
    _politeness_wait(host)
    try:
        resp = _session.get(url, headers=headers, timeout=timeout)
        _LAST_REQUEST_AT[host] = time.time()
        if resp.status_code != 200:
            return None
        return resp.content
    except (_requests.RequestException, OSError):
        _LAST_REQUEST_AT[host] = time.time()
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


# ── Naver day chart (api.stock.naver.com) — OHLCV + 외국인지분율 시계열 ──
# m.stock.naver.com 과 별개 host = rate limit 풀 분리 (8 워커 동시 hit OK).
# 1년 일봉 ~245일 + foreignRetentionRate 시계열 (1회 호출).

NAVER_CHART_API = "https://api.stock.naver.com/chart/domestic/item"


def fetch_naver_day_chart(code: str, days_back: int = 400) -> dict[str, list] | None:
    """api.stock.naver.com 일별 차트. OHLCV + 외국인지분율 시계열.

    Args:
      code: 6자리 종목코드 ("005930").
      days_back: 오늘 기준 며칠 전부터. default 400 (~13개월, 영업일 ~270개).

    Returns:
      {
        "timestamps": list[int],       # epoch seconds (Asia/Seoul 종가 시각 16:00 KST)
        "closes":     list[float],     # 종가
        "opens":      list[float],
        "highs":      list[float],
        "lows":       list[float],
        "volumes":    list[int],       # 누적 거래량
        "foreign_rates": list[float | None],  # 외국인지분율 (%) — null 가능
        "dates":      list[str],       # YYYY-MM-DD
      }
      실패 시 None.
    """
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    today = _dt.now()
    start = (today - _td(days=days_back)).strftime("%Y%m%d") + "0900"
    end = today.strftime("%Y%m%d") + "1600"
    url = f"{NAVER_CHART_API}/{code}/day?startDateTime={start}&endDateTime={end}"

    host = "api.stock.naver.com"
    _politeness_wait(host)
    try:
        resp = _session.get(url, headers={"User-Agent": UA}, timeout=15)
        _LAST_REQUEST_AT[host] = time.time()
        if resp.status_code != 200:
            return None
        data = resp.json()
    except (_requests.RequestException, OSError, ValueError):
        _LAST_REQUEST_AT[host] = time.time()
        return None
    if not isinstance(data, list) or not data:
        return None

    kst = _tz(_td(hours=9))
    timestamps: list[int] = []
    dates: list[str] = []
    closes: list[float] = []
    opens: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    volumes: list[int] = []
    foreign_rates: list[float | None] = []

    for row in data:
        ld = row.get("localDate")
        cp = row.get("closePrice")
        if not ld or cp is None:
            continue
        try:
            dt_iso = f"{ld[:4]}-{ld[4:6]}-{ld[6:8]}"
            ts = int(_dt.strptime(ld + " 16:00", "%Y%m%d %H:%M").replace(tzinfo=kst).timestamp())
        except (ValueError, TypeError):
            continue
        try:
            close_v = float(cp)
        except (ValueError, TypeError):
            continue
        timestamps.append(ts)
        dates.append(dt_iso)
        closes.append(close_v)
        opens.append(float(row.get("openPrice") or close_v))
        highs.append(float(row.get("highPrice") or close_v))
        lows.append(float(row.get("lowPrice") or close_v))
        try:
            volumes.append(int(row.get("accumulatedTradingVolume") or 0))
        except (ValueError, TypeError):
            volumes.append(0)
        fr = row.get("foreignRetentionRate")
        try:
            foreign_rates.append(float(fr) if fr is not None else None)
        except (ValueError, TypeError):
            foreign_rates.append(None)

    if not timestamps:
        return None
    return {
        "timestamps": timestamps,
        "dates": dates,
        "closes": closes,
        "opens": opens,
        "highs": highs,
        "lows": lows,
        "volumes": volumes,
        "foreign_rates": foreign_rates,
    }


# ── Yahoo Finance: 가격 시계열 ──

def yahoo_symbol(code: str, market: str) -> str:
    """'005930' + 'KOSPI' → '005930.KS'."""
    suffix = "KS" if market == "KOSPI" else "KQ"
    return f"{code}.{suffix}"


def fetch_yahoo_chart(symbol: str, range_: str = "1y", interval: str = "1d",
                      period1: int | None = None, period2: int | None = None) -> dict[str, list] | None:
    """Yahoo Finance 차트 API. closes/volumes/timestamps 리스트 반환.

    period1/period2(epoch 초) 지정 시 그 날짜 구간(과거 사이클)을 조회 —
    range_ 무시. 미지정 시 기존대로 range_ 사용(하위호환).
    """
    if period1 is not None and period2 is not None:
        qs = urlencode({"period1": int(period1), "period2": int(period2), "interval": interval})
    else:
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

_DART_EXHAUSTED: set[str] = set()  # status 020(일일 한도 초과)로 소진된 키 (런 단위)


def _dart_keys() -> list[str]:
    """env 의 DART_API_KEY, DART_API_KEY2, DART_API_KEY3 … 순서 키 목록."""
    out: list[str] = []
    for name in ("DART_API_KEY", "DART_API_KEY2", "DART_API_KEY3", "DART_API_KEY4"):
        v = os.environ.get(name)
        if v and v not in out:
            out.append(v)
    return out


def dart_active_key() -> str | None:
    """현재 사용 가능한(소진 안 된) 첫 DART 키. 직접 호출자(company.json 등)용."""
    for k in _dart_keys():
        if k not in _DART_EXHAUSTED:
            return k
    return None


def dart_mark_exhausted(key: str) -> None:
    if key:
        _DART_EXHAUSTED.add(key)


# DART 분당 1000회 제한 (서버 측 IP 단위 — 초과 시 IP 자동 차단)
# 안전 마진: 분당 800회로 제한 (sliding window, process-local 카운터)
# 멀티 워커 모드는 IP 합산이라 환경변수 CANSLIM_DART_RATE_LIMIT 으로 워커별 cap 조정 필요
# 예: 8 워커 = 워커당 100 (총 800), 4 워커 = 200 (총 800), 단일 = 800
_DART_RATE_WINDOW = 60.0  # 초
_DART_RATE_LIMIT = int(os.environ.get("CANSLIM_DART_RATE_LIMIT", "800"))
_dart_call_times: list[float] = []  # 최근 호출 시각 (sliding window, process-local)


def _dart_rate_limit_wait() -> None:
    """sliding window 기반 throttle — 최근 60초 내 호출이 _DART_RATE_LIMIT 도달 시 대기."""
    now = time.time()
    # 윈도우 밖 호출 제거
    cutoff = now - _DART_RATE_WINDOW
    while _dart_call_times and _dart_call_times[0] < cutoff:
        _dart_call_times.pop(0)
    if len(_dart_call_times) >= _DART_RATE_LIMIT:
        # 가장 오래된 호출이 60초 지날 때까지 대기
        wait = _dart_call_times[0] + _DART_RATE_WINDOW - now + 0.1
        if wait > 0:
            time.sleep(wait)
        # 재정리
        now = time.time()
        cutoff = now - _DART_RATE_WINDOW
        while _dart_call_times and _dart_call_times[0] < cutoff:
            _dart_call_times.pop(0)
    _dart_call_times.append(time.time())


def dart_get(endpoint: str, params: dict[str, str]) -> list[dict[str, Any]] | None:
    """DART OpenAPI 호출. 'list' 반환. status 020(한도초과) 시 다음 키로 페일오버.

    Rate limit: 분당 800회 cap (서버 한도 1000, 초과 시 IP 자동 차단).
    정상 흐름 불변(키 1개·정상 응답이면 기존과 동일). 020일 때만 키 교체·재시도.
    """
    _dart_rate_limit_wait()  # 호출 전 throttle
    keys = [k for k in _dart_keys() if k not in _DART_EXHAUSTED]
    if not keys:
        return None
    for key in keys:
        qs = urlencode({**params, "crtfc_key": key})
        url = f"{DART_API}/{endpoint}.json?{qs}"
        data = _http_get_json(url, {"User-Agent": UA}, timeout=15)
        if not data:
            return None  # 네트워크/JSON 실패 — 키 문제 아님
        st = data.get("status")
        if st == "000":
            return data.get("list") or []
        if st == "020":  # 사용한도 초과 → 이 키 소진, 다음 키로
            _DART_EXHAUSTED.add(key)
            continue
        return None  # 013(데이터없음) 등 — 키 바꿔도 동일
    return None  # 모든 키 020 소진


def resolve_corp_code(code: str, corp_map: dict[str, str]) -> tuple[str | None, str | None]:
    """우선주 코드를 보통주 corp_code 로 fallback.

    Returns: (corp_code, parent_common_code).
    parent_common_code 가 None 이면 직접 매칭, 값이 있으면 우선주(보통주 corp_code 사용 중).
    한국 우선주 끝자리 관행: 5(우선주1종), 7(우선주2종/신형), 9(전환우선주).
    """
    if code in corp_map:
        return corp_map[code], None
    if len(code) == 6 and code[-1] in "5679":
        common = code[:5] + "0"
        cc = corp_map.get(common)
        if cc:
            return cc, common
    return None, None


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
    zip_bytes = _http_get_bytes(url, {"User-Agent": UA}, timeout=30)
    if not zip_bytes:
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


def _extract_quarterly_account_row(
    items: list[dict[str, Any]],
    candidates_substrings: list[str],
    exclude_substrings: tuple[str, ...] = (),
) -> dict[str, float] | None:
    """fnlttSinglAcntAll 응답에서 후보 계정 중 하나의 행을 찾아 분기 단일/전년 동기 단일 추출.

    DART 분기 보고서 필드:
      thstrm_amount: 당기 분기 단일
      frmtrm_q_amount: 전기 같은 분기 단일
      thstrm_add_amount: 당기 누적 (YTD)
      frmtrm_add_amount: 전기 누적

    Returns: {"current": float, "prior": float} 또는 None.
    """
    target = None
    for sub in candidates_substrings:
        for it in items:
            if it.get("sj_div") not in ("IS", "CIS"):
                continue
            name = (it.get("account_nm") or "").strip()
            normalized = name.replace(" ", "")
            if sub not in normalized:
                continue
            # EXCLUDE: 매칭됐어도 제외 키워드 포함 시 skip (계속영업/중단영업 단독 행 제외)
            if any(ex in normalized for ex in exclude_substrings):
                continue
            target = it
            break
        if target:
            break
    if not target:
        return None

    out: dict[str, float] = {}
    th = target.get("thstrm_amount")
    fr = target.get("frmtrm_q_amount") or target.get("frmtrm_amount")
    for key, raw in (("current", th), ("prior", fr)):
        if raw is None or raw in ("-", ""):
            continue
        try:
            out[key] = float(str(raw).replace(",", ""))
        except (ValueError, TypeError):
            continue
    return out if out else None


def _extract_quarterly_eps_row(items: list[dict[str, Any]]) -> dict[str, float] | None:
    """기본주당이익 행 추출 (호환 wrapper).

    적자 분기에 "주당손실"로 표기되는 케이스 (롯데케미칼·SK하이닉스 등) 포함.
    보통주/우선주 분리 표기(한진칼, 호텔신라 등)는 보통주 우선 매칭.
    EXCLUDE: 계속영업/중단영업 단독 행은 제외 (전체 손익만 잡음).
    """
    return _extract_quarterly_account_row(
        items,
        [
            # 보통주 분리 표기 (한진칼·호텔신라 등). 가장 먼저 매칭해 우선주 행 흡수 방지.
            "기본주당보통주순이익",
            "기본주당보통주순손익",
            "기본및희석보통주당이익",  # 호텔신라
            "기본및희석보통주당손익",
            # 표준 패턴 (흑자)
            "기본주당이익",
            "기본주당순이익",
            "기본주당분기순이익",
            "기본주당반기순이익",
            "기본및희석주당이익",
            "주당순이익",
            "주당분기순이익",
            "기본주당손익",
            "기본주당순손익",  # 대한전선 등
            # 적자 패턴 (롯데케미칼 등)
            "기본및희석주당손실",
            "기본주당손실",
            "주당손실",
        ],
        exclude_substrings=("계속영업", "중단영업"),
    )


def _extract_quarterly_specific_row(items: list[dict[str, Any]], account_name: str) -> dict[str, Any] | None:
    """정확한 계정명 매칭 (공백 제거 후 동일)."""
    target_norm = account_name.replace(" ", "")
    for it in items:
        if it.get("sj_div") not in ("IS", "CIS"):
            continue
        name = (it.get("account_nm") or "").strip().replace(" ", "")
        if name == target_norm:
            return it
    return None


def _extract_quarterly_sales_row(items: list[dict[str, Any]]) -> dict[str, float] | None:
    """매출액 행 추출.

    1차: 표준 매출 계정 (매출액 / 수익(매출액) / 영업수익 / 수익)
    2차: 증권사 fallback (수수료수익 + 이자수익 + 기타의영업손익 합산)
    """
    # 1차: 표준 매출 계정
    result = _extract_quarterly_account_row(
        items,
        ["매출액", "수익(매출액)", "영업수익", "매출"],
    )
    if result:
        return result

    # 2차: 증권사 fallback (수수료수익 + 이자수익 + 기타의영업손익 합산)
    parts_names = ["수수료수익", "이자수익", "기타의영업손익"]
    sums_curr = 0.0
    sums_prior = 0.0
    found_any = False
    for name in parts_names:
        row = _extract_quarterly_specific_row(items, name)
        if not row:
            continue
        try:
            th = row.get("thstrm_amount")
            if th not in (None, "-", ""):
                sums_curr += float(str(th).replace(",", ""))
                found_any = True
            fr = row.get("frmtrm_q_amount") or row.get("frmtrm_amount")
            if fr not in (None, "-", ""):
                sums_prior += float(str(fr).replace(",", ""))
        except (ValueError, TypeError):
            continue
    if not found_any:
        return None
    out: dict[str, float] = {}
    if sums_curr != 0:
        out["current"] = sums_curr
    if sums_prior != 0:
        out["prior"] = sums_prior
    return out if out else None


def _fetch_dart_quarterly_account_history(
    corp_code: str,
    base_year: int,
    extractor,
) -> list[tuple[str, float]] | None:
    """DART 분기 보고서 3개를 호출해 분기별 단일 금액 6개 (해당년 Q1/Q2/Q3 + 전년 Q1/Q2/Q3) 추출.

    사업보고서(11011)는 누적 빼기 필요해 제외. 사업보고서로 추출되는 분기는 Naver 5분기로 커버.
    extractor: _extract_quarterly_eps_row 또는 _extract_quarterly_sales_row 등 callable.

    Returns None if all sub-calls failed (connection error / quota) — 호출자가 cache 안 함.
    Returns [] if responses OK but no data extractable — negative cache 가능.
    """
    quarter_map = {"11013": "03", "11012": "06", "11014": "09"}
    out: dict[str, float] = {}
    any_ok = False  # 한 번이라도 정상 응답 (items is not None) 받았는지

    for reprt_code, q_suffix in quarter_map.items():
        items_cfs = dart_get("fnlttSinglAcntAll", {
            "corp_code": corp_code,
            "bsns_year": str(base_year),
            "reprt_code": reprt_code,
            "fs_div": "CFS",
        })
        if items_cfs is not None:
            any_ok = True
        items = items_cfs
        if not items:
            items_ofs = dart_get("fnlttSinglAcntAll", {
                "corp_code": corp_code,
                "bsns_year": str(base_year),
                "reprt_code": reprt_code,
                "fs_div": "OFS",
            })
            if items_ofs is not None:
                any_ok = True
            items = items_ofs
        if not items:
            continue
        row = extractor(items)
        if not row:
            continue
        if "current" in row:
            out[f"{base_year}{q_suffix}"] = row["current"]
        if "prior" in row:
            out[f"{base_year - 1}{q_suffix}"] = row["prior"]

    # 모든 호출 connection failure 면 None 반환 (재시도 보장)
    if not any_ok:
        return None
    return sorted(out.items())


def _extract_annual_net_income_row(items: list[dict]) -> dict[str, float] | None:
    """사업보고서(11011) 손익계산서에서 연간 당기순이익 행 추출.

    한국 사업보고서는 당기순이익 표기 다양: '당기순이익', '당기순이익(손실)', '연결당기순이익' 등.
    1차: 표준 단일 행 ('당기순이익' 변형, EXCLUDE 적용)
    2차 fallback: 계속영업+중단영업 합산 (롯데케미칼처럼 단일 '당기순이익' 행 없는 케이스)
    """
    EXCLUDE = ("주당", "계속영업", "중단영업", "법인세", "비지배", "포괄", "영업이익", "영업손익", "영업외")

    # 1차 — 표준 단일 행
    for it in items:
        if it.get("sj_div") not in ("IS", "CIS"):
            continue
        nm = (it.get("account_nm") or "").strip().replace(" ", "")
        if "당기순이익" not in nm and "당기순손익" not in nm:
            continue
        if any(ex in nm for ex in EXCLUDE):
            continue
        th = it.get("thstrm_amount")
        fr = it.get("frmtrm_amount")
        out: dict[str, float] = {}
        try:
            if th not in (None, "-", ""):
                out["current"] = float(str(th).replace(",", ""))
        except (ValueError, TypeError):
            pass
        try:
            if fr not in (None, "-", ""):
                out["prior"] = float(str(fr).replace(",", ""))
        except (ValueError, TypeError):
            pass
        if out:
            return out

    # 2차 — fallback: 계속영업 + 중단영업 합산
    cont_th = cont_fr = disc_th = disc_fr = None
    for it in items:
        if it.get("sj_div") not in ("IS", "CIS"):
            continue
        nm = (it.get("account_nm") or "").strip().replace(" ", "")
        is_cont = "계속영업당기순이익" in nm or "계속영업당기순손익" in nm
        is_disc = "중단영업당기순이익" in nm or "중단영업당기순손익" in nm
        if not (is_cont or is_disc):
            continue
        if "주당" in nm or "법인세" in nm or "비지배" in nm:
            continue
        try:
            th = float(str(it.get("thstrm_amount")).replace(",", "")) if it.get("thstrm_amount") not in (None, "-", "") else None
        except (ValueError, TypeError):
            th = None
        try:
            fr = float(str(it.get("frmtrm_amount")).replace(",", "")) if it.get("frmtrm_amount") not in (None, "-", "") else None
        except (ValueError, TypeError):
            fr = None
        if is_cont:
            if cont_th is None: cont_th = th
            if cont_fr is None: cont_fr = fr
        elif is_disc:
            if disc_th is None: disc_th = th
            if disc_fr is None: disc_fr = fr

    if cont_th is not None or disc_th is not None:
        out: dict[str, float] = {}
        th_sum = (cont_th or 0) + (disc_th or 0)
        fr_sum = (cont_fr or 0) + (disc_fr or 0)
        if th_sum != 0:
            out["current"] = th_sum
        if fr_sum != 0:
            out["prior"] = fr_sum
        if out:
            return out

    return None


def _extract_annual_equity_row(items: list[dict]) -> dict[str, float] | None:
    """사업보고서(11011) 재무상태표에서 자본총계 행 추출. 당기말/전기말 둘 다.

    부채및자본총계 등 다른 행과 구분 — '자본총계' 정확 매칭.
    """
    for it in items:
        if it.get("sj_div") != "BS":
            continue
        nm = (it.get("account_nm") or "").strip().replace(" ", "")
        if nm != "자본총계":
            continue
        th = it.get("thstrm_amount")
        fr = it.get("frmtrm_amount")
        out: dict[str, float] = {}
        try:
            if th not in (None, "-", ""):
                out["current"] = float(str(th).replace(",", ""))
        except (ValueError, TypeError):
            pass
        try:
            if fr not in (None, "-", ""):
                out["prior"] = float(str(fr).replace(",", ""))
        except (ValueError, TypeError):
            pass
        if out:
            return out
    return None


def fetch_dart_annual_financials(corp_code: str, year: int) -> dict | None:
    """사업보고서(11011)에서 연간 재무 종합 추출 + ROE 계산.

    캐시: dart_cache.get_annual_financials (과거연도 영구, 현재연도 24h).
    None / 빈 결과도 캐시 (negative cache).

    Returns:
      {
        "year": year,
        "eps": float | None,         # 기본주당이익 (원)
        "ni_eok": float | None,      # 당기순이익 (억원)
        "equity_eok": float | None,  # 자본총계 당기말 (억원)
        "equity_prior_eok": float | None,  # 전기말 자본총계 (억원)
        "sales_eok": float | None,   # 연간 매출액 (억원)
        "roe_avg": float | None,     # ROE 평균자본 기준 (%)
        "roe_end": float | None,     # ROE 기말자본 기준 (%)
        "fs_div": "CFS" | "OFS",
      }
    """
    from canslim_lib import dart_cache
    cached = dart_cache.get_annual_financials(corp_code, year)
    if cached:  # 빈 dict는 dart_cache가 이미 무시 처리
        return cached

    # connection failure (dart_get None) vs "정상 응답 + 데이터 없음" ([]) 구분
    all_failed = True
    for fs_div in ("CFS", "OFS"):
        items = dart_get("fnlttSinglAcntAll", {
            "corp_code": corp_code, "bsns_year": str(year),
            "reprt_code": "11011", "fs_div": fs_div,
        })
        if items is None:
            continue  # connection error / quota — 이 fs_div 실패
        all_failed = False  # 정상 응답 한 번이라도 받음
        if not items:
            continue  # 응답 OK but 데이터 없음

        ni_row = _extract_annual_net_income_row(items)
        equity_row = _extract_annual_equity_row(items)
        eps_row = _extract_quarterly_eps_row(items)
        sales_row = _extract_quarterly_sales_row(items)

        if not ni_row or not equity_row:
            continue  # 핵심 데이터 부족 — 다음 fs_div 시도

        ni = ni_row.get("current")
        equity = equity_row.get("current")
        equity_prior = equity_row.get("prior")

        roe_end = None
        roe_avg = None
        if ni and equity:
            roe_end = round(ni / equity * 100, 2)
            if equity_prior:
                roe_avg = round(ni / ((equity + equity_prior) / 2) * 100, 2)

        result = {
            "year": year,
            "eps": eps_row.get("current") if eps_row else None,
            "ni_eok": round(ni / 1e8, 2) if ni else None,
            "equity_eok": round(equity / 1e8, 2) if equity else None,
            "equity_prior_eok": round(equity_prior / 1e8, 2) if equity_prior else None,
            "sales_eok": round(sales_row.get("current") / 1e8, 2) if sales_row and sales_row.get("current") else None,
            "roe_avg": roe_avg,
            "roe_end": roe_end,
            "fs_div": fs_div,
        }
        dart_cache.put_annual_financials(corp_code, year, result)
        return result

    # 모든 fs_div 처리 후
    if all_failed:
        # connection failure — cache 안 함 (재시도 보장)
        return None
    # 정상 응답이지만 데이터 추출 실패 — negative cache 가능
    dart_cache.put_annual_financials(corp_code, year, {})
    return None


def fetch_dart_quarterly_eps_history(corp_code: str, base_year: int) -> list[tuple[str, float]]:
    """DART에서 base_year 와 (base_year-1) 의 분기별 단일 EPS 6분기 조회.

    캐시: dart_cache.get_quarter_eps (과거연도 영구, 현재연도 24h TTL).
    connection failure 시 (None) cache put 안 함 — 다음 풀스캔 재시도.
    """
    from canslim_lib import dart_cache
    cached = dart_cache.get_quarter_eps(corp_code, base_year)
    if cached:
        return cached
    data = _fetch_dart_quarterly_account_history(corp_code, base_year, _extract_quarterly_eps_row)
    if data is None:
        return []  # 호출자엔 빈 list 반환 (안전), cache 안 함
    dart_cache.put_quarter_eps(corp_code, base_year, data)
    return data


def fetch_dart_quarterly_sales_history(corp_code: str, base_year: int) -> list[tuple[str, float]]:
    """DART에서 base_year 와 (base_year-1) 의 분기별 단일 매출액 6분기 조회.

    캐시: dart_cache.get_quarter_sales (과거연도 영구, 현재연도 24h TTL).
    connection failure 시 (None) cache put 안 함.
    """
    from canslim_lib import dart_cache
    cached = dart_cache.get_quarter_sales(corp_code, base_year)
    if cached:
        return cached
    data = _fetch_dart_quarterly_account_history(corp_code, base_year, _extract_quarterly_sales_row)
    if data is None:
        return []
    dart_cache.put_quarter_sales(corp_code, base_year, data)
    return data


# ── DART: 잠정실적 (영업(잠정)실적 공정공시) 파싱 ──

import zipfile as _zipfile

def _fetch_disclosure_html(rcept_no: str) -> str | None:
    """rcept_no 로 공시 문서 다운로드 → ZIP 안의 HTML 추출."""
    api_key = os.environ.get("DART_API_KEY")
    if not api_key:
        return None
    url = f"{DART_API}/document.xml?crtfc_key={api_key}&rcept_no={rcept_no}"
    raw = _http_get_bytes(url, {"User-Agent": UA}, timeout=15)
    if not raw:
        return None
    try:
        with _zipfile.ZipFile(io.BytesIO(raw)) as z:
            name = next((n for n in z.namelist() if n.endswith(".xml") or n.endswith(".html")), None)
            if not name:
                return None
            return z.read(name).decode("utf-8", errors="replace")
    except (_zipfile.BadZipFile, KeyError):
        return None


def find_preliminary_disclosure(corp_code: str, year: int, quarter: int) -> tuple[str | None, bool]:
    """주어진 분기의 잠정실적 공시 rcept_no 찾기.

    quarter: 1, 2, 3, 4. 분기 종료월(3/6/9/12) 기준 +1~2개월 내 공시 검색.
    가장 최근 비정정 공시 우선, 없으면 정정 공시 사용.

    Returns: (rcept_no | None, list_ok: bool)
      list_ok=False: dart_get list 호출 자체 실패 (connection error)
      list_ok=True, rcept_no=None: 조회 성공 + 잠정실적 없음 (정당한 negative)
      list_ok=True, rcept_no=str: 잠정실적 발견
    """
    end_month = quarter * 3
    if end_month >= 13:
        return None, True
    start_month = end_month + 1
    end_search_month = end_month + 3
    end_y = year if end_search_month <= 12 else year + 1
    end_search_month_norm = end_search_month if end_search_month <= 12 else end_search_month - 12
    bgn_de = f"{year}{start_month:02d}01"
    end_de = f"{end_y}{end_search_month_norm:02d}28"

    items = dart_get("list", {"corp_code": corp_code, "bgn_de": bgn_de, "end_de": end_de, "page_count": "100"})
    if items is None:
        return None, False  # connection failure — 호출자가 cache 안 함
    if not items:
        return None, True  # 정상 응답 + 공시 없음
    matches = [it for it in items if "잠정" in (it.get("report_nm") or "") and "영업" in (it.get("report_nm") or "")]
    if not matches:
        return None, True
    # 최신 비정정 우선
    primary = [m for m in matches if "기재정정" not in (m.get("report_nm") or "") and "[첨부추가]" not in (m.get("report_nm") or "")]
    target = primary[0] if primary else matches[0]
    return target.get("rcept_no"), True


def parse_preliminary_results(html: str) -> dict[str, float] | None:
    """잠정실적 공시 HTML 에서 매출액·당기순이익(연결실적 당기) 추출.

    Returns:
      {"revenue_eok": float, "net_income_eok": float, "unit_detected": str} 또는 None.
    단위 자동 감지 (백만원/억원/천원).
    """
    import re as _re
    # 단위 감지
    unit = None
    if _re.search(r"단위\s*[:：]?\s*억원", html):
        unit = "억원"
    elif _re.search(r"단위\s*[:：]?\s*백만원", html):
        unit = "백만원"
    elif _re.search(r"단위\s*[:：]?\s*천원", html):
        unit = "천원"
    elif _re.search(r"단위\s*[:：]?\s*원", html):
        unit = "원"
    else:
        return None  # 단위 불명 — 안전하게 스킵

    # HTML 에서 텍스트만 (태그를 |로 치환)
    text = _re.sub(r"<[^>]+>", "|", html)
    # 공백+파이프 연속을 단일 |로 압축 (| | |  → |)
    text = _re.sub(r"[\s\|]*\|[\s\|]*", "|", text)

    def extract_first_numeric_after(label: str) -> float | None:
        idx = text.find(label)
        if idx == -1:
            return None
        # label 이후 첫 "당해실적" 다음 첫 숫자 토큰 (당기 값)
        chunk = text[idx:idx + 800]
        m = _re.search(r"당해실적\|([^|]+)\|", chunk)
        if not m:
            return None
        candidate = m.group(1).strip()
        m2 = _re.match(r"^-?[\d,]+(?:\.\d+)?$", candidate)
        if m2:
            try:
                return float(candidate.replace(",", ""))
            except ValueError:
                return None
        return None

    revenue = extract_first_numeric_after("매출액")
    net_income = extract_first_numeric_after("당기순이익")
    if revenue is None or net_income is None:
        return None

    # 단위 → 억원 환산
    factor = {"억원": 1.0, "백만원": 0.01, "천원": 0.0001, "원": 1e-8}[unit]
    return {
        "revenue_eok": revenue * factor,
        "net_income_eok": net_income * factor,
        "unit_detected": unit,
    }


def fetch_preliminary_quarter(corp_code: str, year: int, quarter: int) -> dict | None:
    """corp_code 의 (year, quarter) 잠정실적 가져오기.

    캐시:
      - 과거 분기 (year < 현재년 또는 현재년 < 현재분기): 영구
      - 현재 진행 분기: 6h TTL (재정정 가능성)
      - None 결과도 캐시 (negative cache)

    Returns: {"period_key": "YYYYQ", "revenue_eok": float, "net_income_eok": float, "rcept_no": str} 또는 None.
    """
    from canslim_lib import dart_cache
    cached = dart_cache.get_preliminary_quarter(corp_code, year, quarter)
    if cached:  # 빈 dict는 dart_cache가 이미 무시 처리
        return cached

    rcept_no, list_ok = find_preliminary_disclosure(corp_code, year, quarter)
    if not list_ok:
        # connection failure — cache 안 함 (재시도 보장)
        return None
    if not rcept_no:
        # 정상 응답 + 잠정실적 없음 — 정당한 negative cache
        dart_cache.put_preliminary_quarter(corp_code, year, quarter, {})
        return None
    html = _fetch_disclosure_html(rcept_no)
    if not html:
        # document.xml fetch 실패 — cache 안 함
        return None
    parsed = parse_preliminary_results(html)
    if not parsed:
        # HTML 받았지만 단위 파싱 실패 — negative cache (계속 시도해도 실패)
        dart_cache.put_preliminary_quarter(corp_code, year, quarter, {})
        return None
    period_key = f"{year}{quarter * 3:02d}"
    result = {
        "period_key": period_key,
        "revenue_eok": parsed["revenue_eok"],
        "net_income_eok": parsed["net_income_eok"],
        "rcept_no": rcept_no,
        "unit_detected": parsed["unit_detected"],
    }
    dart_cache.put_preliminary_quarter(corp_code, year, quarter, result)
    return result


def merge_naver_dart_quarters(
    naver_quarters: list[tuple[str, float]],
    dart_quarters: list[tuple[str, float]],
) -> list[tuple[str, float]]:
    """Naver(최근 5분기 우선) + DART(과거 분기 보강) 머지. 중복 키는 Naver 우선.

    Returns: 시간순 정렬된 EPS 리스트.
    """
    merged: dict[str, float] = {p: e for p, e in dart_quarters}
    for p, e in naver_quarters:
        merged[p] = e
    return sorted(merged.items())


def fetch_majorstock_holding(corp_code: str) -> dict[str, Any] | None:
    """DART 5%룰 대량보유 공시(majorstock)로 기관 합산 보유율 + 최근 1년 추세 계산.

    캐시: dart_cache.get_majorstock (7d TTL — 5%룰 보고 변경 시 stale 가능).
    None / 빈 결과도 캐시 (negative cache).

    Returns:
      {
        "institutional_pct": float,    # 보고자별 최종 보유율 합산
        "recent_trend": "up"|"flat"|"down",
        "reporters": int,               # 보고자 수
      }
    """
    from canslim_lib import dart_cache
    cached = dart_cache.get_majorstock(corp_code)
    if cached:  # dart_cache 가 __none__ sentinel 무시 처리
        return cached

    items = dart_get("majorstock", {"corp_code": corp_code})
    if items is None:
        # connection failure — cache 안 함 (재시도)
        return None
    if not items:
        result = {"institutional_pct": 0.0, "recent_trend": "flat", "reporters": 0}
        dart_cache.put_majorstock(corp_code, result)
        return result

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

    result = {
        "institutional_pct": institutional_pct,
        "recent_trend": trend,
        "reporters": len(by_reporter),
    }
    dart_cache.put_majorstock(corp_code, result)
    return result


def sleep(ms: int) -> None:
    time.sleep(ms / 1000)
