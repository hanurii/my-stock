# -*- coding: utf-8 -*-
"""25 · **분할이 비수정 시계열에 심는 가짜 하루 수익률** 실측.

1차 통과(25-split-check)에서 창 안 factor 가 바뀐 종목 1,070개를 이미 골라 뒀다.
여기서는 그 종목들만 다시 읽어 **비수정 종가의 하루 변화율**을 재고,
같은 날 **수정 종가(Sharadar `close`)의 하루 변화율**과 나란히 놓는다.
차이가 곧 «하네스가 보는 가짜 움직임»이다.

덤: Sharadar `volume` 이 분할 조정된 값인지 확인한다(AAPL 2019-12-05, 4:1 분할 전).
"""
from __future__ import annotations

import csv, io, json, sys, zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import us_loader  # noqa: E402

LO, HI = "2021-02-01", "2026-08-21"
targets = set(json.load(open(ROOT / ".cache/bt5y/out/25-split-factors.json")))
print("대상 %d 종목" % len(targets), flush=True)

ser = defaultdict(list)          # t -> [(date, close_adj, close_unadj)]
aapl = []
with zipfile.ZipFile(us_loader.STOCKS_ZIP) as z:
    rd = csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8"))
    hdr = next(rd)
    print("헤더:", hdr, flush=True)
    for row in rd:
        t, d = row[0], row[1]
        if t == "AAPL" and "2019-12-02" <= d <= "2019-12-09":
            aapl.append(row)
        if t not in targets or d < LO or d > HI:
            continue
        ser[t].append((d, float(row[5]), float(row[8]), float(row[6])))

print("\n--- AAPL 2019-12 (4:1 분할 전) — volume 규약 확인 ---", flush=True)
for r in sorted(aapl, key=lambda x: x[1]):
    print("  ", r[1], "close", r[5], "closeunadj", r[8], "volume", r[6], flush=True)

rows = []
for t, v in ser.items():
    v.sort()
    best = (0.0, None, 0.0)
    for i in range(1, len(v)):
        pu, cu = v[i - 1][2], v[i][2]
        pa, ca = v[i - 1][1], v[i][1]
        if pu <= 0 or pa <= 0:
            continue
        ru, ra = cu / pu - 1, ca / pa - 1
        if abs(ru - ra) > abs(best[0]):
            best = (ru - ra, v[i][0], ra)
    if best[1]:
        rows.append({"code": t, "date": best[1], "fake_pct": best[0] * 100,
                     "real_pct": best[2] * 100})

rows.sort(key=lambda r: -abs(r["fake_pct"]))
print("\n--- 가짜 하루 움직임 (비수정 − 수정) ---", flush=True)
print("종목 %d 중 최대 왜곡" % len(rows), flush=True)
for th in (10, 20, 50, 90):
    k = sum(1 for r in rows if abs(r["fake_pct"]) >= th)
    print("  |왜곡| >= %3d%%p : %4d 종목 (전체 5,666의 %.1f%%)"
          % (th, k, k / 5666 * 100), flush=True)
up = sum(1 for r in rows if r["fake_pct"] > 0)
print("  방향: **위로 %d(가짜 급등·역분할)** · 아래로 %d(가짜 폭락·분할)"
      % (up, len(rows) - up), flush=True)
print("\n  상위 12 (종목 · 날짜 · 가짜%p · 그날 진짜%)", flush=True)
for r in rows[:12]:
    print("    %-7s %s  %+12.1f%%p   (진짜 %+.2f%%)"
          % (r["code"], r["date"], r["fake_pct"], r["real_pct"]), flush=True)
out = ROOT / ".cache/bt5y/out/25-split-impact.json"
json.dump(rows, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("\n저장:", out, flush=True)
