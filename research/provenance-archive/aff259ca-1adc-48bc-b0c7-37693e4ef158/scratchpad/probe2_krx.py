# -*- coding: utf-8 -*-
"""Probe 2: KRX srt blds with correct params (from pykrx source)."""
import io
import json
import sys
import time

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

S = requests.Session()
S.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201",
})
URL = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"

ISIN = {"005930": "KR7005930003", "007340": "KR7007340003", "219130": "KR7219130002"}


def krx(bld, **params):
    data = {"bld": bld, "locale": "ko_KR", "csvxls_isNo": "false"}
    data.update(params)
    r = S.post(URL, data=data, timeout=30)
    if r.status_code != 200:
        return {"_err": r.status_code, "_body": r.text[:200]}
    try:
        return r.json()
    except Exception:
        return {"_raw": r.text[:300]}


def rows(js):
    for k in ("OutBlock_1", "output", "block1"):
        if isinstance(js, dict) and k in js:
            return js[k]
    return []


def show(name, js, nrows=3):
    print("=" * 78)
    print(name)
    if "_err" in (js or {}):
        print("  HTTP", js["_err"], js.get("_body"))
        return
    rr = rows(js)
    print(f"  rows={len(rr)}  keys={list(js.keys()) if isinstance(js, dict) else '?'}")
    for row in rr[:nrows]:
        print("   ", json.dumps(row, ensure_ascii=False)[:260])


# --- 1) per-stock 공매도 거래 추이 (MDCSTAT30102): latest date = trade-data lag ---
for code, isin in ISIN.items():
    js = krx("dbms/MDC/STAT/srt/MDCSTAT30102",
             strtDd="20260701", endDd="20260818", isuCd=isin,
             share="1", money="1")
    show(f"[32001-trend] 공매도 거래 추이 {code}", js, nrows=4)
    time.sleep(0.8)

# --- 2) per-stock 공매도 잔고 추이 (MDCSTAT30502): latest date = balance lag ---
for code, isin in ISIN.items():
    js = krx("dbms/MDC/STAT/srt/MDCSTAT30502",
             strtDd="20260701", endDd="20260818", isuCd=isin,
             share="1", money="1")
    show(f"[33001-trend] 공매도 잔고 추이 {code}", js, nrows=4)
    time.sleep(0.8)

# --- 3) 종합정보 (MDCSTAT30001): 거래+잔고 in one call ---
js = krx("dbms/MDC/STAT/srt/MDCSTAT30001",
         strtDd="20260801", endDd="20260818", isuCd=ISIN["005930"],
         share="1", money="1")
show("[31001] 종합정보 005930", js, nrows=4)
time.sleep(0.8)

# --- 4) 전종목 공매도 거래 snapshot: does 20260817 exist yet? row counts STK/KSQ ---
for dd in ("20260817", "20260814"):
    for mkt in ("STK", "KSQ"):
        js = krx("dbms/MDC/STAT/srt/MDCSTAT30101",
                 trdDd=dd, mktId=mkt, inqCond="STMFRTSCIFDRFS",
                 share="1", money="1")
        rr = rows(js)
        nonzero = sum(1 for r in rr if r.get("CVSRTSELL_TRDVOL", "0").replace(",", "") not in ("0", "-", ""))
        print(f"[32001-all] trdDd={dd} mkt={mkt}: rows={len(rr)} nonzero_shortvol={nonzero}")
        if rr:
            print("    sample:", json.dumps(rr[0], ensure_ascii=False)[:250])
        time.sleep(0.8)

# --- 5) 전종목 공매도 잔고 snapshot: latest date with data ---
for dd in ("20260817", "20260814", "20260813"):
    js = krx("dbms/MDC/STAT/srt/MDCSTAT30501", trdDd=dd, mktTpCd="1",
             share="1", money="1")
    rr = rows(js)
    print(f"[33001-all] trdDd={dd} KOSPI: rows={len(rr)}")
    if rr:
        print("    sample:", json.dumps(rr[0], ensure_ascii=False)[:250])
    time.sleep(0.8)
