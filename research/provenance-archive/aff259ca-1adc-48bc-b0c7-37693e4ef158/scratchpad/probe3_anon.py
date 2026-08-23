# -*- coding: utf-8 -*-
"""Probe 3: anonymous session warm-up on data.krx.co.kr; short.krx.co.kr recon."""
import io
import json
import re
import sys
import time

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

# --- A) anonymous warm-up on data.krx.co.kr then retry srt bld ---
s = requests.Session()
s.headers["User-Agent"] = UA
r = s.get("http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201",
          timeout=20)
print("warmup status:", r.status_code, "cookies:", s.cookies.get_dict())

r2 = s.post("http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd",
            data={"bld": "dbms/MDC/STAT/srt/MDCSTAT30102", "locale": "ko_KR",
                  "strtDd": "20260801", "endDd": "20260818",
                  "isuCd": "KR7005930003", "share": "1", "money": "1",
                  "csvxls_isNo": "false"},
            headers={"Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201"},
            timeout=20)
print("anon srt retry:", r2.status_code, r2.text[:300])

# --- B) short.krx.co.kr recon ---
for url in [
    "https://short.krx.co.kr/",
    "https://short.krx.co.kr/main/main.jsp",
]:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=20, allow_redirects=True)
        print("\n---", url, "->", r.url, r.status_code, "len", len(r.text))
        # look for endpoint hints
        hits = set(re.findall(r"""["'](/[A-Za-z0-9_/.\-]*(?:cmd|jspx|do|json)[^"']*)["']""", r.text))
        for h in sorted(hits)[:30]:
            print("   endpoint-hint:", h)
        hits2 = set(re.findall(r"bld[\"'\s:=]+([A-Za-z0-9_/]+)", r.text))
        for h in sorted(hits2)[:20]:
            print("   bld-hint:", h)
    except Exception as e:
        print("\n---", url, "ERROR", repr(e))
    time.sleep(1)
