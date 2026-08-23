import json, sys
from pathlib import Path
sys.path.insert(0, r"C:/Users/hanul/playground/my-stock/scripts")
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR = Path(r"C:/Users/hanul/playground/my-stock/.cache/ohlcv/series")

ROOT = r"C:/Users/hanul/playground/my-stock"
D = json.load(open(ROOT + "/public/data/backtest-volatility-pilot.json", encoding="utf-8"))
EV = D["events"]

def series_for(e):
    s = ohlcv_matrix.get_series(e["code"])
    b = s["dates"].index(e["entry_date"])
    return s, b

def sim_trade(e, mode="base", trail_pct=10.0, target_pct=20.0, stop_pct=10.0,
              same_day_trail=False, gap_fill=True):
    """mode: base | trail
    반환 dict: exit_kind(target/stop/trail/open), ret_pct, days, exit_date, touched_target
    """
    s, b = series_for(e)
    o,h,l,c,dt = s["opens"], s["highs"], s["lows"], s["closes"], s["dates"]
    n = len(c)
    E = e["entry_price"]
    T = E*(1+target_pct/100); S = E*(1-stop_pct/100)
    def fill(px, i, down):
        if not gap_fill: return px
        op = o[i]
        if op is None: return px
        return min(op, px) if down else max(op, px)
    # phase 1
    k = None
    for i in range(b, n):
        hi, lo = h[i], l[i]
        hit_t = hi is not None and hi >= T
        hit_s = lo is not None and lo <= S
        if hit_t and hit_s:
            # 같은날 둘다: 보수적으로 손절 처리
            px = fill(S, i, True)
            return dict(kind="stop_amb", ret=(px/E-1)*100, days=i-b, date=dt[i], touched=False)
        if hit_s:
            px = fill(S, i, True)
            return dict(kind="stop", ret=(px/E-1)*100, days=i-b, date=dt[i], touched=False)
        if hit_t:
            k = i; break
    if k is None:
        # 미결: 마지막 종가 기준 평가 (open)
        return dict(kind="open", ret=(c[n-1]/E-1)*100, days=n-1-b, date=dt[n-1], touched=False)
    if mode == "base":
        px = fill(T, k, False)
        return dict(kind="target", ret=(px/E-1)*100, days=k-b, date=dt[k], touched=True)
    # trail mode
    peak = h[k]
    start = k if same_day_trail else k+1
    if same_day_trail:
        # 같은날 고점 대비 -10% 이탈했는지 확인
        if l[k] is not None and l[k] <= peak*(1-trail_pct/100):
            px = peak*(1-trail_pct/100)
            return dict(kind="trail", ret=(px/E-1)*100, days=k-b, date=dt[k], touched=True)
        start = k+1
    for i in range(start, n):
        tr = peak*(1-trail_pct/100)
        lo = l[i]
        if lo is not None and lo <= tr:
            px = fill(tr, i, True)
            return dict(kind="trail", ret=(px/E-1)*100, days=i-b, date=dt[i], touched=True)
        if h[i] is not None and h[i] > peak: peak = h[i]
    return dict(kind="open_after_target", ret=(c[n-1]/E-1)*100, days=n-1-b, date=dt[n-1], touched=True)

if __name__ == "__main__":
    import statistics
    rows=[]
    for e in EV:
        a = sim_trade(e,"base"); t = sim_trade(e,"trail")
        rows.append(dict(code=e["code"],name=e["name"],entry=e["entry_date"],pattern=e["pattern"],
                         base_kind=a["kind"],base_ret=a["ret"],base_days=a["days"],base_date=a["date"],
                         tr_kind=t["kind"],tr_ret=t["ret"],tr_days=t["days"],tr_date=t["date"],
                         touched=t["touched"]))
    json.dump(rows, open("rows.json","w"), ensure_ascii=False)
    from collections import Counter
    print("base kinds", Counter(r["base_kind"] for r in rows))
    print("trail kinds", Counter(r["tr_kind"] for r in rows))
    print("n", len(rows))
    def stats(rs, key):
        v=[r[key] for r in rs]
        return f"n={len(v)} mean={sum(v)/len(v):+.2f} med={statistics.median(v):+.2f} sum={sum(v):+.0f}"
    print("ALL base ", stats(rows,"base_ret"))
    print("ALL trail", stats(rows,"tr_ret"))
    tt=[r for r in rows if r["touched"]]
    print("touched", len(tt), stats(tt,"base_ret"), "|", stats(tt,"tr_ret"))
