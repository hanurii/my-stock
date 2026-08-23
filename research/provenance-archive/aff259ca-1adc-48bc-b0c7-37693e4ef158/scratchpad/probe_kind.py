# -*- coding: utf-8 -*-
"""Probe KIND details search for disclosure time."""
import sys
import io
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

url = "https://kind.krx.co.kr/disclosure/details.do"
headers = {
    "User-Agent": UA,
    "Referer": "https://kind.krx.co.kr/disclosure/details.do?method=searchDetailsMain",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
}
data = {
    "method": "searchDetailsSub",
    "currentPageSize": "15",
    "pageIndex": "1",
    "orderMode": "1",
    "orderStat": "D",
    "forward": "details_sub",
    "disclosureType": "",
    "disclosureType01": "",
    "disclosureType02": "",
    "disclosureType03": "",
    "disclosureType04": "",
    "disclosureType05": "",
    "disclosureType06": "",
    "disclosureType07": "",
    "disclosureType08": "",
    "disclosureType09": "",
    "disclosureType10": "",
    "disclosureType11": "",
    "disclosureType13": "",
    "disclosureType14": "",
    "disclosureType20": "",
    "pDisclosureType01": "",
    "pDisclosureType02": "",
    "pDisclosureType03": "",
    "pDisclosureType04": "",
    "pDisclosureType05": "",
    "pDisclosureType06": "",
    "pDisclosureType07": "",
    "pDisclosureType08": "",
    "pDisclosureType09": "",
    "pDisclosureType10": "",
    "pDisclosureType11": "",
    "pDisclosureType13": "",
    "pDisclosureType14": "",
    "pDisclosureType20": "",
    "searchCodeType": "char",
    "repIsuSrtCd": "",
    "allRepIsuSrtCd": "",
    "oldSearchCorpName": "",
    "corpNameTmp": "",
    "corpName": "036930",
    "searchCorpName": "036930",
    "business": "",
    "marketType": "",
    "settlementMonth": "",
    "securities": "",
    "submitOblgNm": "",
    "enterprise": "",
    "fromDate": "2026-07-29",
    "toDate": "2026-07-29",
    "reportNmTemp": "",
    "reportNm": "",
    "searchGrpTypeNm": "",
    "bfrDsclsType": "on",
}
r = requests.post(url, headers=headers, data=data, timeout=15)
print("status", r.status_code, "len", len(r.text))
print(r.text[:4000])
