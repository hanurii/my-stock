# -*- coding: utf-8 -*-
"""Probe 7: FreeSIS recon — find 증권대차 menu/screen ids and per-stock params."""
import io
import json
import re
import sys
import time

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
s = requests.Session()
s.headers["User-Agent"] = UA

# 1) main page: find menu structure / service ids
r = s.get("https://freesis.kofia.or.kr/", timeout=25)
print("main:", r.status_code, len(r.text))
ids = sorted(set(re.findall(r"(STATSCU\d+|MSIS\d+)", r.text)))
print("ids on main:", ids[:40])

# 2) try the known stat page URL pattern for 증권대차
for sid in ["STATSCU0100000060"]:
    url = f"https://freesis.kofia.or.kr/stat/FreeSIS.do?parentDivId=MSIS40100000000000&serviceId={sid}"
    r = s.get(url, timeout=25)
    print("\nstat page", sid, r.status_code, len(r.text))
    # find JS files and dmSearch params
    for m in sorted(set(re.findall(r"""src=["']([^"']+\.js[^"']*)["']""", r.text)))[:15]:
        print("  js:", m)
    for m in sorted(set(re.findall(r"tmpV\d+", r.text)))[:30]:
        print("  param:", m, end="")
    print()
    ids2 = sorted(set(re.findall(r"STATSCU\d+", r.text)))
    print("  service ids in page:", ids2[:30])

# 3) menu list ajax guesses
for u, body in [
    ("https://freesis.kofia.or.kr/meta/getMenuList.do", {}),
    ("https://freesis.kofia.or.kr/stat/getMenuList.do", {}),
]:
    try:
        r = s.post(u, data=json.dumps(body),
                   headers={"Content-Type": "application/json"}, timeout=20)
        print("\n", u, r.status_code, r.text[:300])
    except Exception as e:
        print("\n", u, "ERR", repr(e))
    time.sleep(0.5)
