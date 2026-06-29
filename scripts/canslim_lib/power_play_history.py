"""find-power-play-history — 파워 플레이 검출기 회고·검증 (순수 부품).

기존 evaluate_power_play 를 과거 시계열에 as-of 로 반복 적용한다(새 판정 로직 없음).
post_breakout_outcome 는 패턴 무관 범용 함수라 vcp_history 의 것을 재사용한다(DRY).
정의: docs/superpowers/specs/2026-06-30-find-power-play-history-design.md
"""
from __future__ import annotations

from canslim_lib.power_play import evaluate_power_play
from canslim_lib.vcp_history import post_breakout_outcome  # noqa: F401  패턴 무관 범용 — 재사용·재export

_SERIES_KEYS = ("dates", "closes", "highs", "lows", "volumes", "timestamps")


def replay_power_play(series: dict, scan_days: int, params: dict | None = None) -> list[dict]:
    """마지막 scan_days 거래일 각각을 기준일로 evaluate_power_play 를 재실행.

    시계열을 [:i+1] 로 잘라 넣으면 evaluate_power_play 가 그 시점 마지막 날 기준으로 판정한다.
    """
    dates = series.get("dates") or []
    n = len(dates)
    out: list[dict] = []
    start = max(0, n - scan_days)
    for i in range(start, n):
        sub = {k: (series.get(k) or [])[: i + 1] for k in _SERIES_KEYS if series.get(k) is not None}
        r = evaluate_power_play(sub, params)
        out.append({
            "date": dates[i],
            "pattern_detected": r["pattern_detected"],
            "status": r["status"],
            "pivot_price": r["pivot_price"],
            "flagpole_gain_pct": r["flagpole_gain_pct"],
            "flag_depth_pct": r["flag_depth_pct"],
        })
    return out


def find_breakout_events(replay: list[dict], confirm_lookback: int = 5) -> list[dict]:
    """status 가 breakout 으로 새로 전환 + 직전 confirm_lookback 내 pattern_detected=true 인 날 = 이벤트."""
    events: list[dict] = []
    for j, cur in enumerate(replay):
        if cur["status"] != "breakout":
            continue
        if j > 0 and replay[j - 1]["status"] == "breakout":
            continue  # 같은 돌파 연속 → 첫 전환만
        confirm = None
        lo = max(0, j - confirm_lookback)
        for k in range(j - 1, lo - 1, -1):
            if replay[k]["pattern_detected"]:
                confirm = replay[k]
                break
        if confirm is None:
            continue
        events.append({
            "date": cur["date"],
            "replay_idx": j,
            "confirm_date": confirm["date"],
            "pivot_price": confirm["pivot_price"],
            "flagpole_gain_pct": confirm["flagpole_gain_pct"],
            "flag_depth_pct": confirm["flag_depth_pct"],
        })
    return events


def classify(events: list[dict], replay: list[dict], recent_days: int = 10) -> str:
    """돌파 후 종목 상태 분류.

    Args:
        events: find_breakout_events 결과 (각 이벤트는 {"replay_idx", ...})
        replay: replay_power_play 결과 (각 요소는 {"pattern_detected", "status", ...})
        recent_days: 최근으로 판단할 범위 (기본값 10)

    Returns:
        "no_pattern_found" - 돌파 이벤트 없음
        "recent_breakout"  - 최근 돌파 (days_since <= recent_days)
        "re_basing"        - 오래 전 돌파 후 pattern 재출현 중 (마지막 상태가 forming/actionable)
        "extended"         - 오래 전 돌파 후 계속 상승세 (새 pattern 없음)
    """
    if not events:
        return "no_pattern_found"
    idx = events[-1]["replay_idx"]
    days_since = (len(replay) - 1) - idx
    if days_since <= recent_days:
        return "recent_breakout"
    later_pattern = any(replay[k].get("pattern_detected") for k in range(idx + 1, len(replay)))
    if later_pattern and replay[-1].get("status") in ("forming", "actionable"):
        return "re_basing"
    return "extended"
