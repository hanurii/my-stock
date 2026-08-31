# -*- coding: utf-8 -*-
r"""141f — **㉨ `pre_*` 의 «값»을 검증한다.**

왜 필요한가 — **돌연변이 시험이 구멍을 잡았다**
------------------------------------------------
```
141e ② pre_c[-1] × 1.0001  →  관문 여덟이 «못 잡았다»
```
관문 여덟은 `pre_*` 의 **값을 하나도 안 본다**:
```
㉠′  SHARED 만 본다 — pre_* 는 «옛 파일에 없어서» 애초에 빠져 있다
㉡′  pre_d 의 «마지막 날짜»만 본다 (값이 아니라 날짜)
㉢   «길이»만 센다        ㉣  «키가 있나»와 «길이 정합»만
㉤   마지막 한 봉의 고저종 순서와 진입가 배수만 (1.0001 배는 안 걸린다)
```
> ### **이 재빌드의 «존재 이유»가 `pre_*` 인데 그 값이 무검증이었다.**

어떻게 검증하나 — **이미 «증명된» 배열에 대고 맞춘다**
------------------------------------------------------
같은 종목이 여러 번 나온다. 그러면
```
9월 진입 경로의 pre_* 창(진입 «전» 400봉)   ↔   3월 진입 경로의 d/o/h/l/c(진입 «후» 250봉)
                                                 ↑ ㉠′ 로 «옛 판과 같음»이 이미 증명된 배열
```
**겹치는 날짜에서 값이 «완전히» 같아야 한다.** 다르면 `pre_*` 가 틀린 것이다.
🚨 이 대조는 «옛 파일»을 안 쓴다 — 새 산출물 «안»에서 닫힌다.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/141f-pre-crosscheck.py \
        --new D:/stock-data/uspath-warm/full
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

FWD = (("o", "o"), ("h", "h"), ("l", "l"), ("c", "c"))
PRE = (("pre_o", "o"), ("pre_h", "h"), ("pre_l", "l"), ("pre_c", "c"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", required=True)
    ap.add_argument("--years", default="1999-2026")
    a = ap.parse_args()
    y0, y1 = (int(x) for x in a.years.split("-"))

    n_cmp = n_bad = n_rec = 0
    bad_year = Counter()
    ex = []
    for y in range(y0, y1 + 1):
        f = Path(a.new) / ("uspath_%d.json" % y)
        if not f.exists():
            continue
        ps = json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
        n_rec += len(ps)
        # ① «진입 후» 배열로 (종목, 날짜) → (o,h,l,c) 지도를 만든다 — 이미 증명된 값
        m = defaultdict(dict)
        for r in ps:
            d = r["d"]
            row = m[r["code"]]
            for i, day in enumerate(d):
                row[day] = (r["o"][i], r["h"][i], r["l"][i], r["c"][i])
        # ② 각 경로의 pre_* 를 그 지도에 대고 맞춘다
        for r in ps:
            row = m.get(r["code"])
            if not row:
                continue
            pd = r.get("pre_d") or []
            for i, day in enumerate(pd):
                got = row.get(day)
                if got is None:
                    continue
                mine = (r["pre_o"][i], r["pre_h"][i], r["pre_l"][i], r["pre_c"][i])
                n_cmp += 1
                if mine != got:
                    n_bad += 1
                    bad_year[y] += 1
                    if len(ex) < 5:
                        ex.append((y, r["code"], day, mine, got))
        del ps, m

    print("", flush=True)
    print("=" * 92, flush=True)
    print("㉨ `pre_*` 를 **이미 증명된 «진입 후» 배열**에 대고 맞춘다 (새 산출물 «안»에서 닫힘)",
          flush=True)
    print("=" * 92, flush=True)
    print("   경로 %s건 · 겹쳐서 비교한 (종목·날짜) **%s쌍**"
          % ("{:,}".format(n_rec), "{:,}".format(n_cmp)), flush=True)
    ok = (n_bad == 0)
    print("   어긋난 쌍 **%d** → %s"
          % (n_bad, "**통과**" if ok else "🚨 **미통과 — pre_* 가 경로와 안 맞는다**"), flush=True)
    if ex:
        print("   연도별: %s" % dict(bad_year), flush=True)
        for e in ex[:3]:
            print("   예: %s %s %s · pre %s vs 경로 %s" % e, flush=True)
    if n_cmp == 0:
        print("   🚨 **비교한 쌍이 0 이다 — 이 관문은 «아무것도 안 하고» 있다.**", flush=True)
        return 2
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
