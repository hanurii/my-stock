# -*- coding: utf-8 -*-
"""91b — 관문 ⑥ · **십진 호가 전환을 «세어서» 확인한다.**

사전등록 91 §1 은 「2001-04-09 이전엔 1/16 격자라 성질이 다를 수 있다」를 **가설**로 적었다.
가설을 실측으로 바꾼다. 자료 파일을 안 건드리게 **REST** 로 받는다(경로 빌드와 충돌 방지).

재는 것: 종가가 **1/16(=0.0625)의 배수**인 비율. 십진 이후라면 0에 가까워야 한다.
🚨 대조를 함께 둔다 — 「1/100 배수 비율」. 십진 이후엔 ~100%여야 한다.
   (한쪽만 보면 「아무것도 안 하는 코드」로 통과할 수 있다 — 유형 24′)
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

ENV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".env")
KEY = None
for ln in open(os.path.abspath(ENV), encoding="utf-8"):
    if ln.startswith("NASDAQ_DATA_LINK_API_KEY="):
        KEY = ln.split("=", 1)[1].strip()

# 그 시절에도 살아 있던 큰 종목들 (생존자 편향은 여기선 무해 — 재는 건 «호가 격자»다)
TICKERS = ("AAPL", "MSFT", "INTC", "IBM", "GE", "JNJ", "KO", "PFE", "XOM", "WMT",
           "T", "MRK", "PG", "CSCO", "ORCL", "AMGN", "HD", "MCD", "BA", "CAT")

WINDOWS = (("1999", "1999-01-01", "1999-12-31"),
           ("2000", "2000-01-01", "2000-12-31"),
           ("2001상", "2001-01-01", "2001-04-08"),
           ("2001하", "2001-04-10", "2001-12-31"),
           ("2003", "2003-01-01", "2003-12-31"),
           ("2010", "2010-01-01", "2010-12-31"))


def fetch(tk, lo, hi):
    u = ("https://api.sharadar.com/v1.0/data/stocks?api_key=%s&format=json"
         "&ticker=%s&date.gte=%s&date.lte=%s&limit=10000" % (KEY, tk, lo, hi))
    return json.loads(urllib.request.urlopen(u, timeout=90).read().decode())["data"]


def main() -> int:
    print("91b — 십진 호가 전환 실측 (종가의 «격자»를 센다)\n", flush=True)
    print("  %-8s %8s  %10s  %10s  %10s" % ("구간", "관측", "1/16배수", "1/100배수", "소수3자리+"),
          flush=True)
    print("  " + "-" * 56, flush=True)
    for lab, lo, hi in WINDOWS:
        n = n16 = n100 = n3 = 0
        for tk in TICKERS:
            try:
                rows = fetch(tk, lo, hi)
            except Exception as e:
                print("   %s %s 실패 %s" % (lab, tk, e), flush=True)
                continue
            for r in rows:
                # 🚨 **비수정 종가**(closeunadj)로 잰다 — 분할 조정된 close 는
                #    격자가 깨진다(×0.25 하면 1/16 배수가 1/64 배수가 된다).
                c = r.get("closeunadj")
                if c is None:
                    continue
                c = float(c)
                if c <= 0:
                    continue
                n += 1
                x = c / 0.0625
                if abs(x - round(x)) < 1e-6:
                    n16 += 1
                y = c * 100.0
                if abs(y - round(y)) < 1e-6:
                    n100 += 1
                if abs(c * 1000 - round(c * 1000)) > 1e-6 or abs(y - round(y)) > 1e-6:
                    n3 += 1
        if not n:
            continue
        print("  %-8s %8s  %9.1f%%  %9.1f%%  %9.1f%%"
              % (lab, "{:,}".format(n), 100 * n16 / n, 100 * n100 / n, 100 * n3 / n),
              flush=True)
    print("\n  읽는 법: 분수 호가 시대면 «1/16배수»가 크게 높다.", flush=True)
    print("           «1/100배수»는 대조 — 어느 시대든 높아야 정상(격자가 더 잘다).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
