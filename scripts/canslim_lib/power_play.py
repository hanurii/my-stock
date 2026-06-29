"""미너비니 파워 플레이(High Tight Flag) 평가 부품 (순수 함수).

개념(깃대·깃발·조용한 출발·거래량 마름)=마크 미너비니. 구체 수치·계산규칙=이
프로젝트의 공학적 번역(원전 아님).
정의·근거: docs/superpowers/specs/2026-06-29-find-power-play-design.md
"""
from __future__ import annotations

DEFAULT_PARAMS: dict = {
    "lookback_days": 120,
    "min_total_days": 20,
    "min_flagpole_gain": 100.0,
    "max_flagpole_days": 40,
    "pole_vol_mult": 1.5,
    "quiet_window": 20,
    "max_pre_pole_gain": 30.0,
    "min_flag_days": 8,
    "max_flag_days": 30,
    "max_flag_depth": 20.0,
    "breakout_vol_mult": 1.4,
    "near_pivot_pct": 5.0,
}


def find_flagpole(highs: list[float], lows: list[float], max_flagpole_days: int) -> dict:
    """구간 최고 고가(깃발 고점)와 그 직전 max_flagpole_days 경계 안의 최저
    저점(깃대 시작)을 찾아 상승률·기간을 계산한다."""
    n = len(highs)
    flag_high_idx = max(range(n), key=lambda i: highs[i])
    flag_high = highs[flag_high_idx]
    window_start = max(0, flag_high_idx - max_flagpole_days)
    # 깃발 고점 바는 제외하고 그 이전 구간에서 최저 저점 탐색
    search_end = flag_high_idx  # exclusive 상한
    if search_end <= window_start:
        # 고점이 구간 시작 → 깃대 형성 불가
        return {
            "flag_high_idx": flag_high_idx, "flag_high": flag_high,
            "pole_start_idx": flag_high_idx, "pole_start_low": flag_high,
            "flagpole_gain_pct": 0.0, "flagpole_days": 0,
        }
    pole_start_idx = min(range(window_start, search_end), key=lambda i: lows[i])
    pole_start_low = lows[pole_start_idx]
    gain = (flag_high - pole_start_low) / pole_start_low * 100.0 if pole_start_low > 0 else 0.0
    return {
        "flag_high_idx": flag_high_idx, "flag_high": flag_high,
        "pole_start_idx": pole_start_idx, "pole_start_low": pole_start_low,
        "flagpole_gain_pct": gain, "flagpole_days": flag_high_idx - pole_start_idx,
    }
