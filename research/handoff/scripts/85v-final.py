# -*- coding: utf-8 -*-
"""85v 부속 3 — 마무리 셋 (캐시된 특징으로 «싸게»).

  ㉠ 내 「시간 교란」 가설을 **정면으로 판정**한다 — 연도 «안»에서 잰 효과가 얼마인가
  ㉡ 결측 · NaN — 두뇌 물음(0건이 맞나 · base 가 NaN 을 품는 문제의 크기)
  ㉢ 85 의 표가 «다른 자»를 쓴다 — 같은 자로 다시 낸 요약

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/85v-final.py
"""
from __future__ import annotations

import bisect
import importlib.util as _u
import json
import os
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_s = _u.spec_from_file_location("r85", HERE / "85-entry-predictors.py")
r85 = _u.module_from_spec(_s)
_s.loader.exec_module(r85)
FEATS, SPLIT, NQ = r85.FEATS, r85.SPLIT, r85.NQ
CACHE = Path(os.environ.get("TEMP", "/tmp")) / "85v-feat-cache.json"


def main() -> int:
    if not CACHE.exists():
        print("🚨 캐시가 없다 — 85v-fragility.py 를 먼저 돌린다")
        return 2
    recs = json.loads(CACHE.read_text(encoding="utf-8"))["recs"]
    ins = [r for r in recs if r["d"] < SPLIT]
    outs = [r for r in recs if r["d"] >= SPLIT]
    xs = sorted(r["f"]["prior6m"] for r in ins if not r85._nan(r["f"]["prior6m"]))
    cuts = [xs[int(len(xs) * i / NQ)] for i in range(1, NQ)]

    def q1(r):
        v = r["f"]["prior6m"]
        return (not r85._nan(v)) and bisect.bisect_right(cuts, v) == 0

    def y20(r):
        return 1.0 if r["mfe"] >= 20 else 0.0

    print("=" * 98)
    print("㉠ 내 「시간 교란」 가설의 «정면 판정» — 연도 «안»에서 잰 효과")
    print("=" * 98)
    print("  가설: 「prior6m 1분위가 «좋은 해»에 더 많이 뽑혀서 +8.05%p 가 나왔다」")
    print("  판정법: **연도별 효과를 1분위 건수로 가중평균**한다.")
    print("          연도 혼합이 원인이면 이 값이 «작아져야» 한다.\n")
    tot = st.mean([y20(r) for r in outs])
    sel = [r for r in outs if q1(r)]
    raw = st.mean([y20(r) for r in sel]) - tot
    num = den = 0.0
    print("  %-6s %8s %9s %8s %9s %10s" % ("연도", "전체 n", "기준율", "1분위 n", "1분위율", "연도내 효과"))
    for y in sorted({r["d"][:4] for r in outs}):
        a = [r for r in outs if r["d"][:4] == y]
        b = [r for r in a if q1(r)]
        if not b:
            continue
        e = st.mean([y20(r) for r in b]) - st.mean([y20(r) for r in a])
        num += len(b) * e
        den += len(b)
        print("  %-6s %8d %8.2f%% %8d %8.2f%% %+9.2f%%p"
              % (y, len(a), 100 * st.mean([y20(r) for r in a]), len(b),
                 100 * st.mean([y20(r) for r in b]), 100 * e))
    wi = num / den
    print("\n  통째로 잰 효과        **%+.2f%%p**" % (raw * 100))
    print("  연도 «안»에서 잰 효과 **%+.2f%%p**  (가중평균, n=%d)" % (wi * 100, int(den)))
    print("  → 차이 %+.2f%%p" % ((wi - raw) * 100))
    if wi >= raw:
        print("\n  🚨 **내 가설은 틀렸다.** 연도 안에서 재면 효과가 «더 크다».")
        print("     연도 혼합은 효과를 «만든» 게 아니라 오히려 **가리고 있었다**")
        print("     (1분위가 나쁜 해 2022 에 33.5%, 좋은 해 2024 에 20.5% 로 «거꾸로» 쏠렸다).")
    else:
        print("\n  → 가설이 지지된다: 연도 안에서 재면 효과가 줄어든다.")

    print("\n" + "=" * 98)
    print("㉡ 결측 · NaN — 두뇌 물음")
    print("=" * 98)
    nan = Counter()
    for r in recs:
        for f in FEATS:
            if r85._nan(r["f"][f]):
                nan[f] += 1
    print("  특징별 NaN: %s" % (dict(nan) or "**없음**"))
    print("  특징 만든 거래 %d건 (85 가 찍은 3019 와 %s)"
          % (len(recs), "일치" if len(recs) == 3019 else "🚨 불일치"))
    nn = sum(1 for r in outs if r85._nan(r["f"]["in_pct"]))
    if nn:
        b_all = st.mean([y20(r) for r in outs])
        b_ok = st.mean([y20(r) for r in outs if not r85._nan(r["f"]["in_pct"])])
        print("  표본밖 `in_pct` NaN %d/%d — 기준율 전체 %.2f%% vs 비결측 %.2f%% = **%+.2f%%p**"
              % (nn, len(outs), b_all * 100, b_ok * 100, (b_all - b_ok) * 100))
        print("  → `in_pct` 칸의 기준율차가 그만큼 어긋난다. **승자 칸은 NaN 0 이라 무관.**")
    else:
        print("  → NaN 0건. **`base` 가 NaN 을 품는 문제는 이 자료에서 발화하지 않는다.**")

    print("\n" + "=" * 98)
    print("㉢ 85 의 표가 «다른 자»를 쓴다 — 같은 자로")
    print("=" * 98)
    bi = st.mean([y20(r) for r in ins])
    q_in = [r for r in ins if q1(r)]
    print("  85 의 표      표본안 「최고 33.6%% vs 최저 28.3%%」 = 폭 5.3%%p")
    print("                표본밖 「최고 33.64%% vs 기준율 25.59%%」 = **+8.05%%p**")
    print("  → 앞은 «분위끼리», 뒤는 «기준율 대비». **자가 다르다.**\n")
    print("  같은 자(기준율 대비)로:")
    print("     표본안  %.2f%% vs 기준율 %.2f%%  = **%+.2f%%p**"
          % (100 * st.mean([y20(r) for r in q_in]), 100 * bi,
             100 * (st.mean([y20(r) for r in q_in]) - bi)))
    print("     표본밖  %.2f%% vs 기준율 %.2f%%  = **%+.2f%%p**"
          % (100 * st.mean([y20(r) for r in sel]), 100 * tot, 100 * raw))
    print("  → 「밖 ÷ 안」 = **%.2f배**"
          % (raw / (st.mean([y20(r) for r in q_in]) - bi)))
    print("     고른 근거(안)보다 잰 값(밖)이 «두 배»다 — 크기의 절반은 고르기가 설명 못 한다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
