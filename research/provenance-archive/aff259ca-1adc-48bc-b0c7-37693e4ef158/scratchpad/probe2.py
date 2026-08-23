# -*- coding: utf-8 -*-
"""Probe more consensus endpoint variants + sample distribution across several codes."""
import sys, json, io
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from canslim_lib.fetch import _http_get_json, NAVER_HEADERS, NAVER_API

code = "105560"
candidates = [
    f"{NAVER_API}/{code}/integration",
    f"https://api.stock.naver.com/stock/{code}/integration",
    f"{NAVER_API}/{code}/finance/quarter?consensus=Y",
    f"https://m.stock.naver.com/api/stock/{code}/analyst",
    f"https://m.stock.naver.com/api/stock/{code}/consensus/quarter",
]
for url in candidates:
    d = _http_get_json(url, NAVER_HEADERS)
    print("\n===", url, "===")
    if d is None:
        print("None")
    else:
        s = json.dumps(d, ensure_ascii=False)
        # search for consensus-ish keys
        import re
        hits = set(re.findall(r'"([A-Za-z_]*[cC]onsensus[A-Za-z_]*)"', s))
        print("len:", len(s), "consensus keys:", hits)
        if "integration" in url:
            print("top keys:", list(d.keys()))
            ti = d.get("totalInfos")
            if ti:
                for x in ti:
                    if "컨센" in str(x.get("key","")) + str(x.get("title","")):
                        print(json.dumps(x, ensure_ascii=False))

# sample distribution: check 202606 isConsensus flag for a few of the 92
sample = ["095610", "037710", "241770", "005950", "042660", "010140", "272210", "051910"]
for c in sample:
    d = _http_get_json(f"{NAVER_API}/{c}/finance/quarter", NAVER_HEADERS)
    if not d:
        print(c, "-> no data")
        continue
    fi = d.get("financeInfo") or {}
    periods = fi.get("trTitleList") or []
    p26 = next((p for p in periods if p.get("key") == "202606"), None)
    rows = fi.get("rowList") or []
    op = next((r for r in rows if r.get("title") == "영업이익"), None)
    val = None
    if op:
        cell = (op.get("columns") or {}).get("202606")
        val = cell.get("value") if isinstance(cell, dict) else cell
    print(c, "202606:", p26, "OP:", val)
