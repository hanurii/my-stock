# -*- coding: utf-8 -*-
"""25 · **분할 사건 빈도** — 저메모리 스트리밍 점검.

왜 재는가
---------
한국 경로(`canslim_lib/pdata_series.py`)는 fltRt 연쇄로 **수정주가**를 만든다.
미국 경로(`us_loader.py`)는 지시서대로 **분할을 되돌려 비수정주가**를 쓴다.
→ 두 시장이 **서로 반대 규약**이다. 분할일에 미국 종가는 실제로 뚝 떨어지고,
   보유 중이면 손절로 잡힌다. 그 크기를 먼저 잰다.

방법: 종목마다 창 안에서 나타난 factor(=closeunadj/close)의 **서로 다른 값 개수**를
      센다(반올림 6자리). 2개 이상이면 창 안에 기준가 변경이 있었다는 뜻.
      (날짜 정렬이 필요 없어 8~9M행을 통째로 안 들고 있어도 된다.)
"""
from __future__ import annotations

import csv
import io
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import us_loader  # noqa: E402

LO, HI = "2021-02-01", "2026-08-21"

meta = us_loader.load_tickers("base")
codes = {c for c, m in meta.items()
         if m["firstpricedate"] <= HI and m["lastpricedate"] >= LO}
print("기본판 창 종목 %d" % len(codes), flush=True)

fac = defaultdict(set)
n = 0
with zipfile.ZipFile(us_loader.STOCKS_ZIP) as z:
    name = z.namelist()[0]
    rd = csv.reader(io.TextIOWrapper(z.open(name), encoding="utf-8"))
    next(rd)
    for row in rd:
        t, d = row[0], row[1]
        if d < LO or d > HI or t not in codes:
            continue
        c = float(row[5])
        if c <= 0:
            continue
        fac[t].add(round(float(row[8]) / c, 6))
        n += 1
        if n % 2000000 == 0:
            print("  %dM행" % (n // 1000000), flush=True)

multi = {t: s for t, s in fac.items() if len(s) > 1}
print("\n창 안 행 %d · 시계열 있는 종목 %d" % (n, len(fac)), flush=True)
print("**창 안에서 factor 가 바뀐 종목 %d (%.1f%%)**"
      % (len(multi), len(multi) / max(1, len(fac)) * 100), flush=True)
big = {t: s for t, s in multi.items() if max(s) / min(s) >= 1.5}
print("  그중 배율 1.5배 이상(≈2:1 분할·병합급) **%d**" % len(big), flush=True)
rows = sorted(((max(s) / min(s), t, len(s)) for t, s in multi.items()), reverse=True)
print("\n  상위 15 (배율 · 종목 · 서로다른 factor 수)", flush=True)
for r, t, k in rows[:15]:
    print("    %8.2f  %-8s %d" % (r, t, k), flush=True)
print("\n  중앙 배율 %.3f" % sorted(x[0] for x in rows)[len(rows) // 2], flush=True)
