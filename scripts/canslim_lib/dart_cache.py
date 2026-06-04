"""DART API 응답 영구/장기 캐시 — 풀스캔 재호출 비용 절감.

캐시 대상:
  - 분기 EPS / 매출 (`fnlttSinglAcntAll` 분기보고서) — 확정 데이터는 immutable
  - 잠정실적 — 재정정 외엔 변하지 않음
  - 5%룰 majorstock — 변동 잦으나 일 단위론 거의 일정

TTL 정책:
  - 과거 연도 (year < current_year): 영구 (immutable)
  - 현재 연도 (year == current_year): 1일 (잠정→확정·신규 분기 가능)
  - 잠정실적: 영구 (rcept_no 단위 immutable)
  - majorstock: 7일 (5%룰 보고 변경 시 캐시 stale 가능)

각 캐시는 wrapper로 감싸 호출자는 같은 인터페이스 유지.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CACHE_ROOT = ROOT / ".cache"
DIR_QUARTER = CACHE_ROOT / "dart_quarter"
DIR_PRELIMINARY = CACHE_ROOT / "dart_preliminary"
DIR_MAJORSTOCK = CACHE_ROOT / "dart_majorstock"


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _is_fresh(path: Path, ttl_hours: float | None) -> bool:
    """TTL 검증. ttl_hours=None 이면 영구 (존재하면 fresh)."""
    if not path.exists():
        return False
    if ttl_hours is None:
        return True
    age = time.time() - path.stat().st_mtime
    return age < ttl_hours * 3600


def _read(path: Path) -> Any | None:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _write(path: Path, data: Any) -> None:
    try:
        _ensure_dir(path.parent)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, default=str)
    except OSError:
        pass


# ── 분기 EPS / 매출 ──────────────────────────────────────────

def _quarter_path(corp_code: str, year: int, kind: str) -> Path:
    return DIR_QUARTER / f"{corp_code}_{year}_{kind}.json"


def _quarter_ttl_hours(year: int) -> float | None:
    """과거 연도 = 영구, 현재 연도 = 24h."""
    if year < datetime.now().year:
        return None
    return 24.0


def get_quarter_eps(corp_code: str, year: int) -> list[tuple[str, float]] | None:
    """빈 [] 캐시는 무시 (cache miss) — connection failure 자동 회피."""
    p = _quarter_path(corp_code, year, "eps")
    if _is_fresh(p, _quarter_ttl_hours(year)):
        data = _read(p)
        if data:  # 빈 list 무시
            return [tuple(row) for row in data]
    return None


def put_quarter_eps(corp_code: str, year: int, data: list[tuple[str, float]] | None) -> None:
    """data=None 은 캐시 안 함 (재시도 보장). 빈 [] 도 캐시 안 함 (잘못된 negative 가능)."""
    if not data:
        return
    _write(_quarter_path(corp_code, year, "eps"), data)


def get_quarter_sales(corp_code: str, year: int) -> list[tuple[str, float]] | None:
    """빈 [] 캐시는 무시 (cache miss) — connection failure 자동 회피."""
    p = _quarter_path(corp_code, year, "sales")
    if _is_fresh(p, _quarter_ttl_hours(year)):
        data = _read(p)
        if data:
            return [tuple(row) for row in data]
    return None


def put_quarter_sales(corp_code: str, year: int, data: list[tuple[str, float]] | None) -> None:
    """data=None 또는 빈 [] 은 캐시 안 함."""
    if not data:
        return
    _write(_quarter_path(corp_code, year, "sales"), data)


def get_quarter_ni(corp_code: str, year: int) -> list[tuple[str, float]] | None:
    """분기 당기순이익. EPS·매출과 동일 TTL 정책."""
    p = _quarter_path(corp_code, year, "ni")
    if _is_fresh(p, _quarter_ttl_hours(year)):
        data = _read(p)
        if data:
            return [tuple(row) for row in data]
    return None


def put_quarter_ni(corp_code: str, year: int, data: list[tuple[str, float]] | None) -> None:
    """data=None 또는 빈 [] 은 캐시 안 함."""
    if not data:
        return
    _write(_quarter_path(corp_code, year, "ni"), data)


# ── 연간 재무 종합 (EPS·NI·자본·매출·ROE) ─────────────────────

def _annual_path(corp_code: str, year: int) -> Path:
    return DIR_QUARTER / f"{corp_code}_{year}_annual.json"


def get_annual_financials(corp_code: str, year: int) -> dict | None:
    """연간 재무 종합 dict (eps, ni, equity, equity_prior, roe_avg, sales, fs_div).

    빈 {} 캐시는 무시 (cache miss 처리) — 과거 connection failure로 잘못 저장된
    negative cache 자동 회피. 정당한 negative case도 재시도 가능 (비용 작음).
    """
    p = _annual_path(corp_code, year)
    if _is_fresh(p, _quarter_ttl_hours(year)):
        data = _read(p)
        if data:  # 빈 dict {} 도 falsy — 무시
            return data
    return None


def put_annual_financials(corp_code: str, year: int, data: dict | None) -> None:
    """data=None 은 캐시하지 않음 (connection failure 가능 — 재시도 보장).
    data=dict (빈 dict 포함) 만 캐시.
    """
    if data is None:
        return
    _write(_annual_path(corp_code, year), data)


# ── 잠정실적 ─────────────────────────────────────────────────
# 같은 corp_code · year · quarter 라도 재정정 공시 시 rcept_no 가 바뀜.
# fetch_preliminary_quarter 는 매번 list.json 으로 최신 rcept_no 찾는 호출이 필수 (캐시 안 함).
# parse_preliminary_results(rcept_no) 만 캐시 — rcept_no 단위 immutable.

def _preliminary_path(corp_code: str, year: int, quarter: int) -> Path:
    return DIR_PRELIMINARY / f"{corp_code}_{year}_{quarter}.json"


def get_preliminary_quarter(corp_code: str, year: int, quarter: int) -> dict | None:
    """과거 분기는 영구 캐시, 현재 진행 분기는 6h TTL (재정정 가능성).

    빈 {} 캐시는 무시 (cache miss) — 과거 connection failure 자동 회피.
    """
    p = _preliminary_path(corp_code, year, quarter)
    now = datetime.now()
    is_current = (year == now.year and quarter == (now.month - 1) // 3 + 1)
    ttl = 6.0 if is_current else None
    if _is_fresh(p, ttl):
        data = _read(p)
        if data:  # 빈 dict 무시
            return data
    return None


def put_preliminary_quarter(corp_code: str, year: int, quarter: int, data: dict | None) -> None:
    """data=None 은 캐시 안 함 (connection failure 가능). dict 만 캐시.
    빈 dict {} = "조회 성공 + 잠정실적 미공시" (정당한 negative).
    """
    if data is None:
        return
    _write(_preliminary_path(corp_code, year, quarter), data)


# ── 5%룰 majorstock ──────────────────────────────────────────

def _majorstock_path(corp_code: str) -> Path:
    return DIR_MAJORSTOCK / f"{corp_code}.json"


def get_majorstock(corp_code: str) -> dict | None:
    """5%룰은 변동 잦음 (보고자 신규 진입/이탈). 7일 TTL.

    {"__none__": True} (호출 실패 sentinel) 캐시는 무시 — connection failure 자동 회피.
    """
    p = _majorstock_path(corp_code)
    if _is_fresh(p, 24.0 * 7):
        data = _read(p)
        if data and not data.get("__none__"):
            return data
    return None


def put_majorstock(corp_code: str, data: dict | None) -> None:
    """data=None 은 캐시 안 함 (재시도 보장)."""
    if data is None:
        return
    _write(_majorstock_path(corp_code), data)


# ── 관리 ─────────────────────────────────────────────────────

def clear_quarter(corp_code: str | None = None, year: int | None = None) -> int:
    """분기 캐시 부분/전체 삭제. corp_code+year 조합 또는 전체."""
    if not DIR_QUARTER.exists():
        return 0
    n = 0
    for f in DIR_QUARTER.glob("*.json"):
        if corp_code and not f.stem.startswith(corp_code + "_"):
            continue
        if year and f"_{year}_" not in f.stem:
            continue
        try:
            f.unlink()
            n += 1
        except OSError:
            pass
    return n


def clear_all() -> dict[str, int]:
    """모든 DART 캐시 삭제."""
    out = {}
    for label, d in [("quarter", DIR_QUARTER), ("preliminary", DIR_PRELIMINARY), ("majorstock", DIR_MAJORSTOCK)]:
        n = 0
        if d.exists():
            for f in d.glob("*.json"):
                try:
                    f.unlink()
                    n += 1
                except OSError:
                    pass
        out[label] = n
    return out


def stats() -> dict[str, int]:
    """캐시 종류별 파일 수."""
    return {
        "quarter": len(list(DIR_QUARTER.glob("*.json"))) if DIR_QUARTER.exists() else 0,
        "preliminary": len(list(DIR_PRELIMINARY.glob("*.json"))) if DIR_PRELIMINARY.exists() else 0,
        "majorstock": len(list(DIR_MAJORSTOCK.glob("*.json"))) if DIR_MAJORSTOCK.exists() else 0,
    }
