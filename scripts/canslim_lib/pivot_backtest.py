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


def _daily_first_touch(series, b, start_idx, pivot, target_pct=10.0, stop_pct=5.0):
    """일반 보유일 선착(돌파일 특례 없음): start_idx..끝.
    both→ambiguous, high≥T→win, low≤S→loss, 끝까지 미도달→unresolved.
    결과 metadata 창은 [b, i]. simulate_pivot_trade(i>b)·resolve 재개가 공유."""
    highs, lows = series["highs"], series["lows"]
    n = len(series["closes"])
    T = pivot * (1 + target_pct / 100)
    S = pivot * (1 - stop_pct / 100)
    for i in range(start_idx, n):
        hi, lo = highs[i], lows[i]
        hit_t = hi is not None and hi >= T
        hit_s = lo is not None and lo <= S
        if hit_t and hit_s:
            return _result("ambiguous", series, b, i, pivot, "both_same_day")
        if hit_t:
            return _result("win", series, b, i, pivot, "target")
        if hit_s:
            return _result("loss", series, b, i, pivot, "stop")
    return _result("unresolved", series, b, n - 1, pivot, "open")


def simulate_pivot_trade(series, breakout_idx, pivot, target_pct=10.0, stop_pct=5.0):
    """피벗 매수 후 +target%/-stop% 선착. 돌파일 포함, 같은날 둘다/돌파일 손절만=ambiguous."""
    highs, lows = series["highs"], series["lows"]
    T = pivot * (1 + target_pct / 100)
    S = pivot * (1 - stop_pct / 100)
    b = breakout_idx
    hi, lo = highs[b], lows[b]
    hit_t = hi is not None and hi >= T
    hit_s = lo is not None and lo <= S
    if hit_t and hit_s:
        return _result("ambiguous", series, b, b, pivot, "both_same_day_breakout")
    if hit_t:
        return _result("win", series, b, b, pivot, "target")
    if hit_s:
        return _result("ambiguous", series, b, b, pivot, "stop_on_breakout_day")
    return _daily_first_touch(series, b, b + 1, pivot, target_pct, stop_pct)


def tally(events) -> dict:
    """결과별 개수 + 승률(결착·최악·최선)."""
    n = len(events)
    c = {"win": 0, "loss": 0, "ambiguous": 0, "unresolved": 0}
    for e in events:
        c[e["result"]] = c.get(e["result"], 0) + 1
    resolved = c["win"] + c["loss"]
    denom = resolved + c["ambiguous"]   # 미결 제외, 예외 포함
    wr = round(c["win"] / resolved * 100, 1) if resolved else None
    worst = round(c["win"] / denom * 100, 1) if denom else None
    best = round((c["win"] + c["ambiguous"]) / denom * 100, 1) if denom else None
    return {"n": n, **c, "win_rate_resolved": wr,
            "win_rate_worst": worst, "win_rate_best": best}


def resolve_minute_trade(minutes, daily, breakout_idx, pivot, target_pct=10.0, stop_pct=5.0):
    """돌파 당일 1분봉으로 진입(피벗 첫 도달)→선착 판정. 당일 미결이면 이튿날부터 일봉 선착.
    반환: result·resolved_by·entry_time·resolve_date·reason."""
    bdate = daily["dates"][breakout_idx]
    T = pivot * (1 + target_pct / 100)
    S = pivot * (1 - stop_pct / 100)
    if not minutes:
        return {"result": "ambiguous", "resolved_by": "minute", "reason": "no_minute_data",
                "entry_time": None, "resolve_date": bdate}
    entry = next((k for k, m in enumerate(minutes) if m["h"] >= pivot), None)
    if entry is None:
        return {"result": "ambiguous", "resolved_by": "minute", "reason": "no_entry",
                "entry_time": None, "resolve_date": bdate}
    etime = minutes[entry]["t"]
    for m in minutes[entry:]:
        hit_t = m["h"] >= T
        hit_s = m["l"] <= S
        if hit_t and hit_s:
            return {"result": "ambiguous", "resolved_by": "minute", "reason": "same_minute",
                    "entry_time": etime, "resolve_date": bdate}
        if hit_t:
            return {"result": "win", "resolved_by": "minute", "reason": "target",
                    "entry_time": etime, "resolve_date": bdate}
        if hit_s:
            return {"result": "loss", "resolved_by": "minute", "reason": "stop",
                    "entry_time": etime, "resolve_date": bdate}
    res = _daily_first_touch(daily, breakout_idx, breakout_idx + 1, pivot, target_pct, stop_pct)
    return {"result": res["result"], "resolved_by": "daily", "reason": res["exit_reason"],
            "entry_time": etime, "resolve_date": res["resolve_date"]}


def group_win_rate(events, key) -> dict:
    """key 값별 tally. key 값이 None/누락이면 '미상' 버킷."""
    groups: dict[str, list] = {}
    for e in events:
        groups.setdefault(e.get(key) or "미상", []).append(e)
    return {k: tally(v) for k, v in sorted(groups.items())}
