# -*- coding: utf-8 -*-
r"""156a — **「그날 상장돼 있던 «전부»」로 시총 삼분위 «경계»를 세운다** (156 의 부품)

# 🚨🚨 이 파일이 «왜» 필요한가 — **두 세션이 «같은 방향»으로 틀렸다**
```
두뇌 세션 계획   「그날 «전체 상장사» 분포의 1/3 로 자른다」
검증 세션 답     「✅ 자료는 «전체»를 지원합니다 — `95-cap-pit.json` = **8,032 종목**」
🚨 실제          `95a-marketcap-index.py:44 needed()` —
                 **「모든 «경로»의 (종목 → «진입일»)」만 골라 담는다.**
                 ⇒ `95-cap-pit.json` 은 **«후보로 등장한 적 있는 종목»의 «진입일 근처»만** 있다.
                 ⇒ **「그날 상장돼 있던 전부」가 «아니다».**
```
> ### ★★ 검증 세션은 **«종목 수»를 세고 「전체를 지원한다」고 읽었다.**
> ### ★★ 그건 정본 실패목록 **유형 35** 그 자체다 —
> ###     **「«이미 있다/없다»가 제일 검산을 «안» 받는다. 「있다」가 더 조용하다」**
> ### 🚨 그리고 **판정하는 쪽이 «해법»을 낼 때는 그 해법이 «검산을 안 받는다».**

# ✅ 그런데 고치고 보니 **㉠-2(신선도 상한)가 «사라졌다»**
```
검증 세션 조건  「as-of 신선도 상한 N 을 «지금» 적어라 —
                 안 그러면 상폐 종목이 «얼어붙은 시총»으로 유니버스에 영원히 남는다」
✅ 그건 `95-cap-pit.json`(성긴 파일)을 «쓸 때»의 문제다.
   **원본 `daily.csv` 에서는 상폐 종목이 그날 «행이 없다».**
   ⇒ **「그날 살아 있었나」 = 「그날 행이 있나」. «상한»이라는 «손잡이가 필요 없다».**
```
> ### ★★ **손잡이를 «잘 고르는» 대신, 손잡이가 «없는 자리»로 옮겼다.** (오늘 규약 ③)
> ### ★ 그리고 그 편이 **더 정확하다** — N 을 뭘로 잡든 근사인데, 행의 유무는 «사실»이다.

내는 것: `D:\stock-data\derived\156-cap-tercile.json`
   {"q": {date: [q33, q67]}, "n": {date: 그날 상장 수}}
   🚨 단위는 «백만 달러»(Sharadar `marketcap` 원단위). 경계는 **log 안 씌운 원값 분위**다
      (분위는 «순위»만 쓰므로 log 여부가 «경계를 안 바꾼다» — 95 는 log 를 썼고 같은 자리다)
"""
from __future__ import annotations

import csv
import io
import json
import sys
import zipfile
from array import array
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SRC = Path(r"D:\stock-data\sharadar\daily.csv.zip")
OUT = Path(r"D:\stock-data\derived\156-cap-tercile.json")
LO, HI = 1.0 / 3.0, 2.0 / 3.0


def main() -> int:
    print("=" * 96)
    print("156a — **그날 상장돼 있던 «전부»로 시총 삼분위 경계**")
    print("=" * 96)
    print("🚨 `95-cap-pit.json` 은 «후보 진입일 근처»만 있다 — 「전체」가 «아니다»")
    print("✅ 원본 `daily.csv` 는 상폐 종목의 «행이 없다» ⇒ 신선도 상한이라는 «손잡이가 필요 없다»\n",
          flush=True)

    by = defaultdict(lambda: array("f"))
    z = zipfile.ZipFile(SRC)
    bad = 0
    with z.open("daily.csv") as f:
        r = csv.reader(io.TextIOWrapper(f, encoding="utf-8", newline=""))
        hdr = next(r)
        i_d, i_c = hdr.index("date"), hdr.index("marketcap")
        for n, row in enumerate(r, 1):
            try:
                v = float(row[i_c])
            except (ValueError, IndexError):
                bad += 1
                continue
            if v > 0:                       # 🚨 시총 0/음수는 «값이 아니다» — 세어서 찍는다
                by[row[i_d]].append(v)
            else:
                bad += 1
            if n % 5_000_000 == 0:
                print("  … %s행" % "{:,}".format(n), flush=True)
    print("  총 %s행 · 값 없음/0 이하 **%s행** · 날짜 %s개"
          % ("{:,}".format(n), "{:,}".format(bad), "{:,}".format(len(by))), flush=True)

    q, cnt = {}, {}
    for d, a in by.items():
        if len(a) < 100:                    # 🚨 그날 상장 수가 100 미만이면 «분위를 못 만든다»
            continue
        s = sorted(a)
        m = len(s)
        q[d] = [s[int(LO * m)], s[int(HI * m)]]
        cnt[d] = m
    print("  분위를 세운 날 **%s일** (상장 100개 미만인 날은 뺐다: %d일)"
          % ("{:,}".format(len(q)), len(by) - len(q)), flush=True)

    ks = sorted(q)
    print("\n### 검산 — 경계가 «시간에 따라 움직이나» (백만 달러)")
    print("  %-12s %10s %12s %12s" % ("날짜", "상장 수", "하위 1/3 선", "상위 1/3 선"))
    print("  " + "-" * 50)
    for d in (ks[0], ks[len(ks) // 4], ks[len(ks) // 2], ks[3 * len(ks) // 4], ks[-1]):
        print("  %-12s %9d %11.1f %12.1f" % (d, cnt[d], q[d][0], q[d][1]), flush=True)

    OUT.write_text(json.dumps({"q": q, "n": cnt}, separators=(",", ":")), encoding="utf-8")
    print("\n저장: %s (%.1fMB)" % (OUT, OUT.stat().st_size / 1e6), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
