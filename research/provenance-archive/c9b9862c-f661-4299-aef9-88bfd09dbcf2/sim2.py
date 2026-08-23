import json, sys
from pathlib import Path
sys.path.insert(0, r"C:/Users/hanul/playground/my-stock/scripts")
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR = Path(r"C:/Users/hanul/playground/my-stock/.cache/ohlcv/series")
ROOT = r"C:/Users/hanul/playground/my-stock"
D = json.load(open(ROOT + "/public/data/backtest-volatility-pilot.json", encoding="utf-8"))
EV = D["events"]

def sim(e, mode, target=20.0, stop=10.0, trail=10.0, maxhold=None, gap=True, same_day_trail=False):
    s = ohlcv_matrix.get_series(e["code"]); b = s["dates"].index(e["entry_date"])
    o,h,l,c,dt = s["opens"],s["highs"],s["lows"],s["closes"],s["dates"]; n=len(c)
    E=e["entry_price"]; T=E*(1+target/100); S=E*(1-stop/100)
    lim = n-1 if maxhold is None else min(n-1, b+maxhold)
    def fill(px,i,down):
        if not gap: return px
        op=o[i]
        if op is None: return px
        return min(op,px) if down else max(op,px)
    k=None
    for i in range(b, lim+1):
        hi,lo=h[i],l[i]
        ht = hi is not None and hi>=T; hs = lo is not None and lo<=S
        if hs:  # 같은날 둘다면 보수적으로 손절
            px=fill(S,i,True); return dict(kind="stop",ret=(px/E-1)*100,days=i-b,date=dt[i],touched=False)
        if ht: k=i; break
    if k is None:
        return dict(kind="timeout",ret=(c[lim]/E-1)*100,days=lim-b,date=dt[lim],touched=False)
    if mode=="base":
        px=fill(T,k,False); return dict(kind="target",ret=(px/E-1)*100,days=k-b,date=dt[k],touched=True)
    peak=h[k]; start=k+1
    if same_day_trail and l[k] is not None and l[k]<=peak*(1-trail/100):
        px=peak*(1-trail/100); return dict(kind="trail",ret=(px/E-1)*100,days=k-b,date=dt[k],touched=True)
    for i in range(start, lim+1):
        tr=peak*(1-trail/100); lo=l[i]
        if lo is not None and lo<=tr:
            px=fill(tr,i,True); return dict(kind="trail",ret=(px/E-1)*100,days=i-b,date=dt[i],touched=True)
        if h[i] is not None and h[i]>peak: peak=h[i]
    return dict(kind="timeout_after",ret=(c[lim]/E-1)*100,days=lim-b,date=dt[lim],touched=True)

def build(maxhold=None, **kw):
    out=[]
    for e in EV:
        a=sim(e,"base",maxhold=maxhold,**kw); t=sim(e,"trail",maxhold=maxhold,**kw)
        out.append(dict(code=e["code"],entry=e["entry_date"],pattern=e["pattern"],rs=e["rs"],atr=e["atr_pct"],
                        base_kind=a["kind"],base_ret=a["ret"],base_days=a["days"],base_date=a["date"],
                        tr_kind=t["kind"],tr_ret=t["ret"],tr_days=t["days"],tr_date=t["date"],touched=t["touched"]))
    return out
if __name__=="__main__":
    import statistics
    from collections import Counter
    for mh in (None, 60, 40, 20):
        R=build(maxhold=mh); n=len(R)
        d=[r["tr_ret"]-r["base_ret"] for r in R]
        print(f"maxhold={mh}: base {sum(r['base_ret'] for r in R)/n:+.2f}  trail {sum(r['tr_ret'] for r in R)/n:+.2f}  delta {sum(d)/n:+.3f}  | base보유 {sum(r['base_days'] for r in R)/n:.1f}일 trail {sum(r['tr_days'] for r in R)/n:.1f}일")
        json.dump(R, open(f"rows_mh{mh}.json","w"), ensure_ascii=True)
