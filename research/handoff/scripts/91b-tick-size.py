# -*- coding: utf-8 -*-
"""91b — 관문 ⑥ · **십진 호가 전환을 «세어서» 확인한다.**

사전등록 91 §1 은 「2001-04-09 이전엔 1/16 격자라 성질이 다를 수 있다」를 **가설**로 적었다.
가설을 실측으로 바꾼다. 자료 파일을 안 건드리게 **REST** 로 받는다(경로 빌드와 충돌 방지).

★ 개정 1 (검증 세션 `35f2aaa4` 지적) — **1/4 배수만으로는 못 가른다**
--------------------------------------------------------------------
1차 판에서 「1/16 배수 비율」을 쟀는데, Sharadar 가 분수 호가를 **센트로 반올림**해 둬서
살아남는 건 **1/4 배수뿐**이다. 그런데 1/4 배수는 두 가지가 똑같이 늘린다:
```
㉠ 진짜 1/16 호가 격자
㉡ 반올림 수 몰림(price clustering) — 호가와 «무관»하고 옛날일수록 강하다
```
**가르는 검사: «홀수» 16분의 1.**  k/16 (k 홀수) = .0625 .1875 .3125 .4375 .5625 .6875 .8125 .9375
센트로 반올림하면 → **`.06 .19 .31 .44 .56 .69 .81 .94`** (100칸 중 8칸 = **배경 8%**)
**㉡ 은 이 여덟 칸을 «전혀» 안 늘린다. ㉠ 만 늘린다.**

읽는 법 (값 보기 «전»에 적는다)
```
진짜 1/16 격자면   1/4 25% · 1/8만 25% · 홀수1/16 50%
㉡ 몰림뿐이면      1/4 만 배경(4%) 위 · 1/8만·홀수1/16 은 **배경(8%·8%) 근처**
```
"""
from __future__ import annotations

import json
import os
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

# 센트 단위(0~99)로 본 칸 — 반올림 뒤 값
Q4 = {0, 25, 50, 75}                            # 1/4 배수      배경 4/100
E8 = {13, 12, 38, 37, 63, 62, 88, 87}           # 1/8 «만»      배경 8/100 (반올림 방향 둘 다)
O16 = {6, 19, 31, 44, 56, 69, 81, 94}           # 홀수 1/16     배경 8/100  ← **가르는 칸**
BG = {"1/4": 4.0, "1/8만": 8.0, "홀수1/16": 8.0}


def fetch(tk, lo, hi):
    u = ("https://api.sharadar.com/v1.0/data/stocks?api_key=%s&format=json"
         "&ticker=%s&date.gte=%s&date.lte=%s&limit=10000" % (KEY, tk, lo, hi))
    return json.loads(urllib.request.urlopen(u, timeout=90).read().decode())["data"]


def main() -> int:
    print("91b — 십진 호가 전환 실측 (개정 1: «홀수 16분의 1»로 가른다)\n", flush=True)
    print("  배경값: 1/4 = 4.0%% · 1/8만 = 8.0%% · **홀수1/16 = 8.0%%**", flush=True)
    print("  %-8s %8s %9s %9s %11s %10s"
          % ("구간", "관측", "1/4", "1/8만", "**홀수1/16**", "판정"), flush=True)
    print("  " + "-" * 66, flush=True)
    for lab, lo, hi in WINDOWS:
        n = c4 = c8 = c16 = 0
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
                if c in (None, ""):
                    continue
                c = float(c)
                if c <= 0:
                    continue
                n += 1
                cent = int(round(c * 100)) % 100
                if cent in Q4:
                    c4 += 1
                elif cent in E8:
                    c8 += 1
                elif cent in O16:
                    c16 += 1
        if not n:
            continue
        p4, p8, p16 = 100 * c4 / n, 100 * c8 / n, 100 * c16 / n
        # 판정 — 홀수1/16 이 배경(8%)의 1.5배를 넘으면 «진짜 격자»
        verd = "진짜 1/16" if p16 > 12.0 else ("몰림뿐" if p16 < 9.5 else "애매")
        print("  %-8s %8s %8.1f%% %8.1f%% %10.1f%% %10s"
              % (lab, "{:,}".format(n), p4, p8, p16, verd), flush=True)
    print("\n  ★ 홀수1/16 이 8%% 근처면 ㉡«반올림 몰림»뿐이고, 25%% 쪽으로 붙으면 ㉠«진짜 격자»다.",
          flush=True)
    print("    (진짜 1/16 격자의 이론값은 홀수1/16 50%% — 센트 반올림 손실을 감안해도 크다)",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
