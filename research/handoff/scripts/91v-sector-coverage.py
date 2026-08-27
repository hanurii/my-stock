# -*- coding: utf-8 -*-
"""91v — **사다리가 두 창에서 «같은 일»을 하는가.** 검증 세션. (설계 검증 · 숫자 보기 전)

왜 이걸 재나
------------
`load_ladder` 의 `lvl1` 첫 줄:
```
s = sector.get(p["code"])
if not s:
    return True            # 제3군 = 통과 (61번 규약)
```
**섹터 라벨이 «없으면» 그 경로는 사다리 ①②를 «통째로 그냥 지나간다».**

사전등록 §6-1 은 **라벨의 «정확도»**를 한계로 적었다(오늘 라벨을 옛날에 붙인다).
🚨 **그런데 라벨의 «덮개율»은 안 적혀 있다.** 그리고 이쪽이 D★ 에 직접 걸린다:

```
덮개율이 두 창에서 다르면 → 사다리 ①② 가 «거르는 양»이 다르다
                          → D★(0<①<②)가 «전략»이 아니라 «자료 덮개»를 재게 된다
```
1999~2016 은 사라진 발행사가 훨씬 많으므로 **덮개율이 낮을 «수» 있다.**
**그러면 옛 창에서 사다리가 덜 일하고, D★ 는 전략과 무관하게 약해진다.**

★ 이건 **가정이 아니라 세면 끝나는 것**이다. 시뮬레이션 없이 «세기만» 한다.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/91v-sector-coverage.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SUB = ROOT / ".cache" / "bt5y" / "sub"
OUT = ROOT / ".cache" / "bt5y" / "out"

WINDOWS = (
    ("표본밖 B (1999~2001)", range(1999, 2002), "91-monthly-us-full.json"),
    ("표본밖 A (2002~2016)", range(2002, 2017), "91-monthly-us-full.json"),
    ("이미본  (2017~2026)", range(2017, 2027), "61-monthly-us.json"),
    ("이미본  (2017~2026) · 전체팩", range(2017, 2027), "91-monthly-us-full.json"),
)


def main() -> int:
    print("=" * 100)
    print("91v — 사다리 «덮개율»: 섹터 라벨이 없는 경로는 ①② 를 그냥 지나간다")
    print("=" * 100, flush=True)
    packs = {}
    for f in ("91-monthly-us-full.json", "61-monthly-us.json"):
        p = OUT / f
        if not p.exists():
            print("🚨 %s 없음" % f)
            continue
        packs[f] = json.loads(p.read_text(encoding="utf-8"))["sector"]
        print("  %-28s 섹터 라벨 **%d개**" % (f, len(packs[f])), flush=True)

    print("\n  %-32s %9s %9s %11s %11s"
          % ("창", "경로", "있는 해", "라벨 없음", "**제3군 통과율**"), flush=True)
    print("  " + "-" * 78, flush=True)
    rows = []
    for lab, years, mf in WINDOWS:
        sec = packs.get(mf)
        if sec is None:
            continue
        n, miss, have = 0, 0, 0
        codes_miss = Counter()
        for y in years:
            f = SUB / ("uspath_%d.json" % y)
            if not f.exists():
                continue
            have += 1
            ps = json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
            for p in ps:
                n += 1
                if not sec.get(p["code"]):
                    miss += 1
                    codes_miss[p["code"]] += 1
        if not n:
            print("  %-32s (경로 파일 없음 — 건너뜀)" % lab, flush=True)
            continue
        r = 100.0 * miss / n
        rows.append((lab, n, r, codes_miss))
        print("  %-32s %9d %9d %11d %10.2f%%" % (lab, n, have, miss, r), flush=True)

    if len(rows) >= 2:
        print("\n  ★ 읽는 법", flush=True)
        a = [r for r in rows if "표본밖" in r[0]]
        b = [r for r in rows if "이미본" in r[0] and "전체팩" in r[0]]
        if a and b:
            worst = max(a, key=lambda r: r[2])
            print("     표본밖 최악 **%.2f%%** vs 이미본(같은 팩) **%.2f%%** — 차 **%.2f%%p**"
                  % (worst[2], b[0][2], worst[2] - b[0][2]), flush=True)
            d = abs(worst[2] - b[0][2])
            if d < 2.0:
                print("     → **덮개율이 두 창에서 사실상 같다.** 사다리는 같은 일을 한다. "
                      "D★ 를 그대로 읽어도 된다 ✅", flush=True)
            else:
                print("     → 🚨 **덮개율이 다르다.** 옛 창에서 사다리 ①② 가 «덜 거른다» → "
                      "D★ 가 전략이 아니라 «덮개»를 잰다.", flush=True)
                print("        → 창마다 이 수를 «같이 적어야» D★ 를 읽을 수 있다.", flush=True)
        for lab, n, r, cm in rows:
            if cm:
                top = ", ".join("%s(%d)" % (c, k) for c, k in cm.most_common(5))
                print("     %-32s 라벨 없는 상위 종목: %s" % (lab, top), flush=True)
    print("\n  🚨 이 스크립트는 «세기»만 한다 — 시뮬레이션 없음, 91 의 결과 숫자 아님.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
