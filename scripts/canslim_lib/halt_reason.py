"""거래정지 사유 태깅 — 왜 멈췄는지를 DART 공시에서 읽어 기록한다.

`liveness.py` 는 "최근 5거래일 연속 거래량 0" 으로 거래정지를 **정확히** 잡아낸다
(2026-07-31 194종목 전수 네이버 대조 결과 오탐 0건). 다만 사유가 섞여 있어서,
주식분할로 사흘 멈춘 종목과 상장적격성 심사에 걸린 종목이 똑같아 보인다.

이 모듈은 **기록만** 한다 — 제외 규칙(행동)은 바꾸지 않는다. 제외는 매 실행
다시 계산되므로 거래가 재개되면 저절로 복귀하고, 정지 중엔 어차피 매수할 수 없다.

설계: docs/superpowers/specs/2026-07-31-halt-reason-tagging-design.md
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / ".cache" / "halt_reason"

# "주권매매거래정지              (주식분할)" → 괄호 안 사유
_HALT_NOTICE = re.compile(r"주권매매거래정지\s*\(([^)]*)\)")
_HALT_LIFTED = re.compile(r"주권매매거래정지\s*해제")

# 곧 재개되는 기업행위 — 회사가 죽어서 멈춘 게 아니다.
_TEMPORARY_KEYWORDS = (
    "주식분할", "액면분할", "주식병합", "액면병합", "전자등록", "말소",
    "감자", "합병", "분할", "주식교환", "주식이전", "변경상장", "SPAC",
)
# 존속이 걸린 사유.
_SERIOUS_KEYWORDS = (
    "상장적격성", "상장폐지", "관리종목", "감사의견", "회생", "파산",
    "횡령", "배임", "부도", "자본잠식", "불성실공시",
)


def _match_kind(text: str) -> tuple[str, str] | None:
    """사유 문구 → (kind, 매칭된 키워드). 심각을 먼저 본다."""
    for kw in _SERIOUS_KEYWORDS:
        if kw in text:
            return "serious", kw
    for kw in _TEMPORARY_KEYWORDS:
        if kw in text:
            return "temporary", kw
    return None


def classify_halt_reason(reports: list[tuple[str, str]]) -> dict:
    """DART 공시 (접수일, 제목) 목록 → {"kind", "label", "report"}.

    kind: "temporary"(곧 재개될 기업행위) | "serious"(존속 문제) | "unknown".

    **괄호 우선 원칙**: `주권매매거래정지 (사유)` 제목의 괄호 안을 1순위로 본다.
    한 종목의 공시 목록에는 상반된 사건이 섞여 있어서(정지와 해제가 같이 있음)
    제목 전체를 키워드로 훑으면 오분류한다 — CSA 코스믹이 실제 사례다.
    억지로 분류하지 않는 게 낫다: 근거가 약하면 unknown 을 돌려준다.
    """
    if not reports:
        return {"kind": "unknown", "label": None, "report": None}

    # 최신순으로 정렬(접수일 내림차순) — 가장 최근 상태가 현재 상태다.
    ordered = sorted(reports, key=lambda r: r[0] or "", reverse=True)

    for _dt, name in ordered:
        title = name or ""
        if _HALT_LIFTED.search(title):
            # 해제가 더 최근 = 이미 풀렸다. 과거 정지 사유로 못 박지 않는다.
            return {"kind": "unknown", "label": None, "report": title.strip()}
        m = _HALT_NOTICE.search(title)
        if m:
            body = m.group(1).strip()
            hit = _match_kind(body)
            kind = hit[0] if hit else "unknown"
            return {"kind": kind, "label": body, "report": title.strip()}

    # 보조 경로 — 심각 신호만. 거래소가 정지 공시 대신 "기타시장안내
    # (상장적격성 실질심사 …)" 로 알리는 경우가 있다(덱스터·진원생명과학).
    # 일시적 쪽은 보조 경로를 두지 않는다: 합병·분할 결정 공시는 정지와 무관하게
    # 흔해서, 멀쩡히 거래되는 종목까지 "곧 재개" 로 잘못 태깅된다.
    for _dt, name in ordered:
        title = name or ""
        for kw in _SERIOUS_KEYWORDS:
            if kw in title:
                return {"kind": "serious", "label": kw, "report": title.strip()}

    return {"kind": "unknown", "label": None, "report": None}


# ── DART 조회 + 캐시 ─────────────────────────────────────────

def _ensure_env() -> None:
    """`.env` 의 DART 키를 os.environ 에 올린다(이미 있으면 아무것도 안 함).

    호출자(스크리너)가 .env 를 안 읽는 경우가 있다 — pdata 가 전부 캐시 히트면
    키 없이도 스캔이 돌기 때문. 그러면 DART 만 조용히 실패해 사유가 전부
    '불명' 이 된다(2026-07-31 첫 실행에서 실제로 겪음).
    """
    import os
    if os.environ.get("DART_API_KEY"):
        return
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    try:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
    except OSError:
        pass


def _cache_path(code: str) -> Path:
    return CACHE_DIR / f"{code}.json"


def read_cache(code: str, halt_started: str | None) -> dict | None:
    """캐시된 사유. `halt_started` 가 다르면 새로운 정지로 보고 무효 처리."""
    try:
        data = json.loads(_cache_path(code).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if halt_started and data.get("halt_started") != halt_started:
        return None
    return data


def write_cache(code: str, halt_started: str | None, result: dict) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        payload = {"code": code, "halt_started": halt_started,
                   "fetched_at": int(time.time()), **result}
        _cache_path(code).write_text(json.dumps(payload, ensure_ascii=False),
                                     encoding="utf-8")
    except OSError:
        pass          # 캐시는 있으면 좋은 것 — 실패해도 진행


def fetch_halt_reason(code: str, corp_map: dict[str, str],
                      halt_started: str | None = None,
                      bgn_de: str | None = None,
                      end_de: str | None = None) -> dict:
    """정지 사유 1종목. 캐시 우선, 미스면 DART 조회.

    DART 실패·키 없음·corp_code 미매칭은 전부 비차단 — unknown 을 돌려준다.
    """
    cached = read_cache(code, halt_started)
    if cached:
        return {"kind": cached.get("kind", "unknown"),
                "label": cached.get("label"), "report": cached.get("report")}

    unknown = {"kind": "unknown", "label": None, "report": None}
    _ensure_env()
    try:
        from .fetch import resolve_corp_code
        from .management import fetch_disclosure_list
    except ImportError:
        return unknown

    corp_code, _ = resolve_corp_code(code, corp_map)
    if not corp_code:
        return unknown

    if not (bgn_de and end_de):
        from datetime import datetime, timedelta
        today = datetime.now()
        bgn_de = bgn_de or (today - timedelta(days=180)).strftime("%Y%m%d")
        end_de = end_de or today.strftime("%Y%m%d")
    try:
        items = fetch_disclosure_list(corp_code, bgn_de, end_de)
    except Exception:
        return unknown

    # 빈 응답은 캐시하지 않는다 — "공시가 없다" 와 "조회가 실패했다" 를 구분할 수
    # 없기 때문. 캐시하면 실패가 굳어 다음 실행에도 계속 '불명' 이 나온다
    # (첫 실행에서 키 미로드로 99종목이 통째로 굳었다). pdata.py 도 같은 원칙.
    if not items:
        return unknown

    reports = [(it.get("rcept_dt") or "", it.get("report_nm") or "") for it in items]
    result = classify_halt_reason(reports)
    write_cache(code, halt_started, result)
    return result


# ── 제외 목록에 사유 붙이기 ──────────────────────────────────

def _halt_span(series: dict | None) -> tuple[int, str | None, str | None]:
    """(연속 거래량0 일수, 마지막 거래일, 정지 시작일)."""
    if not series:
        return 0, None, None
    vols = series.get("volumes") or []
    dates = series.get("dates") or []
    zero = 0
    for i in range(len(vols) - 1, -1, -1):
        if (vols[i] or 0) == 0:
            zero += 1
        else:
            break
    if zero == 0 or zero >= len(dates):
        return zero, None, None
    return zero, dates[len(dates) - zero - 1], dates[len(dates) - zero]


def annotate_dropped(dropped: list[dict], get_series, corp_map: dict | None = None,
                     verbose: bool = True) -> list[dict]:
    """`liveness.filter_live_universe` 의 dropped 목록에 정지 기간·사유를 붙인다.

    corp_map 이 None 이면 DART 조회 없이 기간만 채운다(kind=unknown).
    """
    if corp_map is None:
        corp_map = {}
    out: list[dict] = []
    fetched = 0
    for stock in dropped:
        code = str(stock.get("code", "")).zfill(6)
        zero, last_trade, halt_started = _halt_span(get_series(code))
        rec = {**stock, "zero_days": zero, "last_trade": last_trade}
        if corp_map:
            cached = read_cache(code, halt_started)
            reason = (cached if cached else None) or fetch_halt_reason(
                code, corp_map, halt_started)
            if not cached:
                fetched += 1
            rec.update({"kind": reason.get("kind", "unknown"),
                        "label": reason.get("label"),
                        "report": reason.get("report")})
        else:
            rec.update({"kind": "unknown", "label": None, "report": None})
        out.append(rec)
    if verbose and corp_map:
        print(f"  🏷️  정지 사유 조회: 신규 {fetched}종목 (나머지 캐시)")
        # 새로 조회한 게 있는데 전부 unknown = DART 가 조용히 실패한 것. 첫 실행에서
        # 키 미로드로 99/99 불명이 나왔는데 눈으로만 잡혔다 — 이제 스스로 알린다.
        if fetched >= 5 and all(s.get("kind") == "unknown" for s in out):
            print("  ⚠️  조회분이 전부 '불명' — DART_API_KEY·네트워크 확인 필요")
    return out


def summarize(stocks: list[dict]) -> dict:
    """counts 집계 — reason(자동/수동) 과 kind(사유) 는 다른 축이라 따로 센다."""
    counts = {"total": len(stocks), "temporary": 0, "serious": 0,
              "unknown": 0, "manual": 0}
    for s in stocks:
        counts[s.get("kind", "unknown")] = counts.get(s.get("kind", "unknown"), 0) + 1
        if s.get("reason") == "excluded":
            counts["manual"] += 1
    return counts
