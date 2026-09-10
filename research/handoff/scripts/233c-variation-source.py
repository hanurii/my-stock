# -*- coding: utf-8 -*-
r"""233c - **「«전»이 «변동원»을 «지웠나»」를 «잰다**  (조사 세션 2026-09-08)

  🚨 검증(7f8ea8b5): 「«길이»로는 «양» 방향 다 설명 «안» 된다 ⇒ «논증»으로 «닫지» 말고 «재라**」
  ⇒ **재는 것 «둘»**(«전»/«후» «둘» 다):
       ㈎ **«복제»당 «거래 수»**(슬롯을 «얻은» 것)의 «흩어짐»
       ㈏ **«복제»당 «점유 자리-일»**의 «흩어짐»
  ✅ 「전」이 **«훨씬» 작으면** ⇒ 「«전»이 «변동원»을 «지웠다**」가 **«실측»으로 «선다**
  🔴 «안» 그러면 ⇒ **그 문장은 «죽는다**  (⇒ **«반증» 가능한 «형태»** · 유형 103)

  🚨 **유형 67 «신고»**: 「점유 자리-일」의 **«자»가 «전»/«후»에서 «다르다**
     («전»의 «자리»는 진입일 · «후»의 «자리»는 거래일)
     ⇒ ⛔ **«절대»값을 «견주지» «않는다** — **«변동계수»(SD÷평균)«만»** 견준다(무차원)

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/233c-variation-source.py
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
CR = chr(0x211D)
NBOOT, SEED = 2000, 201201
BMN, BMX = 20, 40


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


m201d = _load("m201d", "201d-rs-threshold.py")
r91 = m201d.r91


def eq_stats(by_pos, n_pos, slots=5):
    """슬롯 «얻은» 건수와 «점유 자리-일»을 «같이» 낸다."""
    eq, held, got, occ = 1.0, [], 0, 0
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
                occ += min(p + rel, n_pos) - p
    return got, occ


def draw(n, rnd):
    out, tot = [], 0
    while tot < n:
        L = rnd.randint(BMN, BMX)
        a = rnd.randint(0, n - 1)
        LL = min(L, n - tot)
        for j in range(LL):
            out.append((a + j) % n)
        tot += LL
    return out


def run(built, all_d, label):
    pos = {d: i for i, d in enumerate(all_d)}
    n_pos = len(all_d)
    ia = {k: defaultdict(list) for k in built}
    for k, lst in built.items():
        for j, (d, _h, _n) in enumerate(lst):
            ia[k][pos[d]].append(j)
    rnd = random.Random(SEED)
    got = {k: [] for k in built}
    occ = {k: [] for k in built}
    for bi in range(NBOOT):
        order = draw(n_pos, rnd)
        for k, lst in built.items():
            bp = defaultdict(list)
            for newp, oldp in enumerate(order):
                for j in ia[k].get(oldp, ()):
                    _d, h, nt = lst[j]
                    bp[newp].append((h, nt, 0))
            g, o = eq_stats(bp, n_pos)
            got[k].append(g)
            occ[k].append(o)
        if (bi + 1) % 500 == 0:
            P("  [%s] 부트 %d/%d" % (label, bi + 1, NBOOT), flush=True)
    return got, occ, n_pos


def main():  # noqa: C901
    P("# 233c - **「«전»이 «변동원»을 «지웠나»」 — «잰다**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/233c-variation-source.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> 🚨 검증 " + BQ + "7f8ea8b5" + BQ + ": 「«논증»으로 «닫지» 말고 «재라»」")
    P("")
    P("---")
    P("")
    P(F3)
    P("🚨 **유형 67 «신고»** — 「점유 «자리»-일」의 **«자»가 «전»/«후»에서 «다르다**")
    P("   («전»의 자리 = 진입일 · «후»의 자리 = 거래일)")
    P("   ⇒ ⛔ **«절대»값 «견줌» «금지** — **«변동계수»(SD ÷ 평균) «만»** 견준다(무차원)")
    P("")
    P("🚨 **사전등록**(값 보기 «전» · 검증이 «준» 것 «그대로»):")
    P("   ✅ 「전」의 «흩어짐»이 **«훨씬» 작으면** ⇒ 「«전»이 «변동원»을 «지웠다»」가 **«섭니다**")
    P("   🔴 «안» 그러면 ⇒ **그 문장은 «죽습니다**")
    P("   ⛔ **「훨씬」의 «문턱»을 «미리» 박는다: «변동계수»가 «절반» «아래»(비 < 0.5)**")
    P(F3)
    P("")

    old = json.loads(Path(str(r91.OUT / "201d-arms.json")).read_text(encoding="utf-8"))
    new = json.loads(Path(str(r91.OUT / "201d-arms2.json")).read_text(encoding="utf-8"))
    b_old = {k: [tuple(x) for x in old[k]] for k in (C1, CR)}
    b_new = {k: [tuple(x) for x in new["arms"][k]] for k in (C1, CR)}
    d_old = sorted({d for lst in b_old.values() for d, _h, _n in lst})
    d_new = new["cal"]

    t0 = time.time()
    g_o, o_o, np_o = run(b_old, d_old, "전")
    g_n, o_n, np_n = run(b_new, d_new, "후")
    el = time.time() - t0
    P("")

    P("# 1. **«복제»당 «거래 수»**(슬롯을 «얻은» 것)")
    P("")
    P("| | 자리 수 | 팔 | 평균 | SD | **변동계수** |")
    P("|---|---:|---|---:|---:|---:|")
    cvg = {}
    for lab, g, npz in (("«전»", g_o, np_o), ("**«후»**", g_n, np_n)):
        for k in (C1, CR):
            m, s = st.mean(g[k]), st.stdev(g[k])
            cvg[(lab, k)] = s / m
            P("| %s | %s | %s | %.1f | %.2f | **%.4f** |"
              % (lab, format(npz, ","), k, m, s, s / m))
    P("")
    P(F3)
    for k in (C1, CR):
        a, b = cvg[("«전»", k)], cvg[("**«후»**", k)]
        P("   %s  변동계수 «전» %.4f → «후» %.4f   (비 **%.2f**)" % (k, a, b, a / b))
    P(F3)
    P("")

    P("# 2. **«복제»당 «점유 자리-일»**")
    P("")
    P("| | 팔 | 평균 | SD | **변동계수** |")
    P("|---|---|---:|---:|---:|")
    cvo = {}
    for lab, o in (("«전»", o_o), ("**«후»**", o_n)):
        for k in (C1, CR):
            m, s = st.mean(o[k]), st.stdev(o[k])
            cvo[(lab, k)] = s / m
            P("| %s | %s | %.0f | %.1f | **%.4f** |" % (lab, k, m, s, s / m))
    P("")
    P(F3)
    for k in (C1, CR):
        a, b = cvo[("«전»", k)], cvo[("**«후»**", k)]
        P("   %s  변동계수 «전» %.4f → «후» %.4f   (비 **%.2f**)" % (k, a, b, a / b))
    P("")
    P("   ⛔ **평균·SD 의 «절대»값은 «자»가 «달라» «견주지» «않는다**(유형 67)")
    P(F3)
    P("")
    P("---")
    P("")

    P("# 3. **판정**")
    P("")
    P(F3)
    ratios = [cvg[("«전»", k)] / cvg[("**«후»**", k)] for k in (C1, CR)]
    ratios += [cvo[("«전»", k)] / cvo[("**«후»**", k)] for k in (C1, CR)]
    n_lo = sum(1 for r in ratios if r < 0.5)
    P("   문턱: **비 < 0.50**(「전」의 변동계수가 「후」의 «절반» 아래)")
    P("   비 넷 = %s" % " · ".join("**%.2f**" % r for r in ratios))
    P("   ★ **4 «중» %d** 이 문턱 아래" % n_lo)
    P("")
    if n_lo == 4:
        P("⇒ ✅ **「«전»이 «변동원»을 «지웠다»」가 «섭니다** ⇒ **「«원래»가 «과소»」를 «쓸 수» 있습니다**")
    elif n_lo == 0:
        P("⇒ 🔴 **«죽습니다** — 「«전»이 «변동원»을 «지웠다»」는 **«실측»으로 «안** 섭니다")
        P("   ⇒ ⇒ **「올랐다」도 「원래가 과소였다」도 «둘» 다 «못» 씁니다** — **검증 판정 «그대로»**")
    else:
        P("⇒ 🟡 **4 중 %d** — ⛔ **「가른다」로 «읽지» «않습니다**(「몇 중 몇」으로 «그대로»)" % n_lo)
    P(F3)
    P("")
    P("---")
    P("")
    P("# ⚠️ **이 판이 «못» 하는 것**")
    P("")
    P(F3)
    P("⛔ ① **블록 «하나»**(20~40)로만 쟀다 · **`201d` 자료 «하나»**")
    P("⛔ ② **「변동원」은 «둘»만 봤다**(거래 수 · 점유) — **«다른» 변동원이 «있을» 수 있다**")
    P("⛔ ③ **«절대»값은 «자»가 달라 «못» 견준다** — **변동계수«만»**")
    P("⛔ ④ 이 판은 **「CI 가 «왜» 달라졌나」를 «다» 설명하지 «않는다**")
    P("⛔ ⑤ 실측 **%.1f 분**" % (el / 60.0))
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
