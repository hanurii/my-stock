# -*- coding: utf-8 -*-
r"""232 - is our ruler able to SEE an effect at all?  (조사 세션 2026-09-08)

  사전등록: results/232-PRE.md  (값 보기 «전»에 박음)
  순서: §1 계산 검산 -> (§1b 편향찍기는 232a) -> §2 양성+음성 대조 -> §3 기전
  읽는 것: 캐시 231-arms.json «하나». 정본·uspath-* 는 «열지» 않는다.

  🔧 검증 반론 반영: 보태는 값 b 는 **«거래당» net** 이고 - 연환산 «문턱»에 «닿도록» «푼다».
      문턱 둘 = MDE 의 «두» 배 · MDE 의 «절반»  (MDE 는 231b 20~40 의 5.393%p)

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/232-instrument-check.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
HERE = Path(__file__).resolve().parent

C1 = chr(0x2460)          # circled 1
CL = chr(0x24C1)          # circled L
CE = chr(0x24BA)          # circled E
CG = chr(0x24BC)          # circled G
T1 = chr(0x3260)          # parenthesized-like marker for threshold 1
T2 = chr(0x3261)
DELTA, MDE_K = 1.23, 2.8016
NBOOT, SEED = 2000, 231231
BLOCKS = ((20, 40), (80, 80))
MDE_REF = 5.393           # 231b 20~40 - «다른» 판은 «다르다»
B_CAP = 400.0             # b 탐색 상한


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


r91 = _load("r91", "91-us-out-of-sample.py")
m220 = _load("m220", "220-fa-four.py")


def boot_eq_count(by_pos, n_pos, slots=5):
    """220:92-111 «그대로» + 슬롯을 «얻은» 것의 tag 를 «센다»(_k 자리는 원래 «안» 쓰인다)."""
    eq, held = 1.0, []
    got = defaultdict(int)
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
                got[_k] += 1
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
    P("# 232 - **«자»가 «효과»를 «볼 수» 있나**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/232-instrument-check.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⛔ 사전등록 " + BQ + "results/232-PRE.md" + BQ + " 에 **«먼저»** 박았다 · 편향찍기는 "
      + BQ + "232a" + BQ)
    P("")
    P("---")
    P("")

    CA = Path(str(r91.OUT / "231-arms.json"))
    if not CA.exists():
        P("🚨 캐시가 «없다» - 멈춘다: %s" % CA)
        return 1
    d_ = json.loads(CA.read_text(encoding="utf-8"))
    base = [tuple(x) for x in d_["base"]]
    extra = [tuple(x) for x in d_["extra"]]
    P(F3)
    P("   읽은 것 " + BQ + str(CA) + BQ + "  (**%s bytes**)" % format(CA.stat().st_size, ","))
    P("   base **%s** · extra **%s**" % (format(len(base), ","), format(len(extra), ",")))
    P(F3)
    P("")

    all_d = sorted({d for d, _h, _n in (base + extra)})
    pos = {d: i for i, d in enumerate(all_d)}
    n_pos = len(all_d)

    def mk(lst, tg):
        ia = defaultdict(list)
        for j, (d, _h, _n) in enumerate(lst):
            ia[pos[d]].append(j)
        return (lst, tg, ia)

    def bp_of(arm, order):
        lst, tg, ia = arm
        bp = defaultdict(list)
        for newp, oldp in enumerate(order):
            for j in ia.get(oldp, ()):
                _d, h, nt = lst[j]
                bp[newp].append((h, nt, tg[j]))
        return bp

    def obs_bp(arm):
        lst, tg, _ia = arm
        bp = defaultdict(list)
        for j, (d, h, nt) in enumerate(lst):
            bp[pos[d]].append((h, nt, tg[j]))
        return bp

    TB = [0] * len(base)
    TE = [0] * len(base) + [1] * len(extra)
    A_base = mk(base, TB)
    A_g0 = mk(base + extra, TE)

    def val(arm):
        return m220.ann(boot_eq_count(obs_bp(arm), n_pos)[0])

    o_base = val(A_base)
    o_g0 = val(A_g0)

    # -- 1. 계산 검산 ---------------------------------------------------
    P("# 1. **«계산» 오류인가** - «항등» 검산")
    P("")
    P(F3)
    P("자: 부트의 자리 뽑기를 **order = [0,1,...,n_pos-1]**(항등)로 놓으면")
    P("    부트 경로가 " + BQ + "obs()" + BQ + " 와 **«같은» 값**을 내야 한다.")
    P("")
    ident = list(range(n_pos))
    ok_all = True
    for nm, arm in ((C1, A_base), (CG + "0", A_g0)):
        a = m220.ann(boot_eq_count(obs_bp(arm), n_pos)[0])
        b = m220.ann(boot_eq_count(bp_of(arm, ident), n_pos)[0])
        same = abs(a - b) < 1e-9
        ok_all = ok_all and same
        P("   %-3s  obs = %+.9f   ·  boot(항등) = %+.9f   ⇒ %s"
          % (nm, a, b, "✅ «같다»" if same else "🔴 «다르다»"))
    P("")
    P("   %s0 − %s (관측 차) = **%+.3f%%p**   <- 231b 는 **-3.690%%p**  ⇒ %s"
      % (CG, C1, o_g0 - o_base,
         "✅ «재현»" if abs((o_g0 - o_base) + 3.690) < 0.01 else "🔴 **«재현» «안» 됨**"))
    P("")
    if ok_all:
        P("✅ **두 경로가 «같은» 함수·«같은» 자료다** ⇒ 「점추정이 CI 밖」은 **«계산» 오류가 «아니다**")
        P("   ⛔ 이것이 «말하는» 것은 **«경로»가 같다는 것뿐**이다 - **부트 «분포»가 «어디» 앉는지는 §2**")
    else:
        P("🔴 **«다르다» - «여기»서 «멈춘다**. 아래는 «돌리지» 않는다(사전등록 §1)")
    P(F3)
    P("")
    if not ok_all:
        return 0
    P("---")
    P("")

    # -- 2. b 를 «푼다» -------------------------------------------------
    P("# 2. **«거래당» b 를 «푼다** - 연환산 «문턱»에 «닿도록**")
    P("")
    P(F3)
    P("🚨 **b 는 «내»가 «푼» «가짜» 수**다 - 원전·자료와 **«무관»**하다.")
    P("   문턱: **MDE = %.3f%%p**(231b 20~40) ⇒ **%s 두 배 = %+.3f** · **%s 절반 = %+.3f**"
      % (MDE_REF, T1, 2 * MDE_REF, T2, 0.5 * MDE_REF))
    P("   모양: **%s «수준»** = base+extra 의 **«모든»** net +b   ·   "
      "**%s «덧붙임»** = extra %s 건«만» net +b" % (CL, CE, format(len(extra), ",")))
    P("")

    def eff_level(b):
        return val(mk([(d, h, nt + b) for d, h, nt in (base + extra)], TE)) - o_base

    def eff_extra(b):
        return val(mk(base + [(d, h, nt + b) for d, h, nt in extra], TE)) - o_base

    def solve(f, target):
        top = f(B_CAP)
        if top < target:
            return None, top
        lo, hi = 0.0, B_CAP
        for _ in range(50):
            mid = (lo + hi) / 2.0
            if f(mid) < target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0, f((lo + hi) / 2.0)

    plan = []
    for nm, fn in ((CL, eff_level), (CE, eff_extra)):
        for tn, tgt in ((T1, 2 * MDE_REF), (T2, 0.5 * MDE_REF)):
            b, got = solve(fn, tgt)
            if b is None:
                P("   🚨 **%s%s — b 를 «못» 푼다**: b=%.0f 에서도 효과 %+.3f%%p < 문턱 %+.3f"
                  % (nm, tn, B_CAP, got, tgt))
                plan.append((nm + tn, None, got, tgt))
            else:
                P("   **%s%s**  b = **%+.4f** (거래당 %%p) ⇒ 효과 **%+.3f%%p**(문턱 %+.3f)"
                  % (nm, tn, b, got, tgt))
                plan.append((nm + tn, b, got, tgt))
    P(F3)
    P("")
    P("---")
    P("")

    # -- 3. 부트 ---------------------------------------------------------
    P("# 3. **판정** - «가짜» 효과를 자가 «보나**")
    P("")
    arms = {CG + "0": A_g0}
    for nm, b, _g, _t in plan:
        if b is None:
            continue
        if nm.startswith(CL):
            arms[nm] = mk([(d, h, nt + b) for d, h, nt in (base + extra)], TE)
        else:
            arms[nm] = mk(base + [(d, h, nt + b) for d, h, nt in extra], TE)
    o = {k: val(v) for k, v in arms.items()}

    P("| 팔 | **점추정** | **95%% CI** | CI폭 | CI«중앙» | **편향** | |편향|/SD | 점추정 CI«안»? | 판정칸 |")
    P("|---|---:|---:|---:|---:|---:|---:|:--|:--|")
    res = defaultdict(list)
    for bi_blk, (bmn, bmx) in enumerate(BLOCKS):
        m220.BMIN, m220.BMAX = bmn, bmx
        rnd = random.Random(SEED + bi_blk)
        acc = {k: [] for k in arms}
        for bi in range(NBOOT):
            order = m220.draw(n_pos, rnd)
            eb = m220.ann(boot_eq_count(bp_of(A_base, order), n_pos)[0])
            for k, arm in arms.items():
                acc[k].append(m220.ann(boot_eq_count(bp_of(arm, order), n_pos)[0]) - eb)
            if (bi + 1) % 250 == 0:
                P("  [%d~%d] 부트 %d/%d" % (bmn, bmx, bi + 1, NBOOT), flush=True)
        for k in arms:
            v = sorted(acc[k])
            lo, hi = v[int(NBOOT * .025)], v[int(NBOOT * .975)]
            sd = st.stdev(acc[k])
            mid = (lo + hi) / 2.0
            obsd = o[k] - o_base
            bias = mid - obsd
            cell = cell_of(lo, hi)
            res[k].append(cell)
            P("| **%s** %d~%d | **%+.3f%%p** | [%+.3f, %+.3f] | %.2f | %+.3f | **%+.3f** | **%.2f** | %s | %s |"
              % (k, bmn, bmx, obsd, lo, hi, hi - lo, mid, bias, abs(bias) / sd if sd else 0,
                 "✅ 안" if lo <= obsd <= hi else "🚨 **밖**", cell), flush=True)
    P("")

    P(F3)
    for k in arms:
        P("   **%s** 판정칸 = %s" % (k, " · ".join(res[k])))
    P("")
    hi_cells = set(res.get(CL + T1, [])) | set(res.get(CE + T1, []))
    lo_cells = set(res.get(CL + T2, [])) | set(res.get(CE + T2, []))
    hi_split = bool(hi_cells) and hi_cells <= {"**1**", "**2**"}
    lo_split = bool(lo_cells) and lo_cells <= {"**1**", "**2**"}
    if hi_split and not lo_split:
        P("⇒ ① **두 배는 «갈랐고» 절반은 «못» 갈랐다** ⇒ ✅ **관문이 «살았고» «분해능»도 «맞다**")
    elif (not hi_split) and (not lo_split):
        P("⇒ ② **«둘» 다 «못» 갈랐다** 🚨🚨 ⇒ **판정칸 5 는 「«언제나» 통과하는 관문」**(유형 ㊁·63)")
        P("   ⛔ 그래도 **「«전부» «틀렸다»」가 «아니라 「«판정»을 «다시» 해야 한다」**이다")
    elif hi_split and lo_split:
        P("⇒ ③ **«둘» 다 «갈랐다** 🟡 ⇒ **«너무» 민감 — MDE 가 «과대»평가돼 있다**")
    else:
        P("⇒ 🚨 **사전등록에 «없는» 모양** - **«그대로» 적는다**")
    lc = set(res.get(CL + T1, []))
    ec = set(res.get(CE + T1, []))
    if lc and ec and (lc <= {"**1**", "**2**"}) and not (ec <= {"**1**", "**2**"}):
        P("⇒ ④ **%s(수준)은 «갈랐고» %s(덧붙임)은 «못» 갈랐다** 🚨" % (CL, CE))
        P("   ⇒ **팔을 «더하는» 판(231b·227b·218·201d)의 칸 5 가 «다시» 읽혀야** 한다")
    if any(b is None and nm.startswith(CE) for nm, b, _g, _t in plan):
        P("⇒ ⑤ **%s 는 «어떤» b 로도 문턱에 «못» 닿았다** 🚨🚨" % CE)
        P("   ⇒ **271 건«만»으로는 «구조»상 «못» 움직인다** — `231b` 는 「효과가 «없다»」가 «아니라")
        P("      **「«볼 수» «없다»」**였다")
    P(F3)
    P("")
    P("---")
    P("")

    # -- 4. 기전 --------------------------------------------------------
    P("# 4. **기전** - «덧붙인» 것이 «슬롯»을 «얻나**")
    P("")
    _e, g_obs = boot_eq_count(obs_bp(A_g0), n_pos)
    A_obs, B_obs = g_obs[1], g_obs[0]
    m220.BMIN, m220.BMAX = BLOCKS[0]
    rnd = random.Random(SEED)
    A_b, B_b = [], []
    for bi in range(NBOOT):
        order = m220.draw(n_pos, rnd)
        _v, g = boot_eq_count(bp_of(A_g0, order), n_pos)
        A_b.append(g[1])
        B_b.append(g[0])
        if (bi + 1) % 500 == 0:
            P("  [기전] 부트 %d/%d" % (bi + 1, NBOOT), flush=True)
    A_med, B_med = st.median(A_b), st.median(B_b)
    ra = A_med / A_obs if A_obs else float("nan")
    rb = B_med / B_obs if B_obs else float("nan")
    R = ra / rb if rb else float("nan")
    n_half = sum(1 for x in A_b if x < A_obs / 2.0)
    P(F3)
    P("   **A_obs**(관측에서 슬롯을 «얻은» extra) = **%s** / 덧붙은 **%s**"
      % (format(A_obs, ","), format(len(extra), ",")))
    P("   **B_obs**(관측에서 슬롯을 «얻은» base)  = **%s** / base **%s**"
      % (format(B_obs, ","), format(len(base), ",")))
    P("   **A_boot 중앙값** = **%.1f** (비 %.3f)  ·  **B_boot 중앙값** = **%.1f** (비 %.3f)"
      % (A_med, ra, B_med, rb))
    P("   ★ **R = %.3f**  ·  **2000 «중» %s** 가 A_obs 의 «절반» 아래" % (R, format(n_half, ",")))
    P("")
    if R < 0.7:
        P("⇒ ① **R < 0.7** - 「재표집이 «덧붙임»«만» «굶긴다»」")
    elif 0.9 <= R <= 1.1:
        P("⇒ ② **0.9 <= R <= 1.1** - 🔴 **«내» 가설이 «틀렸다**. 포화는 «대칭»이고 **«모른다»로 «남긴다**")
    else:
        P("⇒ ③ **사이** - ⛔ 「가른다」로 **«읽지» «않는다**")
    P(F3)
    P("")
    P("---")
    P("")
    P("# ⚠️ **이 판이 «못» 하는 것**")
    P("")
    P(F3)
    P("⛔ ① **b 는 «내»가 «푼» «가짜» 수**다 - 원전·자료와 «무관»하다")
    P("⛔ ② 이 판은 **「풀백이 «좋냐»」를 «묻지» 않았다** - " + BQ + "231b" + BQ + " 판정은 **«그대로»**다")
    P("⛔ ③ **«어느» 결과든 「부호가 «있었다»」로 «읽으면» «틀린다**")
    P("⛔ ④ **MDE 5.393 은 " + BQ + "231b" + BQ + " «한» 판의 값**이다 - «다른» 판은 «다르다**")
    P("⛔ ⑤ §4 는 **블록 20~40 «하나»**로만 쟀다 · **이 판의 자료 «하나»**로만 쟀다")
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
