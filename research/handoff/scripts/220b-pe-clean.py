# -*- coding: utf-8 -*-
r"""220b — **`223`(P/E)의 «음수 eps» 와 «대조군»을 «바로잡는다»** · 검증 2차 지적 2026-09-07

  🚨 **검증이 짚은 것** — 「음수 P/E 를 「«낮다»」로 «정렬»하면 «적자» 기업이 「제일 «싸다»」가 된다」

  ✅ **코드로 답한다**(`220-fa-four.py:170`):
       `pe = (epx / fl["eps_ttm"]) if (fl["eps_ttm"] and fl["eps_ttm"] > 0) else None`
     ⇒ **`> 0` 이 «아니면» `None`** ⇒ **음수·0 은 «제외»**됐다. 「낮은 쪽」으로 «안» 갔다.

  🔴 **그러나 «다른» 결함이 «있다** — **대조군**:
     `220` 은 **Ⓓ(715) vs ① «전체»(1,749)** 로 쟀는데 —
     Ⓓ 는 **P/E 를 «낼 수» 있는 1,628 의 «부분»**이다.
     ⇒ 🚨 **「높은 P/E 효과」와 「P/E 를 «낼 수» 있음 효과」가 «섞였다**.
     ⇒ ✅ **고침**: **Ⓓ⁺(높은 쪽) vs Ⓓ⁻(낮은 쪽)** — **«같은» 집합 «안»에서 «절반»씩**.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/220b-pe-clean.py
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
r102 = _load("r102", "102-implement-principles.py")
m220 = _load("m220", "220-fa-four.py")
f92a = r102.f92a

YEARS = tuple(range(1999, 2027))
D0, D1 = "1999-04-01", "2026-08-21"
NBOOT, SEED, YRS = 2000, 220222, 27.4
BLOCKS = ((20, 40), (80, 80))
DELTA, MDE_K = 1.23, 2.8016

PRE_UP = "**Ⓓ⁺ 가 «위»로 갈라지면** → 「**«높은» P/E 가 «낫다**」 — 원전(v2:45)이 «일한다»"
PRE_DN = "**«아래»로 갈라지면** → 「**«낮은» P/E 가 «낫다**」 — 원전과 «어긋난» «관측»"
PRE_NO = "**«못» 가리면** → 「«같은» 집합 «안»에서 «절반»으로 «갈라도» «못» 가린다」"


def main():          # noqa: C901
    P("# 220b — **`223`(P/E) «음수 eps» 와 «대조군» 바로잡기**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/220b-pe-clean.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("---")
    P("")
    P("# ★★★ 0. **검증 물음 «넷»에 «코드»로 답한다**")
    P("")
    P(F3)
    P("## ① **음수 TTM eps 를 «어찌» 했나** → ✅ **«제외»했다**")
    P("")
    P("   🔎 " + BQ + "220-fa-four.py:170" + BQ)
    P("      " + BQ + "pe = (epx / fl['eps_ttm']) if (fl['eps_ttm'] and fl['eps_ttm'] > 0) else None"
      + BQ)
    P("   ⇒ **" + BQ + "> 0" + BQ + " 이 «아니면» " + BQ + "None" + BQ + "** ⇒ "
      "**음수·0 은 «아예» «빠졌다**")
    P("   ⇒ ⇒ ✅ **「«적자» 기업이 「제일 «싸다»」로 «몰리는»」 일은 «일어나지» 않았다**")
    P("")
    P("## ④ **TTM 4분기 중 «일부»가 «없는» 행** → ✅ **«제외»했다**")
    P("")
    P("   🔎 " + BQ + "220-fa-four.py:135-137" + BQ)
    P("      " + BQ + "es = [g(j-k,'eps') for k in range(4)]" + BQ)
    P("      " + BQ + "if not any(_nan(x) for x in es): out['eps_ttm'] = sum(es)" + BQ)
    P("   ⇒ **«하나»라도 «없으면» " + BQ + "eps_ttm = None" + BQ + "** ⇒ 제외")
    P(F3)
    P("", flush=True)

    # ── ② «몇» 건이 빠졌나 — «갈라» 센다 ──────────────────────────────
    CC = Path(str(r91.OUT / "220b-split.json"))
    if CC.exists():
        sp = json.loads(CC.read_text(encoding="utf-8"))
    else:
        P("(② «음수» vs «결측» 을 «갈라» 세는 중 …)", flush=True)
        (_a, _b, by2), _m, _ = r91.load_ladder(
            YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
        fund, ixf = f92a.load()
        ix = {f: i for i, f in enumerate(ixf)}
        n_ok = n_neg = n_miss = 0
        for y in sorted(by2):
            ou = {}
            for p in by2[y]:
                arq = (fund.get(p["code"]) or {}).get("ARQ") or []
                a = f92a.asof(arq, p["entry_date"]) if arq else None
                if a is None or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX:
                    continue
                j = arq.index(a)
                fl = m220._flags(arq, j, ix)
                if fl is None or fl["base2"] is not True:
                    continue
                cd = p["code"]
                if cd in ou and p["entry_date"] <= ou[cd]:
                    continue
                ou[cd] = p["entry_date"]
                t = fl["eps_ttm"]
                if t is None:
                    n_miss += 1
                elif t <= 0:
                    n_neg += 1
                else:
                    n_ok += 1
        sp = {"ok": n_ok, "neg": n_neg, "miss": n_miss}
        CC.write_text(json.dumps(sp), encoding="utf-8")
    tot = sp["ok"] + sp["neg"] + sp["miss"]
    P(F3)
    P("## ② **«몇» 건이 «빠졌나** — «갈라» 세었다")
    P("")
    P("   **재계수 집합(진입일 기준 중복 제거) = %s**" % format(tot, ","))
    P("   ✅ P/E 를 «낸» 것(TTM eps > 0)     **%s**  (%.1f%%)"
      % (format(sp["ok"], ","), sp["ok"] / tot * 100))
    P("   🔴 **TTM eps ≤ 0**(«적자»)          **%s**  (%.1f%%)  ← **«제외**됨"
      % (format(sp["neg"], ","), sp["neg"] / tot * 100))
    P("   🔴 **4분기 중 «결측»**              **%s**  (%.1f%%)  ← **«제외**됨"
      % (format(sp["miss"], ","), sp["miss"] / tot * 100))
    P("")
    P("")
    P("🚨🚨 **«수»가 «둘»이다 — «신고**한다(규약 ⑦)")
    P("")
    P("   ㉠ " + BQ + "220" + BQ + " 의 ① 거래  **1,749**  ← " + BQ + "resolve_trade" + BQ
      + " 의 **«결착일»**로 중복 제거")
    P("   ㉡ **이 판의 재계수**   **%s**  ← **«진입일»**로만 중복 제거" % format(tot, ",")
      + "(" + BQ + "resolve_trade" + BQ + " 를 «안» 불렀다)")
    P("   ⇒ ⛔ **㉡ 은 «덜» 제거된 집합**이다 ⇒ **«개수»를 «그대로» «쓰면» «안» 된다**")
    P("")
    P("   ✅ **«쓸 수» 있는 것은 «갈래»(비)뿐**: **음수 : 결측 = %d : %d ≈ %.0f : %.0f**"
      % (sp["neg"], sp["miss"], sp["neg"] / (sp["neg"] + sp["miss"]) * 100,
         sp["miss"] / (sp["neg"] + sp["miss"]) * 100))
    P("   🔎 그리고 " + BQ + "220" + BQ + " 의 **«실제» 제외는 121 / 1,749 = 6.9%**(갈무리에서 «셈»)")
    P("   ⇒ ⇒ **그 121 을 위 «갈래»로 나누면 — 음수 ≈ %d · 결측 ≈ %d**"
      % (round(121 * sp["neg"] / (sp["neg"] + sp["miss"])),
         round(121 * sp["miss"] / (sp["neg"] + sp["miss"]))))
    P("   ⚠️ **「≈」다** — «갈래»를 «다른» 집합에서 «옮겼다**(유형 68 의 «작은» 얼굴 · «신고**한다)")
    P("")
    P("   ⚠️ 견줌 — `172` 의 「N2(ii) 전년동기 EPS ≤ 0 가 None 의 **90.2%**」와는 **«다른» 자**다")
    P("     (거기는 **None 집합 «안»**의 비율이고 — 여기는 **현행 «통과»분 «전체»**의 비율이다)")
    P(F3)
    P("")
    P("---")
    P("")

    # ── ③ 대조군 고침 — Ⓓ⁺ vs Ⓓ⁻ ────────────────────────────────────
    recs = json.loads((r91.OUT / "220-recs.json").read_text(encoding="utf-8"))
    dp = [(z["d"], z["h"], z["n"]) for z in recs if z.get("D") is True]
    dm = [(z["d"], z["h"], z["n"]) for z in recs if z.get("D") is False]
    P("# ★★ 1. **③ 대조군을 «고친다**")
    P("")
    P(F3)
    P("🔴 **`220` 이 «쟀던» 것**: Ⓓ(**%s**) **−** ① «전체»(**%s**)"
      % (format(len(dp), ","), format(len(recs), ",")))
    P("   ⇒ 🚨 **Ⓓ 는 「P/E 를 «낼 수» 있는 %s」의 «부분»**이다"
      % format(sp["ok"], ","))
    P("   ⇒ ⇒ **「높은 P/E 효과」와 「P/E 를 «낼 수» «있음» 효과」가 «섞였다**")
    P("")
    P("✅ **고침**: **Ⓓ⁺(높은 쪽 %s) − Ⓓ⁻(낮은 쪽 %s)** — **«같은» 집합 «안»에서 «절반»씩**"
      % (format(len(dp), ","), format(len(dm), ",")))
    P("   ⇒ ✅ **«적자»도 «결측»도 «양쪽» «다» «빠져» 있어 — «대조»가 «맞는다**")
    P(F3)
    P("")
    P("## **사전등록**(값 보기 «전»)")
    P("")
    P(F3)
    P("① " + PRE_UP)
    P("② " + PRE_DN)
    P("③ " + PRE_NO)
    P(F3)
    P("", flush=True)

    built = {"Ⓓ⁻": dm, "Ⓓ⁺": dp}
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
    obsd = o["Ⓓ⁺"] - o["Ⓓ⁻"]

    P("---")
    P("")
    P("# 2. **판정**")
    P("")
    P("| 블록 | **점추정** | **95% CI** | CI폭 | **MDE** | MDE÷Δ | 판정칸 |")
    P("|---|---:|---:|---:|---:|---:|:--|")
    cells = []
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
            boots.append(eqs["Ⓓ⁺"] - eqs["Ⓓ⁻"])
            if (bi + 1) % 500 == 0:
                P("  [블록 %d~%d] 부트 %d/%d" % (bmn, bmx, bi + 1, NBOOT), flush=True)
        v = sorted(boots)
        lo, hi = v[int(NBOOT * .025)], v[int(NBOOT * .975)]
        sd = st.stdev(boots)
        mde = MDE_K * sd
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
        P("| **%d~%d** | **%+.3f%%p** | [%+.3f, %+.3f] | %.2f | **%.3f** | %.2f | %s |"
          % (bmn, bmx, obsd, lo, hi, hi - lo, mde, mde / DELTA, cell))
    P("")
    P(F3)
    P("**두 블록의 판정칸이 %s**"
      % ("«같다» ⇒ ✅" if cells[0] == cells[1] else "«다르다» ⇒ 🚨"))
    P("")
    P("## ⇒ 사전등록 «셋» 중")
    if "**1**" in cells[0]:
        P("   ⇒ ① " + PRE_UP)
    elif "**2**" in cells[0]:
        P("   ⇒ ② " + PRE_DN)
    else:
        P("   ⇒ ③ " + PRE_NO)
    P(F3)
    P("")
    P("---")
    P("")
    P("# ⇒ **한 문장**")
    P("")
    P("> ## **«음수» eps 는 «제외»돼 있었다 — 「적자가 «제일» 싸다」는 **«안»** 일어났다.**")
    P("> ## **`220` 에서 «빠진» 것은 **121 / 1,749 = 6.9%%** 이고, 그 «대부분»(≈%d)이 «적자»다.**"
      % round(121 * sp["neg"] / (sp["neg"] + sp["miss"])))
    P("> ## **그러나 «대조군»이 «틀렸었고» — «고쳐» 다시 재도 **%s** 다.**"
      % cells[0].replace("**", "").replace(" 🚨", "").replace(" ✅", ""))
    P("")
    P("⛔ **커밋은 그쪽 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
