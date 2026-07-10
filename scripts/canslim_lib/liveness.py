"""거래정지·상폐 종목 걸러내기 (유니버스 정화).

스크리너 입구에서 "지금 실제로 거래되는 종목"만 남기기 위한 공용 헬퍼.
두 가지를 함께 본다:

1. **자동 감지** — 최근 N 거래일 연속 거래량이 0 이면 거래정지로 본다.
   거래가 멈춘 종목은 데이터 소스가 마지막 체결가를 매일 복사하고 거래량만
   0 으로 찍는다(가격은 얼어붙고 거래량 0). 활성 종목은 KOSPI/KOSDAQ 본장에서
   N일 연속 거래량 0 이 사실상 나오지 않으므로 오탐 위험이 없다.
2. **수동 제외 목록** — `public/data/excluded-codes.json` 에 사용자가 직접 적은
   코드(예: 상폐 예정 통보를 받았지만 아직 거래량이 있는 종목처럼 자동 감지가
   못 잡는 경우)를 항상 제외한다.

`sepa-trend-candidates.json` 유니버스 단계 한 곳에서 걸러내면, 이 파일을 읽는
VCP·3C·파워플레이(트렌드/전수) 산출물 전부에서 함께 사라진다.
"""

from __future__ import annotations

import json
from bisect import bisect_right
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXCLUDED_CODES_PATH = ROOT / "public" / "data" / "excluded-codes.json"

# 최근 이만큼의 거래일이 모두 거래량 0 이면 거래정지로 판정.
HALT_ZERO_VOL_DAYS = 5


def load_excluded_codes(path: Path | None = None) -> set[str]:
    """수동 제외 코드 집합. 파일이 없거나 깨지면 빈 집합(비차단)."""
    p = path or EXCLUDED_CODES_PATH
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return set()
    codes = data.get("codes", []) if isinstance(data, dict) else data
    out: set[str] = set()
    for c in codes or []:
        # 문자열 코드 또는 {"code": ...} 객체 둘 다 허용
        raw = c.get("code") if isinstance(c, dict) else c
        if raw:
            out.add(str(raw).zfill(6))
    return out


def is_halted(series: dict | None, asof: str | None = None,
              days: int = HALT_ZERO_VOL_DAYS) -> bool:
    """시계열이 거래정지 상태인가 = 최근 `days` 거래일 거래량이 모두 0.

    series: get_series 반환 형태({"dates":[...], "volumes":[...]}).
    asof: 주어지면 그 날짜까지로 잘라(룩어헤드 방지) 판정 — 백테스트용.
    데이터가 `days` 미만이면 판정 불가로 보고 정지 아님(False) 처리.
    """
    if not series:
        return False
    vols = series.get("volumes") or []
    dates = series.get("dates") or []
    if asof and dates:
        idx = bisect_right(dates, asof)
        vols = vols[:idx]
    if len(vols) < days:
        return False
    return all((v or 0) == 0 for v in vols[-days:])


def filter_live_universe(universe: list[dict], get_series,
                         asof: str | None = None,
                         days: int = HALT_ZERO_VOL_DAYS,
                         excluded: set[str] | None = None
                         ) -> tuple[list[dict], list[dict]]:
    """유니버스에서 거래정지·수동제외 종목을 걸러낸다.

    Args:
        universe: [{"code", "name", ...}, ...]
        get_series: code -> series dict | None (예: ohlcv_matrix.get_series)
        asof: 백테스트 기준일(None 이면 최신).
        days: 연속 거래량 0 판정 일수.
        excluded: 수동 제외 코드 집합(None 이면 파일에서 로드).

    Returns:
        (kept, dropped). dropped 원소에는 "reason"("excluded"|"halted") 부가.
    """
    if excluded is None:
        excluded = load_excluded_codes()
    kept: list[dict] = []
    dropped: list[dict] = []
    for stock in universe:
        code = str(stock.get("code", "")).zfill(6)
        if code in excluded:
            dropped.append({**stock, "reason": "excluded"})
            continue
        if is_halted(get_series(code), asof=asof, days=days):
            dropped.append({**stock, "reason": "halted"})
            continue
        kept.append(stock)
    return kept, dropped
