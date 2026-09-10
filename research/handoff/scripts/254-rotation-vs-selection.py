# -*- coding: utf-8 -*-
r"""254 - **−17.955%p 를 «회전»과 «고르기»로 «가른다**  (조사 세션 2026-09-09)

  🚨 **물음**(검증 2차): **「−17.955%p 가 «매도 규칙»이 나쁜 것인가 — 「거래를 «6.4배» 하면 나쁘다」인가」**

  🔴 **설계는 «검증»이 «고쳤다** — ⛔ **「같은 «분포»에서 «뽑기»」가 «아니라**:
     ✅ **Ⓡ = Ⓢ 가 «실제»로 낸 보유길이 `h` 들을 «거래끼리» «순열**(라벨 순열 — `60-regime-faithful` 얼개)
     · 보유길이 «분포» → **«정확»히 같다**
     · **`h` 의 «합» → «정의»상 «보존»**  ⇒ **뽑으면 «흔들리는» 것이 «안» 흔들린다**
     · 깨지는 것은 **「«어느» 거래가 «어느» `h` 를 받나」의 «상관»** ← **«그게» 「고르기」**

  ⛔ **Ⓡ 은 «전략»이 «아니라 «귀무»**다 — **`net` 은 Ⓢ 것을 «그대로» 쓴다**(실행 «불가**)

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/254-rotation-vs-selection.py
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

C1 = chr(0x2460)          # ① 현행
CS = chr(0x24C8)          # Ⓢ ＋ 매도 규칙
CR = chr(0x24C7)          # Ⓡ 귀무(순열)
DELTA, MDE_K = 1.23, 2.8016
NBOOT, SEED = 2000, 254254
BLOCKS = ((20, 40), (80, 80))
KPERM = 20                # 점추정용 순열 «수** — ⛔ 결과 «보기» 전에 박음


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
    eq, held, got, sd = 1.0, [], 0, 0
    for p in range(n_pos):
        if held:
            keep_ = []
            for hh in held:
                if hh[0] < p:
                    eq += hh[1] * hh[2] / 100
                else:
                    keep_.append(hh)
            held = keep_
        free = slots - len(held)
        cc = by_pos.get(p)
        if free > 0 and cc:
            wgt = eq / slots
            for rel, nt, _k in cc[:free]:
                held.append([p + rel, wgt, nt])
                got += 1
                sd += rel
    for hh in held:
        eq += hh[1] * hh[2] / 100
    return (eq - 1.0) * 100.0, got, sd


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
    P("# 254 - **−17.955%p 를 «회전»과 «고르기»로 «가른다**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/254-rotation-vs-selection.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P(F3)
    P("🚨 **물음** — **「−17.955%p 가 «매도 규칙»의 몫인가, 「거래를 «6.4배» 하면 나쁘다」인가」**")
    P("")
    P("🔴 **설계는 «검증»이 «고쳤다** — ⛔ **«뽑기»가 «아니라» «순열**")
    P("   · **«뽑으면»** `h` 의 **«합»이 «흔들려»** ⇒ **Ⓢ−Ⓡ 에 «회전» 몫이 «남는다**")
    P("   · **«섞으면»** `h` 의 **«합»이 «정의»상 «보존»** ⇒ **«회전»이 «정확»히 «같다**")
    P("   ⇒ ★★ **Ⓢ − Ⓡ 에 «남는» 것은 「«어느» 거래가 «어느» `h` 를 받나」의 «상관» = 「고르기」**")
    P("")
    P("⛔ **Ⓡ 은 «전략»이 «아니라 «귀무»**다 — `net` 은 **Ⓢ 것을 «그대로»** 쓴다 ⇒ **실행 «불가**")
    P("")
    P("🔴🔴 **«그런데» 위 «설계» 문장이 «깨졌다** — **«쟀더니» 그렇다**(§1)")
    P("   ⛔ 「`h` 의 «합» = «슬롯-일» ⇒ «정의»상 «보존»」 — **«틀렸다**")
    P("   🔎 뿌리: **「«가진» `h` 의 합」과 「«실현»된 «슬롯-일»」을 «같은» 낱말로 «썼다**(유형 67)")
    P("      그 «사이»에 **«슬롯» 관문**이 있고 — **«순서 의존» «비선형» 필터**다")
    P("   ⇒ ★★★ **유형 109**: 「**«보존»을 주장할 땐 «어디»까지 보존되는지 «자리»를 적어라.**")
    P("      **«뒤»에 «비선형» 관문(문턱·상한·«슬롯»)이 있으면 «거기»서 «깨진다**」")
    P("      🔎 검출기: **「이 «합»이 «관문»을 «지나서»도 «합»인가」**")
    P("   ⚠️ 그리고 이 오류는 **«설계»를 «실제»보다 «깨끗»해 보이게 만드는 쪽**이었다")
    P(F3)
    P("")
    P("---")
    P("")

    # ── 판정표를 «미리» 인쇄 (규약 ④) ───────────────────────────────
    P("# ⛔ **0. 판정표 — «결과»를 «보기» «전»에 «박는다**")
    P("")
    P(F3)
    P("| 결과 | ✅ «쓸» 말 | ⛔ «쓰지» «않을» 말 |")
    P("|---|---|---|")
    P("| **Ⓢ−Ⓡ 칸 5** | 「고르기 몫을 **«못» 가린다**」 | ⛔ **「회전이 «전부»다」** — "
      "**「못 가림」 ≠ 「0」** |")
    P("| **Ⓢ−Ⓡ 칸 2** | 「고르기가 **«거꾸로»** 간다 — 단 **문턱 «하나»**」 | ⛔ 「매도 규칙이 «해롭다»」 |")
    P("| **Ⓢ−Ⓡ 칸 1** | 「규칙에 **«고르는» 값이 «있다»**」 | 🚨🚨 ⛔ **「문턱을 «올리면» «살린다»」** — "
      "**«이» 판이 «묻지» «않은» 물음**이다 |")
    P("")
    P("   🚨 **마지막 줄이 «제일** 중요하다 — **「Ⓢ > Ⓡ ⇒ «구제» 가능」으로 «넘어가지» «않는다**")
    P("   ✅ **양쪽에 «같은» 제약**: 「Ⓢ < Ⓡ ⇒ 규칙이 «해롭다»」도 **«못** 쓴다(문턱 «하나»의 «집행»)")
    P("")
    P("   📐 **Δ = 1.23%p** · 판정칸 **1 / 2 / 4a / 4b / 5**(정본 «그대로») · **CI «둘» 다**")
    P("   📐 **순열 «수» KPERM = %d** — ⛔ **결과 «보기» 전에 박았다**" % KPERM)
    P(F3)
    P("")
    P("---")
    P("")

    CA = OUT / "253-recs.json"
    if not CA.exists():
        P("🚨 `253-recs.json` 이 «없다** — `253` 을 «먼저** 돌려야 한다")
        return 1
    raw = json.loads(CA.read_text(encoding="utf-8"))
    recs = {k: [tuple(x) for x in v] for k, v in raw["arms"].items()}
    base, arm = recs[C1], recs[CS]

    cal = json.loads((OUT / "201d-arms2.json").read_text(encoding="utf-8"))["cal"]
    ents = {d for k in recs for d, _h, _n in recs[k]}
    if ents - set(cal):
        cal = sorted(set(cal) | ents)
    pos = {d: i for i, d in enumerate(cal)}
    n_pos = len(cal)

    def obs(lst):
        bp = defaultdict(list)
        for d, h, nt in lst:
            bp[pos[d]].append((h, nt, 0))
        return eq_of(bp, n_pos)

    def perm_arm(rnd):
        hs = [h for _d, h, _n in arm]
        rnd.shuffle(hs)
        return [(d, hs[i], nt) for i, (d, _h, nt) in enumerate(arm)]

    t0 = time.time()
    e1, g1, s1 = obs(base)
    es, gs, ss = obs(arm)
    o = {C1: m201d.ann(e1), CS: m201d.ann(es)}
    got = {C1: g1, CS: gs}
    sdays = {C1: s1, CS: ss}

    rnd0 = random.Random(SEED)
    vals, gots, sds, clamp = [], [], [], []
    for _k in range(KPERM):
        pa = perm_arm(rnd0)
        e, g, sdd = obs(pa)
        vals.append(m201d.ann(e))
        gots.append(g)
        sds.append(sdd)
        clamp.append(sum(1 for d, h, _n in pa if pos[d] + h >= n_pos))
    o[CR] = st.mean(vals)
    got[CR] = st.mean(gots)
    sdays[CR] = st.mean(sds)
    clamp_s = sum(1 for d, h, _n in arm if pos[d] + h >= n_pos)
    obs_sel = o[CS] - o[CR]
    obs_rot = o[CR] - o[C1]

    P("# 1. **팔 «셋** · **«회전»이 «정말» «같은가**")
    P("")
    P(F3)
    for k in (C1, CS, CR):
        P("   %-3s **%+.3f%%p/해**  ·  슬롯 «얻은» 것 **%s**  ·  «슬롯-일» **%s**"
          % (k, o[k], format(int(round(got[k])), ","), format(int(round(sdays[k])), ",")))
    P("")
    P("   ★★ **«검산» — Ⓡ 의 «회전»이 Ⓢ 와 «같은가**")
    dg = 100.0 * (got[CR] - got[CS]) / max(1, got[CS])
    ds = 100.0 * (sdays[CR] - sdays[CS]) / max(1, sdays[CS])
    P("      슬롯 «얻은» 것  Ⓢ %s vs Ⓡ %s  ⇒ **%+.2f%%**"
      % (format(got[CS], ","), format(int(round(got[CR])), ","), dg))
    P("      «슬롯-일»       Ⓢ %s vs Ⓡ %s  ⇒ **%+.2f%%**"
      % (format(sdays[CS], ","), format(int(round(sdays[CR])), ","), ds))
    P("")
    P("   🚨 **«정확»히 같지는 «않다** — **`h` 의 «합»은 «후보» 목록에서 보존되나**")
    P("      **«슬롯»이 «찬» 날엔 거래가 «버려져** — **«실제로» 쓰인 `h` 는 «달라진다**")
    P("      ⇒ ⛔ **그러니 「회전 몫이 «정확»히 0」이라고 «못** 쓴다 — **위 «두» 수를 «같이» 읽어라**")
    P("")
    P("   ⚠️ **클램프**(결착이 달력 «끝»을 넘는 거래) — Ⓢ **%s** · Ⓡ 평균 **%.1f**"
      % (format(clamp_s, ","), st.mean(clamp)))
    P("")
    P("   🚨🚨 **그래서 «이름»을 «고친다** — **셋이 «단조»**다")
    P("      슬롯-일 **%s → %+.3f** · **%s → %+.3f** · **%s → %+.3f**"
      % (format(sdays[C1], ","), o[C1], format(int(round(sdays[CR])), ","), o[CR],
         format(sdays[CS], ","), o[CS]))
    P("      ⇒ **슬롯-일이 «많을수록» 좋다** ⇒ **Ⓡ 이 Ⓢ 보다 «많으니» 잔여 회전이 Ⓡ 을 «좋게» 만든다**")
    P("      ⇒ 🚨 **그 «방향»이 Ⓢ−Ⓡ 의 부호(%+.3f)와 «같다**" % obs_sel)
    P("      ⛔ **«단가»로 「몇 %가 설명된다」를 «세지» «않는다** — **두 축이 «같이» 변한 판**이다(유형 68)")
    P("")
    P("      ⇒ ★★★ **Ⓢ−Ⓡ 은 「«고르기»」의 «자»가 «아니다** —")
    P("         **「«어디»서 «자르느냐»의 몫 ＋ «잔여» 회전(슬롯-일 %+.2f%%)」의 «자»**다" % ds)
    P("      ⇒ ★★★ **Ⓡ−① 도 「«회전»」이 «아니라 — 「«자르는» 것 «자체»」**다")
    P("         (Ⓡ 은 **«무작위» 절단**이라 «회전»만 «달라진» 것이 «아니다**)")
    P(F3)
    P("")
    P("---")
    P("")

    # ── 2. MDE «먼저» (㉤) ────────────────────────────────────────
    P("# 🚨 **2. MDE 를 «먼저** — **「가릴 수 «있는가»」를 «수»로**")
    P("")
    P(F3)
    P("   ⛔ **`253` 의 MDE 는 12.87 · 11.89 였다** — **17.955 를 «둘»로 «가르려면**")
    P("      **Ⓢ−Ⓡ 의 MDE 가 «그보다» «작아야** 뜻이 있다")
    P("   ⛔ **판정을 «보기» «전»에 «먼저** 찍는다(`143` 사전등록 §6 과 «같은» 순서)")
    P(F3)
    P("")
    ia1 = defaultdict(list)
    for j, (d, _h, _n) in enumerate(base):
        ia1[pos[d]].append(j)
    iaS = defaultdict(list)
    for j, (d, _h, _n) in enumerate(arm):
        iaS[pos[d]].append(j)

    def boot(pairname, bmn, bmx, seed):
        rnd = random.Random(seed)
        out = []
        for _bi in range(NBOOT):
            order = m201d.draw(n_pos, rnd)
            pa = perm_arm(rnd)
            iaR = defaultdict(list)
            for j, (d, _h, _n) in enumerate(pa):
                iaR[pos[d]].append(j)
            vv = {}
            for nm, lst, ia in ((C1, base, ia1), (CS, arm, iaS), (CR, pa, iaR)):
                bp = defaultdict(list)
                for newp, oldp in enumerate(order):
                    for j in ia.get(oldp, ()):
                        _d, h, nt = lst[j]
                        bp[newp].append((h, nt, 0))
                vv[nm] = m201d.ann(eq_of(bp, n_pos)[0])
            out.append((vv[CS] - vv[CR], vv[CR] - vv[C1]))
        return out

    P("| 짝 | 블록 | 점추정 | **MDE** | MDE÷Δ | **17.955 대비** |")
    P("|---|---|---:|---:|---:|:--|")
    boots = {}
    for bi_blk, (bmn, bmx) in enumerate(BLOCKS):
        m201d.BMIN, m201d.BMAX = bmn, bmx
        bb = boot("x", bmn, bmx, SEED + bi_blk)
        boots[(bmn, bmx)] = bb
        for nm, idx, ob in (("**Ⓢ−Ⓡ**(«어디»서 자르나 ＋ 잔여 회전)", 0, obs_sel), ("Ⓡ−①(«자르는» 것 «자체»)", 1, obs_rot)):
            sd = st.stdev([x[idx] for x in bb])
            mde = MDE_K * sd
            P("| %s | %d~%d | **%+.3f%%p** | **%.3f** | %.2f | %s |"
              % (nm, bmn, bmx, ob, mde, mde / DELTA,
                 "✅ **작다**" if mde < abs(obs_rot + obs_sel) else "🔴 **«크다** — «못» 가른다"))
        P("", end="")
    P("")
    P(F3)
    P("   ★ **읽는 법**: Ⓢ−Ⓡ 의 MDE 가 **17.955 «보다» 크면** — **«어느» 분해도 «못» 가린다**")
    P(F3)
    P("")
    P("---")
    P("")

    # ── 3. 항등식 검산 ────────────────────────────────────────────
    P("# ★★ **3. «항등식» 검산 — «출력»으로**(규약 ②)")
    P("")
    P(F3)
    tot = obs_sel + obs_rot
    ref = -17.955
    P("   (Ⓢ−Ⓡ) **%+.3f**  ＋  (Ⓡ−①) **%+.3f**  =  **%+.3f**" % (obs_sel, obs_rot, tot))
    P("   `253` 의 (Ⓢ−①) = **%+.3f**" % ref)
    okk = abs(tot - ref) < 0.01
    P("   ⇒ %s" % ("✅ **맞는다**(차 %.4f)" % abs(tot - ref) if okk
                   else "🔴🔴 **어긋난다**(차 %.4f) ⇒ ⛔ **멈춘다**" % abs(tot - ref)))
    P(F3)
    P("")
    if not okk:
        P("⛔ **커밋은 두뇌 몫입니다.**")
        return 2
    P("---")
    P("")

    # ── 4. 판정 ───────────────────────────────────────────────────
    P("# 4. **판정** — CI 를 **«둘» 다**")
    P("")
    P("| 짝 | 블록 | 점추정 | **백분위 CI** | 칸 | **기본 CI** | 칸 |")
    P("|---|---|---:|---:|:--|---:|:--|")
    cells = {"sel": [], "rot": []}
    sel_up, sel_width, sel_mde = [], [], []
    for (bmn, bmx), bb in boots.items():
        for nm, idx, ob, key in (("**Ⓢ−Ⓡ**(«어디»서 자르나 ＋ 잔여 회전 +4.74%)", 0, obs_sel, "sel"),
                                 ("Ⓡ−①(**«자르는» 것 «자체»**)", 1, obs_rot, "rot")):
            v = sorted(x[idx] for x in bb)
            lo, hi = v[int(NBOOT * .025)], v[int(NBOOT * .975)]
            blo, bhi = 2 * ob - hi, 2 * ob - lo
            cp, cb = cell_of(lo, hi), cell_of(blo, bhi)
            cells[key].append((cp, cb))
            if key == "sel":
                sel_up.extend([hi, bhi])
                sel_width.append(hi - lo)
                sel_mde.append(MDE_K * st.stdev([x[idx] for x in bb]))
            P("| %s | %d~%d | **%+.3f%%p** | [%+.3f, %+.3f] | %s | [%+.3f, %+.3f] | %s |"
              % (nm, bmn, bmx, ob, lo, hi, cp, blo, bhi, cb))
    P("")
    P(F3)
    for key, nm in (("sel", "Ⓢ−Ⓡ («어디»서 자르나 ＋ 잔여 회전)"),
                    ("rot", "Ⓡ−① («자르는» 것 «자체»)")):
        cc = [c for pair in cells[key] for c in pair]
        P("   **%s** — 칸 %s" % (nm, " · ".join(cc)))
    P("")
    P("")
    P("## 🔴 **판정 낱말 — 「«작다»」가 «아니라 「«못» 잰다」**")
    P("")
    P(F3)
    ups = [u for u in sel_up]
    P("   효과 **%+.3f%%p** · MDE **%.3f** ⇒ **MDE 가 효과의 «%.1f배»**"
      % (obs_sel, sel_mde[0], sel_mde[0] / max(1e-9, abs(obs_sel))))
    P("   CI «폭» **%.3f** ⇒ **Δ(1.23)의 «%.1f배»** ⇒ ⛔ **칸 4a(「작다」)와는 «한참» 멀다**"
      % (sel_width[0], sel_width[0] / DELTA))
    P("")
    P("   ✅ **참 효과의 «상한»**(양측 95% CI 의 «위» 끝 — «같은 줄»에 적는다):")
    P("      백분위 **%+.3f · %+.3f**  ·  기본 **%+.3f · %+.3f**  ⇒ **제일 «큰» 상한 %+.3f%%p**"
      % (ups[0], ups[2], ups[1], ups[3], max(ups)))
    P("   ⇒ ✅ **「«이» 자로는 «못» 넘었다 — 참 효과가 %+.3f%%p «보다» 클 «가능성»은 «못» 배제한다」**"
      % max(ups))
    P("")
    P("   🚨 **그리고 «한» 칸 «더**: **「이 판에는 «고르기»를 «따로» 재는 «자»가 «없었다**」")
    P("      Ⓢ−Ⓡ 에 **«잔여» 회전이 «섞여** 있으므로 — **«순수»한 「고르기」는 «안** 잰 것이다")
    P("      ⇒ ⛔ 다만 **«결론»은 «같다**: 「고르기에 대해 «못» 쓴다」로 «수렴**한다")
    P(F3)
    P("")
    sel_set = {c for pair in cells["sel"] for c in pair}
    if sel_set == {"**5**"}:
        P("⇒ **Ⓢ−Ⓡ 칸 5** ⇒ ✅ 「**「«어디»서 «자르느냐»」의 몫을 «못» 가린다**」")
        P("   (⛔ **«순수» 「고르기」가 «아니다** — **잔여 회전 슬롯-일 +4.74%가 «섞여» 있다**)")
        P("   ⛔ **「회전이 «전부»다」로 «읽지» «않는다** — **「못 가림」 ≠ 「0」**")
    elif sel_set == {"**1**"}:
        P("⇒ **Ⓢ−Ⓡ 칸 1** ⇒ ✅ 「**규칙에 «고르는» 값이 «있다**」")
        P("   🚨🚨 ⛔ **「문턱을 «올리면» «살린다»」로 «가지» «않는다** — **«묻지» «않은» 물음**이다")
    elif sel_set == {"**2**"}:
        P("⇒ **Ⓢ−Ⓡ 칸 2** ⇒ ✅ 「**고르기가 «거꾸로» 간다 — 단 문턱 «하나»**」")
        P("   ⛔ **「매도 규칙이 «해롭다»」로 «읽지» «않는다**")
    else:
        P("⇒ 🚨 **칸이 «갈린다** — **「몇 중 몇」**으로 «그대로** 적는다")
    P(F3)
    P("")
    P("---")
    P("")
    P("# ⚠️ **이 판이 «못** 한 것**")
    P("")
    P(F3)
    P("⛔ ① **Ⓡ 은 «실행» «불가**다 — `net` 이 Ⓢ 것이다 ⇒ **«귀무»이지 «대안»이 «아니다**")
    P("⛔ ② **`h` 합 «보존»은 «후보» 목록에서**다 — **슬롯이 «차면» 버려져 «실제» 회전은 «조금» 다르다**")
    P("     ⇒ **§1 에 «수»로 적었다**")
    P("⛔ ③ **문턱 「1」 «하나»의 «집행»**만 봤다 — **어느 칸이 나와도 「문턱을 «바꾸면»」은 «못** 말한다")
    P("⛔ ④ **순열 %d 회**의 «평균»이 Ⓡ 점추정이다 — **순열 «잡음»은 부트에 «넣었다**" % KPERM)
    P("⛔ ⑤ 💰 **비용 실측**: **%.1f 분**" % ((time.time() - t0) / 60.0))
    P(F3)
    P("")
    P("---")
    P("")
    P("# 📌 **«기록»만 — «같은» 병이 «저장소»에 «또» 있다**(⛔ **«고치지» «않았다**)")
    P("")
    P(F3)
    P("🔎 **명령** `grep -rlE \"ps[i+1] = ps[i]|cumsum|누적합|prefix_sum\" scripts/*.py "
      "../../scripts/*.py ../../scripts/canslim_lib/*.py` ⇒ **맞은 파일 «5»**")
    P("")
    P("| 자리 | 무엇 | «같은» 병인가 |")
    P("|---|---|:--|")
    P("| **`scripts/_build_passmatrix.py:197-199`** | `ct = cumsum(rawt)` → "
      "`avg = (ct[nh] - ct[nh-wlen]) / wlen / 1e8` → **`MIN_TURNOVER_EOK` 문턱과 «비교»** "
      "| 🔴 **«그렇다** — 누적합 차로 «이동평균»을 짓고 **«문턱»에 «건다** |")
    P("| `scripts/_build_passmatrix.py:189` | `cz = cumsum(zero)` — **정수** 세기 "
      "| ⚪ **«아니다**(부동소수 «아님») |")
    P("| `research/handoff/scripts/02-grade-table.py:272` | leave-one-out 합 — **«순위»용** "
      "| 🟡 **위험 «낮다**(동점이면 «차례»만 바뀐다) |")
    P("| `253*`(내 것 셋) | `rolling_avgv` | 🔴 **«그것»이 이 판의 결함**(주석에 «박았다**) |")
    P("")
    P("⛔ **«고치지» «않았다** — **`_build_passmatrix` 는 🇰🇷 «한국» 실전 도구 축**이고")
    P("   **사용자께서 한국 자료를 「분석 «안» 함」으로 정하셨으며 — 도구도 «멈춰» 둔 상태**다")
    P("   (`Disable-ScheduledTask` · 메모리 `sepa-auto-schedule`)")
    P("✅ **고치는 «법»**(적어만 둔다): `avg` 를 **창 «직접» 합산**으로 짓거나 —")
    P("   **`math.fsum`**(보정 합)으로 누적합을 지으면 «마지막» 비트 차가 «사라진다**")
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
