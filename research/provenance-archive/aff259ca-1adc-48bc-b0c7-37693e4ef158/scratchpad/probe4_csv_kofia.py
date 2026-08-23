# -*- coding: utf-8 -*-
"""Probe 4: KRX CSV-OTP path (anon) + KOFIA freesis 대차거래."""
import io
import json
import sys
import time

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

# --- A) KRX CSV OTP path, anonymous ---
s = requests.Session()
s.headers["User-Agent"] = UA
s.get("http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC02030101", timeout=20)
otp_params = {
    "locale": "ko_KR",
    "strtDd": "20260801", "endDd": "20260818", "isuCd": "KR7005930003",
    "share": "1", "money": "1",
    "name": "fileDown", "url": "dbms/MDC/STAT/srt/MDCSTAT30102",
}
r = s.post("http://data.krx.co.kr/comm/fileDn/GenerateOTP/generate.cmd",
           data=otp_params,
           headers={"Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd"},
           timeout=20)
print("OTP status:", r.status_code, "len:", len(r.text), "body head:", r.text[:120])
if r.status_code == 200 and len(r.text) > 10:
    r2 = s.post("http://data.krx.co.kr/comm/fileDn/download_csv/download.cmd",
                data={"code": r.text},
                headers={"Referer": "http://data.krx.co.kr/comm/fileDn/download_csv/download.cmd"},
                timeout=20)
    print("CSV status:", r2.status_code, "len:", len(r2.content))
    print(r2.content[:400].decode("euc-kr", errors="replace"))

# --- B) KOFIA freesis 대차거래 ---
# Known screen object names circulating for FreeSIS AJAX:
#   STATSCU0100000060BO : 증권대차 > 대차거래추이 (market aggregate)
#   try also item-level variants
kf = requests.Session()
kf.headers.update({"User-Agent": UA, "Content-Type": "application/json",
                   "Referer": "https://freesis.kofia.or.kr/stat/FreeSIS.do"})

def kofia(obj, dm):
    body = {"dmSearch": dict(dm, OBJ_NM=obj)}
    try:
        r = kf.post("https://freesis.kofia.or.kr/meta/getMetaDataList.do",
                    data=json.dumps(body), timeout=25)
        print(f"\nKOFIA {obj}: HTTP {r.status_code} len {len(r.text)}")
        if r.status_code == 200:
            try:
                js = r.json()
                for k, v in js.items():
                    if isinstance(v, list):
                        print(f"  {k}: rows={len(v)}")
                        for row in v[:3]:
                            print("   ", json.dumps(row, ensure_ascii=False)[:250])
                    else:
                        print(f"  {k}: {str(v)[:100]}")
            except Exception:
                print("  non-json:", r.text[:200])
    except Exception as e:
        print(f"\nKOFIA {obj}: ERROR {e!r}")

# market-aggregate 대차거래추이 (well-known)
kofia("STATSCU0100000060BO",
      {"tmpV40": "1000000", "tmpV41": "1", "tmpV1": "12",
       "tmpV45": "20260801", "tmpV46": "20260818"})
time.sleep(1)
# guesses for 종목별 대차거래
for obj in ["STATSCU0100000070BO", "STATSCU0100000080BO", "STATSCU0100000090BO"]:
    kofia(obj, {"tmpV40": "1000000", "tmpV41": "1", "tmpV1": "12",
                "tmpV45": "20260801", "tmpV46": "20260818", "tmpV74": "005930"})
    time.sleep(1)
