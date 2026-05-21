"""KOSPI/KOSDAQ 유니버스 + 시총 일괄 수집 (FDR 기반).

파일명은 `pykrx_universe.py` 그대로 유지 — 후속 통합 코드 호환용.
내부 구현은 `FinanceDataReader` 사용 (pykrx 는 최근 KRX 인증을 요구해 동작 불가).
한 번의 호출로 종목명·시장·시총까지 같이 받는다.
"""

from __future__ import annotations

import re

import FinanceDataReader as fdr

EXCLUDE_PATTERN = re.compile(r"스팩|SPAC|리츠|REIT|ETF|ETN|인프라|우B$|우C$|\d우$")

# FDR MarketId → 우리 표준 시장 라벨
_MARKET_ID_MAP = {"STK": "KOSPI", "KSQ": "KOSDAQ"}


def _fetch_one_market(market: str) -> list[dict]:
    """단일 시장(KOSPI 또는 KOSDAQ) 종목 + 시총 추출."""
    df = fdr.StockListing(market)
    if df is None or df.empty:
        return []

    rows: list[dict] = []
    for _, r in df.iterrows():
        code = r.get("Code")
        name = r.get("Name")
        marcap = r.get("Marcap")
        market_id = r.get("MarketId")

        # Code 검증: 6자리 문자열
        if not isinstance(code, str) or len(code) != 6:
            continue
        if not name or not isinstance(name, str):
            continue
        # 제외 패턴 (스팩/리츠/ETF/ETN/인프라/우선주)
        if EXCLUDE_PATTERN.search(name):
            continue
        # 시총 0/NaN 스킵 (거래정지/상장정지)
        try:
            cap_won = float(marcap)
        except (TypeError, ValueError):
            continue
        if cap_won != cap_won or cap_won <= 0:  # NaN check
            continue

        rows.append({
            "code": code,
            "name": name,
            "market": _MARKET_ID_MAP.get(market_id, market),
            "market_cap_eok": int(cap_won // 10**8),
        })
    return rows


def fetch_universe_with_cap(market: str = "all") -> list[dict]:
    """KOSPI + KOSDAQ 유니버스를 시총(억원)과 함께 반환.

    Args:
        market: "all" | "KOSPI" | "KOSDAQ"

    Returns:
        시총 내림차순 정렬된 [{"code", "name", "market", "market_cap_eok"}, ...]
    """
    market = market.upper()
    if market == "ALL":
        rows = _fetch_one_market("KOSPI") + _fetch_one_market("KOSDAQ")
    elif market in ("KOSPI", "KOSDAQ"):
        rows = _fetch_one_market(market)
    else:
        raise ValueError(f"market must be 'all'|'KOSPI'|'KOSDAQ', got {market!r}")

    rows.sort(key=lambda r: r["market_cap_eok"], reverse=True)
    return rows
