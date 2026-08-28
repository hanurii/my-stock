# -*- coding: utf-8 -*-
"""101a — 비교표에 쓸 ETF 의 **OHLC 전체**를 받아 캐시한다.

🚨 왜 91c 로 안 되나:
   91c 는 `[closeadj, close]` 둘만 담는다. **무한매수법은 「3/4 지정가매도」가 있고
   그건 «장중 고가»가 닿아야 체결**이다. `high` 가 없으면 규칙을 못 짠다.

🚨 배당 처리 — **지수 쪽과 «같은 자»로 맞춘다**:
   91c 가 벤치마크에 `closeadj`(배당 포함)를 썼다. TQQQ 만 배당을 빼면
   **무한매수법에 불리한 자**가 된다. 그래서 `factor = closeadj / close` 를 OHLC «전부»에 곱해
   **총수익 기준 OHLC** 로 만든다. 장중 비율(고가/종가 등)은 그대로 보존된다.

내는 것: `.cache/bt5y/out/101-fund-ohlc.json`
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / ".cache" / "bt5y" / "out" / "101-fund-ohlc.json"
KEY = None
for ln in open(ROOT / ".env", encoding="utf-8"):
    if ln.startswith("NASDAQ_DATA_LINK_API_KEY="):
        KEY = ln.split("=", 1)[1].strip()

TICKERS = ("TQQQ", "SPY", "QQQ", "SOXL")
LO, HI = "1998-01-01", "2026-12-31"


def fetch_all(tk):
    rows, skip = [], 0
    while True:
        u = ("https://api.sharadar.com/v1.0/data/funds?api_key=%s&format=json"
             "&ticker=%s&date.gte=%s&date.lte=%s&limit=10000&skip=%d"
             % (KEY, tk, LO, HI, skip))
        d = json.loads(urllib.request.urlopen(u, timeout=180).read().decode())
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
        if not rows:
            print("%-5s **0행 — 없다**" % tk, flush=True)
            continue
        cols = list(rows[0])
        ser = {}
        for r in rows:
            try:
                o, h, lo_, c = (float(r["open"]), float(r["high"]),
                                float(r["low"]), float(r["close"]))
                ca = float(r["closeadj"]) if r.get("closeadj") not in (None, "") else c
            except (KeyError, TypeError, ValueError):
                continue
            if c <= 0:
                continue
            f = ca / c                      # 배당 포함 환산 계수
            ser[r["date"]] = [round(o * f, 6), round(h * f, 6),
                              round(lo_ * f, 6), round(c * f, 6), c]
        ds = sorted(ser)
        out[tk] = {"cols": "o,h,l,c(총수익) + c_raw(미조정)", "series": ser}
        print("%-5s %s행 · %s ~ %s" % (tk, "{:,}".format(len(ds)), ds[0], ds[-1]), flush=True)
        # 자릿수 검산 — 첫날·끝날 «미조정» 종가를 찍는다(외부 확인용)
        print("      첫날 미조정종가 %.2f · 끝날 미조정종가 %.2f · 총수익 배수 %.2f배"
              % (ser[ds[0]][4], ser[ds[-1]][4], ser[ds[-1]][3] / ser[ds[0]][3]), flush=True)
        # 관문 — 장중 관계가 깨지지 않았는가
        bad = sum(1 for d in ds if not (ser[d][2] <= ser[d][3] <= ser[d][1]
                                        and ser[d][2] <= ser[d][0] <= ser[d][1]))
        print("      관문 저가<=시·종<=고가 어긋난 날: **%d**" % bad, flush=True)
        if cols and "closeadj" not in cols:
            print("      ⚠️ closeadj 열이 없다 — 미조정으로 갔다", flush=True)
    OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print("저장: %s (%.1f MB)" % (OUT.name, OUT.stat().st_size / 1e6), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
