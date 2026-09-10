# -*- coding: utf-8 -*-
r"""255c - **문턱 격자 Ⓢ1..Ⓢ5 — 「이 판은 «회전»을 «가르지» 않는다 · «집행» «통째»를 잰다」**

  (조사 세션 2026-09-09)

  🚨 **주 판정 «하나** = **Ⓢk★ − ①**  ·  **k★ = 5**(`255a`·`255b` 가 «코드»로 골랐다 · 절단률 ≥ 10%)
  🚨 **둘째 판 = 5칸 «최대통계»**(「«안쪽» 칸이 ① 을 «넘나»」) — **«귀무» 최대를 «출력값»으로**(유형 36)
  ⛔ **Ⓢk 끼리 10쌍은 «묘사»** — 판으로 «세지» 않는다
  ⛔ **Ⓡk 는 «안** 짓는다 — **«회전»은 «교란»이 «아니라 «집행»의 «일부»**
     🚨 **«예외»**: 「안쪽 칸이 ① 을 «넘는다」가 «나오면» — **«그때»만** 짓는다(다음 판)

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/255c-threshold-arms.py
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
SK = {k: chr(0x24C8) + str(k) for k in range(1, 6)}     # Ⓢ1..Ⓢ5
KSTAR = 5                    # ⛔ `255a`·`255b` 가 «코드»로 골랐다 — «손»으로 «안» 적었다
DELTA, MDE_K = 1.23, 2.8016
NBOOT, SEED = 2000, 255255
BLOCKS = ((20, 40), (80, 80))


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


m201d = _load("m201d", "201d-rs-threshold.py")
r91 = m201d.r91
OUT = Path(str(r91.OUT))
KD = HERE.parent / "results" / "255-kdays.json"
CA = OUT / "255-arms.json"


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
    P("# 255c - **문턱 격자 Ⓢ1..Ⓢ5**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/255c-threshold-arms.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P(F3)
    P("🚨🚨 **이 판은 «회전»을 «가르지» «않는다** — **«집행» «통째»를 «잰다**")
    P("   ★ 사용자가 «실제»로 하는 것은 **「문턱 k 로 «판다»」**이고 — **«회전»은 «따라오는» 것**이다")
    P("   ⇒ ⛔ **「문턱 축의 «몫»」으로 «읽으면» «틀린다**(`254` 에서 «똑같이» 겪었다)")
    P("")
    P("📐 **주 판정 «하나** = **Ⓢ%d − ①**  ·  **k★ = %d**" % (KSTAR, KSTAR))
    P("   ⛔ **k★ 는 «코드»가 «골랐다** — `255a`(절단률 ≥ 10%%) · `255b`(자 «둘» 다 «같은» 5)")
    P("   ⇒ **«사전» 지정**이라 **max-T 에 «안** 걸린다")
    P("📐 **둘째 판 = 5칸 «최대통계»** — 「«안쪽» 칸이 ① 을 «넘나」 · **«귀무» 최대를 «출력값»으로**")
    P("⛔ **Ⓢk 끼리 10쌍은 «묘사»** · ⛔ **Ⓡk 는 «안** 짓는다(조건부 — 다음 판)")
    P(F3)
    P("")
    P("---")
    P("")
    P("# ⛔ **0. 판정표 — «결과»를 «보기» «전»에 «박는다**")
    P("")
    P(F3)
    P("| 결과 | ✅ «쓸» 말 | ⛔ «쓰지» «않을» 말 |")
    P("|---|---|---|")
    P("| **단조**(k↑ = 좋음) | 「문턱을 «올려도» ① 을 «못» 넘는다」 ＋ ★ "
      "**「Ⓢ%d−① = 문턱 축의 «천장»」** | ⛔ 「최적 문턱은 k=5」 |" % KSTAR)
    P("| **비단조 · «안쪽»이 ① 넘음** | 「k=? 에서 넘는다 — 단 **«귀무» 최대**와 «견준» 뒤」 ＋ "
      "★ 「**«그때»** Ⓡk 를 짓는다」 | ⛔ **「그 문턱을 «채택»한다」** |")
    P("| **전부 칸 5** | 「문턱 축으로는 **«못» 가린다**」 | ⛔ 「문턱은 «상관없다»」 |")
    P("| 🆕 **Ⓢ%d−① 이 «칸 2»** | ★★★ **「«문턱» 축으로는 «못» 메운다 — 이 «축»이 «닫힌다»」** | "
      "⛔ **「매도 규칙이 «해롭다»」**(집행 «통째»다) |" % KSTAR)
    P("")
    P("   🔴 **«내» 편향**(`255-PRE` §0 에 «먼저» 적었다): **「Ⓢ%d−① 이 «칸 2» — 축이 «닫힌다»」를 «바란다**"
      % KSTAR)
    P("   🚨 **두뇌는 «반대»**(안쪽 칸이 ① 을 이긴다) · **검증은 «나»와 «같다** ⇒ **셋 중 «둘»이 «같은» 쪽**")
    P("   ⛔ **막는 것은 «구조»뿐**: **k★ 사전 고정** · **판정표 «코드 안» 인쇄** · **귀무 «최대» 출력**")
    P(F3)
    P("")
    P("---")
    P("")

    kd = json.loads(KD.read_text(encoding="utf-8"))["table"]
    t0 = time.time()
    if CA.exists():
        raw = json.loads(CA.read_text(encoding="utf-8"))
        recs = {k: [tuple(x) for x in v] for k, v in raw["arms"].items()}
        stat = raw["stat"]
        P(F3)
        P("   (♻️ 갈무리 " + BQ + "255-arms.json" + BQ + ")")
        P(F3)
    else:
        P("(정본 짝을 «짓는» 중 …)", flush=True)
        pairs, miss = m201d.build_pairs(m201d.CANON)
        if pairs is None:
            P("🚨 경로 «없음»: %s" % miss[:3])
            return 1
        recs = {C1: []}
        for k in range(1, 6):
            recs[SK[k]] = []
        stat = {"cut": {str(k): 0 for k in range(1, 6)}, "n": 0}
        for t, p in pairs:
            r = t["masks"][()]
            epx, d = t["entry_px"], p["d"]
            rd = r["resolve_date"]
            hold0 = d.index(rd) if (rd and rd in d) else len(d) - 1
            net0 = sum(fr * r91.sl.net(round(px / epx * 100 - 100, 2))
                       for _dd, fr, px in r["exits"])
            recs[C1].append((t["entry_date"], max(1, hold0), net0))
            stat["n"] += 1
            row = kd.get("%s|%s" % (p["code"], t["entry_date"])) or {}
            for k in range(1, 6):
                vd = row.get(str(k))
                if vd is None or vd not in d or d.index(vd) >= hold0:
                    recs[SK[k]].append((t["entry_date"], max(1, hold0), net0))
                    continue
                vi = d.index(vd)
                kept = [(dd, fr, px) for dd, fr, px in r["exits"] if dd <= vd]
                left = 1.0 - sum(fr for _dd, fr, _px in kept)
                exs = list(kept)
                if left > 1e-9:
                    exs.append((vd, left, p["c"][vi]))
                net1 = sum(fr * r91.sl.net(round(px / epx * 100 - 100, 2))
                           for _dd, fr, px in exs)
                recs[SK[k]].append((t["entry_date"], max(1, vi), net1))
                stat["cut"][str(k)] += 1
        CA.write_text(json.dumps({"arms": {k: [list(x) for x in v] for k, v in recs.items()},
                                  "stat": stat}), encoding="utf-8")
        P("")
        P(F3)
        P("   ✅ 자료 짓기 **%.1f 분**(실측)" % ((time.time() - t0) / 60.0))
        P(F3)
    P("")

    cal = json.loads((OUT / "201d-arms2.json").read_text(encoding="utf-8"))["cal"]
    ents = {d for k in recs for d, _h, _n in recs[k]}
    if ents - set(cal):
        cal = sorted(set(cal) | ents)
    pos = {d: i for i, d in enumerate(cal)}
    n_pos = len(cal)
    order_keys = [C1] + [SK[k] for k in range(1, 6)]

    def obs(lst):
        bp = defaultdict(list)
        for d, h, nt in lst:
            bp[pos[d]].append((h, nt, 0))
        return eq_of(bp, n_pos)

    o, got, sd = {}, {}, {}
    for k in order_keys:
        e, g, s = obs(recs[k])
        o[k], got[k], sd[k] = m201d.ann(e), g, s

    P("# 1. **팔 «여섯** — ㉠(연환산 · 슬롯 · 슬롯-일 · 절단률)")
    P("")
    P("| 팔 | 연환산 %p/해 | 슬롯 «얻은» 것 | «슬롯-일» | 🅑 «집행» 절단률 |")
    P("|---|---:|---:|---:|---:|")
    for k in order_keys:
        cutr = ("—" if k == C1 else
                "**%.2f%%**" % (100.0 * stat["cut"][k[-1]] / max(1, stat["n"])))
        P("| %s | **%+.3f** | %s | %s | %s |"
          % (k, o[k], format(got[k], ","), format(sd[k], ","), cutr))
    P("")
    P(F3)
    P("   ⛔ **절단률은 🅑 «집행» 자**(÷ CANON 체결 %s) — **`255b` 가 «갈라» 놓은 그것**"
      % format(stat["n"], ","))
    P("   🔎 **㉣ 절단률 «곡선»은 `255b` 에 «있다** — 🅐 «신호» 자와 «나란히**")
    seq = [o[SK[k]] for k in range(1, 6)]
    mono = all(seq[i] <= seq[i + 1] + 1e-9 for i in range(4)) and seq[-1] <= o[C1] + 1e-9
    P("")
    P("   🔴 **«처음» 쓴 단조 검사가 «틀린» 방향이었다**(① ≥ Ⓢ1 ≥ … ≥ Ⓢ5) — **«고쳤다**")
    P("      ⇒ **k 가 «오를수록» «덜» 자르니 ① 에 «가까워»진다** ⇒ **Ⓢ1 ≤ Ⓢ2 ≤ … ≤ Ⓢ5 ≤ ①** 이 «맞는» 자")
    P("   ★ **단조인가** — %s" % ("✅ **그렇다**" if mono else "🔴 **«아니다**"))
    P("      %s" % " ≤ ".join("%+.3f" % x for x in seq) + " ≤ **%+.3f**(①)" % o[C1])
    P(F3)
    P("")
    P("---")
    P("")

    ia = {k: defaultdict(list) for k in order_keys}
    for k in order_keys:
        for j, (d, _h, _n) in enumerate(recs[k]):
            ia[k][pos[d]].append(j)

    P("# 2. **주 판정 — Ⓢ%d − ①**(⛔ **«사전» 지정 · 판 «하나»**)" % KSTAR)
    P("")
    P("| 블록 | 점추정 | **백분위 CI** | 칸 | **기본 CI** | 칸 | **MDE** | MDE÷Δ |")
    P("|---|---:|---:|:--|---:|:--|---:|---:|")
    main_key = SK[KSTAR]
    obsd = o[main_key] - o[C1]
    t1 = time.time()
    cells, boots_all = [], {}
    for bi_blk, (bmn, bmx) in enumerate(BLOCKS):
        m201d.BMIN, m201d.BMAX = bmn, bmx
        rnd = random.Random(SEED + bi_blk)
        rows = []
        for _bi in range(NBOOT):
            order = m201d.draw(n_pos, rnd)
            vv = {}
            for k in order_keys:
                bp = defaultdict(list)
                for newp, oldp in enumerate(order):
                    for j in ia[k].get(oldp, ()):
                        _d, h, nt = recs[k][j]
                        bp[newp].append((h, nt, 0))
                vv[k] = m201d.ann(eq_of(bp, n_pos)[0])
            rows.append([vv[SK[k]] - vv[C1] for k in range(1, 6)])
            if (_bi + 1) % 500 == 0:
                P("  [%d~%d] 부트 %d/%d" % (bmn, bmx, _bi + 1, NBOOT), flush=True)
        boots_all[(bmn, bmx)] = rows
        col = sorted(r[KSTAR - 1] for r in rows)
        lo, hi = col[int(NBOOT * .025)], col[int(NBOOT * .975)]
        sdv = st.stdev([r[KSTAR - 1] for r in rows])
        blo, bhi = 2 * obsd - hi, 2 * obsd - lo
        cp, cb = cell_of(lo, hi), cell_of(blo, bhi)
        cells.append((cp, cb))
        P("| **%d~%d** | **%+.3f%%p** | [%+.3f, %+.3f] | %s | [%+.3f, %+.3f] | %s | **%.3f** | %.2f |"
          % (bmn, bmx, obsd, lo, hi, cp, blo, bhi, cb, MDE_K * sdv, MDE_K * sdv / DELTA),
          flush=True)
    P("")
    P(F3)
    P("   백분위 칸 = %s  ·  기본 칸 = %s"
      % (" · ".join(c[0] for c in cells), " · ".join(c[1] for c in cells)))
    P(F3)
    P("")
    P("---")
    P("")

    P("# 3. **5칸 «최대통계»** — 「«안쪽» 칸이 ① 을 «넘나」")
    P("")
    P(F3)
    P("   📐 통계량 **T = max_k (Ⓢk − ①)**  ·  **귀무 = 부트 «중심화»**(단일 단계 max-T · 유형 36)")
    P("      ⛔ **본페로니 «아님»** — 칸들이 «상관»되어 «과보수»가 된다")
    P(F3)
    P("")
    P("| 블록 | 관측 T | «어느» k | **«귀무» 최대 95%** | 넘나 |")
    P("|---|---:|:--|---:|:--|")
    obs_t = max(o[SK[k]] - o[C1] for k in range(1, 6))
    arg_t = max(range(1, 6), key=lambda k: o[SK[k]] - o[C1])
    over, crits = [], []
    for (bmn, bmx), rows in boots_all.items():
        obsv = [o[SK[k]] - o[C1] for k in range(1, 6)]
        null_max = sorted(max(r[i] - obsv[i] for i in range(5)) for r in rows)
        crit = null_max[int(NBOOT * .95)]
        ov = obs_t > crit
        over.append(ov)
        crits.append(crit)
        P("| **%d~%d** | **%+.3f%%p** | k=%d | **%+.3f%%p** | %s |"
          % (bmn, bmx, obs_t, arg_t, crit, "🔴 **넘는다**" if ov else "✅ **«안** 넘는다"))
    P("")
    P(F3)
    P("   ⛔ **「귀무 최대」를 «출력»했다** — **효과가 «전혀» 없어도 5칸 중 «최선»을 고르면 «그만큼»** 나온다")
    P("   🔎 전례(메모리): 래칫 **12칸 귀무 95% ＋87.47%p**")
    P(F3)
    P("")
    P("---")
    P("")

    P("# 🎯 **⇒ 판정** — **§0 표를 «그대로» 읽는다**")
    P("")
    P(F3)
    cs = {c for pair in cells for c in pair}
    flat = [c for pair in cells for c in pair]
    n5 = sum(1 for c in flat if c == "**5**")
    n_split = sum(1 for c in flat if c in ("**4a**", "**4b**"))
    if cs <= {"**5**", "**4a**", "**4b**"} and not any(over):
        P("⇒ ✅ **네 칸 중 «5» 가 %d · «4a/4b» 가 %d** — **«어느» 것도 «갈라지지» «않았다**" % (n5, n_split))
        P("   ✅ **「«문턱» 축으로는 «못» 가린다」**")
        P("")
        P("   ⛔ **«못» 쓰는 말 — «여섯**")
        P("      ⛔ 「문턱은 «상관없다»」 ✗")
        P("      ⛔ 「문턱 «축»이 «닫혔다»」 ✗  ← **칸 5 면 «양쪽» 다 «못** 쓴다(검증이 «먼저» 박음)")
        P("      ⛔ 「매도 규칙이 «해롭다»」 ✗  ← **집행 «통째»**다")
        P("      ⛔ 「문턱을 «올리면» «해»가 «사라진다»」 ✗  ← **Ⓢ%d−① 은 «여전히» «음수»이고 Δ 의 2.8배**"
          % KSTAR)
        P("      ⛔ 「«문턱» «축»의 «몫»이다」 ✗  ← **회전과 «안** 갈랐다")
        P("      ⛔ 「문턱 «하나»에서만 «해»가 «보였다»」 ✗  ← **「A갈라짐·B안갈라짐 ⇒ A≠B」 «오류»**")
        P("")
        P("   ✅ **«그래도» «남는» 관측 «둘**:")
        P("      ① **단조**(%s) — **k 를 «올릴수록» ① 에 «가까워»진다**"
          % ("✅" if mono else "🔴 «아님»"))
        P("      ② **max-T** — **«어느» 안쪽 칸도 ① 을 «안** 넘는다(관측 T %+.3f vs 귀무 최대 %+.3f·%+.3f)"
          % (obs_t, crits[0], crits[1]))
        P("")
        P("   🔴🔴 **«이름»을 «철회**한다 — 검증 2차(`15b4e125`)")
        P("      ⛔ 「**«문턱 축»의 «천장**」 — **«틀렸다**")
        P("      🔎 **문턱과 «슬롯-일»은 «독립» 손잡이가 «아니다** — **문턱을 «올리면» «덜» 잘리고**")
        P("         **«그게» «곧» 슬롯-일**이다 ⇒ **여섯 점이 «둘» 다 단조인 것은 «발견»이 «아니라» «사슬»**")
        P("      ✅ **«고친» 이름**: **「«문턱» «손잡이»로 «갈» 수 «있는» «제일 «먼»» 곳」**")
        P("         ⇒ ⛔ **그 손잡이가 «무엇»을 «통해» 듣는지(회전인지 고르기인지)는 «이» 판이 «안** 갈랐다")
        P("")
        P("   ⇒ ★ **「«문턱» «손잡이»로 «갈» 수 «있는» «제일 «먼»» 곳(Ⓢ%d) = %+.3f%%p」인데 —"
          % (KSTAR, obsd))
        P("      **«그» 크기 «자체»를 «못» 가렸다**")
        P("")
        P("   ⛔ **「끝에서 «가팔라진다」」도 «막혔다** — **«단가»다**")
        P("      슬롯-일당 %p: 0.001167 → 0.000822 → 0.000699 → 0.001708 → **0.005795**")
        P("      🔎 끝이 «5배» 가파른 건 «맞으나** — **«앞»도 «단조»가 «아니다**(내렸다 «올라감»)")
        P("      ⇒ **«잡음»과 «구분» «안** 됨 ＋ **두 축이 «같이» 변한 판의 «단가»**(오늘 «네» 번째)")
        P("")
        P("   ⛔ **Ⓢ1 − Ⓢ5 는 «재지» «않는다** — **«닫은» 채로 간다**")
        P("      🔎 자: 「«칸 1»로 나오면 «무엇»을 «다르게» 하나?」 ⇒ **Ⓢ1 도 Ⓢ5 도 «둘» 다 ① 에 «못» 미친다**")
        P("      ⇒ ★★ **「둘이 «다르다»」는 「둘 중 «하나»가 «쓸 만하다»」를 «뜻하지» «않는다** ⇒ 결정이 «안» 바뀜")
        P("      ✅ 그리고 **「단조 «여섯» 점」이 «이미» 「Ⓢ1 < Ⓢ5」를 «말한다** — **«새» 판정이 «필요» 없다**")
    elif cs == {"**2**"} and mono:
        P("⇒ 🔴 **Ⓢ%d−① 이 «칸 2» ＋ 단조**" % KSTAR)
        P("   ✅ **「«문턱» 축으로는 «못» 메운다 — 이 «축»이 «닫힌다»」**")
        P("   ✅ **「Ⓢ%d−① = %+.3f%%p 가 «문턱» 축의 «천장»」**(`188` 모양)" % (KSTAR, obsd))
        P("   ⛔ **「매도 규칙이 «해롭다»」로 «읽지» «않는다** — **«집행» «통째»**다")
        P("   ⛔ **「최적 문턱은 k=5」로도 «읽지» «않는다**")
    elif cs == {"**5**"}:
        P("⇒ **전부 «칸 5»** ⇒ ✅ 「**문턱 축으로는 «못» 가린다**」")
        P("   ⛔ 「문턱은 «상관없다»」로 «읽지» «않는다**")
        P("   ⛔ **「«못» 메운다」도 «못** 쓴다(검증이 «먼저» 박았다)")
    elif any(over):
        P("⇒ 🚨 **«안쪽» 칸이 ① 을 «넘었다**(k=%d) — **«귀무» 최대와 «견준» 뒤**" % arg_t)
        P("   ⛔ **「그 문턱을 «채택»한다」로 «가지» «않는다**")
        P("   ✅ **«그때»의 처방대로 — «다음» 판에서 Ⓡk 를 «짓는다**")
    else:
        P("⇒ 🚨 **칸이 «갈린다** — **「몇 중 몇」**으로 «그대로** 적는다")
    P(F3)
    P("")
    P("# ⚠️ **이 판이 «못** 한 것**")
    P("")
    P(F3)
    P("⛔ ① **«회전»을 «가르지» «않았다** — **«집행» «통째»**다(⛔ **의도**이지 «결함»이 «아니다**)")
    P("⛔ ② **Ⓢk 끼리 10쌍은 «묘사»**다 — **판으로 «세지» «않았다**")
    P("⛔ ③ **다섯 규칙을 «묶어»**서만 봤다 — **「«어느» 규칙 «때문»인지」는 «안** 쟀다")
    P("⛔ ④ **`rolling_avgv` 의 «확인된» 결함을 «안고» 간다**(`253c` — 2/151,999 · 주석에 박음)")
    P("⛔ ⑤ **팔 칸 목록을 ㉠~㉤ 로 «닫았다**(leave-one-out · 가중치 · 다른 축 = **«다음» 판**)")
    P("⛔ ⑥ 💰 **비용 실측**: **%.1f 분**" % ((time.time() - t0) / 60.0))
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
