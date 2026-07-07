import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from canslim_lib.pivot_backtest import (
    simulate_pivot_trade, price_bucket, rel_volume, truncate_series,
)


def mk(highs, lows, closes=None, dates=None, volumes=None):
    n = len(highs)
    closes = closes or [(highs[i] + lows[i]) / 2 for i in range(n)]
    dates = dates or [f"2026-04-{i+1:02d}" for i in range(n)]
    return {"dates": dates, "closes": closes, "opens": list(closes),
            "highs": list(highs), "lows": list(lows),
            "volumes": volumes or [1000.0] * n}


def test_breakout_day_target_is_win():
    # 돌파일(b=0) 고가가 +10% 도달, 저가는 피벗 위 → win
    s = mk(highs=[112.0, 100.0], lows=[100.0, 99.0], dates=["2026-04-01", "2026-04-02"])
    r = simulate_pivot_trade(s, 0, 100.0)
    assert r["result"] == "win" and r["days_held"] == 0


def test_breakout_day_stop_only_is_ambiguous():
    # 돌파일 저가만 -5% 이하(고가는 +10% 미만) → ambiguous(매수 전 저점)
    s = mk(highs=[104.0, 104.0], lows=[94.0, 96.0])
    r = simulate_pivot_trade(s, 0, 100.0)
    assert r["result"] == "ambiguous" and r["exit_reason"] == "stop_on_breakout_day"


def test_breakout_day_both_is_ambiguous():
    s = mk(highs=[112.0, 104.0], lows=[94.0, 96.0])
    r = simulate_pivot_trade(s, 0, 100.0)
    assert r["result"] == "ambiguous" and "both" in r["exit_reason"]


def test_later_day_win_and_loss():
    # b=0 은 무결착, 1일차 고가만 +10% → win
    s = mk(highs=[103.0, 111.0], lows=[99.0, 101.0])
    assert simulate_pivot_trade(s, 0, 100.0)["result"] == "win"
    # 1일차 저가만 -5% → loss
    s2 = mk(highs=[103.0, 104.0], lows=[99.0, 94.0])
    r2 = simulate_pivot_trade(s2, 0, 100.0)
    assert r2["result"] == "loss" and r2["days_held"] == 1


def test_later_day_both_is_ambiguous():
    s = mk(highs=[103.0, 111.0], lows=[99.0, 94.0])
    assert simulate_pivot_trade(s, 0, 100.0)["result"] == "ambiguous"


def test_unresolved_reports_gain():
    s = mk(highs=[103.0, 104.0, 105.0], lows=[99.0, 98.0, 100.0],
           closes=[102.0, 103.0, 104.0])
    r = simulate_pivot_trade(s, 0, 100.0)
    assert r["result"] == "unresolved" and r["gain_at_resolve_pct"] == 4.0


def test_price_bucket_and_rel_volume():
    assert price_bucket(1500) == "<2천"
    assert price_bucket(12000) == "1~2만"
    assert price_bucket(80000) == "5만+"
    s = mk(highs=[1]*60, lows=[1]*60, volumes=[100.0]*50 + [200.0]*10)
    assert rel_volume(s, 50, window=50) == 2.0  # 직전 50일 평균 100, 당일 200


def test_truncate_series():
    s = mk(highs=[1, 2, 3], lows=[1, 2, 3], dates=["2026-04-01", "2026-04-02", "2026-04-03"])
    t = truncate_series(s, "2026-04-02")
    assert t["dates"] == ["2026-04-01", "2026-04-02"] and len(t["closes"]) == 2


from canslim_lib.pivot_backtest import tally, group_win_rate


def _ev(result, **kw):
    return {"result": result, **kw}


def test_tally_counts_and_resolved_win_rate():
    evs = [_ev("win"), _ev("win"), _ev("loss"), _ev("ambiguous"), _ev("unresolved")]
    t = tally(evs)
    assert t["n"] == 5 and t["win"] == 2 and t["loss"] == 1
    assert t["ambiguous"] == 1 and t["unresolved"] == 1
    # 결착 승률 = 승/(승+패) = 2/3
    assert t["win_rate_resolved"] == round(2 / 3 * 100, 1)


def test_tally_no_resolved_is_none():
    assert tally([_ev("ambiguous"), _ev("unresolved")])["win_rate_resolved"] is None


def test_group_win_rate_by_key():
    evs = [_ev("win", pattern="VCP"), _ev("loss", pattern="VCP"),
           _ev("win", pattern="3C")]
    g = group_win_rate(evs, "pattern")
    assert g["VCP"]["n"] == 2 and g["VCP"]["win_rate_resolved"] == 50.0
    assert g["3C"]["win"] == 1
