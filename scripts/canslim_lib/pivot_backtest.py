# scripts/canslim_lib/pivot_backtest.py
"""SEPA 피벗 백테스트 순수 로직 — 시뮬·특징·집계.
정의: docs/superpowers/specs/2026-07-07-pivot-backtest-design.md
"""
from __future__ import annotations

PRICE_BUCKETS = [(2000, "<2천"), (5000, "2~5천"), (10000, "5~1만"),
                 (20000, "1~2만"), (50000, "2~5만"), (float("inf"), "5만+")]


def price_bucket(p: float) -> str:
    for hi, label in PRICE_BUCKETS:
        if p < hi:
            return label
    return "5만+"


def rel_volume(series, idx, window=50):
    """idx일 거래량 ÷ 직전 window 거래일 평균(idx 제외). 표본/데이터 없으면 None."""
    vols = series["volumes"]
    lo = max(0, idx - window)
    sample = [v for v in vols[lo:idx] if v]
    if not sample or vols[idx] is None:
        return None
    return round(vols[idx] / (sum(sample) / len(sample)), 2)


def truncate_series(series, asof: str) -> dict:
    """dates <= asof 로 모든 배열을 자른 새 series dict."""
    dates = series["dates"]
    keep = sum(1 for d in dates if d <= asof)
    return {k: (v[:keep] if isinstance(v, list) else v) for k, v in series.items()}


def _result(result, series, b, i, pivot, reason):
    closes, highs, lows, dates = (series["closes"], series["highs"],
                                  series["lows"], series["dates"])
    seg_h = [h for h in highs[b:i + 1] if h is not None]
    seg_l = [l for l in lows[b:i + 1] if l is not None]
    max_gain = (max(seg_h) / pivot - 1) * 100 if seg_h else 0.0
    max_dd = (min(seg_l) / pivot - 1) * 100 if seg_l else 0.0
    return {
        "result": result,
        "resolve_date": dates[i],
        "days_held": i - b,
        "exit_reason": reason,
        "gain_at_resolve_pct": round((closes[i] / pivot - 1) * 100, 2),
        "max_gain_pct": round(max_gain, 2),
        "max_dd_pct": round(max_dd, 2),
    }


def simulate_pivot_trade(series, breakout_idx, pivot, target_pct=10.0, stop_pct=5.0):
    """피벗 매수 후 +target%/-stop% 선착 판정. 돌파일 포함, 같은날 둘다=ambiguous."""
    highs, lows = series["highs"], series["lows"]
    n = len(series["closes"])
    T = pivot * (1 + target_pct / 100)
    S = pivot * (1 - stop_pct / 100)
    b = breakout_idx
    for i in range(b, n):
        hi, lo = highs[i], lows[i]
        hit_t = hi is not None and hi >= T
        hit_s = lo is not None and lo <= S
        if i == b:
            if hit_t and hit_s:
                return _result("ambiguous", series, b, i, pivot, "both_same_day_breakout")
            if hit_t:
                return _result("win", series, b, i, pivot, "target")
            if hit_s:
                return _result("ambiguous", series, b, i, pivot, "stop_on_breakout_day")
        else:
            if hit_t and hit_s:
                return _result("ambiguous", series, b, i, pivot, "both_same_day")
            if hit_t:
                return _result("win", series, b, i, pivot, "target")
            if hit_s:
                return _result("loss", series, b, i, pivot, "stop")
    return _result("unresolved", series, b, n - 1, pivot, "open")


def tally(events) -> dict:
    """결과별 개수 + 결착(win/loss) 승률."""
    n = len(events)
    c = {"win": 0, "loss": 0, "ambiguous": 0, "unresolved": 0}
    for e in events:
        c[e["result"]] = c.get(e["result"], 0) + 1
    resolved = c["win"] + c["loss"]
    wr = round(c["win"] / resolved * 100, 1) if resolved else None
    return {"n": n, **c, "win_rate_resolved": wr}


def group_win_rate(events, key) -> dict:
    """key 값별 tally. key 값이 None/누락이면 '미상' 버킷."""
    groups: dict[str, list] = {}
    for e in events:
        groups.setdefault(e.get(key) or "미상", []).append(e)
    return {k: tally(v) for k, v in sorted(groups.items())}
