# -*- coding: utf-8 -*-
"""102b — **왜 나빠졌나.** 사용자 물음(2026-08-29):

> 「살 수 있는 종목이 줄어드는 게 나쁜 것만은 아닙니다. **검증된 좋은 종목만을 계좌에 담을 수 있잖아요.**
>  이것 외에 혹시 왜 원칙을 더 지킬수록 나빠졌나요?」

**정확한 지적이고, 102 는 그걸 «안 쟀다».** 「적게 사도 좋은 것만 담으면 낫다」는 **잴 수 있는 주장**이다.

# 이 판이 가르는 것 — 두 갈래
```
㉮ «고른 것이 좋았나»   필터를 통과한 후보의 **거래당 수익률**이 더 높은가
                        → 높으면 사용자 말이 맞고, 문제는 «다른 데»(칸이 논다) 있다
                        → 같거나 낮으면 그 필터는 «좋은 종목»을 고른 게 아니다
㉯ «담을 수 있었나»     칸 5개 중 실제로 얼마나 채웠나 (노출)
                        → 후보가 아무리 좋아도 «칸이 비면» 현금이 논다
```
🚨 **이건 «판정»이 아니라 «기전 진단»이다. 문턱을 안 건다.**
🚨 후보 수준(슬롯 배정 «전»)에서 잰다 — 슬롯 추첨이 섞이면 두 갈래가 안 갈린다.
"""
from __future__ import annotations

import importlib.util as _u
import random
import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pyr_trigger as pt                                          # noqa: E402

_s = _u.spec_from_file_location("r102", HERE / "102-implement-principles.py")
r102 = _u.module_from_spec(_s)
_s.loader.exec_module(r102)
r91 = r102.r91
f92a = r102.f92a

BLOCKS = r102.BLOCKS


def per_trade(paths):
    """후보 하나하나의 «실현 손익». 슬롯 배정 «전»이라 추첨이 안 섞인다."""
    out = []
    for p in paths:
        t = pt.resolve_trade(p, ft="limit", fs="market", stop=r91.STOP,
                             target=r91.TARGET, shares=(1.0,), add_stop="floor_entry")
        m = t["masks"][()]
        epx = t["entry_px"]
        if not epx or not m["exits"]:
            continue
        w = sum(x[1] for x in m["exits"]) or 1.0
        px = sum(x[1] * x[2] for x in m["exits"]) / w
        hold = m["resolve_date"] or p["entry_date"]
        out.append(((px / epx - 1.0) * 100.0, p["entry_date"], hold))
    return out


def main() -> int:
    print("=" * 104, flush=True)
    print("102b — 왜 나빠졌나 · **기전 진단 · 문턱 없음**", flush=True)
    print("=" * 104, flush=True)
    print("사용자 물음: 「적게 사도 «검증된 좋은 종목»만 담으면 낫지 않나」", flush=True)
    print("→ 그건 **잴 수 있는 주장**이다. 후보 수준(슬롯 배정 «전»)에서 잰다.\n", flush=True)

    (_b0, _b1, by2), missing, _ = r91.load_ladder(
        r102.YEARS, r102.D0, r102.D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음 %s" % missing, flush=True)
        return 2
    fund, ixf = f92a.load()
    V, _stats = r102.build_variants(by2, fund, ixf)

    NAMES = ("바탕(91 정본)", "㉠ code33 만", "㉡ 실적전매도 만", "㉢ 돌파먹힘 만", "★ 셋 전부")

    print("# ㉮ **고른 것이 좋았나** — 후보 «거래당» 실현 손익 (슬롯 추첨 «전»)", flush=True)
    print("  %-18s %8s %10s %10s %8s %9s" %
          ("판", "후보 수", "거래당 평균", "거래당 중앙", "이긴 비율", "보유일 중앙"), flush=True)
    print("  " + "-" * 80, flush=True)
    tab = {}
    for nm in NAMES:
        rows = []
        for y in sorted(V[nm]):
            rows += per_trade(V[nm][y])
        if not rows:
            continue
        r = [x[0] for x in rows]
        hd = [r91._ord(x[2]) - r91._ord(x[1]) for x in rows]
        tab[nm] = {"n": len(r), "mean": st.mean(r), "med": st.median(r), "_r": r,
                   "win": 100.0 * sum(1 for v in r if v > 0) / len(r),
                   "hold": st.median(hd)}
        t = tab[nm]
        print("  %-18s %8s %+9.3f%% %+9.3f%% %7.1f%% %8.0f일"
              % (nm, "{:,}".format(t["n"]), t["mean"], t["med"], t["win"], t["hold"]), flush=True)

    b = tab["바탕(91 정본)"]
    print("", flush=True)
    print("  ★ 바탕 대비 «거래당» 차이 — **이게 「좋은 종목을 골랐나」의 답이다**", flush=True)
    print("     🚨 표본이 작은 팔이 있다(108·61건). **재표집 구간을 «같은 줄»에 적는다.**", flush=True)
    rnd = random.Random(0)
    for nm in NAMES[1:]:
        if nm not in tab:
            continue
        t = tab[nm]
        d = t["mean"] - b["mean"]
        A, B = t["_r"], b["_r"]
        na, nb = len(A), len(B)
        ds = sorted(sum(rnd.choice(A) for _ in range(na)) / na
                    - sum(rnd.choice(B) for _ in range(nb)) / nb for _ in range(2000))
        lo, hi = ds[50], ds[1949]
        zero = "**0 포함 = 못 가림**" if lo <= 0 <= hi else "0 배제"
        print("     %-16s %+7.3f%%p  구간 [%+7.3f, %+7.3f] %s  (이긴 비율 %+5.1f%%p · n=%s)"
              % (nm, d, lo, hi, zero, t["win"] - b["win"], "{:,}".format(t["n"])), flush=True)

    # ── ㉯ 칸을 얼마나 채웠나 ──────────────────────────────────────────
    print("\n# ㉯ **담을 수 있었나** — 칸 5개 중 실제 노출 (102 본판에서)", flush=True)
    d102 = json.loads((r91.OUT / "102-implement-principles.json").read_text(encoding="utf-8"))
    print("  %-18s %s" % ("판", "창별 노출(%) · 동시보유가 아니라 «돈이 일한 비율»"), flush=True)
    print("  " + "-" * 80, flush=True)
    for nm in NAMES:
        w = d102["res"].get(nm, {}).get("win", {})
        if not w:
            continue
        print("  %-18s %s" % (nm, "  ".join("%s %5.1f%%" % (l.split()[0], w[l]["expo"])
                                            for l in w)), flush=True)

    print("\n" + "=" * 104, flush=True)
    print("  ★ 읽는 법", flush=True)
    print("     ㉮ 가 «플러스»인데 성적이 나쁘면  → 좋은 종목을 골랐는데 **칸이 놀았다**", flush=True)
    print("     ㉮ 가 «0 이하»이면              → 그 필터는 **좋은 종목을 고른 게 아니다**", flush=True)
    (r91.OUT / "102b-why-worse.json").write_text(
        json.dumps({k: {a: c for a, c in v.items() if a != "_r"}
                    for k, v in tab.items()}, ensure_ascii=False,
                   separators=(",", ":")), encoding="utf-8")
    print("\n저장: 102b-why-worse.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
