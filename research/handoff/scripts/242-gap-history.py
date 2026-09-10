# -*- coding: utf-8 -*-
r"""242 - **「과거 3~6개월 «갭 다운» 이력이 «있던» 종목을 «빼면»」** (조사 세션 2026-09-09)

  사전등록: results/242-PRE.md  (값 보기 «전»에 박음)
  원전 `rm:14` [Ⓜ] 「과거 3~6개월 이내에 시가에 «큰» 갭 다운이 나타난 적이 있는 종목 … 연쇄 갭 생성기」

  🚨 **«우리»가 «정한» 것 «넷»**: ㉠「큰」=−10%(까닭: `STOP_PCT`) ㉡6개월=126봉 ㉢1회 이상
                                ㉣기준가 = 전일 «종가»
  ⛔ 자리 = **«고친» 자**(달력 6,893) · CI **«둘» 다** · **격자 «없음»**

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/242-gap-history.py
"""
from __future__ import annotations

import importlib.util as _u
import io
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
WARM = Path("D:/stock-data/uspath-warm2")

C1 = chr(0x2460)
CG = chr(0x24BC)
DELTA, MDE_K = 1.23, 2.8016
NBOOT, SEED = 2000, 242242
BLOCKS = ((20, 40), (80, 80))

GAP = -0.10        # ㉠ «우리»가 «정한» 수 — 까닭은 `STOP_PCT = 10.0`
LOOK = 126         # ㉡ 6개월 = 126 거래일
MINCNT = 1         # ㉢ 1회 «이상»
YEARS = tuple(range(1999, 2027))


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


def scan_gaps():
    """(진입일, 종목) -> 「진입 «전» 126봉에 시가 갭 ≤ −10% 가 «있었나»」."""
    flag, short, tot = {}, 0, 0
    for y in YEARS:
        f = WARM / ("uspath_%d.json" % y)
        if not f.exists():
            continue
        d = json.loads(io.open(f, encoding="utf-8").read())
        for r in d.get("trigger_paths") or []:
            po, pc = r.get("pre_o") or [], r.get("pre_c") or []
            n = min(len(po), len(pc))
            tot += 1
            if n < LOOK + 1:
                short += 1
            lo_i = max(1, n - LOOK)
            cnt = 0
            for i in range(lo_i, n):
                a, b = po[i], pc[i - 1]
                if a is None or b is None or b <= 0:
                    continue
                if a / b - 1.0 <= GAP:
                    cnt += 1
                    if cnt >= MINCNT:
                        break
            k = (r["entry_date"], r["code"])
            flag[k] = flag.get(k, False) or (cnt >= MINCNT)
        P("   %d 끝 — 누적 키 %s" % (y, format(len(flag), ",")), flush=True)
    return flag, short, tot


def main():  # noqa: C901
    P("# 242 - **「과거 3~6개월 «갭 다운» 이력이 «있던» 종목을 «빼면»」**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/242-gap-history.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⛔ 사전등록 " + BQ + "results/242-PRE.md" + BQ + " 에 **«먼저»** 박았다")
    P("")
    P(F3)
    P("🚨 **«우리»가 «정한» 것 «넷»** — ㉠「큰」 = **−10%**(까닭: `STOP_PCT = 10.0` — **«새» 수를 «안» 만들려고**)")
    P("   ㉡ **6개월 = 126 거래일**(3~6 중 **«넓은» 쪽**) · ㉢ **1회 «이상»** · ㉣ 기준가 = **전일 «종가»**")
    P("   ⇒ ⛔ **「원전 «그대로» 쟀다」로 «읽으면» «틀린다**")
    P(F3)
    P("")
    P("---")
    P("")

    t0 = time.time()
    CF = OUT / "242-gap.json"
    if CF.exists():
        z = json.loads(CF.read_text(encoding="utf-8"))
        flag = {tuple(k.split("|", 1)): v for k, v in z["flag"].items()}
        short, tot = z["short"], z["tot"]
        P(F3)
        P("   (♻️ 갈무리 " + BQ + "242-gap.json" + BQ + " — 키 %s)" % format(len(flag), ","))
        P(F3)
        t_scan = 0.0
    else:
        P("(warm2 28해를 «훑는» 중 — `pre_o`/`pre_c` 로 «갭»을 «센다** …)", flush=True)
        flag, short, tot = scan_gaps()
        CF.write_text(json.dumps({"flag": {"%s|%s" % k: v for k, v in flag.items()},
                                  "short": short, "tot": tot,
                                  "gap": GAP, "look": LOOK, "mincnt": MINCNT}),
                      encoding="utf-8")
        t_scan = time.time() - t0
        P("")
        P(F3)
        P("   ✅ 훑기 **%.1f 분**(실측) · 경로 **%s** · 키 **%s**"
          % (t_scan / 60.0, format(tot, ","), format(len(flag), ",")))
        P(F3)
    P("")

    P("# 1. **자료 — 「126봉을 «다» 채우나」**(관문 ㈑)")
    P("")
    P(F3)
    P("   경로 **%s** 중 **`pre_*` 가 %d봉 «미만»인 것 = %s**  (**%.2f%%**)"
      % (format(tot, ","), LOOK + 1, format(short, ","), 100.0 * short / max(tot, 1)))
    if short:
        P("   ⚠️ **그 경로는 «있는» 만큼«만» 봤다** — **「갭이 «없다»」로 «기울** 수 있다(보수적)")
    else:
        P("   ✅ **«전부» 채운다**")
    n_true = sum(1 for v in flag.values() if v)
    P("")
    P("   **(진입일, 종목) 키 %s** 중 **갭 이력 «있음» = %s**  (**%.1f%%**)"
      % (format(len(flag), ","), format(n_true, ","), 100.0 * n_true / max(len(flag), 1)))
    P(F3)
    P("")
    P("---")
    P("")

    # ── 팔 ────────────────────────────────────────────────────────────
    CA = OUT / "242-recs.json"
    t1 = time.time()
    if CA.exists():
        recs = [tuple(x) for x in json.loads(CA.read_text(encoding="utf-8"))]
        t_build = 0.0
    else:
        P("(팔을 «짓는» 중 …)", flush=True)
        pairs, miss = m201d.build_pairs(m201d.CANON)
        if pairs is None:
            P("🚨 경로 «없음»: %s" % miss[:3])
            return 1
        recs = []
        for t, p in pairs:
            r = t["masks"][()]
            epx = t["entry_px"]
            net = sum(fr * r91.sl.net(round(px / epx * 100 - 100, 2))
                      for _d, fr, px in r["exits"])
            dd, rd = p["d"], r["resolve_date"]
            hold = dd.index(rd) if (rd and rd in dd) else len(dd) - 1
            recs.append((t["entry_date"], max(1, hold), net, p["code"]))
        CA.write_text(json.dumps([list(x) for x in recs]), encoding="utf-8")
        t_build = time.time() - t1
        P("   ✅ 팔 짓기 **%.1f 분**(실측) · 거래 **%s**"
          % (t_build / 60.0, format(len(recs), ",")), flush=True)
    P("")

    base = [(d, h, n) for d, h, n, _c in recs]
    miss_k = sum(1 for d, _h, _n, cd in recs if (d, cd) not in flag)
    arm = [(d, h, n) for d, h, n, cd in recs if not flag.get((d, cd), False)]

    P("# 2. **팔 크기 · «양성» 대조**")
    P("")
    P(F3)
    P("   **① 현행 거래 = %s**" % format(len(base), ","))
    P("   **%s 「갭 이력 «있는» 종목」을 «뺀» 거래 = %s**  (**%.1f%%**가 «남는다**)"
      % (CG, format(len(arm), ","), 100.0 * len(arm) / len(base)))
    P("   **★ ① «에만» = %s** · **%s «에만» = 0**(구성상) ⇒ ✅ **%s ⊂ ①**"
      % (format(len(base) - len(arm), ","), CG, CG))
    P("   ⚠️ **`flag` 에 «없는» 거래 = %s** — **「갭 «없음»」으로 «두었다**(보수적)" % format(miss_k, ","))
    P("")
    keep = 100.0 * len(arm) / len(base)
    P("   ★ **«예상»(⛔ 팔 크기를 «찍은» «뒤»에 적는다)**: **%.1f%% 가 «남는다**" % keep)
    if keep >= 90:
        P("      ⇒ **`236`(96.3% 남김 · MDE÷Δ 3.34~3.90)에 «가깝다** ⇒ **Ⓥ 무리** 쪽을 «본다**")
    elif keep <= 50:
        P("      ⇒ **`237`(39.3% 남김 · MDE÷Δ 8.48~9.18)에 «가깝다** ⇒ **Ⓤ 무리** 쪽을 «본다**")
    else:
        P("      ⇒ **`236`(96.3%)와 `237`(39.3%) «사이»**다 ⇒ **«둘» 사이 어디쯤**을 «본다**")
    P("   ⛔ **«수»로 «옮기지» 않는다** — **«맞대는» 데만**")
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
    built = {C1: base, CG: arm}

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
    P("# 3. **팔의 «절대» 값**(연환산 %p)")
    P("")
    P(F3)
    for k in built:
        P("   %-3s **%+.3f%%p/해**  ·  슬롯 «얻은» 것 **%s** / %s"
          % (k, o[k], format(got[k], ","), format(len(built[k]), ",")))
    P("   **%s − %s = %+.3f%%p**  ·  날짜 자리 **%s**" % (CG, C1, obsd, format(n_pos, ",")))
    P(F3)
    P("")
    P("---")
    P("")

    ia = {k: defaultdict(list) for k in built}
    for k, lst in built.items():
        for j, (d, _h, _n) in enumerate(lst):
            ia[k][pos[d]].append(j)

    P("# 4. **판정** — CI **«둘» 다**")
    P("")
    P("| 블록 | 점추정 | **백분위 CI** | 칸 | **기본 CI** | 칸 | **MDE** | MDE÷Δ | 편향 |")
    P("|---|---:|---:|:--|---:|:--|---:|---:|---:|")
    t2 = time.time()
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
        cells.append((cp, cb, MDE_K * sd / DELTA))
        P("| **%d~%d** | **%+.3f%%p** | [%+.3f, %+.3f] | %s | [%+.3f, %+.3f] | %s | **%.3f** | %.2f | %+.3f |"
          % (bmn, bmx, obsd, lo, hi, cp, blo, bhi, cb, MDE_K * sd, MDE_K * sd / DELTA,
             (lo + hi) / 2.0 - obsd), flush=True)
    t_boot = time.time() - t2
    P("")
    P(F3)
    P("   백분위 칸 = %s  ·  기본 칸 = %s"
      % (" · ".join(c[0] for c in cells), " · ".join(c[1] for c in cells)))
    P("")
    pc = {c[0] for c in cells}
    if pc == {"**5**"}:
        P("⇒ ③ **«빼도» «못» 가린다** ⇒ **§B 에 「봤는데 «못» 가렸다」로 «오른다**")
    elif pc == {"**1**"}:
        P("⇒ ① **Ⓖ 가 «위»로** — 「«연쇄 갭 생성기»를 «빼는» 게 «낫다」 ⇒ **원전 쪽이 «일한다**")
    elif pc == {"**2**"}:
        P("⇒ ② **Ⓖ 가 «아래»로** — 「빼면 «해»다」")
    else:
        P("⇒ 🚨 **블록마다 «다르다** — **「몇 중 몇」**으로 «그대로** 적는다")
    P("")
    md = st.mean([c[2] for c in cells])
    P("   ★ **MDE÷Δ = %.2f** — 견줌: `236`(96.3%% 남김) **3.34~3.90** · `237`(39.3%%) **8.48~9.18**" % md)
    P("   ⇒ **`224` 대로 「«얼마나» «겹치나»」로 «갈린다**")
    P(F3)
    P("")
    P("---")
    P("")
    P("# 💰 **실측**")
    P("")
    P(F3)
    P("   warm2 훑기 **%s** · 팔 짓기 **%s** · 부트 2×%d **%.1f 분**"
      % (("%.1f 분" % (t_scan / 60.0)) if t_scan else "(갈무리)",
         ("%.1f 분" % (t_build / 60.0)) if t_build else "(갈무리)", NBOOT, t_boot / 60.0))
    P("   ⚠️ **어림은 「≈20분」이었다** — 위가 **«실측»**이다")
    P(F3)
    P("")
    P("# ⚠️ **이 판이 «못» 하는 것**")
    P("")
    P(F3)
    P("⛔ ① **「«큰»」의 «수»(−10%%)가 «우리» 것**이다 ⇒ **「원전이 «옳다»」로 «못** 간다")
    P("⛔ ② **«우리»가 «정한» 것이 «넷»**(㉠~㉣) — `242-PRE.md` §2 «표»")
    P("⛔ ③ **격자를 «안** 돌렸다 — **−10%% «한» 값 · 6개월 «하나» · 1회 «이상»**«만**")
    P("⛔ ④ **`flag` 에 «없는» 거래는 「갭 «없음»」으로 «뒀다** — **보수적**이나 **«기울** 수 있다")
    P("⛔ ⑤ **팔은 현행 관문 «통과»분**(`CANON`)«만** — **«다른» 유니버스는 «안** 봤다")
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
