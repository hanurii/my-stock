# -*- coding: utf-8 -*-
r"""141 — **웜업 재빌드 관문 넷.** 자료만 검사한다. 특징·체·성적은 «없다».

두뇌 세션 확정(2026-08-31):
```
㉠′ 옛 경로 vs 새 경로 — 공유 키가 **완전히** 같은가   ← 실패할 수 «있는» 관문
㉡′ pre_d[-1] == scan_date                            ← 「< d[0]」보다 한 칸 조인 판
㉢  len(pre_*) == 250 · 못 채운 건은 **연도별 분포**까지
㉣  키 구성이 약속대로인가 (pre_* 여섯 + v)
```
🚨 ㉠′ 가 이 작업의 전부다. **한 자리라도 다르면 되돌리고 «왜인지»부터.**

실행:
  PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/141-warmup-gates.py \
      --old .cache/bt5y/sub --new D:/stock-data/uspath-warm
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

SHARED = ("code", "pattern", "scan_date", "entry_date",
          "pivot", "entry_price", "atr_band", "d", "o", "h", "l", "c")
NEWKEYS = ("pre_d", "pre_o", "pre_h", "pre_l", "pre_c", "pre_v", "v")
W = 250


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))["trigger_paths"]


def key(r):
    return (r["scan_date"], r["code"], r["pattern"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", default=".cache/bt5y/sub")
    ap.add_argument("--new", required=True)
    ap.add_argument("--years", default="1999-2026")
    a = ap.parse_args()
    y0, y1 = (int(x) for x in a.years.split("-"))
    years = range(y0, y1 + 1)

    n_pair = n_only_old = n_only_new = 0
    a_bad = Counter()
    a_ex = []
    b_bad, b_ex = 0, []
    c_short, c_short_by_year, c_len = 0, Counter(), Counter()
    d_bad, d_ex = 0, []
    n_new_tot = 0

    for y in years:
        fo, fn = Path(a.old) / ("uspath_%d.json" % y), Path(a.new) / ("uspath_%d.json" % y)
        if not fn.exists():
            print("   %d년 — 새 파일 없음, 건너뜀" % y, flush=True)
            continue
        if not fo.exists():
            print("🚨 %d년 — 옛 파일이 없어 ㉠′ 를 못 건다" % y, flush=True)
            return 2
        old = {key(r): r for r in load(fo)}
        new = load(fn)
        n_new_tot += len(new)
        seen = set()
        for r in new:
            k = key(r)
            seen.add(k)
            o = old.get(k)
            if o is None:
                n_only_new += 1
                continue
            n_pair += 1
            # ── ㉠′ 공유 키가 «완전히» 같은가 ────────────────────────────
            for f in SHARED:
                if r.get(f) != o.get(f):
                    a_bad[f] += 1
                    if len(a_ex) < 5:
                        a_ex.append((y, k, f))
            # ── ㉡′ pre_d[-1] == scan_date ──────────────────────────────
            pd = r.get("pre_d") or []
            if not pd or pd[-1] != r["scan_date"]:
                b_bad += 1
                if len(b_ex) < 5:
                    b_ex.append((k, pd[-1] if pd else None))
            # ── ㉢ 길이 ────────────────────────────────────────────────
            c_len[len(pd)] += 1
            if len(pd) < W:
                c_short += 1
                c_short_by_year[y] += 1
            # ── ㉣ 키 구성 ─────────────────────────────────────────────
            miss = [f for f in NEWKEYS if f not in r]
            if miss:
                d_bad += 1
                if len(d_ex) < 5:
                    d_ex.append((k, miss))
            else:
                n = len(pd)
                if not all(len(r[f]) == n for f in ("pre_o", "pre_h", "pre_l", "pre_c", "pre_v")):
                    d_bad += 1
                    if len(d_ex) < 5:
                        d_ex.append((k, "pre_* 길이 불일치"))
                elif len(r["v"]) != len(r["d"]):
                    d_bad += 1
                    if len(d_ex) < 5:
                        d_ex.append((k, "v 길이 != d 길이"))
        n_only_old += sum(1 for k in old if k not in seen)
        print("   %d년 — 짝 %d · 새쪽만 %d · 옛쪽만 %d"
              % (y, len(seen & set(old)), len(seen - set(old)),
                 len(set(old) - seen)), flush=True)

    print("", flush=True)
    print("=" * 92, flush=True)
    print("관문 넷 — 새 경로 %s건 · 짝지은 것 %s건"
          % ("{:,}".format(n_new_tot), "{:,}".format(n_pair)), flush=True)
    print("=" * 92, flush=True)

    ok = True
    tot_a = sum(a_bad.values())
    ok &= (tot_a == 0 and n_only_old == 0 and n_only_new == 0)
    print("㉠′ 공유 키가 «완전히» 같은가 — 어긋난 필드 **%d** · 옛쪽만 %d · 새쪽만 %d  → %s"
          % (tot_a, n_only_old, n_only_new,
             "**통과**" if (tot_a == 0 and n_only_old == 0 and n_only_new == 0)
             else "🚨 **미통과 — 되돌리고 «왜인지»부터**"), flush=True)
    if a_bad:
        print("    필드별: %s" % dict(a_bad), flush=True)
        print("    예: %s" % (a_ex[:3],), flush=True)

    ok &= (b_bad == 0)
    print("㉡′ pre_d[-1] == scan_date — 어긋난 건 **%d** → %s"
          % (b_bad, "**통과**" if b_bad == 0 else "🚨 **미통과**"), flush=True)
    if b_ex:
        print("    예: %s" % (b_ex[:3],), flush=True)

    print("㉢ 웜업 길이 — %d봉 미만 **%d건** (%.2f%%)"
          % (W, c_short, 100 * c_short / max(1, n_pair)), flush=True)
    if c_short_by_year:
        print("    🚨 **연도별 분포** (다음 판의 표본을 정한다):", flush=True)
        for y in sorted(c_short_by_year):
            print("       %d  %5d건 / 그해 짝 대비" % (y, c_short_by_year[y]), flush=True)
    sml = sorted(c_len.items())[:5]
    print("    가장 짧은 쪽 길이 분포: %s" % (sml,), flush=True)
    print("    (㉢ 은 «세기»만 한다 — 빼나·짧은 채 두나·결측 처리하나는 «다음 판 사전등록»)",
          flush=True)

    ok &= (d_bad == 0)
    print("㉣ 키 구성(pre_* 여섯 + v · 길이 정합) — 어긋난 건 **%d** → %s"
          % (d_bad, "**통과**" if d_bad == 0 else "🚨 **미통과**"), flush=True)
    if d_ex:
        print("    예: %s" % (d_ex[:3],), flush=True)

    print("", flush=True)
    print("→ %s" % ("**넷 다 통과.** 덧붙이기가 성공했다." if ok
                    else "🚨 **미통과가 있다. 재빌드 산출을 쓰지 말 것.**"), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
