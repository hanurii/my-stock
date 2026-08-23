import json, pickle, re, sys
from pathlib import Path
from collections import defaultdict
PD = Path(r"C:/Users/hanul/playground/my-stock/.cache/pdata")
EXCL = re.compile(r"스팩|SPAC|리츠|REIT|ETF|ETN|인프라|우B$|우C$|\d우$|우$|우\(전환\)|우B\(전환\)")
files = sorted(p for p in PD.glob("price_*.json") if "20211001" <= p.stem[6:] <= "20260821")
print("files", len(files), files[0].stem, files[-1].stem)
dates=[]; rec=defaultdict(dict)
for p in files:
    d=p.stem[6:]; date=f"{d[:4]}-{d[4:6]}-{d[6:]}"
    try: raw=json.loads(p.read_text(encoding="utf-8"))
    except Exception: continue
    if not raw: continue
    dates.append(date)
    for code,r in raw.items():
        if r.get("mrktCtg") not in ("KOSPI","KOSDAQ"): continue
        nm=r.get("itmsNm") or ""
        if EXCL.search(nm): continue
        cl=r.get("clpr"); 
        if not cl: continue
        rec[code][date]=(cl, r.get("mkp"), r.get("hipr"), r.get("lopr"), r.get("trqu"), r.get("trPrc_eok"), r.get("fltRt"))
print("dates",len(dates),"codes",len(rec))
pickle.dump({"dates":dates,"rec":dict(rec)}, open("oos_raw_full.pkl","wb"), protocol=4)
print("saved")
