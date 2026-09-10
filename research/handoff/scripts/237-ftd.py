# -*- coding: utf-8 -*-
r"""237 - **「FTD «뒤»에만 사면 어떻게 되나」** (조사 세션 2026-09-08)

  사전등록: results/237-PRE.md  (값 보기 «전»에 박음)
  🚨 **이 판이 «재는» 것은 「원전의 FTD」가 «아니라» — 「«우리»가 «만든» FTD」다.**
     «우리»가 «정한» 것이 **다섯**이고 **넷**에 원전이 «수»를 «주지» 않았다.

  자료: `.cache/spy_volume.json`(거래량 · «새» 파일) ＋ `101-fund-ohlc.json`(SPY 미조정 종가 c_raw)
  자리: **«고친» 자**(달력 6,893) · 팔 갈무리: `236-recs.json`

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/237-ftd.py
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
ROOT = HERE.resolve().parents[2]

C1 = chr(0x2460)
CF = chr(0x24BB)
DELTA, MDE_K = 1.23, 2.8016
NBOOT, SEED = 2000, 237237
BLOCKS = ((20, 40), (80, 80))

# ── «우리»가 «정한» 다섯 (사전등록 §2) ───────────────────────────────
UP_PCT = 1.5          # ㉡ 원전이 «준» 수
DAY_LO, DAY_HI = 3, 7  # ㉡ 원전 «범위» «그대로»
CORR_DD = 0.10        # ㉤ 「조정」 = 52주 최고 종가 대비 −10%  («우리» 수)
LOOK52 = 252          # ㉤ 「52주」                              («우리» 수)


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


def build_allow():
    """날짜 -> 「매수 허용」  (⛔ «그날»까지의 자료«만» — 룩어헤드 «없음»)."""
    vol = json.loads((ROOT / ".cache" / "spy_volume.json").read_text(encoding="utf-8"))["series"]
    px = json.loads((OUT / "101-fund-ohlc.json").read_text(encoding="utf-8"))["SPY"]["series"]
    ds = sorted(d for d in px if d in vol)
    c = [px[d][4] for d in ds]                 # c_raw — 거래량과 «같은» 원천의 «미조정» 종가
    v = [vol[d] for d in ds]
    allow, state = {}, True
    corr_low = None          # 조정 «중»의 «최저» 종가
    corr_low_i = None
    prev_corr = False        # 🔧 «어제»가 조정이었나 — 「진입」은 «전환»으로만 «센다»
    n_ftd = n_corr = 0
    for i, d in enumerate(ds):
        if i == 0:
            allow[d] = state
            continue
        hi52 = max(c[max(0, i - LOOK52 + 1): i + 1])
        in_corr = c[i] <= hi52 * (1.0 - CORR_DD)
        if in_corr and not prev_corr:          # ★ 조정 «진입»(«전환») ⇒ 매수 «금지»
            state = False
            corr_low, corr_low_i = c[i], i
            n_corr += 1
        elif in_corr and (corr_low is None or c[i] < corr_low):
            corr_low, corr_low_i = c[i], i     # «최저»가 «갱신»되면 랠리도 «다시» 센다
        if not state and corr_low_i is not None:
            n = i - corr_low_i + 1             # 랠리 «며칠째»(최저일 = 1)
            up = c[i] / c[i - 1] - 1.0
            if DAY_LO <= n <= DAY_HI and up >= UP_PCT / 100.0 and v[i] > v[i - 1]:
                state = True                   # ★ FTD ⇒ «다음» 조정 «진입»까지 «허용»
                n_ftd += 1
        prev_corr = in_corr
        allow[d] = state
    return allow, ds, n_ftd, n_corr


def main():  # noqa: C901
    P("# 237 - **「FTD «뒤»에만 사면 어떻게 되나」**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/237-ftd.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⛔ 사전등록 " + BQ + "results/237-PRE.md" + BQ + " 에 **«먼저»** 박았다")
    P("")
    P(F3)
    P("🚨 **이 판이 «재는» 것은 「원전의 FTD」가 «아니라» — 「«우리»가 «만든» FTD」다.**")
    P("   **«우리»가 «정한» 것이 «다섯»이고 «넷»에 원전이 «수»를 «주지» «않았다.**")
    P("   ⛔ **«이겨도» 「원전이 «옳다»」로 «못** 간다 · ⛔ **«져도» 「원전이 «틀렸다»」로 «못** 간다")
    P(F3)
    P("")
    P("---")
    P("")

    allow, ds, n_ftd, n_corr = build_allow()
    nal = sum(1 for d in ds if allow[d])
    P("# 1. **«우리»가 «만든» FTD — 얼마나 «켜지나**")
    P("")
    P(F3)
    P("   SPY 날 **%s** (%s ~ %s)" % (format(len(ds), ","), ds[0], ds[-1]))
    P("   「조정」 «진입» **%d 번**(종가 ≤ 52주 최고 × %.2f)" % (n_corr, 1 - CORR_DD))
    P("   **FTD %d 번**(랠리 %d~%d일째 ∧ +%.1f%% 이상 ∧ 거래량 > 전일)"
      % (n_ftd, DAY_LO, DAY_HI, UP_PCT))
    P("   「매수 허용」인 날 **%s / %s = %.1f%%**"
      % (format(nal, ","), format(len(ds), ","), 100.0 * nal / len(ds)))
    P(F3)
    P("")

    recs = [tuple(x) for x in json.loads((OUT / "236-recs.json").read_text(encoding="utf-8"))]
    base = [(d, h, n) for d, h, n, _g in recs]
    miss = sorted({d for d, _h, _n in base if d not in allow})
    arm = [(d, h, n) for d, h, n in base if allow.get(d, True)]
    built = {C1: base, CF: arm}

    P("# 2. **팔 크기 · «양성» 대조**")
    P("")
    P(F3)
    P("   **① 현행(FTD «안» 봄) 거래 = %s**" % format(len(base), ","))
    P("   **%s FTD «허용»일 진입«만» = %s**  (**%.1f%%**가 «남는다**)"
      % (CF, format(len(arm), ","), 100.0 * len(arm) / len(base)))
    P("   **★ ① «에만» = %s** · **%s «에만» = 0**(구성상) ⇒ ✅ **%s ⊂ ①**"
      % (format(len(base) - len(arm), ","), CF, CF))
    P("   ⚠️ SPY 달력에 «없는» 진입일 = **%d**(있으면 「허용」으로 «둔다** — 보수적)" % len(miss))
    P(F3)
    P("")
    P("---")
    P("")

    cal = json.loads((OUT / "201d-arms2.json").read_text(encoding="utf-8"))["cal"]
    ents = {d for d, _h, _n in base}
    if ents - set(cal):
        cal = sorted(set(cal) | ents)
    pos = {d: i for i, d in enumerate(cal)}
    n_pos = len(cal)

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
    obsd = o[CF] - o[C1]
    P("# 3. **팔의 «절대» 값**(연환산 %p)")
    P("")
    P(F3)
    for k in built:
        P("   %-3s **%+.3f%%p/해**  ·  슬롯 «얻은» 것 **%s** / %s"
          % (k, o[k], format(got[k], ","), format(len(built[k]), ",")))
    P("   **%s − %s = %+.3f%%p**  ·  날짜 자리 **%s**" % (CF, C1, obsd, format(n_pos, ",")))
    P(F3)
    P("")
    P("---")
    P("")

    ia = {k: defaultdict(list) for k in built}
    for k, lst in built.items():
        for j, (d, _h, _n) in enumerate(lst):
            ia[k][pos[d]].append(j)

    P("# 4. **판정** — CI 를 **«둘» 다**")
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
            boots.append(eqs[CF] - eqs[C1])
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
    el = time.time() - t1
    P("")
    P(F3)
    P("   백분위 칸 = %s  ·  기본 칸 = %s"
      % (" · ".join(c[0] for c in cells), " · ".join(c[1] for c in cells)))
    P("")
    pc = {c[0] for c in cells}
    if pc == {"**1**"}:
        P("⇒ ① **Ⓕ 가 «위»로 갈라졌다** → **원전이 «맞았다** — 우리 얼개가 «느슨»했다")
    elif pc == {"**2**"}:
        P("⇒ ② **Ⓕ 가 «아래»로 갈라졌다** → **원전과 «어긋난다** — 「최종 «선고»는 «주식»」 쪽")
    elif pc == {"**5**"}:
        P("⇒ ③ **«못» 가린다** ⇒ **§B ⑳ 이 「«못» 잰다」에서 「봤는데 «못» 가렸다」로 «바뀐다**")
    else:
        P("⇒ 🚨 **블록마다 «다르다** — **「몇 중 몇」**으로 «그대로** 적는다")
    P("")
    P("   💰 부트 2×%d **%.1f 분**" % (NBOOT, el / 60.0))
    P(F3)
    P("")
    P("---")
    P("")
    P("# ⚠️ **이 판이 «못» 하는 것**")
    P("")
    P(F3)
    P("⛔ ① **「«우리»가 «만든» FTD」다** — **다섯 중 «넷»에 원전 «수»가 «없다**")
    P("⛔ ② **SPY «하나»**로 「시장」을 삼았다 — 원전은 「«주요» 지수«들»」이라 했다")
    P("⛔ ③ **「조정 −10%%」·「52주」·「거래량 > 전일」은 «우리» 수**다 — ⛔ **격자를 «안** 돌렸다")
    P("⛔ ④ **팔은 `236-recs.json`**(현행 관문 «통과»분) — **«다른» 유니버스는 «안** 봤다")
    P("⛔ ⑤ 받은 자료는 **커밋 «금지**(Sharadar 라이선스) · " + BQ + ".cache/spy_volume.json" + BQ)
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
