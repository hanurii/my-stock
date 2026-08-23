# -*- coding: utf-8 -*-
"""Probe 5: KIS OpenAPI 국내주식 공매도 일별추이 (daily-short-sale, FHPST04830000)."""
import io
import json
import sys
import time
import urllib.parse
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = "C:/Users/hanul/playground/my-stock"
sys.path.insert(0, ROOT + "/scripts")

# load .env into os.environ (repo pattern)
import os
for line in open(ROOT + "/.env", encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

from canslim_lib import kis_api  # noqa: E402

token = kis_api.get_access_token()
print("token ok:", bool(token))

def kis_get(path, tr_id, params):
    qs = urllib.parse.urlencode(params)
    url = f"{kis_api._base_url()}{path}?{qs}"
    req = urllib.request.Request(url, headers={
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": os.environ["KIS_APP_KEY"],
        "appsecret": os.environ["KIS_APP_SECRET"],
        "tr_id": tr_id,
        "custtype": "P",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

for code in ["005930", "007340", "219130"]:
    try:
        js = kis_get("/uapi/domestic-stock/v1/quotations/daily-short-sale",
                     "FHPST04830000",
                     {"FID_COND_MRKT_DIV_CODE": "J",
                      "FID_INPUT_ISCD": code,
                      "FID_INPUT_DATE_1": "20260701",
                      "FID_INPUT_DATE_2": "20260818"})
        print("=" * 78)
        print(code, "rt_cd:", js.get("rt_cd"), "msg:", js.get("msg1", "").strip())
        for blk in ("output", "output1", "output2"):
            v = js.get(blk)
            if isinstance(v, dict):
                print(f"  {blk} (dict):", json.dumps(v, ensure_ascii=False)[:300])
            elif isinstance(v, list):
                print(f"  {blk}: rows={len(v)}")
                for row in v[:3]:
                    print("   ", json.dumps(row, ensure_ascii=False)[:400])
    except Exception as e:
        print(code, "ERROR", repr(e))
        try:
            print(e.read().decode()[:300])
        except Exception:
            pass
    time.sleep(0.5)
