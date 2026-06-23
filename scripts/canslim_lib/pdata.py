"""공공데이터포털 (apis.data.go.kr) — 금융위원회 KRX 시세/상장종목정보 batch fetch.

이 모듈은 m.stock.naver.com fetch_integration 를 대체하기 위한 source.
종목당 fetch 안 함 — basDt 기준 전체 종목 1회 호출.

엔드포인트:
  - GetStockSecuritiesInfoService/getStockPriceInfo : 시세·시총·거래량
  - GetKrxListedInfoService/getItemInfo : crno·법인명 메타

T-1 ~ T-2 lag (장 마감 후 야간/익일 업로드). 일일 운영(새벽)엔 충분.

캐시: 일자별 파일 (immutable basDt — 영구).
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / ".cache" / "pdata"

PDATA_BASE = "https://apis.data.go.kr/1160100/service"
ENDPOINT_PRICE = f"{PDATA_BASE}/GetStockSecuritiesInfoService/getStockPriceInfo"
ENDPOINT_ITEM = f"{PDATA_BASE}/GetKrxListedInfoService/getItemInfo"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _api_key() -> str | None:
    return os.environ.get("DATA_GO_KR_KEY")


def _ensure_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _fetch_json(url: str, timeout: int = 30) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return None


def _normalize_num(s: Any) -> float | None:
    """문자열/숫자 정규화. 빈 값은 None."""
    if s is None or s == "":
        return None
    try:
        return float(str(s).replace(",", ""))
    except (ValueError, TypeError):
        return None


def _coerce_price_row(row: dict) -> dict:
    """getStockPriceInfo 응답 1 row → 숫자 타입 정규화.

    응답 raw 필드는 전부 문자열. 숫자 필드 변환 + market_cap_eok 등 파생 계산.
    """
    out = {
        "srtnCd": row.get("srtnCd"),                # 단축코드 (005930)
        "isinCd": row.get("isinCd"),                # ISIN (KR7005930003)
        "itmsNm": row.get("itmsNm"),                # 종목명
        "mrktCtg": row.get("mrktCtg"),              # KOSPI / KOSDAQ / KONEX
        "basDt": row.get("basDt"),                  # 기준일자
        "clpr": _normalize_num(row.get("clpr")),    # 종가
        "vs": _normalize_num(row.get("vs")),        # 전일 대비
        "fltRt": _normalize_num(row.get("fltRt")),  # 등락률 (%)
        "mkp": _normalize_num(row.get("mkp")),      # 시가
        "hipr": _normalize_num(row.get("hipr")),    # 고가
        "lopr": _normalize_num(row.get("lopr")),    # 저가
        "trqu": _normalize_num(row.get("trqu")),    # 거래량 (주)
        "trPrc": _normalize_num(row.get("trPrc")),  # 거래대금 (원)
    }
    shares = _normalize_num(row.get("lstgStCnt"))
    mcap = _normalize_num(row.get("mrktTotAmt"))
    out["lstgStCnt"] = shares                       # 상장주식수
    out["mrktTotAmt"] = mcap                        # 시가총액 (원)
    # 파생 — 우리 코드 호환용
    out["market_cap_eok"] = (mcap / 1e8) if mcap else None  # 시총 (억원)
    out["trPrc_eok"] = (out["trPrc"] / 1e8) if out["trPrc"] else None  # 거래대금 (억원)
    return out


def _coerce_item_row(row: dict) -> dict:
    """getItemInfo 응답 1 row → 메타 dict.

    srtnCd 는 "A005930" 형태로 prefix A 가 붙음 → 6자리만 추출.
    """
    raw_srtn = (row.get("srtnCd") or "").strip()
    code = raw_srtn[1:] if raw_srtn.startswith("A") and len(raw_srtn) == 7 else raw_srtn
    return {
        "srtnCd": code,                       # 6자리 종목코드 (A 제거)
        "isinCd": row.get("isinCd"),
        "mrktCtg": row.get("mrktCtg"),
        "itmsNm": row.get("itmsNm"),
        "crno": row.get("crno"),              # 법인등록번호 (DART jurir_no)
        "corpNm": row.get("corpNm"),          # 법인명 (예: "삼성전자(주)")
    }


def _latest_available_basDt() -> str | None:
    """오늘부터 거꾸로 시도해 첫 데이터 보유 일자 (최근 영업일) 반환."""
    key = _api_key()
    if not key:
        return None
    today = datetime.now()
    for back in range(0, 10):
        bd = (today - timedelta(days=back)).strftime("%Y%m%d")
        url = ENDPOINT_PRICE + "?" + urllib.parse.urlencode({
            "serviceKey": key, "resultType": "json", "numOfRows": "1", "pageNo": "1",
            "basDt": bd,
        })
        data = _fetch_json(url, timeout=15)
        if not data:
            continue
        total = data.get("response", {}).get("body", {}).get("totalCount", 0)
        if total and int(total) > 0:
            return bd
    return None


# ── 시세 batch ───────────────────────────────────────────────

def fetch_pdata_price_info(basDt: str | None = None) -> dict[str, dict]:
    """basDt 일자의 전체 한국 시장 시세 정보. dict[srtnCd → row dict].

    basDt=None 이면 _latest_available_basDt() 자동 탐색.
    캐시: 일자별 영구 (basDt 데이터 immutable).
    """
    key = _api_key()
    if not key:
        return {}

    if basDt is None:
        basDt = _latest_available_basDt()
        if basDt is None:
            return {}

    _ensure_dir()
    cache_path = CACHE_DIR / f"price_{basDt}.json"
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    url = ENDPOINT_PRICE + "?" + urllib.parse.urlencode({
        "serviceKey": key, "resultType": "json",
        "numOfRows": "20000", "pageNo": "1", "basDt": basDt,
    })
    data = _fetch_json(url, timeout=60)
    if not data:
        return {}
    items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    if not isinstance(items, list):
        items = [items] if items else []

    out: dict[str, dict] = {}
    for raw in items:
        row = _coerce_price_row(raw)
        code = row.get("srtnCd")
        if not code:
            continue
        # 한국 종목만 (외국 종목 KOSDAQ 상장은 srtnCd=A900xxx 형태로 나오는데 mrktCtg 는 KOSDAQ)
        # → mrktCtg 기준으로 필터 안 함 (외인+한국 다 포함). 호출자가 자기 universe 로 필터.
        out[code] = row

    # 빈 결과는 캐시하지 않음 — 미공개 영업일(포털 업로드 지연)을 빈 캐시로 굳히면
    # 나중에 데이터가 올라와도 빈 캐시가 반환돼 갱신이 조용히 깨짐.
    if out:
        cache_path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


# ── 메타 batch ───────────────────────────────────────────────

def fetch_pdata_item_info(basDt: str | None = None) -> dict[str, dict]:
    """basDt 일자의 전체 한국 시장 상장종목 메타. dict[srtnCd → row dict].

    crno (법인등록번호) 포함 — DART corp_code 매핑 보강에 사용.
    """
    key = _api_key()
    if not key:
        return {}

    if basDt is None:
        basDt = _latest_available_basDt()
        if basDt is None:
            return {}

    _ensure_dir()
    cache_path = CACHE_DIR / f"meta_{basDt}.json"
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    url = ENDPOINT_ITEM + "?" + urllib.parse.urlencode({
        "serviceKey": key, "resultType": "json",
        "numOfRows": "20000", "pageNo": "1", "basDt": basDt,
    })
    data = _fetch_json(url, timeout=60)
    if not data:
        return {}
    items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
    if not isinstance(items, list):
        items = [items] if items else []

    out: dict[str, dict] = {}
    for raw in items:
        row = _coerce_item_row(raw)
        code = row.get("srtnCd")
        if not code:
            continue
        out[code] = row

    # 빈 결과는 캐시하지 않음 (미공개 영업일 빈 캐시 굳힘 방지 — price 쪽과 동일)
    if out:
        cache_path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def clear_cache() -> int:
    """모든 pdata 캐시 삭제."""
    if not CACHE_DIR.exists():
        return 0
    n = 0
    for f in CACHE_DIR.glob("*.json"):
        try:
            f.unlink()
            n += 1
        except OSError:
            pass
    return n


def stats() -> dict[str, int]:
    """캐시 파일 수."""
    if not CACHE_DIR.exists():
        return {"price": 0, "meta": 0}
    return {
        "price": len(list(CACHE_DIR.glob("price_*.json"))),
        "meta": len(list(CACHE_DIR.glob("meta_*.json"))),
    }
