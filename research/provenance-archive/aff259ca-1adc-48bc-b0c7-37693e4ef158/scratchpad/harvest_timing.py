# -*- coding: utf-8 -*-
"""TASK 1: harvest disclosure times from KIND for all 92 reveal filings.

Source: KIND details search (POST, repIsuSrtCd=A<code>) — rows carry 공시시각 HH:MM.
Fallback: Daum finance disclosure API (createdAt).
Cache raw responses: .cache/earnings_classify/timing_<code>.json
"""
import json
import os
import re
import sys
import time
import datetime

import requests

sys.stdout.reconfigure(encoding="utf-8")

SCRATCH = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad"
REPO = r"C:\Users\hanul\playground\my-stock"
CACHE_DIR = os.path.join(REPO, ".cache", "earnings_classify")
os.makedirs(CACHE_DIR, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
KIND_HEADERS = {
    "User-Agent": UA,
    "Referer": "https://kind.krx.co.kr/disclosure/details.do?method=searchDetailsMain",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
}
DAUM_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json",
    "Referer": "https://finance.daum.net/",
}

ROW_TIME = re.compile(r'<td class="txc">(\d{4}-\d\d-\d\d \d\d:\d\d)</td>')
ROW_TITLE = re.compile(r"openDisclsViewer\('(\d+)'[^\)]*\)\"\s+title='([^']*)'")


def kind_rows(code: str, from_date: str, to_date: str):
    """Return (raw_html, [{time, title, acptno}]) for one company's filings in window."""
    data = {
        "method": "searchDetailsSub",
        "currentPageSize": "50",
        "pageIndex": "1",
        "orderMode": "1",
        "orderStat": "D",
        "forward": "details_sub",
        "searchCodeType": "char",
        "repIsuSrtCd": f"A{code}",
        "searchCorpName": f"A{code}",
        "corpName": f"A{code}",
        "fromDate": from_date,
        "toDate": to_date,
        "reportNm": "",
    }
    r = requests.post("https://kind.krx.co.kr/disclosure/details.do",
                      headers=KIND_HEADERS, data=data, timeout=20)
    r.raise_for_status()
    html = r.text
    rows = []
    # parse per <tr> chunk to keep time/title aligned
    for chunk in html.split("<tr")[1:]:
        mt = ROW_TIME.search(chunk)
        mi = ROW_TITLE.search(chunk)
        if mt and mi:
            rows.append({"time": mt.group(1), "acptno": mi.group(1),
                         "title": mi.group(2)})
    return html, rows


def daum_rows(code: str):
    url = f"https://finance.daum.net/api/disclosures?symbolCode=A{code}&page=1&perPage=60"
    r = requests.get(url, headers=DAUM_HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def match_filing(rows, reveal_kind):
    """Pick the reveal filing among rows; earliest matching time wins."""
    if reveal_kind == "잠정":
        cands = [r for r in rows if "잠정" in r["title"] and "실적" in r["title"]]
    else:
        cands = [r for r in rows if "반기보고서" in r["title"]]
    if not cands:
        return None
    return sorted(cands, key=lambda r: r["time"])[0]


def classify(hhmm):
    """장전 <09:00, 장중 09:00~15:30, 장후 >15:30."""
    if hhmm is None:
        return "시각미상"
    h, m = int(hhmm[:2]), int(hhmm[3:5])
    v = h * 60 + m
    if v < 9 * 60:
        return "장전"
    if v <= 15 * 60 + 30:
        return "장중"
    return "장후"


def main():
    with open(os.path.join(SCRATCH, "ec_reaction.json"), encoding="utf-8") as f:
        reaction = json.load(f)

    results = {}
    n_kind = n_daum = n_null = 0
    for i, (code, rec) in enumerate(sorted(reaction.items())):
        reveal = rec["reveal_date"]
        kind = rec["reveal_kind"]
        name = rec["name"]
        if not reveal:
            results[code] = {"time": None, "source": None, "title": None}
            n_null += 1
            continue

        cache_path = os.path.join(CACHE_DIR, f"timing_{code}.json")
        cached = None
        if os.path.exists(cache_path):
            with open(cache_path, encoding="utf-8") as f:
                cached = json.load(f)
            if cached.get("reveal_date") != reveal:
                cached = None
        if cached is not None:
            results[code] = {k: cached.get(k) for k in ("time", "source", "title")}
            if cached.get("time"):
                n_kind += 1 if cached.get("source") == "kind" else 0
                n_daum += 1 if cached.get("source") == "daum" else 0
            else:
                n_null += 1
            continue

        entry = {"code": code, "name": name, "reveal_date": reveal,
                 "reveal_kind": kind, "fetched_at": datetime.datetime.now().isoformat(timespec="seconds"),
                 "time": None, "source": None, "title": None,
                 "kind_rows": None, "kind_raw_len": 0, "daum_raw": None}

        # --- KIND (primary) ---
        try:
            html, rows = kind_rows(code, reveal, reveal)
            entry["kind_rows"] = rows
            entry["kind_raw_len"] = len(html)
            entry["kind_raw"] = html
            m = match_filing(rows, kind)
            if m:
                entry["time"] = m["time"][11:]  # HH:MM
                entry["source"] = "kind"
                entry["title"] = m["title"]
        except Exception as e:
            entry["kind_error"] = repr(e)
        time.sleep(0.4)

        # --- Daum fallback ---
        if entry["time"] is None:
            try:
                dj = daum_rows(code)
                entry["daum_raw"] = dj
                items = dj.get("data", [])
                if kind == "잠정":
                    cands = [it for it in items
                             if it.get("createdAt", "").startswith(reveal)
                             and "잠정" in it.get("title", "") and "실적" in it.get("title", "")]
                else:
                    cands = [it for it in items
                             if it.get("createdAt", "").startswith(reveal)
                             and "반기보고서" in it.get("title", "")]
                if cands:
                    c = sorted(cands, key=lambda it: it["createdAt"])[0]
                    entry["time"] = c["createdAt"][11:16]
                    entry["source"] = "daum"
                    entry["title"] = c["title"]
                time.sleep(0.4)
            except Exception as e:
                entry["daum_error"] = repr(e)

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=1)

        results[code] = {"time": entry["time"], "source": entry["source"],
                         "title": entry["title"]}
        if entry["time"] is None:
            n_null += 1
            print(f"[{i+1}/{len(reaction)}] {code} {name} {reveal} {kind} -> NULL")
        else:
            n_kind += 1 if entry["source"] == "kind" else 0
            n_daum += 1 if entry["source"] == "daum" else 0
            print(f"[{i+1}/{len(reaction)}] {code} {name} {reveal} {kind} -> {entry['time']} ({entry['source']}) {classify(entry['time'])}")

    with open(os.path.join(SCRATCH, "timing_raw.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)

    dist = {}
    for code, r in results.items():
        dist[classify(r["time"])] = dist.get(classify(r["time"]), 0) + 1
    print(f"\nfound: kind={n_kind} daum={n_daum} null={n_null}")
    print("timing dist:", dist)


if __name__ == "__main__":
    main()
