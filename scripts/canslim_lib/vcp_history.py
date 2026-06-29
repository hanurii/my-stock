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
