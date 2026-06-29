"""find-vcp-history — VCP 검출기 회고·검증 (순수 부품).

기존 evaluate_vcp 를 과거 시계열에 as-of 로 반복 적용한다(새 판정 로직 없음).
정의: docs/superpowers/specs/2026-06-29-find-vcp-history-design.md
"""
from __future__ import annotations

from canslim_lib.vcp import evaluate_vcp

_SERIES_KEYS = ("dates", "closes", "highs", "lows", "volumes", "timestamps")


def replay_vcp(series: dict, scan_days: int, params: dict | None = None) -> list[dict]:
    """마지막 scan_days 거래일 각각을 기준일로 evaluate_vcp 를 재실행.

    시계열을 [:i+1] 로 잘라 넣으면 evaluate_vcp 가 그 시점 마지막 날 기준으로 판정한다.
    """
    dates = series.get("dates") or []
    n = len(dates)
    out: list[dict] = []
    start = max(0, n - scan_days)
    for i in range(start, n):
        sub = {k: (series.get(k) or [])[: i + 1] for k in _SERIES_KEYS if series.get(k) is not None}
        r = evaluate_vcp(sub, params)
        out.append({
            "date": dates[i],
            "vcp_detected": r["vcp_detected"],
            "status": r["status"],
            "pivot_price": r["pivot_price"],
            "contractions": r["contractions"],
        })
    return out


def find_breakout_events(replay: list[dict], confirm_lookback: int = 5) -> list[dict]:
    """status 가 breakout 으로 새로 전환 + 직전 confirm_lookback 내 vcp_detected=true 인 날 = 이벤트."""
    events: list[dict] = []
    for j, cur in enumerate(replay):
        if cur["status"] != "breakout":
            continue
        if j > 0 and replay[j - 1]["status"] == "breakout":
            continue  # 같은 돌파 연속 → 첫 전환만
        confirm = None
        lo = max(0, j - confirm_lookback)
        for k in range(j - 1, lo - 1, -1):
            if replay[k]["vcp_detected"]:
                confirm = replay[k]
                break
        if confirm is None:
            continue
        events.append({
            "date": cur["date"],
            "replay_idx": j,
            "confirm_date": confirm["date"],
            "pivot_price": confirm["pivot_price"],
            "contractions": confirm["contractions"],
        })
    return events


def post_breakout_outcome(series: dict, event_date: str,
                          stop_pct: float = 8.0, target_pct: float = 20.0) -> dict | None:
    """돌파일 이후 성과 계산: 수익률, 최대 수익, 최대 손실, 목표 달성 여부.

    Args:
        series: {"dates", "closes", "highs", "lows", "volumes", ...} 형식의 시계열
        event_date: 돌파 기준일 ("d0" 등)
        stop_pct: 손절가 퍼센트 (기본값 8%)
        target_pct: 수익 목표 퍼센트 (기본값 20%)

    Returns:
        {breakout_close, days_since, gain_since_pct, max_gain_pct, max_drawdown_pct, good_breakout}
        또는 event_date가 없으면 None
    """
    dates = series.get("dates") or []
    closes = series.get("closes") or []
    highs = series.get("highs") or []
    lows = series.get("lows") or []
    try:
        idx = dates.index(event_date)
    except ValueError:
        return None
    bc = closes[idx]
    if not bc:
        return None
    after_h, after_l, after_c = highs[idx + 1:], lows[idx + 1:], closes[idx + 1:]
    gain_since = (closes[-1] - bc) / bc * 100.0
    max_gain = max(((h - bc) / bc * 100.0 for h in after_h), default=0.0)
    max_dd = min(((c - bc) / bc * 100.0 for c in after_c), default=0.0)
    # good_breakout: 손절은 intrabar low, 목표는 intrabar high 기준(체결 가정).
    # 같은 바에서 둘 다 닿으면 손절 우선(보수적). max_drawdown_pct(=close 기준)와
    # 판정 기준이 달라 둘이 어긋나 보일 수 있음(의도된 차이).
    good = False
    for h, l in zip(after_h, after_l):
        if (l - bc) / bc * 100.0 <= -stop_pct:
            good = False
            break
        if (h - bc) / bc * 100.0 >= target_pct:
            good = True
            break
    return {
        "breakout_close": round(bc, 2),
        "days_since": len(dates) - 1 - idx,
        "gain_since_pct": round(gain_since, 2),
        "max_gain_pct": round(max_gain, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "good_breakout": good,
    }


def classify(events: list[dict], replay: list[dict], recent_days: int = 10) -> str:
    """돌파 후 종목 상태 분류.

    Args:
        events: find_breakout_events 결과 (각 이벤트는 {"replay_idx", ...})
        replay: replay_vcp 결과 (각 요소는 {"vcp_detected", "status", ...})
        recent_days: 최근으로 판단할 범위 (기본값 10)

    Returns:
        "no_vcp_found" - 돌파 이벤트 없음
        "recent_breakout" - 최근 돌파 (days_since <= recent_days)
        "re_basing" - 오래 전 돌파 후 vcp 재출현 중 (마지막 상태가 forming/actionable)
        "extended" - 오래 전 돌파 후 계속 상승세 (새 vcp 없음)
    """
    if not events:
        return "no_vcp_found"
    idx = events[-1]["replay_idx"]
    days_since = (len(replay) - 1) - idx
    if days_since <= recent_days:
        return "recent_breakout"
    later_vcp = any(replay[k].get("vcp_detected") for k in range(idx + 1, len(replay)))
    if later_vcp and replay[-1].get("status") in ("forming", "actionable"):
        return "re_basing"
    return "extended"
