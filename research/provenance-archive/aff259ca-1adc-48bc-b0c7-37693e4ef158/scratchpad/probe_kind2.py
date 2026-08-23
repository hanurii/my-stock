# -*- coding: utf-8 -*-
"""Probe KIND company-filtered search variants."""
import sys
import io
import re
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
headers = {
    "User-Agent": UA,
    "Referer": "https://kind.krx.co.kr/disclosure/details.do?method=searchDetailsMain",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
}

BASE = {
    "method": "searchDetailsSub",
    "currentPageSize": "30",
    "pageIndex": "1",
    "orderMode": "1",
    "orderStat": "D",
    "forward": "details_sub",
    "searchCodeType": "char",
    "fromDate": "2026-07-29",
    "toDate": "2026-07-29",
    "reportNm": "",
}

def run(name, extra):
    d = dict(BASE)
    d.update(extra)
    r = requests.post("https://kind.krx.co.kr/disclosure/details.do",
                      headers=headers, data=d, timeout=15)
    rows = re.findall(r'<td class="txc">(2026-\d\d-\d\d \d\d:\d\d)</td>', r.text)
    titles = re.findall(r"openDisclsViewer\('(\d+)',''\)\" title='([^']*)'", r.text)
    total = re.search(r'class="first txc">(\d+)<', r.text)
    print(f"--- {name}: status {r.status_code} len {len(r.text)} firstrow# {total.group(1) if total else 'none'}")
    for t, (num, title) in list(zip(rows, titles))[:6]:
        print("   ", t, title[:50])

# variant A: repIsuSrtCd with A-prefix
run("A: repIsuSrtCd=A036930", {"repIsuSrtCd": "A036930", "searchCorpName": "A036930", "corpName": "A036930"})
# variant B: repIsuSrtCd plain
run("B: repIsuSrtCd=036930", {"repIsuSrtCd": "036930", "searchCorpName": "036930", "corpName": "036930"})
# variant C: company name
run("C: corpName=주성엔지니어링", {"searchCorpName": "주성엔지니어링", "corpName": "주성엔지니어링"})
# variant D: reportNm keyword only (no company)
run("D: reportNm=영업(잠정)실적", {"reportNmTemp": "영업(잠정)실적", "reportNm": "영업(잠정)실적"})
