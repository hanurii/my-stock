# -*- coding: utf-8 -*-
r"""233 - **`201d` 를 (A)로 «고쳐» «다시» 잰다** (조사 세션 2026-09-08)

  사전등록: results/233-PRE.md  ·  «전» 갈무리: results/233a-snapshot.md
  ⛔ **원본 `201d-rs-threshold.py` 는 «건드리지» 않는다** - 여기서 **«읽기»만** 한다.

  🔧 (A) = `23c` «원형»으로 «되돌리기**  (편집 넷)
     E1  cal = sorted({d for p in <paths> for d in p["d"]} | {entry_dates})   <- 23c:71 모양
     E2  hold = pos_cal[resolve_date] - pos_cal[entry_date]                   <- 23c:103 모양
     E3  all_d = cal  (pos·n_pos 따라감)
     E4  캐시 **이름을 바꾸고**(201d-arms2.json) **cal 을 «같이» 담는다**

  🚨 블록(20~40 · 80~80)의 «뜻»도 「진입일」 -> 「거래일」로 «바뀐다** - 그것도 «적는다**.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/233-201d-fixed.py
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

C1 = chr(0x2460)          # ①
CR = chr(0x211D)          # ℝ
DELTA, MDE_K = 1.23, 2.8016
NBOOT, SEED = 2000, 201201
BLOCKS = ((20, 40), (80, 80))

# «전» 갈무리(233a) - **「전/후 나란히」 자리에서«만** 쓴다
BEFORE = {"n_pos": 3723, "n1": 5951, "nR": 7680,
          (20, 40): (2.943, -5.723, 7.052, 9.040, "5"),
          (80, 80): (2.943, -5.591, 6.264, 8.515, "5")}


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


m201d = _load("m201d", "201d-rs-threshold.py")
r91 = m201d.r91


def boot_eq_count(by_pos, n_pos, slots=5):
    """220:92-111 «그대로» + 슬롯을 «얻은» 수를 «센다»."""
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
    P("# 233 - **`201d` 를 (A)로 «고쳐» «다시» 잰다**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/233-201d-fixed.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⛔ 사전등록 " + BQ + "results/233-PRE.md" + BQ + " · «전» 갈무리 "
      + BQ + "results/233a-snapshot.md" + BQ)
    P("> ⛔ **원본 " + BQ + "201d-rs-threshold.py" + BQ + " 는 «건드리지» 않았다**")
    P("")
    P("---")
    P("")

    CA2 = Path(str(r91.OUT / "201d-arms2.json"))
    t_build = 0.0
    if CA2.exists():
        d_ = json.loads(CA2.read_text(encoding="utf-8"))
        cal = d_["cal"]
        built = {k: [tuple(x) for x in v] for k, v in d_["arms"].items()}
        P(F3)
        P("   (♻️ 갈무리 " + BQ + "201d-arms2.json" + BQ + " — 팔 %d · 달력 %s)"
          % (len(built), format(len(cal), ",")))
        P(F3)
    else:
        P(F3)
        P("   자료를 «짓는다** — ① " + str(m201d.CANON))
        P("                    " + chr(0x211D) + " " + str(m201d.RS70))
        P(F3, flush=True)
        t0 = time.time()
        p80, miss = m201d.build_pairs(m201d.CANON)
        if p80 is None:
            P("🚨 ① 경로 «없음»: %s" % miss[:3])
            return 1
        p70, miss = m201d.build_pairs(m201d.RS70)
        if p70 is None:
            P("🚨 " + chr(0x211D) + " 경로 «없음»: %s" % miss[:3])
            return 1
        # ── E1: 달력을 «짓는다**(23c:71 모양) ──────────────────────────
        cal_s = set()
        for _t, p in (p80 + p70):
            cal_s.update(p["d"])
        for t, _p in (p80 + p70):
            cal_s.add(t["entry_date"])
        cal = sorted(cal_s)
        posc = {d: i for i, d in enumerate(cal)}

        # ── E2: 보유를 «자리» 차로 ────────────────────────────────────
        def trades2(t, p):
            r = t["masks"][()]
            epx = t["entry_px"]
            net = sum(fr * r91.sl.net(round(px / epx * 100 - 100, 2))
                      for _d, fr, px in r["exits"])
            rd = r["resolve_date"]
            e = posc[t["entry_date"]]
            x = posc[rd] if (rd and rd in posc) else posc[p["d"][-1]]
            return (t["entry_date"], max(1, x - e), net)

        built = {C1: [trades2(t, p) for t, p in p80],
                 CR: [trades2(t, p) for t, p in p70]}
        # ── E4: 이름을 «바꾸고» cal 을 «같이» 담는다 ───────────────────
        CA2.write_text(json.dumps({"cal": cal,
                                   "arms": {k: [list(x) for x in v] for k, v in built.items()}}),
                       encoding="utf-8")
        t_build = time.time() - t0
        P("")
        P(F3)
        P("   ✅ 자료 짓기 **%.1f 분**(실측) · 달력 **%s** 일 · 캐시 " % (t_build / 60.0,
                                                                format(len(cal), ",")) + BQ
          + "201d-arms2.json" + BQ)
        P(F3)
    P("")

    # ── E3: 얼개 ──────────────────────────────────────────────────────
    pos = {d: i for i, d in enumerate(cal)}
    n_pos = len(cal)
    idx_at = {k: defaultdict(list) for k in built}
    for k, lst in built.items():
        for j, (d, _h, _n) in enumerate(lst):
            idx_at[k][pos[d]].append(j)

    P("# 1. **«전» / «후» — 얼개**")
    P("")
    P(F3)
    P("| | «전»(진입일 자리) | **«후»(모든 거래일)** |")
    P("|---|---:|---:|")
    P("| 날짜 «자리» 수 | %s | **%s** |"
      % (format(BEFORE["n_pos"], ","), format(n_pos, ",")))
    P("| ① 거래 수 | %s | **%s** |" % (format(BEFORE["n1"], ","), format(len(built[C1]), ",")))
    P("| %s 거래 수 | %s | **%s** |"
      % (CR, format(BEFORE["nR"], ","), format(len(built[CR]), ",")))
    P("")
    P("   🚨 **블록(20~40 · 80~80)의 «뜻»도 「진입일」 → 「거래일」로 «바뀌었다**")
    P("      ⇒ ⛔ **«전»과 «똑같은» 것을 «재는» 게 «아니다** — 「«규약»대로」로 «돌아간» 것이다")
    P(F3)
    P("")

    def obs(lst):
        bp = defaultdict(list)
        for d, h, nt in lst:
            bp[pos[d]].append((h, nt, 0))
        return boot_eq_count(bp, n_pos)

    o, got = {}, {}
    for k, v in built.items():
        e, g = obs(v)
        o[k] = m201d.ann(e)
        got[k] = g
    obsd = o[CR] - o[C1]

    P("# 2. **슬롯을 «얻은» 건수** — «전» / «후»")
    P("")
    P(F3)
    P("   ⛔ «전» 수치는 **`232c` 가 `231b` 자료로 «잰» 것**이라 — **`201d` 의 «전»은 «없다**")
    P("      ⇒ ✅ 그래서 **«옛» 얼개로도 «여기»서 «같이» 잰다**(같은 팔·같은 자료)")
    old_pos = sorted({d for lst in built.values() for d, _h, _n in lst})
    op = {d: i for i, d in enumerate(old_pos)}

    def obs_old(lst, holds):
        bp = defaultdict(list)
        for (d, _h, nt), ho in zip(lst, holds):
            bp[op[d]].append((ho, nt, 0))
        return boot_eq_count(bp, len(old_pos))
    P("")
    P("| 팔 | «후»(자리 차 보유) | 거래 수 | 얻은 비율 |")
    P("|---|---:|---:|---:|")
    for k in (C1, CR):
        P("| %s | **%d** | %s | %.1f%% |"
          % (k, got[k], format(len(built[k]), ","), 100.0 * got[k] / len(built[k])))
    P("")
    P("   ⚠️ **「«전»의 얻은 건수」는 «못» 낸다** — «옛» 캐시의 hold 는 **「거래일」**이고")
    P("      **«옛» 자리(진입일)와 «짝»**인데, **여기 built 는 «새» 보유**다(섞으면 «틀린다**)")
    P("      ⇒ ⛔ **「몇 배 늘었다」를 «적지» «않는다**")
    P(F3)
    P("")
    P("---")
    P("")

    P("# 3. **팔의 «절대» 값**(연환산 %p)")
    P("")
    P(F3)
    for k in (C1, CR):
        P("   %-4s **%+.3f%%p/해**" % (k, o[k]))
    P("   %s − %s = **%+.3f%%p**" % (CR, C1, obsd))
    P(F3)
    P("")
    P("---")
    P("")

    P("# 4. ★★★ **판정 — «전» / «후» «나란히»**")
    P("")
    t1 = time.time()
    P("| 블록 | | 점추정 | 95%% CI | CI폭 | **MDE** | MDE÷Δ | 편향 | 판정칸 |")
    P("|---|---|---:|---:|---:|---:|---:|---:|:--|")
    news = {}
    for bi_blk, (bmn, bmx) in enumerate(BLOCKS):
        m201d.BMIN, m201d.BMAX = bmn, bmx
        rnd = random.Random(SEED + bi_blk)
        boots = []
        for bi in range(NBOOT):
            order = m201d.draw(n_pos, rnd)
            eqs = {}
            for k, lst in built.items():
                bp = defaultdict(list)
                ia = idx_at[k]
                for newp, oldp in enumerate(order):
                    for j in ia.get(oldp, ()):
                        _d, h, nt = lst[j]
                        bp[newp].append((h, nt, 0))
                eqs[k] = m201d.ann(boot_eq_count(bp, n_pos)[0])
            boots.append(eqs[CR] - eqs[C1])
            if (bi + 1) % 250 == 0:
                P("  [%d~%d] 부트 %d/%d" % (bmn, bmx, bi + 1, NBOOT), flush=True)
        v = sorted(boots)
        lo, hi = v[int(NBOOT * .025)], v[int(NBOOT * .975)]
        sd = st.stdev(boots)
        mde = MDE_K * sd
        mid = (lo + hi) / 2.0
        cell = cell_of(lo, hi)
        news[(bmn, bmx)] = (obsd, lo, hi, mde, cell)
        b = BEFORE[(bmn, bmx)]
        P("| **%d~%d** | «전» | %+.3f | [%+.3f, %+.3f] | %.2f | %.3f | %.2f | — | **%s** |"
          % (bmn, bmx, b[0], b[1], b[2], b[2] - b[1], b[3], b[3] / DELTA, b[4]))
        P("| | **«후»** | **%+.3f** | [%+.3f, %+.3f] | %.2f | **%.3f** | %.2f | %+.3f | %s |"
          % (obsd, lo, hi, hi - lo, mde, mde / DELTA, mid - obsd, cell), flush=True)
    t_boot = time.time() - t1
    P("")

    P(F3)
    P("## 🎯 **사전등록 «둘» 중 «어느» 쪽인가**")
    P("")
    downs = [(k, BEFORE[k][3], news[k][3]) for k in news]
    ndown = sum(1 for _k, a, b in downs if b < a)
    for k, a, b in downs:
        P("   블록 %-7s MDE  %.3f → **%.3f**   (%s %.1f%%)"
          % ("%d~%d" % k, a, b, "↓" if b < a else "↑", abs(b - a) / a * 100.0))
    P("")
    P("   ★ **%d 블록 «중» %d** 에서 **MDE 가 «내려갔다**" % (len(downs), ndown))
    cells_same = all(news[k][4].strip("*") == BEFORE[k][4] for k in news)
    P("   ★ 판정칸: %s"
      % ("**«둘» 다 «그대로»**" if cells_same else "🚨 **«바뀌었다**"))
    P("")
    if ndown == len(downs) and not cells_same:
        P("⇒ ✅ **사전등록 ①** — MDE 가 «내려갔고» 판정이 «바뀌었다**")
        P("   ⇒ **§B 가 «줄고» 「길이 «열린다»」** ⇒ **나머지 13 을 «돌릴» «근거»가 «생겼다**")
    elif ndown == len(downs) and cells_same:
        P("⇒ 🟡 **«사이»** — **MDE 는 «내려갔으나» «판정»은 «그대로»**다")
        P("   ⇒ ⛔ 「길이 «열린다»」로 **«읽지» «않는다** — **«내려간» «크기»를 «적고» 「나머지 13」은 «묻는다**")
    elif ndown == 0:
        P("⇒ 🔴 **사전등록 ②** — **MDE 가 «안» 내려갔다**")
        P("   ⇒ **「단위는 «결함»이었으나 «결론»은 «안» 바뀐다」** ⇒ **나머지 13 은 «위생»으로«만**")
    else:
        P("⇒ 🟡 **«셋째» 갈래** — **블록마다 «다르다**. **「몇 중 몇」**으로 «그대로» 적었다")
    P(F3)
    P("")
    P("---")
    P("")

    P("# 5. 💰 **실측**")
    P("")
    P(F3)
    P("   자료 짓기 **%s**" % ("%.1f 분" % (t_build / 60.0) if t_build else "(갈무리 씀 — «안» 쟀다)"))
    P("   부트 2×%d  **%.1f 분**" % (NBOOT, t_boot / 60.0))
    P("   합         **%.1f 분**   ⟵  «전» `201d` 는 **5.4 분**" % ((t_build + t_boot) / 60.0))
    P("")
    P("   ⛔ **«전» 5.4분은 「묘사 셋」까지 «넷» 팔을 «잰» 값**이고 —")
    P("      **여기는 «판정» 짝 «하나»**다. ⇒ **«곧장» 견주면 «틀린다**")
    P(F3)
    P("")
    P("---")
    P("")
    P("# ⚠️ **이 판이 «못» 하는 것**")
    P("")
    P(F3)
    P("⛔ ① **묘사 셋(VCP·3C·PP)은 «안** 쟀다 — **판정 짝 «하나»**만")
    P("⛔ ② **「«전»의 슬롯 얻은 건수」는 «없다** — «옛» 캐시의 보유는 «다른» 뜻이라 **«못» 섞는다**")
    P("⛔ ③ **블록의 «뜻»이 «바뀌었다** ⇒ **«전»과 «똑같은» 것을 «잰» 게 «아니다**")
    P("⛔ ④ **이 판은 `201d` «하나»**다 — **나머지 13 은 «다를» 수 «있다**")
    P("⛔ ⑤ **양성 대조는 «아직»** — 관문 ②(단위 고침이 «관문»을 «살렸나»)는 **«다음»**이다")
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
