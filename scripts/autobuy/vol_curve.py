"""장중 거래량 곡선 로더 — "평소 이 시각까지 하루 거래량의 몇 %가 나오는가"(C(t)).
봇이 거래량 페이스를 '동시간대 대비'로 정규화하는 데 쓴다(선형 경과시간의 시간대 오염 제거).
곡선 산출: scripts/autobuy/build_vol_curve.py · 데이터: public/data/intraday-vol-curve.json
"""
from __future__ import annotations
import json
from bisect import bisect_right
from pathlib import Path

_curve: dict[str, float] | None = None
_keys: list[str] = []


def _linear(hhmmss: str) -> float:
    """폴백: 선형 경과시간(09:00~15:30). 곡선 없을 때만."""
    s = int(hhmmss[:2]) * 3600 + int(hhmmss[2:4]) * 60 + int(hhmmss[4:6]) - 9 * 3600
    return max(1e-6, min(1.0, s / (6.5 * 3600)))


def _load(base: Path | None = None) -> dict:
    global _curve, _keys
    if _curve is not None:
        return _curve
    if base is None:
        from autobuy.config import BASE as base  # noqa: N813
    p = Path(base) / "public" / "data" / "intraday-vol-curve.json"
    try:
        _curve = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        _curve = {}
    _keys = sorted(_curve)
    return _curve


def expected_vol_frac(hhmmss: str, base: Path | None = None) -> float:
    """평소 이 시각까지 하루 거래량의 누적 비율(0<x<=1). 곡선 없으면 선형 폴백.
    hhmmss='HHMMSS'. 곡선에 정확한 시각 없으면 직전(<=t) 값 사용."""
    c = _load(base)
    if not c:
        return _linear(hhmmss)
    if hhmmss in c:
        return max(1e-6, c[hhmmss])
    i = bisect_right(_keys, hhmmss)          # <=hhmmss 중 마지막
    if i == 0:
        return max(1e-6, c[_keys[0]])
    return max(1e-6, c[_keys[i - 1]])


def _minus_min(hhmmss: str, mins: int) -> str:
    """hhmmss에서 mins분 뺀 시각(09:00 이전으로는 안 감)."""
    s = int(hhmmss[:2]) * 3600 + int(hhmmss[2:4]) * 60 + int(hhmmss[4:6]) - mins * 60
    s = max(s, 9 * 3600)
    return f"{s // 3600:02d}{(s % 3600) // 60:02d}{s % 60:02d}"


def window_vol_frac(hhmmss: str, window_min: int, base: Path | None = None) -> float:
    """평소 최근 window_min분에 나오는 하루 거래량 비율 = C(t) - C(t-window).
    스파이크 페이스 계산용: spike = 최근 W분 거래량 / (avg50 × window_vol_frac(t, W)).
    ★곡선 평탄부(연속 동일값)로 diff≈0 되는 아티팩트 방지 — 그 시각까지 '평균 분당율 × window'를
    하한으로 둔다(그 분의 정상 거래량을 모르면 평균율로 가정). 안 그러면 분모가 0에 가까워 spike가
    뻥튀기돼 여러 종목이 같은 시각에 가짜 발화(예: 10:00·11:30 평탄부)."""
    hi = expected_vol_frac(hhmmss, base)
    lo = expected_vol_frac(_minus_min(hhmmss, window_min), base)
    elapsed_min = max(1, (int(hhmmss[:2]) * 60 + int(hhmmss[2:4])) - 9 * 60)
    avg_rate_floor = hi / elapsed_min * window_min
    return max(hi - lo, avg_rate_floor, 1e-6)
