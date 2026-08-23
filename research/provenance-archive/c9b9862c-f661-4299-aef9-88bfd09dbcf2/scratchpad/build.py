import json,sys
from pathlib import Path
MAIN=Path(r"C:\Users\hanul\playground\my-stock")
sys.path.insert(0,str(MAIN/"scripts"))
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR = MAIN/".cache"/"ohlcv"/"series"
d=json.load(open(MAIN/"public/data/backtest-volatility-pilot.json",encoding="utf-8"))
ev=d["events"]
out=[]
miss=0
cache={}
for e in ev:
    c=e["code"]
    if c not in cache:
        cache[c]=ohlcv_matrix.get_series(c)
    s=cache[c]
    if not s or e["entry_date"] not in s["dates"]:
        miss+=1; continue
    i=s["dates"].index(e["entry_date"])
    cl=s["closes"][i]; op=(s.get("opens") or [None]*len(s["dates"]))[i]
    hi=s["highs"][i]; lo=s["lows"][i]
    if cl is None: miss+=1; continue
    epx=e["entry_price"]
    r=dict(e)
    r["d1_close"]=cl
    r["d1_ret"]=(cl/epx-1)*100
    r["d1_high"]=(hi/epx-1)*100 if hi else None
    r["d1_low"]=(lo/epx-1)*100 if lo else None
    r["d1_open"]=(op/epx-1)*100 if op else None
    # resolve close (for forward calc)
    rd=e.get("resolve_date")
    r["resolve_idx"]=s["dates"].index(rd) if rd in s["dates"] else None
    out.append(r)
print("miss",miss,"kept",len(out))
json.dump(out,open(MAIN.parent/"x.json","w"),ensure_ascii=False) if False else None
SP=Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
json.dump(out,open(SP/"ev1.json","w",encoding="utf-8"),ensure_ascii=False)
