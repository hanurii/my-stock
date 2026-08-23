import json, sys
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from canslim_lib import ohlcv_matrix

MAIN = r"C:\Users\hanul\playground\my-stock"
D = json.load(open(MAIN + r"\public\data\backtest-volatility-pilot.json", encoding="utf-8"))
EV = D["events"]
SER = {c: ohlcv_matrix.get_series(c) for c in sorted({e["code"] for e in EV})}

def path(e, maxlen=200):
    """진입일 b 부터의 상대경로(%). 배열: o,h,l,c (진입가 대비 %)."""
    s = SER[e["code"]]; b = s["dates"].index(e["entry_date"])
    px = e["entry_price"]; n = len(s["dates"])
    end = min(n, b + maxlen + 1)
    f = lambda a: [(None if a[i] is None else (a[i]/px-1)*100) for i in range(b, end)]
    return {"dates": s["dates"][b:end], "o": f(s["opens"]), "h": f(s["highs"]),
            "l": f(s["lows"]), "c": f(s["closes"]), "b": b, "n_after": n-1-b}

PATHS = {i: path(e) for i, e in enumerate(EV)}

def simulate(i, target=20.0, stop=-10.0, cut_day=None, cut_level=None,
             gap_fill=True, amb="loss", trail=None):
    """반환 dict: ret(%), days, kind. amb='loss'|'skip'|'mid'
    gap_fill=True 면 손절은 min(시가,스탑), 목표는 max(시가,목표) 로 체결."""
    p = PATHS[i]; h, l, c, o = p["h"], p["l"], p["c"], p["o"]
    m = len(c)
    for k in range(0, m):
        hi, lo, op = h[k], l[k], o[k]
        ht = hi is not None and hi >= target
        hs = lo is not None and lo <= stop
        if k == 0:
            if ht and hs: return {"ret": (stop if amb=="loss" else (target+stop)/2), "days":0, "kind":"amb"}
            if ht:
                r = max(op, target) if (gap_fill and op is not None) else target
                return {"ret": r, "days": 0, "kind": "win"}
            if hs:
                r = min(op, stop) if (gap_fill and op is not None) else stop
                return {"ret": (r if amb=="loss" else r), "days": 0, "kind": "amb"}
        else:
            if ht and hs:
                return {"ret": (min(op,stop) if (gap_fill and op is not None and op<=stop) else stop) if amb=="loss" else (target+stop)/2,
                        "days": k, "kind": "amb"}
            if ht:
                r = max(op, target) if (gap_fill and op is not None and op>=target) else target
                return {"ret": r, "days": k, "kind": "win"}
            if hs:
                r = min(op, stop) if (gap_fill and op is not None and op<=stop) else stop
                return {"ret": r, "days": k, "kind": "loss"}
        if cut_day is not None and k == cut_day and c[k] is not None and c[k] <= cut_level:
            return {"ret": c[k], "days": k, "kind": "cut"}
    last = next((c[k] for k in range(m-1, -1, -1) if c[k] is not None), 0.0)
    return {"ret": last, "days": m-1, "kind": "open"}

def agg(rs):
    n = len(rs); tot = sum(r["ret"] for r in rs)
    wins = [r["ret"] for r in rs if r["ret"] > 0]; los = [r["ret"] for r in rs if r["ret"] <= 0]
    aw = sum(wins)/len(wins) if wins else 0; al = sum(los)/len(los) if los else 0
    return {"n": n, "per": tot/n, "tot": tot, "wr": 100*len(wins)/n,
            "avg_win": aw, "avg_loss": al, "pl": (aw/-al if al else None),
            "days": sum(r["days"] for r in rs)/n}
