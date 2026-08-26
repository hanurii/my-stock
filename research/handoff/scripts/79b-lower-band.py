# -*- coding: utf-8 -*-
"""79b — **아래 문턱: 79번이 본 「모양」이 촘촘한 격자에서도 나오는가**

79번 관측(세 점): 아래 문턱을 올리면 **자산은 유지되고 「최악일 때」가 오른다.**
```
+0%  자산 +319.25%  하단 +164.31%  (증액률 73.5%)
+2%  자산 +328.31%  하단 +204.59%  (62.6%)
+5%  자산 +320.00%  하단 +208.32%  (50.4%)
```
🚨 **세 점이 한 방향으로 늘어설 확률은 우연으로도 33%다.** 그래서 격자를 촘촘히 하고
**짝비교**를 붙인다.

## 묻는 것 — 값 보기 «전»에 고정
```
Q1  「최악일 때」가 아래 문턱에 «단조 증가» 하는가   ← 79번이 본 모양
Q2  「자산」이 그 사이에 «안 떨어지는가»(≥ +0% 칸의 95%)
Q3  짝지어 200판에서 «이기는 판 > 50%» 인 칸이 있는가
```
🚨 **어느 쪽이든 「최적 문턱은 X%」라고 쓰지 않는다.** 모양과 짝비교만 적는다(78b·79 규약).

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/79b-lower-band.py [--quick]
"""
from __future__ import annotations

import importlib.util as _u
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]

import dataaxis as da                                         # noqa: E402

_s = _u.spec_from_file_location("r79", HERE / "79-stop-and-band.py")
r79 = _u.module_from_spec(_s)
_s.loader.exec_module(r79)
r78, r76, r75a, r74, r41 = r79.r78, r79.r76, r79.r75a, r79.r74, r79.r41

OUT = ROOT / ".cache" / "bt5y" / "out"
LOS = (0.0, 1.0, 2.0, 3.0, 5.0, 8.0)
HALF = (0.5, 0.5)


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    n_seed = 20 if "--quick" in sys.argv else 200
    print("=" * 96, flush=True)
    print("79b — 아래 문턱의 «모양» (촘촘한 격자 + 짝비교)", flush=True)
    print("=" * 96, flush=True)
    by2, n_all, n_sel, _x = r74.load_filtered()
    print("경로 %d → 조합 %d · seed %d\n" % (n_all, n_sel, n_seed), flush=True)

    base_eq = None
    print("  %6s %11s %11s %8s %6s %8s %11s %9s"
          % ("문턱", "자산중앙", "운나쁠때", "MDD", "노출", "증액률", "짝 중앙", "이기는판"),
          flush=True)
    print("  " + "-" * 82, flush=True)
    R, curves = {}, {}
    for lo in LOS:
        ev, _b = r79.replay(by2, HALF, 8.0, r78.TR(3, lo))
        rs = r79.run(ev, n_seed)
        s = r76.summ(rs, n_seed)
        s["rate"] = r79.addrate(ev, HALF)
        eq = [x["equity_pct"] for x in rs]
        curves[lo] = [x["curve"] for x in rs]
        if base_eq is None:
            base_eq = eq
            pm, pw = 0.0, 0.0
        else:
            pr = sorted(((1 + a / 100) / (1 + b / 100) - 1) * 100
                        for a, b in zip(eq, base_eq))
            pm, pw = pr[len(pr) // 2], 100.0 * sum(1 for x in pr if x > 0) / len(pr)
        R[lo] = {**s, "pair_median": pm, "pair_win": pw}
        print("  %+5.0f%% %+10.2f%% %+10.2f%% %7.1f%% %5.1f%% %7.1f%% %+10.2f%% %8.1f%%"
              % (lo, s["equity"], s["p5"], s["mdd"], s["expo"], s["rate"], pm, pw),
              flush=True)

    p5s = [R[x]["p5"] for x in LOS]
    eqs = [R[x]["equity"] for x in LOS]
    mono_p5 = all(p5s[i] < p5s[i + 1] for i in range(len(p5s) - 1))
    im = p5s.index(max(p5s))
    uni_p5 = (all(p5s[i] < p5s[i + 1] for i in range(im))
              and all(p5s[i] > p5s[i + 1] for i in range(im, len(p5s) - 1)))
    p_mono = 2.0 / math.factorial(len(p5s))
    keep = [x for x in LOS[1:] if R[x]["equity"] >= 0.95 * eqs[0]]
    wins = [x for x in LOS[1:] if R[x]["pair_win"] > 50.0]

    print("\n" + "-" * 96, flush=True)
    print("판정 (🚨 «최적 문턱»을 고르지 않는다)", flush=True)
    print("  Q1 「최악일 때」 단조 증가: **%s** · 단봉(산 모양): **%s** "
          "(무작위 단조 확률 %.4f%%)"
          % ("예" if mono_p5 else "아니오", "예" if uni_p5 else "아니오", p_mono * 100),
          flush=True)
    print("     하단 %s" % " → ".join("%+.0f" % v for v in p5s), flush=True)
    print("  Q2 자산이 +0%% 칸의 95%% 이상인 칸: **%d / %d** %s"
          % (len(keep), len(LOS) - 1, [("%+.0f%%" % x) for x in keep]), flush=True)
    print("  Q3 짝지어 이기는 판 > 50%% 인 칸: **%d / %d** %s"
          % (len(wins), len(LOS) - 1, [("%+.0f%%" % x) for x in wins]), flush=True)
    verdict = ("**79번이 본 모양이 촘촘한 격자에서도 나온다**"
               if (mono_p5 or uni_p5) and len(wins) >= (len(LOS) - 1) // 2
               else "**모양이 재현되지 않는다 — 79번의 세 점은 우연이었을 수 있다**")
    print("  → %s" % verdict, flush=True)

    # 자료 축 — 짝비교가 가장 강한 칸이 아니라 **+2%(79번이 본 자리)** 로 고정
    print("\n🚨 자료 축 — 79번이 본 자리(+2%%)로 «고정»해서 건다 (사후 고르기 방지)",
          flush=True)
    sw = da.sweep(curves[2.0], curves[0.0], n_stream=n_seed,
                  n_rep=max(1, 1000 // n_seed))
    mm = r75a.mde(sw)
    for b in da.BLOCKS:
        v = mm[b]
        if v:
            print("  블록 %2d  관측 %+8.2f%% · **필요 %.2f배 = %.0f년** · 0배제 %s%s"
                  % (b, v["median"], v["T"], v["years"], "✅" if v["excl0"] else "❌",
                     "" if v["consistent"] else "  🚨자기점검 실패"), flush=True)

    (OUT / "79b-lower-band.json").write_text(json.dumps(
        {"los": list(LOS), "res": {str(k): v for k, v in R.items()},
         "mono_p5": mono_p5, "uni_p5": uni_p5, "keep": keep, "wins": wins,
         "n_seed": n_seed}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 79b-lower-band.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
