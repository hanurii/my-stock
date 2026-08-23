# -*- coding: utf-8 -*-
"""Probe 1: KRX data.krx.co.kr 공매도 (srt) bld codes."""
import json
import time

import requests

S = requests.Session()
S.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201",
})
URL = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"


def krx(bld, **params):
    data = {"bld": bld, "locale": "ko_KR", "csvxls_isNo": "false"}
    data.update(params)
    r = S.post(URL, data=data, timeout=20)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        return {"_raw": r.text[:500], "_status": r.status_code}


def show(name, js, nrows=3):
    print("=" * 70)
    print(name)
    if not isinstance(js, dict):
        print(" not dict:", str(js)[:200])
        return
    for k, v in js.items():
        if isinstance(v, list):
            print(f"  key={k} rows={len(v)}")
            for row in v[:nrows]:
                print("   ", json.dumps(row, ensure_ascii=False)[:300])
        else:
            print(f"  key={k} val={str(v)[:120]}")


# --- 0) finder: resolve full ISIN codes for our 3 stocks ---
for txt in ["005930", "007340", "219130"]:
    js = krx("dbms/comm/finder/finder_srtisu", mktsel="ALL", searchText=txt)
    show(f"finder_srtisu {txt}", js, nrows=2)
    time.sleep(0.7)

# --- 1) 전종목 공매도 거래 (snapshot for one day) — try a few bld candidates ---
for bld in [
    "dbms/MDC/STAT/srt/MDCSTAT30101",
    "dbms/MDC/STAT/srt/MDCSTAT30001",
]:
    js = krx(bld, mktId="STK", trdDd="20260814", share="1", money="1")
    show(f"{bld} trdDd=20260814 STK", js, nrows=2)
    time.sleep(0.7)
