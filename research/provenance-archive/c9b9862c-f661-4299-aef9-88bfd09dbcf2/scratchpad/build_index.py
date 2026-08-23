# -*- coding: utf-8 -*-
"""pdata 스냅샷으로 시점(상폐포함) 지수를 직접 재구성 — fltRt 연쇄."""
import json, re, sys
from pathlib import Path
PD = Path(r"C:\Users\hanul\playground\my-stock\.cache\pdata")
OUT = Path(sys.argv[1])
START, END = "20250401", "20260821"
EXCL = re.compile(r"스팩|SPAC|리츠|REIT|ETF|ETN|인프라|우B$|우C$|\d우$|우$|우\(전환\)|우B\(전환\)")

files = sorted(p for p in PD.glob("price_*.json") if START <= p.stem[6:] <= END)
dates, ret_all, ret_ex, ret_cw, ncount = [], [], [], [], []
for p in files:
    d = p.stem[6:]
    recs = json.loads(p.read_text(encoding="utf-8"))
    ra, rx, num, den = [], [], 0.0, 0.0
    for code, r in recs.items():
        if r.get("mrktCtg") not in ("KOSPI", "KOSDAQ"):
            continue
        f = r.get("fltRt")
        if f is None:
            continue
        try:
            f = float(f)
        except Exception:
            continue
        if abs(f) > 60:      # 액면분할·병합 기준가 변경 방어
            continue
        ra.append(f)
        nm = r.get("itmsNm") or ""
        if not EXCL.search(nm):
            rx.append(f)
        cap = r.get("market_cap_eok")
        if cap and f > -99:
            prev = cap / (1 + f / 100.0)   # 전일 시총 = 가중치
            num += prev * f
            den += prev
    if not ra:
        continue
    dates.append(f"{d[:4]}-{d[4:6]}-{d[6:]}")
    ret_all.append(sum(ra) / len(ra))
    ret_ex.append(sum(rx) / len(rx) if rx else 0.0)
    ret_cw.append(num / den if den else 0.0)
    ncount.append(len(ra))

def chain(rets):
    lv, out = 100.0, []
    for r in rets:
        lv *= (1 + r / 100.0)
        out.append(lv)
    return out

json.dump({"dates": dates, "ew_all": chain(ret_all), "ew_ex": chain(ret_ex),
           "cw": chain(ret_cw), "r_all": ret_all, "r_ex": ret_ex, "r_cw": ret_cw,
           "n": ncount}, open(OUT, "w", encoding="utf-8"))
print("days", len(dates), dates[0], dates[-1], "n median", sorted(ncount)[len(ncount)//2])
