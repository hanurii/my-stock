# -*- coding: utf-8 -*-
"""Probe 6: KIS daily-short-sale history depth / row cap; Naver quick check."""
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = "C:/Users/hanul/playground/my-stock"
sys.path.insert(0, ROOT + "/scripts")
for line in open(ROOT + "/.env", encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())
from canslim_lib import kis_api  # noqa: E402

token = kis_api.get_access_token()

def short_sale(code, d1, d2):
    qs = urllib.parse.urlencode({
        "FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code,
        "FID_INPUT_DATE_1": d1, "FID_INPUT_DATE_2": d2})
    url = f"{kis_api._base_url()}/uapi/domestic-stock/v1/quotations/daily-short-sale?{qs}"
    req = urllib.request.Request(url, headers={
        "content-type": "application/json", "authorization": f"Bearer {token}",
        "appkey": os.environ["KIS_APP_KEY"], "appsecret": os.environ["KIS_APP_SECRET"],
        "tr_id": "FHPST04830000", "custtype": "P"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

tests = [
    ("005930", "20250301", "20260818"),   # spans 공매도 재개 2025-03-31
    ("005930", "20230101", "20231231"),   # ban period (2023-11 ban starts)
    ("005930", "20200101", "20201231"),   # deep history
    ("007340", "20250301", "20251231"),
]
for code, d1, d2 in tests:
    js = short_sale(code, d1, d2)
    rows = js.get("output2") or []
    rows = [r for r in rows if r.get("stck_bsop_date")]
    dates = sorted(r["stck_bsop_date"] for r in rows)
    nz = sum(1 for r in rows if int(r.get("ssts_cntg_qty") or 0) > 0)
    print(f"{code} {d1}~{d2}: rows={len(rows)} range={dates[0] if dates else '-'}..{dates[-1] if dates else '-'} nonzero_short={nz}")
    time.sleep(0.4)

# row-cap check: full year 2025
js = short_sale("005930", "20250101", "20251231")
rows = [r for r in (js.get("output2") or []) if r.get("stck_bsop_date")]
dates = sorted(r["stck_bsop_date"] for r in rows)
print(f"cap-check 2025 full year: rows={len(rows)} range={dates[0] if dates else '-'}..{dates[-1] if dates else '-'}")

# --- Naver quick check: any short-sale/loan endpoints? ---
def naver(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        return f"ERR {e!r}"

t = naver("https://m.stock.naver.com/api/stock/005930/integration")
print("\nNaver integration keys:", t[:200] if t.startswith("ERR") else json.dumps(sorted(json.loads(t).keys()), ensure_ascii=False))
