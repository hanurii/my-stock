"""pdata 2025-11-26 ~ 2026-08-21 패널 적재 -> pickle 캐시"""
import json, pickle, sys
from pathlib import Path
PDATA = Path(r"C:\Users\hanul\playground\my-stock\.cache\pdata")
OUT = Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad\panel.pkl")

S, E = "20251126", "20260821"
files = sorted(p for p in PDATA.glob("price_*.json") if S <= p.stem[6:] <= E)
print("files", len(files), files[0].stem, files[-1].stem)
dates = []
rows = {}   # code -> {date: rec}
meta = {}   # code -> {name, market}
for p in files:
    d = p.stem[6:]
    date = f"{d[:4]}-{d[4:6]}-{d[6:]}"
    recs = json.loads(p.read_text(encoding="utf-8"))
    dates.append(date)
    for code, r in recs.items():
        mkt = r.get("mrktCtg")
        if mkt not in ("KOSPI", "KOSDAQ"):
            continue
        meta.setdefault(code, {"name": r.get("itmsNm") or "", "market": mkt})
        rows.setdefault(code, {})[date] = (
            r.get("fltRt"), r.get("clpr"), r.get("market_cap_eok"), r.get("trqu"), r.get("trPrc_eok"))
print("dates", len(dates), dates[0], dates[-1])
print("codes", len(rows))
pickle.dump({"dates": dates, "rows": rows, "meta": meta}, open(OUT, "wb"))
print("saved", OUT)
