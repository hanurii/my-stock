# -*- coding: utf-8 -*-
"""Probe disclosure-time sources: Naver, KIND, Daum."""
import json
import sys
import io
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
NAVER_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json",
    "Referer": "https://m.stock.naver.com/",
}

code = "036930"  # 주성엔지니어링, reveal 2026-07-29 잠정

print("=== 1. Naver disclosure ===")
try:
    r = requests.get(f"https://m.stock.naver.com/api/stock/{code}/disclosure",
                     headers=NAVER_HEADERS, timeout=10)
    print("status", r.status_code)
    print(r.text[:2000])
except Exception as e:
    print("ERR", e)

print("\n=== 2. Daum disclosure ===")
DAUM_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json",
    "Referer": f"https://finance.daum.net/quotes/A{code}",
}
for url in [
    f"https://finance.daum.net/api/quotes/A{code}/disclosures?page=1&perPage=10",
    f"https://finance.daum.net/api/disclosures?symbolCode=A{code}&page=1&perPage=10",
]:
    try:
        r = requests.get(url, headers=DAUM_HEADERS, timeout=10)
        print(url, "->", r.status_code)
        print(r.text[:1500])
    except Exception as e:
        print("ERR", e)
    print("---")
