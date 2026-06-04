"""한국투자증권 OpenAPI 클라이언트 — NXT 통합시세 fetch.

OAuth 토큰: .cache/kis_token.json 에 access_token + expires_at 저장 (1일 캐시).
환경 변수: KIS_APP_KEY · KIS_APP_SECRET · KIS_ENV (real / vps).

키 없거나 토큰 발급 실패 시 모든 함수는 None 반환 → 호출자가 KRX 데이터로 자연 fallback.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.parse as _urlparse
import urllib.request as _urlreq
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / ".cache"
TOKEN_CACHE = CACHE_DIR / "kis_token.json"

# KIS rate limit: 초당 약 20회 (실전), 일반적으로 초당 5-10회 권장.
# 글로벌 lock 으로 호출 사이 최소 간격 보장.
_RATE_LOCK = threading.Lock()
_LAST_CALL_AT = [0.0]
_MIN_INTERVAL_SEC = 0.12  # 초당 ~8회 — 안전 마진


def _throttle() -> None:
    with _RATE_LOCK:
        now = time.time()
        wait = (_LAST_CALL_AT[0] + _MIN_INTERVAL_SEC) - now
        if wait > 0:
            time.sleep(wait)
        _LAST_CALL_AT[0] = time.time()

# 환경별 base URL
BASE_REAL = "https://openapi.koreainvestment.com:9443"
BASE_VPS = "https://openapivts.koreainvestment.com:29443"

_TOKEN_LEEWAY_SEC = 300  # 만료 5분 전 갱신


def _base_url() -> str:
    env = (os.environ.get("KIS_ENV") or "real").strip().lower()
    return BASE_VPS if env in ("vps", "mock", "demo") else BASE_REAL


def _have_keys() -> bool:
    return bool(os.environ.get("KIS_APP_KEY") and os.environ.get("KIS_APP_SECRET"))


def _read_token_cache() -> dict | None:
    if not TOKEN_CACHE.exists():
        return None
    try:
        return json.loads(TOKEN_CACHE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_token_cache(data: dict) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        TOKEN_CACHE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _issue_token() -> str | None:
    """POST /oauth2/tokenP — 새 토큰 발급."""
    if not _have_keys():
        return None
    body = json.dumps({
        "grant_type": "client_credentials",
        "appkey": os.environ["KIS_APP_KEY"],
        "appsecret": os.environ["KIS_APP_SECRET"],
    }).encode()
    req = _urlreq.Request(
        _base_url() + "/oauth2/tokenP",
        data=body,
        method="POST",
        headers={"content-type": "application/json"},
    )
    try:
        with _urlreq.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    token = data.get("access_token")
    if not token:
        return None
    expires_in = int(data.get("expires_in") or 86400)
    _write_token_cache({
        "access_token": token,
        "expires_at": time.time() + expires_in,
        "env": (os.environ.get("KIS_ENV") or "real"),
        "issued_at": datetime.now(timezone(timedelta(hours=9))).isoformat(),
    })
    return token


def get_access_token() -> str | None:
    """캐시된 유효 토큰 또는 새 발급. 키 없으면 None."""
    if not _have_keys():
        return None
    cached = _read_token_cache()
    if cached and (cached.get("env") == (os.environ.get("KIS_ENV") or "real")):
        expires_at = float(cached.get("expires_at") or 0)
        if expires_at > time.time() + _TOKEN_LEEWAY_SEC:
            return cached.get("access_token")
    return _issue_token()


def fetch_integrated_price(code: str, token: str | None = None,
                           market_div: str = "UN") -> dict[str, Any] | None:
    """주식 현재가 시세 — `inquire-price`, FID_COND_MRKT_DIV_CODE=UN(통합) 기본.

    Returns:
      {"current": int, "prev_close": int, "open": int, "high": int, "low": int,
       "high_52w": int, "low_52w": int, "market_div": str} | None
    """
    if token is None:
        token = get_access_token()
    if not token:
        return None

    qs = _urlparse.urlencode({
        "FID_COND_MRKT_DIV_CODE": market_div,
        "FID_INPUT_ISCD": code,
    })
    url = f"{_base_url()}/uapi/domestic-stock/v1/quotations/inquire-price?{qs}"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": os.environ.get("KIS_APP_KEY", ""),
        "appsecret": os.environ.get("KIS_APP_SECRET", ""),
        "tr_id": "FHKST01010100",
        "custtype": "P",
    }
    # rate limit 에 걸리면 백오프 후 재시도 (최대 3회)
    last_err: Exception | None = None
    for attempt in range(3):
        _throttle()
        try:
            req = _urlreq.Request(url, headers=headers)
            with _urlreq.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            break
        except _urlreq.HTTPError as e:
            last_err = e
            # 429 등 rate limit → 점진적 백오프
            if e.code in (429, 500, 502, 503):
                time.sleep(0.5 * (attempt + 1))
                continue
            return None
        except Exception as e:
            last_err = e
            time.sleep(0.3 * (attempt + 1))
            continue
    else:
        return None
    if data.get("rt_cd") != "0":
        # EGW00201 = 초당 거래건수 초과 → 재시도 한 번
        if data.get("msg_cd") == "EGW00201":
            time.sleep(1.0)
            _throttle()
            try:
                req = _urlreq.Request(url, headers=headers)
                with _urlreq.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                if data.get("rt_cd") != "0":
                    return None
            except Exception:
                return None
        else:
            return None
    out = data.get("output") or {}

    def _i(key: str) -> int | None:
        v = out.get(key)
        if v is None or v == "":
            return None
        try:
            return int(str(v).replace(",", ""))
        except (ValueError, TypeError):
            return None

    cur = _i("stck_prpr")
    if cur is None or cur <= 0:
        return None
    return {
        "current": cur,
        "prev_close": _i("stck_sdpr"),
        "open": _i("stck_oprc"),
        "high": _i("stck_hgpr"),
        "low": _i("stck_lwpr"),
        "high_52w": _i("w52_hgpr"),
        "low_52w": _i("w52_lwpr"),
        "market_div": market_div,
    }
