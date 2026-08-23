import json, sys
from pathlib import Path
MAIN = Path(r"C:\Users\hanul\playground\my-stock")
sys.path.insert(0, str(MAIN/"scripts"))
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR = MAIN/".cache"/"ohlcv"/"series"
ohlcv_matrix.FOREIGN_PATH = MAIN/".cache"/"ohlcv"/"foreign.json"
ev = json.load(open(MAIN/"public/data/backtest-volatility-pilot.json",encoding="utf-8"))["events"]
PRE, HOR = 150, 130
out=[]
for e in ev:
    s = ohlcv_matrix.get_series(e["code"]); ds=s["dates"]
    bi = ds.index(e["entry_date"])
    lo = max(0, bi-PRE); hi = min(len(ds), bi+HOR+1)
    rec = dict(e)
    rec["bi_local"] = bi-lo
    rec["ser"] = {k:(s.get(k) or [None]*len(ds))[lo:hi] for k in ("dates","opens","highs","lows","closes","volumes")}
    out.append(rec)
json.dump(out, open("evfull.json","w",encoding="utf-8"), ensure_ascii=False)
print("ok",len(out), "prefix min", min(r["bi_local"] for r in out))
