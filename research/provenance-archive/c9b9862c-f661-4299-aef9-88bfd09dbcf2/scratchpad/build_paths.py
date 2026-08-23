import json, sys
from pathlib import Path
MAIN = Path(r"C:\Users\hanul\playground\my-stock")
sys.path.insert(0, str(MAIN/"scripts"))
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR = MAIN/".cache"/"ohlcv"/"series"
ohlcv_matrix.FOREIGN_PATH = MAIN/".cache"/"ohlcv"/"foreign.json"

ev = json.load(open(MAIN/"public/data/backtest-volatility-pilot.json",encoding="utf-8"))["events"]
HOR = 130
out=[]
miss=0
for e in ev:
    s = ohlcv_matrix.get_series(e["code"])
    if not s: miss+=1; continue
    ds = s["dates"]
    try: bi = ds.index(e["entry_date"])
    except ValueError: miss+=1; continue
    hi_i = min(len(ds), bi+HOR+1)
    rec = dict(e)
    rec["bi"]=bi
    rec["path"]={
      "dates": ds[bi:hi_i],
      "opens": (s.get("opens") or [None]*len(ds))[bi:hi_i],
      "highs": s["highs"][bi:hi_i],
      "lows": s["lows"][bi:hi_i],
      "closes": s["closes"][bi:hi_i],
      "volumes": s["volumes"][bi:hi_i],
    }
    out.append(rec)
print("events",len(ev),"paths",len(out),"miss",miss)
json.dump(out, open(Path(sys.argv[1]),"w",encoding="utf-8"), ensure_ascii=False)
