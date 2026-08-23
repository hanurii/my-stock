# -*- coding: utf-8 -*-
"""독립 재구현: 청산 규칙별 per-trade 수익률."""
import json, sys, os
from pathlib import Path
MAIN = Path(r"C:\Users\hanul\playground\my-stock")
sys.path.insert(0, str(MAIN / "scripts"))
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR = MAIN / ".cache" / "ohlcv" / "series"
ohlcv_matrix.FOREIGN_PATH = MAIN / ".cache" / "ohlcv" / "foreign.json"

HORIZON = 60

_cache = {}
def series(code):
    if code not in _cache:
        _cache[code] = ohlcv_matrix.get_series(code)
    return _cache[code]

def load_events():
    d = json.load(open(MAIN / "public/data/backtest-volatility-pilot.json", encoding="utf-8"))
    return d["events"]

def prep(events):
    """각 이벤트에 entry idx, 앞으로 60일 경로 붙이기."""
    out = []
    for e in events:
        s = series(e["code"])
        if not s: continue
        try:
            bi = s["dates"].index(e["entry_date"])
        except ValueError:
            continue
        n = len(s["dates"])
        last = min(n - 1, bi + HORIZON)
        e2 = dict(e)
        e2["bi"] = bi
        e2["last"] = last
        e2["full_obs"] = (bi + HORIZON <= n - 1)
        e2["s"] = s
        out.append(e2)
    return out

def _exit(E, px, i, bi, dates, why):
    return {"ret": (px / E - 1) * 100, "days": i - bi, "exit_date": dates[i], "why": why}

def sim(e, mode, **kw):
    """mode 별 청산. 반환 dict(ret %, days, exit_date, why, censored)."""
    s = e["s"]; bi = e["bi"]; last = e["last"]; E = e["entry_price"]
    H, L, C, O, D = s["highs"], s["lows"], s["closes"], s["opens"], s["dates"]
    tgt = kw.get("target", 20.0); stp = kw.get("stop", 10.0)
    trail = kw.get("trail")          # 추적손절 %
    arm_at = kw.get("arm_at")        # 이 수익률 도달 후 추적 개시(None이면 처음부터)
    T = E * (1 + tgt / 100) if tgt is not None else None
    S = E * (1 - stp / 100)
    armed = (arm_at is None) and (trail is not None)
    runmax = None
    for i in range(bi, last + 1):
        hi, lo, op = H[i], L[i], O[i] if O else None
        if hi is None or lo is None: continue
        if armed and runmax is not None:
            level = runmax * (1 - trail / 100)
            level = max(level, S) if kw.get("keep_hard_stop") else level
            if lo <= level:
                px = min(op, level) if op is not None else level
                return _exit(E, px, i, bi, D, "trail")
        else:
            hit_s = lo <= S
            hit_t = (T is not None) and hi >= T
            if hit_s and hit_t:
                px = min(op, S) if op is not None else S
                return _exit(E, px, i, bi, D, "stop_both")   # 보수: 손절
            if hit_s:
                px = min(op, S) if op is not None else S
                return _exit(E, px, i, bi, D, "stop")
            if hit_t:
                if trail is None:
                    px = max(op, T) if op is not None else T
                    return _exit(E, px, i, bi, D, "target")
                armed = True
                runmax = hi
        runmax = hi if runmax is None else max(runmax, hi)
    # 지평 도달 → 종가 청산
    i = last
    return _exit(E, C[i], i, bi, D, "horizon")

MODES = {
    "a_20_10":   dict(target=20.0, stop=10.0),
    "f_trail10": dict(target=20.0, stop=10.0, trail=10.0, arm_at=20.0),
    "f_trail15": dict(target=20.0, stop=10.0, trail=15.0, arm_at=20.0),
    "f_trail20": dict(target=20.0, stop=10.0, trail=20.0, arm_at=20.0),
    "d_trail10": dict(target=None, stop=10.0, trail=10.0),
    "d_trail15": dict(target=None, stop=10.0, trail=15.0),
    "d_trail20": dict(target=None, stop=10.0, trail=20.0),
}
