# -*- coding: utf-8 -*-
"""Probe Naver mobile stock API for quarterly consensus data (KB금융 105560)."""
import sys, json, io
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from canslim_lib.fetch import _http_get_json, NAVER_HEADERS, NAVER_API

code = "105560"

# 1) finance/quarter — inspect periods incl. isConsensus flags
data = _http_get_json(f"{NAVER_API}/{code}/finance/quarter", NAVER_HEADERS)
if data:
    fi = data.get("financeInfo") or {}
    periods = fi.get("trTitleList") or []
    print("=== finance/quarter periods ===")
    for p in periods:
        print(json.dumps(p, ensure_ascii=False))
    rows = fi.get("rowList") or []
    print("row titles:", [r.get("title") for r in rows])
    # print operating profit row raw
    for r in rows:
        if "영업이익" in str(r.get("title", "")):
            print("=== row:", r.get("title"), "===")
            print(json.dumps(r, ensure_ascii=False)[:2000])
else:
    print("finance/quarter -> None")

# 2) probe candidate consensus endpoints
candidates = [
    f"{NAVER_API}/{code}/consensus",
    f"{NAVER_API}/{code}/finance/consensus",
    f"https://api.stock.naver.com/stock/{code}/consensus",
]
for url in candidates:
    d = _http_get_json(url, NAVER_HEADERS)
    print("\n=== ", url, " ===")
    if d is None:
        print("None (4xx or fail)")
    else:
        s = json.dumps(d, ensure_ascii=False)
        print(s[:3000])
