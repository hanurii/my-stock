# -*- coding: utf-8 -*-
r"""236 - **「«갭» 추격 «폭»을 «좁히면» 어떻게 되나」** (조사 세션 2026-09-08)

  사전등록: results/236-PRE.md  (값 보기 «전»에 박음)
  ⛔ **«갭 «추격» «매수» 폭»«만»** — «추격» «손절» 폭(`80:73`)과 **«섞지» 않는다**(유형 67)
  🚨 **「현행」에도 «자»가 «둘»**: 하네스는 **상한이 «없다**(`pilot_us.py:193-201`)
      · 실전은 3.0(봇)·5.0(검출기)·5%(주문표) ⇒ **① = 「상한 «없음»」**

  ⛔ 자리 = **«고친» 자**(달력 6,893 · `201d-arms2.json` 의 cal) — «옛» 얼개 «금지**

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/236-chase-width.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
HERE = Path(__file__).resolve().parent

C1 = chr(0x2460)
CG = chr(0x24BC)
DELTA, MDE_K = 1.23, 2.8016
NBOOT, SEED = 2000, 236236
BLOCKS = ((20, 40), (80, 80))
CAP = 1.5          # 원전 중앙 1.03~1.54 의 «위»끝 — 사전등록에 박음
DESC_CAPS = (3.0, 5.0)


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


m201d = _load("m201d", "201d-rs-threshold.py")
r91 = m201d.r91
OUT = Path(str(r91.OUT))


def eq_of(by_pos, n_pos, slots=5):
    eq, held, got = 1.0, [], 0
    for p in range(n_pos):
        if held:
            keep_ = []
            for h in held:
                if h[0] < p:
                    eq += h[1] * h[2] / 100
                else:
                    keep_.append(h)
            held = keep_
        free = slots - len(held)
        cc = by_pos.get(p)
        if free > 0 and cc:
            wgt = eq / slots
            for rel, nt, _k in cc[:free]:
                held.append([p + rel, wgt, nt])
                got += 1
    for h in held:
        eq += h[1] * h[2] / 100
    return (eq - 1.0) * 100.0, got


def cell_of(lo, hi):
    if lo >= DELTA:
        return "**1**"
    if hi <= -DELTA:
        return "**2**"
    if lo <= 0 <= hi:
        return "**5**"
    if -DELTA <= lo and hi <= DELTA:
        return "**4a**"
    return "**4b**"


def main():  # noqa: C901
    P("# 236 - **「«갭» 추격 «폭»을 «좁히면» 어떻게 되나」**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/236-chase-width.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⛔ 사전등록 " + BQ + "results/236-PRE.md" + BQ + " 에 **«먼저»** 박았다")
    P("")
    P("---")
    P("")

    CA = OUT / "236-recs.json"
    t_build = 0.0
    if CA.exists():
        recs = [tuple(x) for x in json.loads(CA.read_text(encoding="utf-8"))]
        P(F3)
        P("   (♻️ 갈무리 " + BQ + "236-recs.json" + BQ + " — 거래 %s)" % format(len(recs), ","))
        P(F3)
    else:
        P("(자료를 «짓는» 중 — 피벗과 진입가를 «같이» 담는다 …)", flush=True)
        t0 = time.time()
        pairs, miss = m201d.build_pairs(m201d.CANON)
        if pairs is None:
            P("🚨 경로 «없음»: %s" % miss[:3])
            return 1
        recs = []
        for t, p in pairs:
            r = t["masks"][()]
            epx = t["entry_px"]
            piv = p.get("pivot") or p.get("pivot_price")
            if not piv:
                continue
            net = sum(fr * r91.sl.net(round(px / epx * 100 - 100, 2))
                      for _d, fr, px in r["exits"])
            d, rd = p["d"], r["resolve_date"]
            hold = d.index(rd) if (rd and rd in d) else len(d) - 1
            gap = (epx / piv - 1.0) * 100.0
            recs.append((t["entry_date"], max(1, hold), net, round(gap, 4)))
        CA.write_text(json.dumps([list(x) for x in recs]), encoding="utf-8")
        t_build = time.time() - t0
        P("")
        P(F3)
        P("   ✅ 자료 짓기 **%.1f 분**(실측) · 거래 **%s** · 캐시 "
          % (t_build / 60.0, format(len(recs), ",")) + BQ + "236-recs.json" + BQ)
        P(F3)
    P("")

    cal = json.loads((OUT / "201d-arms2.json").read_text(encoding="utf-8"))["cal"]
    ents = {r[0] for r in recs}
    if ents - set(cal):
        cal = sorted(set(cal) | ents)
    pos = {d: i for i, d in enumerate(cal)}
    n_pos = len(cal)

    base = [(d, h, n) for d, h, n, _g in recs]
    arm = [(d, h, n) for d, h, n, g in recs if g <= CAP]
    built = {C1: base, CG: arm}

    P("# 1. **팔 크기 · «양성» 대조 · «갭»의 «모양**")
    P("")
    P(F3)
    gaps = sorted(g for _d, _h, _n, g in recs)
    nz = [g for g in gaps if g > 0]
    P("   **① 현행(상한 «없음») 거래 = %s**" % format(len(base), ","))
    P("   **%s 진입가 ≤ 피벗＋%.1f%% 거래 = %s**  (**%.1f%%**가 «남는다**)"
      % (CG, CAP, format(len(arm), ","), 100.0 * len(arm) / len(base)))
    P("")
    P("   ★ **%s ⊂ ① ?**  %s ‧ ① «에만» = **%s** · %s «에만» = **0**(구성상)"
      % (CG, "✅ «그렇다»", format(len(base) - len(arm), ","), CG))
    P("")
    P("   🔎 **묘사(«판정» 아님) — «실전» 값으로 자르면**:")
    for c in DESC_CAPS:
        k = sum(1 for g in gaps if g <= c)
        P("      피벗＋%.1f%% 이하 = **%s** (%.1f%%)" % (c, format(k, ","), 100.0 * k / len(gaps)))
    P("")
    P("   🔎 **«갭»의 «모양»**: 0%%(피벗 «그대로» 체결) = **%s** (%.1f%%)"
      % (format(len(gaps) - len(nz), ","), 100.0 * (len(gaps) - len(nz)) / len(gaps)))
    if nz:
        nz.sort()
        P("      0 «초과»만: 중앙 **%.2f%%** · P90 **%.2f%%** · 최대 **%.2f%%**"
          % (st.median(nz), nz[int(len(nz) * .9)], nz[-1]))
    P(F3)
    P("")
    P("---")
    P("")

    def obs(lst):
        bp = defaultdict(list)
        for d, h, nt in lst:
            bp[pos[d]].append((h, nt, 0))
        return eq_of(bp, n_pos)

    o, got = {}, {}
    for k, v in built.items():
        e, g = obs(v)
        o[k] = m201d.ann(e)
        got[k] = g
    obsd = o[CG] - o[C1]
    P("# 2. **팔의 «절대» 값**(연환산 %p)")
    P("")
    P(F3)
    for k in built:
        P("   %-3s **%+.3f%%p/해**  ·  슬롯 «얻은» 것 **%s** / %s"
          % (k, o[k], format(got[k], ","), format(len(built[k]), ",")))
    P("   **%s − %s = %+.3f%%p**" % (CG, C1, obsd))
    P("   날짜 자리 **%s**(달력)" % format(n_pos, ","))
    P(F3)
    P("")
    P("---")
    P("")

    ia = {k: defaultdict(list) for k in built}
    for k, lst in built.items():
        for j, (d, _h, _n) in enumerate(lst):
            ia[k][pos[d]].append(j)

    P("# 3. **판정** — CI 를 **«둘» 다** 찍는다")
    P("")
    P("| 블록 | 점추정 | **백분위 CI** | 칸 | **기본(basic) CI** | 칸 | **MDE** | MDE÷Δ | 편향 |")
    P("|---|---:|---:|:--|---:|:--|---:|---:|---:|")
    t1 = time.time()
    cells = []
    for bi_blk, (bmn, bmx) in enumerate(BLOCKS):
        m201d.BMIN, m201d.BMAX = bmn, bmx
        rnd = random.Random(SEED + bi_blk)
        boots = []
        for bi in range(NBOOT):
            order = m201d.draw(n_pos, rnd)
            eqs = {}
            for k, lst in built.items():
                bp = defaultdict(list)
                for newp, oldp in enumerate(order):
                    for j in ia[k].get(oldp, ()):
                        _d, h, nt = lst[j]
                        bp[newp].append((h, nt, 0))
                eqs[k] = m201d.ann(eq_of(bp, n_pos)[0])
            boots.append(eqs[CG] - eqs[C1])
            if (bi + 1) % 500 == 0:
                P("  [%d~%d] 부트 %d/%d" % (bmn, bmx, bi + 1, NBOOT), flush=True)
        v = sorted(boots)
        lo, hi = v[int(NBOOT * .025)], v[int(NBOOT * .975)]
        sd = st.stdev(boots)
        blo, bhi = 2 * obsd - hi, 2 * obsd - lo
        cp, cb = cell_of(lo, hi), cell_of(blo, bhi)
        cells.append((cp, cb))
        P("| **%d~%d** | **%+.3f%%p** | [%+.3f, %+.3f] | %s | [%+.3f, %+.3f] | %s | **%.3f** | %.2f | %+.3f |"
          % (bmn, bmx, obsd, lo, hi, cp, blo, bhi, cb, MDE_K * sd, MDE_K * sd / DELTA,
             (lo + hi) / 2.0 - obsd), flush=True)
    t_boot = time.time() - t1
    P("")
    P(F3)
    P("   백분위 칸 = %s  ·  기본 칸 = %s"
      % (" · ".join(c[0] for c in cells), " · ".join(c[1] for c in cells)))
    P("")
    pc = {c[0] for c in cells}
    if pc == {"**5**"}:
        P("⇒ ③ **«못» 가린다** ⇒ **§B ㉒ 가 「«안» 쟀다」에서 「봤는데 «못» 가렸다」로 «바뀐다**")
    elif pc == {"**1**"}:
        P("⇒ ① **Ⓖ 가 «위»로 갈라졌다** — 「좁히는 게 «낫다」")
    elif pc == {"**2**"}:
        P("⇒ ② **Ⓖ 가 «아래»로 갈라졌다** — 「좁히면 «해»다」")
    else:
        P("⇒ 🚨 **블록마다 «다르다** — **「몇 중 몇」**으로 «그대로» 적는다")
    P(F3)
    P("")
    P("---")
    P("")
    P("# 💰 **실측**")
    P("")
    P(F3)
    P("   자료 짓기 **%s** · 부트 2×%d **%.1f 분**"
      % (("%.1f 분" % (t_build / 60.0)) if t_build else "(갈무리 씀)", NBOOT, t_boot / 60.0))
    P(F3)
    P("")
    P("# ⚠️ **이 판이 «못» 하는 것**")
    P("")
    P(F3)
    P("⛔ ① **「«우리»가 «정한» 것」이 «넷» 중 «셋»**이다(`236-PRE.md` §4) —")
    P("     **「원전 «그대로» 쟀다」로 «읽으면» «틀린다**")
    P("⛔ ② **1.5%% «한» 값**만 잤다 — **«격자»를 «안** 돌렸다(원전이 «수»를 «안» 줬다)")
    P("⛔ ③ **「현행」은 «하네스»의 것**(상한 «없음») — **«실전»의 3.0/5.0 과 «다르다**")
    P("⛔ ④ **«갭»만이 «아니라» 「피벗 «위» 진입 «전부»」**를 잘랐다(원전이 「갭」이라 했다)")
    P("⛔ ⑤ **«추격» «손절» 폭과 «다른» 것**이다(유형 67)")
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
