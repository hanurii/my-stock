# -*- coding: utf-8 -*-
"""91c — 지수 벤치마크(SPY·QQQ)를 REST 로 받아 캐시한다.

🚨 `stocks` 표엔 ETF 가 없다(SPY 조회 0행). `funds` 표에 있다 — 91b 에서 확인.
🚨 **배당 조정본(`closeadj`)을 쓴다.** 지수 «총수익»과 견주는 게 맞고,
   우리 전략 쪽은 배당을 안 받으므로 **지수에 유리한 자로 잰다**(보수적).
   대조로 미조정 종가도 함께 담아 둔다.
내는 것: `.cache/bt5y/out/91-benchmarks.json`
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / ".cache" / "bt5y" / "out" / "91-benchmarks.json"
KEY = None
for ln in open(ROOT / ".env", encoding="utf-8"):
    if ln.startswith("NASDAQ_DATA_LINK_API_KEY="):
        KEY = ln.split("=", 1)[1].strip()

TICKERS = ("SPY", "QQQ")
LO, HI = "1998-01-01", "2026-12-31"


def fetch_all(tk):
    rows, skip = [], 0
    while True:
        u = ("https://api.sharadar.com/v1.0/data/funds?api_key=%s&format=json"
             "&ticker=%s&date.gte=%s&date.lte=%s&limit=10000&skip=%d"
             % (KEY, tk, LO, HI, skip))
        d = json.loads(urllib.request.urlopen(u, timeout=120).read().decode())
        got = d.get("data") or []
        rows += got
        if len(got) < 10000:
            break
        skip += 10000
    return rows


def main() -> int:
    out = {}
    for tk in TICKERS:
        rows = fetch_all(tk)
        cols = set(rows[0]) if rows else set()
        adj = "closeadj" if "closeadj" in cols else "close"
        ser = {}
        for r in rows:
            v = r.get(adj)
            c = r.get("close")
            if v in (None, ""):
                continue
            ser[r["date"]] = [float(v), float(c) if c not in (None, "") else None]
        ds = sorted(ser)
        out[tk] = {"adj_col": adj, "series": ser}
        print("%-4s %s행 · %s ~ %s · 조정열=%s" % (tk, "{:,}".format(len(ds)), ds[0], ds[-1], adj),
              flush=True)
        # 자릿수 검산 — 알려진 값으로 대조
        print("     %s 종가 %.2f · %s 종가 %.2f"
              % (ds[0], ser[ds[0]][1], ds[-1], ser[ds[-1]][1]), flush=True)
    OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print("저장: %s (%.1f MB)" % (OUT.name, OUT.stat().st_size / 1e6), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
