# -*- coding: utf-8 -*-
r"""228 — **v2:30 「«매출»이 «견인»하는 이익」** · 🔴 사용자 「ㄱ 진행」 2026-09-07

  🚨 **원전 «안»에서 «두» 문장이 «어긋난다**:
     v2:30   「**«매출»이 «견인»하는 «이익»**」        ⇒ **매출 ≥ 이익**
     v2:36③ 「**«이익» 성장이 «매출»보다 «가속»**」  ⇒ **이익 > 매출**  ← `220`Ⓐ 가 «잰» 쪽
  ⇒ ✅ **이 판은 «다른» 쪽(v2:30)을 «잰다**.

  ✅ **갈무리를 «그대로» 쓴다** — `220-recs.json` 의 `A` 가
     `A = (e0−e1) > (r0−r1)` 「이익 가속 > 매출 가속」이므로
     **`A is False` ⟺ `(r0−r1) ≥ (e0−e1)` = 「매출 가속 ≥ 이익 가속」 = v2:30** 이다.
     ⇒ **자료를 «새로» «안» 만든다** ⇒ **부트스트랩«만»**.

  ⛔ **사전등록은 `results/228-PRE.md` 에 «먼저» 박았다**(값 보기 «전»).

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/228-rev-leads.py
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


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


r91 = _load("r91", "91-us-out-of-sample.py")
m220 = _load("m220", "220-fa-four.py")

NBOOT, SEED = 2000, 228228
BLOCKS = ((20, 40), (80, 80))
DELTA, MDE_K = 1.23, 2.8016

PRE_UP = "**Ⓝ 가 «위»로 갈라지면** → 「**v2:30 이 «일한다**」 ⇒ **«매출» 견인 쪽이 «맞다**"
PRE_DN = "**Ⓝ 가 «아래»로 갈라지면** → 「**v2:30 이 «해»다**」 ⇒ **v2:36③ 쪽이 «맞다**"
PRE_NO = "**«못» 가리면** → 「**«넣어도» «못» 가린다**」"
A220 = (2.476, -2.885, 2.831, 4.104, "5")     # `220`Ⓐ 관측(이익 > 매출)


def c(s):
    return BQ + s + BQ


def main():          # noqa: C901
    P("# 228 — **v2:30 「«매출»이 «견인»하는 이익」**")
    P("")
    P("> 조사 세션 · " + c("research/handoff/scripts/228-rev-leads.py")
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⛔ **사전등록은 " + c("results/228-PRE.md") + " 에 «먼저» 박았다**")
    P("")
    P("---")
    P("")
    P("# 0. **사전등록**(«그대로» 옮긴다)")
    P("")
    P(F3)
    P("① " + PRE_UP)
    P("② " + PRE_DN)
    P("③ " + PRE_NO)
    P("")
    P("**팔**  ① 현행(`103.judge(nq=1, nitem=2)` 통과분 «전부»)")
    P("      Ⓝ 현행 ∧ **(r0 − r1) ≥ (e0 − e1)**  「매출 가속이 이익 가속 «이상»」")
    P("      ⇒ 🔎 갈무리의 " + c("A") + " 가 " + c("(e0−e1) > (r0−r1)") + " 이므로 — **Ⓝ = "
      + c("A is False") + "**")
    P("")
    P("**«예상»**: **Ⓥ 무리**(«같은» 후보 «안»에서 «더» 거름) ⇒ **MDE 가 «작을» 것** "
      "(견줌 `220`~`223` **3.3~4.7배**) ⛔ **«수»로 «옮기지» 않는다**")
    P("")
    P("⛔ 🚨 **«이겨도» «못» 쓰는 것**: 「«가속»」의 «정의»가 원전과 «같은지»는 **«안** 쟀다")
    P(F3)
    P("")
    P("---")
    P("")

    CA = Path(str(r91.OUT / "220-recs.json"))
    if not CA.exists():
        P("🚨 **멈춘다** — " + c("220-recs.json") + " 이 «없다»(`220` 을 «먼저» 돌려야 한다)")
        return 3
    recs = json.loads(CA.read_text(encoding="utf-8"))
    base = [(z["d"], z["h"], z["n"]) for z in recs]
    rev = [(z["d"], z["h"], z["n"]) for z in recs if z.get("A") is False]
    a_true = sum(1 for z in recs if z.get("A") is True)
    a_none = sum(1 for z in recs if z.get("A") is None)

    P("# 1. **팔 크기와 «양성» 대조**(«먼저» 찍는다)")
    P("")
    P(F3)
    P("   **① 현행 거래 = %s**" % format(len(base), ","))
    P("   **Ⓝ v2:30(매출 ≥ 이익) 거래 = %s**" % format(len(rev), ","))
    P("   (견줌 — `220`Ⓐ v2:36③(이익 > 매출) = **%s** · 판정 «불가»(`A is None`) = **%s**)"
      % (format(a_true, ","), format(a_none, ",")))
    P("")
    P("   **★ ① «에만» 있는 거래 = %s**  (= Ⓐ %s + 판정불가 %s)"
      % (format(len(base) - len(rev), ","), format(a_true, ","), format(a_none, ",")))
    P("   **★ Ⓝ «에만» 있는 거래 = 0**  ⟵ **Ⓝ 는 ① 의 «부분집합»**이다")
    P("")
    P("✅ **Ⓝ ⊂ ①** — 「현행 «통과»분 «안»에서 «더» 거른」 것이다(«양성» 대조 «통과»)")
    P("🚨 그리고 **Ⓝ 와 `220`Ⓐ 는 «서로» «여집합»**이다(판정불가 %s 를 «빼면»)"
      % format(a_none, ","))
    P("   ⇒ ⛔ **그래서 «둘» 다 «같은» 방향으로 «가려지면» «모순»**이다 — 사전등록 §3 에 «미리» 적었다")
    P(F3)
    P("", flush=True)

    built = {"①": base, "Ⓝ": rev}
    all_d = sorted({d for lst in built.values() for d, _h, _n in lst})
    pos = {d: i for i, d in enumerate(all_d)}
    n_pos = len(all_d)
    idx_at = {k: defaultdict(list) for k in built}
    for k, lst in built.items():
        for j, (d, _h, _n) in enumerate(lst):
            idx_at[k][pos[d]].append(j)

    def obs(lst):
        bp = defaultdict(list)
        for d, h, nt in lst:
            bp[pos[d]].append((h, nt, 0))
        return m220.boot_eq(bp, n_pos)

    o = {k: m220.ann(obs(v)) for k, v in built.items()}
    obsd = o["Ⓝ"] - o["①"]

    P("---")
    P("")
    P("# 2. **판정**")
    P("")
    P("| 블록 | **점추정** | **95% CI** | CI폭 | **MDE** | MDE÷Δ | t | 판정칸 |")
    P("|---|---:|---:|---:|---:|---:|---:|:--|")
    cells, mdes, cis = [], [], []
    for bi_blk, (bmn, bmx) in enumerate(BLOCKS):
        m220.BMIN, m220.BMAX = bmn, bmx
        rnd = random.Random(SEED + bi_blk)
        boots = []
        for bi in range(NBOOT):
            order = m220.draw(n_pos, rnd)
            eqs = {}
            for k, lst in built.items():
                bp = defaultdict(list)
                ia = idx_at[k]
                for newp, oldp in enumerate(order):
                    for j in ia.get(oldp, ()):
                        _d, h, nt = lst[j]
                        bp[newp].append((h, nt, 0))
                eqs[k] = m220.ann(m220.boot_eq(bp, n_pos))
            boots.append(eqs["Ⓝ"] - eqs["①"])
            if (bi + 1) % 500 == 0:
                P("  [블록 %d~%d] 부트 %d/%d" % (bmn, bmx, bi + 1, NBOOT), flush=True)
        v = sorted(boots)
        lo, hi = v[int(NBOOT * .025)], v[int(NBOOT * .975)]
        sd = st.stdev(boots)
        mde = MDE_K * sd
        tt = abs(obsd) / max(sd, 1e-9)
        if lo >= DELTA:
            cell = "**1** ✅"
        elif hi <= -DELTA:
            cell = "**2**"
        elif lo <= 0 <= hi:
            cell = "**5** 🚨"
        elif -DELTA <= lo and hi <= DELTA:
            cell = "**4a**"
        else:
            cell = "**4b**"
        cells.append(cell)
        mdes.append(mde)
        cis.append((lo, hi))
        P("| **%d~%d** | **%+.3f%%p** | [%+.3f, %+.3f] | %.2f | **%.3f** | %.2f | %.2f | %s |"
          % (bmn, bmx, obsd, lo, hi, hi - lo, mde, mde / DELTA, tt, cell))
    P("")
    P(F3)
    P("**두 블록의 판정칸이 %s**"
      % ("«같다» ⇒ ✅ 블록 길이에 «안» 흔들린다" if cells[0] == cells[1] else "«다르다» ⇒ 🚨"))
    P(F3)
    P("")
    P("## 사전등록 «셋» 중")
    P("")
    P(F3)
    if "**1**" in cells[0]:
        P("⇒ ① " + PRE_UP)
    elif "**2**" in cells[0]:
        P("⇒ ② " + PRE_DN)
    else:
        P("⇒ ③ " + PRE_NO)
    P(F3)
    P("")
    P("---")
    P("")
    P("# ★★★ 3. **`220`Ⓐ 와 «짝»으로 «읽는다**(사전등록 §3)")
    P("")
    P(F3)
    P("   `220`Ⓐ **v2:36③**(이익 > 매출)  **%+.3f%%p** [%+.3f, %+.3f] · MDE %.3f · **칸 %s**"
      % A220)
    P("   `228`Ⓝ **v2:30**(매출 ≥ 이익)   **%+.3f%%p** [%+.3f, %+.3f] · MDE %.3f · **칸 %s**"
      % (obsd, cis[0][0], cis[0][1], mdes[0], cells[0].replace("**", "").replace(" 🚨", "")))
    P("")
    both5 = ("**5**" in cells[0]) and (A220[4] == "5")
    if both5:
        P("## ⇒ ✅ **「«둘» 다 «못» 가렸다」**")
        P("")
        P("   ⇒ **「원전 «안»의 «어긋남»을 «우리» 자료로는 «가릴» 수 «없다」**")
        P("   ⇒ ⇒ **§B 에 「원전 «어긋남» — «판정» 불가」로 «남는다**")
        P("   ⛔ **「원전이 «틀렸다»」도 「«한» 쪽이 «맞다»」도 «말할 수» «없다**")
    elif "**5**" not in cells[0]:
        P("## ⇒ 🚨 **「«한» 쪽만 «가려졌다」** — **그게 «큰» 것**이다")
        P("")
        P("   ⇒ **원전 «어느» 문장이 «맞나»에 «닿는다**")
        P("   ⇒ ⛔ 그래도 **「원전이 «틀렸다»」가 «아니라 「«우리» 자료에서 «그» 쪽이 «일한다»」**까지다")
    P("")
    P("🚨 **«두» 팔은 «서로» «여집합»**이므로(판정불가 %s 제외) — "
      "**«둘» 다 «같은» 방향으로 «가려지면» «모순»**이다. 그때는 **«기계»를 «의심**한다."
      % format(a_none, ","))
    P(F3)
    P("")
    P("## 🚨 **«예상»과 맞댄다**")
    P("")
    P(F3)
    P("   «예상»: **Ⓥ 무리라 MDE 가 «작을» 것**(견줌 `220`~`223` **3.3~4.7배**)")
    P("   «관측»: **%.2f 배**" % (mdes[0] / DELTA))
    P("   ⇒ %s" % ("✅ **Ⓥ 무리 범위 «안»**" if 3.3 <= mdes[0] / DELTA <= 4.8
                   else "🚨 **Ⓥ 무리 범위를 «벗어났다» — 그게 «소득»이다**"))
    P(F3)
    P("")
    P("⚠️ **이 판이 «못» 하는 것**")
    P("")
    P(F3)
    P("⛔ ① 🚨 **「«가속»」의 «정의»가 원전과 «같은지» «안** 쟀다")
    P("     원전 「성장 «속도»가 «빨라져야»」 vs " + c("103.judge") + " 「YoY 가 «직전»보다 «큼»」")
    P("⛔ ② **v2:30 은 「«매출»이 «견인»한다」는 «서술»**이고 — **«문턱»이 «없다**")
    P("     ⇒ **「매출 가속 ≥ 이익 가속」은 «우리»가 «만든» «조작적 정의»**다")
    P("⛔ ③ **`229`(ROE)와 «섞지» «않는다** — **«다른» 판**이다")
    P("⛔ ④ 승률·거래당은 **«안» 적는다**")
    P(F3)
    P("")
    P("⛔ **커밋은 그쪽 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
