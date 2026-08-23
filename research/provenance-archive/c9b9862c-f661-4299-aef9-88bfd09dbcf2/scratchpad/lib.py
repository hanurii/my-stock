import json, os, functools
REPO = r"C:\Users\hanul\playground\my-stock"
SCR  = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad"

@functools.lru_cache(maxsize=None)
def series(code):
    p = os.path.join(REPO, ".cache", "ohlcv", "series", f"{code}.json")
    if not os.path.exists(p): return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def load(name):
    with open(os.path.join(REPO,"public","data",name), encoding="utf-8") as f:
        return json.load(f)

def simulate(code, entry_date, entry_price, target=20.0, stop=-10.0, last_date=None):
    """entry_date 당일부터 이후 봉을 순회. 고가>=목표 -> win, 저가<=손절 -> loss, 같은날 둘다 -> ambiguous."""
    s = series(code)
    if s is None: return None
    try:
        i = s["dates"].index(entry_date)
    except ValueError:
        return None
    tp = entry_price * (1 + target/100.0)
    sl = entry_price * (1 + stop/100.0)
    mg, mdd = 0.0, 0.0
    for j in range(i, len(s["dates"])):
        if last_date and s["dates"][j] > last_date: break
        hi, lo, cl = s["highs"][j], s["lows"][j], s["closes"][j]
        if hi is None or lo is None: continue
        mg = max(mg, (hi/entry_price-1)*100)
        mdd = min(mdd, (lo/entry_price-1)*100)
        hit_t = hi >= tp
        hit_s = lo <= sl
        if hit_t and hit_s:
            return dict(result="ambiguous", days=j-i, resolve=s["dates"][j], gain=None, mg=mg, mdd=mdd)
        if hit_t:
            return dict(result="win", days=j-i, resolve=s["dates"][j], gain=target, mg=mg, mdd=mdd)
        if hit_s:
            return dict(result="loss", days=j-i, resolve=s["dates"][j], gain=stop, mg=mg, mdd=mdd)
    lastc = None
    for j in range(len(s["dates"])-1, i-1, -1):
        if last_date and s["dates"][j] > last_date: continue
        lastc = s["closes"][j]; lastd = s["dates"][j]; break
    return dict(result="unresolved", days=None, resolve=None,
                gain=(lastc/entry_price-1)*100 if lastc else None, mg=mg, mdd=mdd, last_date=lastd if lastc else None)
