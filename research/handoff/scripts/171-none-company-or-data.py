# -*- coding: utf-8 -*-
r"""171 — **「None 이 «회사»의 성질인가 «자료»의 성질인가」** · 사전등록 `tasks/171-none-company-or-data.md`

  🏷️ **세대 B** · `170` 이 «적어 둔» 물음. **시뮬레이션 «없다» — «묘사»와 «시간 분할»뿐**

  🔴 **`168` 의 «헤드라인»이 걸려 있다:**
     `168` 대박률 — **None 15.3%** > True 8.4% > False 6.2%
     `170` None 의 **94.8%**가 «EPS·매출 결측» · **91.6%**가 **«중·대형»**
     🚨 **중·대형인데 자료가 «없다»는 건 «회사»보다 «자료» 이야기에 가깝다**

  🚨 **RF★ — 이 판의 자는 «비율 %p» 이지 «계좌 %p» 가 «아니다** ⇒ **Δ(1.23) 를 «안» 쓴다**(유형 67)
"""
from __future__ import annotations
import importlib.util as _u
import json
import math
import os
import statistics as st
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _load(mod, fn):
    s = _u.spec_from_file_location(mod, HERE / fn)
    m = _u.module_from_spec(s)
    s.loader.exec_module(m)
    return m


r91 = _load("r91", "91-us-out-of-sample.py")
r102 = _load("r102", "102-implement-principles.py")
r103 = _load("r103", "103-code33-strength.py")
gates = _load("gates", "_gates.py")
f92a = r102.f92a

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
FWD_MAX = 12                    # ㉡ — 앞으로 «몇 분기»까지 보나


def why_none(arq, j, ix, nq=1, nitem=2):
    if j < 4 + nq:
        return "N1"

    def g(k, f):
        return arq[k][ix[f]] if 0 <= k < len(arq) else None
    for q in range(j, j - nq, -1):
        e0, e1 = r103._yoy(g(q, "eps"), g(q - 4, "eps")), r103._yoy(g(q - 1, "eps"), g(q - 5, "eps"))
        r0, r1 = r103._yoy(g(q, "revenue"), g(q - 4, "revenue")), \
            r103._yoy(g(q - 1, "revenue"), g(q - 5, "revenue"))
        if r103._nan(e0) or r103._nan(e1) or r103._nan(r0) or r103._nan(r1):
            return "N2"
        if nitem == 3:
            m0, m4 = g(q, "netmargin"), g(q - 4, "netmargin")
            if r103._nan(m0) or r103._nan(m4):
                return "N3"
    return None


def _ci_diff(k1, n1, k2, n2):
    """두 «비율»의 차 + 95% CI (%p)"""
    p1, p2 = k1 / max(n1, 1), k2 / max(n2, 1)
    se = math.sqrt(max(p1 * (1 - p1) / max(n1, 1) + p2 * (1 - p2) / max(n2, 1), 1e-18))
    d = 100.0 * (p1 - p2)
    return d, d - 196.0 * se, d + 196.0 * se


def main():
    P = print
    P("=" * 104)
    P("171 — **「None 이 «회사»의 성질인가 «자료»의 성질인가」** · 🚨 **시뮬레이션 «없음»**")
    P("=" * 104)
    P("")
    P("> 조사 세션 · 2026-09-03 · `scripts/171-none-company-or-data.py` · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("## 🚨 **RF★ — 이 판은 Δ 를 «안» 쓴다**")
    P("")
    P("```")
    P("이 판의 자 = **«대박률»의 차 (%p)**   ·   Δ(1.23) = **«계좌 연환산»의 차 (%p)**")
    P("⇒ **«다른 자»**다(유형 67). **Δ 를 대면 «단위»가 «안» 맞는다**")
    P("✅ 판정: **「앞·뒤 «둘 다» CI 0 배제 · «같은 부호»」**면 «선다» — **문턱을 «안» 건다**")
    P("🚨 문턱은 **「작지만 «분명한»» 부호를 «지운다»**(`168` 에서 겪었다)")
    P("```")
    P("")
    P("## 🔎 **RE★ — 「없다」엔 «명령»과 «돌린 자리»**")
    P("")
    P("```")
    P("자리 `%s`" % os.getcwd().replace("\\\\", "/"))
    P("```")
    P("")
    P("## 🚨🚨 **«값 보기 «전»»에 박는 것 «셋»**")
    P("")
    P("```")
    P("### ① **«판정»은 «+100% 자» «하나»로 한다** — 나머지 셋은 **«묘사»**다")
    P("   ★ 이유: **`168` 헤드라인이 «+100% 자»에서 났다** ⇒ **그 자로 «되묻는» 것이 맞다**")
    P("   ⇒ 그래서 **「몇 개가 A1 인가」를 «세지» 않는다**")
    P("   🚨 네 자는 **«독립»이 «아니다»** — **상위1% ⊂ 상위5%** · **+100% ⊂ +30%**")
    P("   ⇒ ✅ 묘사 셋이 «다르게» 나오면 **「A2 «냄새»로 «읽되» — «판정»은 «안» 바꾼다」**")
    P("     (자를 **«미리»** 박았으므로)")
    P("")
    P("### ② **A 가 나오면 «무엇을» 말할 수 있나 — «미리» 한 문장으로:**")
    P("   ## **「효과가 «구간에 «안» 흔들린다»(«강건성»).**")
    P("   ## **  그러나 그것이 «회사» 때문인지는 «이 판으로 «못» 답한다」**")
    P("   🚨 이유: **「바라는 답」과 「«못 재는» 답」이 «같은 칸»**이다 —")
    P("     A 는 「커버리지가 «안» 좋아졌다」·「남은 None 이 «같은 성질»」·「두 효과 «상쇄»」가")
    P("     **«전부»** 낸다. **A 는 «하나»를 «가리키지» 않는다**")
    P("")
    P("### ③ ⛔ **이 판의 결과로 «매매 규칙»은 «안» 바꾼다**")
    P("   「«자료»」면  ⇒ `168` 헤드라인을 **«내린다»**")
    P("   「«회사»」면  ⇒ **「None 을 «고르는» 것」은 `168` 이 «안» 쟀다**")
    P("   ## ⇒ **«어느 쪽이든» 매매는 «안» 바뀌고 — 바뀌는 건 «우리가 «믿는» 것»이다**")
    P("   🚨 **안 박으면** 「회사」가 나왔을 때 **「None 을 «사자」」로 «흘러간다»**")
    P("```")
    P("")
    P("## 📋 **판정칸 — 🚨 «안 바라는» 칸을 «먼저», A 안에서도 A2 를 «먼저»**")
    P("")
    P("```")
    P("🚨 두뇌 세션이 «바라는» 건 **A** 다(`168` 은 «그쪽» 판이다) ⇒ **B·C 를 «먼저» 쓴다**")
    P("")
    P("**B**  부호 «어긋남»           ⇒ 🔴 「«구간»에 달렸다 — 헤드라인 «못» 쓴다」")
    P("**C**  한쪽만 0 배제           ⇒ 「«반쪽»만 선다 — «어느 쪽»인지 «적는다»」")
    P("**D**  둘 다 0 «포함»          ⇒ 「«못» 가린다」")
    P("**A2** 둘 다 0 배제·같은 부호 «인데» **크기가 «크게» 다름**(CI «안» 겹침)")
    P("       ⇒ 🚨 「부호는 같은데 **«세기»가 «변한다»** — «자료»가 섞였을 수 있다」")
    P("**A1** 둘 다 0 배제·같은 부호 «이고» 크기도 «비슷»(CI 겹침) ⇒ ✅ 「구간에 «안» 흔들린다」")
    P("```", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        P("🚨 경로 없음")
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    # 🚨 ㉡ 의 «우측 절단» — 「진입일 + %d 분기」가 «자료 끝» 안에 드는 거래만 «센다**
    ARQ_END = max((r102._ord(v["ARQ"][-1][0]) for v in fund.values()
                   if v.get("ARQ")), default=0)

    rows = []
    for y in sorted(by2):
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            ok_ = (a is not None
                   and r102._ord(p["entry_date"]) - r102._ord(a[0]) <= r102.STALE_MAX)
            if not ok_:
                v, why, j = None, "N0", None
            else:
                j = arq.index(a)
                v = r103.judge(arq, j, ix, 1, 2)
                why = why_none(arq, j, ix, 1, 2) if v is None else None
            ep = p["entry_price"]
            hs = [x for x in p["h"] if x is not None]
            run = (max(hs) / ep - 1.0) if (hs and ep and ep > 0) else None
            # ㉡ — 「«나중에» 판정 가능해지는가」 (**«묘사»** · 규칙에 «안» 씀)
            fwd, inwin = None, None
            if v is None and j is not None:
                inwin = (r102._ord(p["entry_date"]) + 365 * FWD_MAX // 4) <= ARQ_END
            if v is None and j is not None and inwin:
                for k in range(j + 1, min(j + 1 + FWD_MAX, len(arq))):
                    if r103.judge(arq, k, ix, 1, 2) is not None:
                        fwd = r102._ord(arq[k][0]) - r102._ord(p["entry_date"])
                        break
            rows.append({"y": int(p["entry_date"][:4]), "d": p["entry_date"],
                         "v": v, "why": why, "run": run, "fwd": fwd,
                         "inwin": inwin, "hasj": j is not None})

    n_all = len(rows)
    nones = [r for r in rows if r["v"] is None]
    # 🚨 규약 ③ — ㉢ 의 «입력»에서 `fwd`(룩어헤드)를 **«떼어낸다»**. 「안 쓴다」를 «구조»로
    ROWS3 = [{k: v for k, v in r.items() if k != "fwd"} for r in rows]
    good = sorted([r for r in ROWS3 if r["run"] is not None], key=lambda r: -r["run"])
    n_g = len(good)
    THS = (good[max(1, n_g // 100) - 1]["run"], good[max(1, n_g // 20) - 1]["run"], 1.0, 0.30)
    TH_NM = ("상위1%", "상위5%", "+100%", "+30%")

    def wr(sub, ti):
        s2 = [r for r in sub if r["run"] is not None]
        k = sum(1 for r in s2 if r["run"] >= THS[ti])
        return k, len(s2)

    P("")
    P("## 1. 관문 RA★")
    P("")
    P("```")
    P("연도별 합 **%s** vs 24,995  →  %s   ·   None 합 **%s** vs 11,531  →  %s"
      % (format(n_all, ","), "✅" if n_all == 24995 else "🚨 **멈춘다**",
         format(len(nones), ","), "✅" if len(nones) == 11531 else "🚨 **멈춘다**"))
    P("```", flush=True)
    if n_all != 24995 or len(nones) != 11531:
        return 3

    P("")
    P("## 2. ㉠ **«연도별» — None 비율이 «시간»에 따라 «주는가»**")
    P("")
    P("```")
    P("🚨 **「단조 «감소»」만으로는 «부족»하다 — «시장 구성»이 바뀌어도 «감소»한다.** «같은 줄»에 적는다")
    P("")
    P("| 해 | 후보 | **None %** | N1 | N2 | 상위1% | 상위5% | +100% | +30% |")
    P("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    yrs = sorted({r["y"] for r in rows})
    ncur = []
    for y in yrs:
        sub = [r for r in rows if r["y"] == y]
        nn = [r for r in sub if r["v"] is None]
        pct = 100.0 * len(nn) / max(len(sub), 1)
        ncur.append((y, pct))
        n1 = sum(1 for r in nn if r["why"] == "N1")
        n2 = sum(1 for r in nn if r["why"] == "N2")
        P("| %d | %s | **%.1f%%** | %.1f%% | %.1f%% | %s |"
          % (y, format(len(sub), ","), pct,
             100.0 * n1 / max(len(nn), 1), 100.0 * n2 / max(len(nn), 1),
             " | ".join("%.1f%%" % (100.0 * wr(nn, i)[0] / max(wr(nn, i)[1], 1))
                        for i in range(len(THS)))))
    P("")
    h1 = [p for y, p in ncur if y <= (yrs[0] + yrs[-1]) // 2]
    h2 = [p for y, p in ncur if y > (yrs[0] + yrs[-1]) // 2]
    P("앞 절반(%d~%d) 평균 **%.1f%%**  vs  뒤 절반(%d~%d) 평균 **%.1f%%**  →  **%+.1f%%p**"
      % (yrs[0], (yrs[0] + yrs[-1]) // 2, st.mean(h1),
         (yrs[0] + yrs[-1]) // 2 + 1, yrs[-1], st.mean(h2), st.mean(h2) - st.mean(h1)))
    P("🚨 **이것만으로는 «자료»인지 «시장»인지 «못» 가른다** — ㉡·㉢ 이 «그것»을 묻는다")
    P("```", flush=True)

    P("")
    P("## 3. ㉡ **「«나중에» 판정 «가능»해지는가」 — 🚨 «묘사»다**")
    P("")
    P("```")
    P("🚨🚨 **RC★ — 이건 «룩어헤드»가 «맞다». 그래서 «가둔다**:")
    P("   ✅ **「이것은 «룩어헤드»다. 그래서 «묘사»에만 쓰고 «매매 규칙»에는 «못» 들어간다」**")
    P("   🚨 그리고 그걸 **«글»이 아니라 «구조»로** 건다(규약 ③):")
    P("     ㉢ 의 «입력»은 **`fwd` 열을 «떼어낸» 표**다 ⇒ **㉡ 의 출력이 ㉢ 에 «닿을 수가 «없다»»**")
    P("     검사 — ㉢ 입력에 `fwd` 열이 «있나»: **%s**  →  %s"
      % ("있다" if any("fwd" in r for r in ROWS3) else "**없다**",
         "🚨 **멈춘다**" if any("fwd" in r for r in ROWS3) else "✅"))
    P("   ⇒ ⛔ **「그러니 «기다렸다» 사라」로 «가지» 않는다**")
    P("")
    P("🚨 **«우측 절단»을 «세었다»**(`167` 과 «같은 꼴» — «라벨»이 아니라 «수»):")
    nw = [r for r in nones if r["hasj"]]
    n_in = sum(1 for r in nw if r["inwin"])
    P("   「진입일 + %d 분기(≈%d년)」가 **«자료 끝» 안**에 드는 것만 «센다»"
      % (FWD_MAX, FWD_MAX // 4))
    P("   **%s / %s (%.1f%%)** 만 «셀 수 있다** — **«뺀» 것 %s 건**"
      % (format(n_in, ","), format(len(nw), ","), 100.0 * n_in / max(len(nw), 1),
         format(len(nw) - n_in, ",")))
    P("")
    P("   ## 🚨 **치우침의 «방향» — «고쳐도» «0» 이 되진 «않는다»:**")
    P("   우측 절단은 「«안» 바뀐 것」을 «늘려» ⇒ **「«자료»다」 쪽을 «약하게»** 만든다")
    P("   🚨 그런데 **「자료다」는 판정칸 B 쪽**이고 — **두뇌 세션이 «바라는» 건 A**(`168` 이 살아남기)다")
    P("   ⇒ ★ **치우침이 «바라는» 쪽으로 간다** ⇒ **그런데도 「자료다」가 나오면 «판정 «강화»»다**")
    P("     (`166` 과 **«같은 구조»** — 「유리한 쪽으로 치우쳤는데도 «졌다»」)")
    P("")
    nj = [r for r in nones if r["hasj"] and r["inwin"]]
    got = [r for r in nj if r["fwd"] is not None]
    P("None 중 «앞으로 볼 수 있는» 것 **%s** (`arq` 가 «있는» 것) — %d 분기까지 본다"
      % (format(len(nj), ","), FWD_MAX))
    P("   그중 **«나중에» 판정 가능해진 것** **%s** (**%.1f%%**)"
      % (format(len(got), ","), 100.0 * len(got) / max(len(nj), 1)))
    if got:
        dd = sorted(r["fwd"] for r in got)
        P("   «바뀌기까지» — 중앙 **%d일** · P10 **%d일** · P90 **%d일**"
          % (dd[len(dd) // 2], dd[len(dd) // 10], dd[9 * len(dd) // 10]))
    for k, lab in (("N1", "이력 «부족»"), ("N2", "EPS·매출 «결측»")):
        sub = [r for r in nj if r["why"] == k]
        g2 = [r for r in sub if r["fwd"] is not None]
        P("   **%s**(%s) — %s / %s 이 «나중에» 판정 가능 (**%.1f%%**)"
          % (k, lab, format(len(g2), ","), format(len(sub), ","),
             100.0 * len(g2) / max(len(sub), 1)))
    P("")
    P("")
    P("## 🔴🔴 **«전면 철회**(2026-09-03 · `172`) — 위 «수»는 «아무 말도» 안 한다**")
    P("")
    P("   `171-…py` 의 `for k in range(j+1, …)` 는 **«분기 인덱스»를 «앞으로» 미는** 것이다 ⇒")
    P("     **N1 «나이»**   `k` 가 4+nq 를 «넘기만» 하면 됨            ⇒ **«항등식»**")
    P("     **N2(ii) «적자»** «적자 구간»이 «끝나기만» 하면 «저절로»   ⇒ **«거의» 항등식**")
    P("     **N2(i) «비어»** `k` 를 밀면 **«다른» 분기**를 본다        ⇒ **«소급 채움» 증거가 «아니다»**")
    P("")
    P("   ## ⇒ 🔴 **「64.0%가 «나중에» 판정 가능 ⇒ «자료» 쪽」은 «전면 철회»다**")
    P("   ⇒ **«항등식»의 «달성률»**을 «증거»로 읽은 것이다")
    P("")
    P("   ✅ **검출기(이제부터 «먼저» 건다): 「이 «변화»가 «시간만» 지나도 «저절로» 일어나는가」**")
    P("")
    P("   🔴 그리고 **산수도 틀렸다** — 「207일 ≈ 4분기」는 **«아니다»**(4분기 = **365일**)")
    P("     **207 ÷ 91.25 = «2.27» 분기**  ⇒ 「4분기 «쌓기»」도 「1년 뒤 «흑자 전환»」도 **못 받친다**")
    P("   ✅ 낱말도 — 「회사가 «회복»」이 «아니라** **「«비교 분기»가 «흑자» 분기로 «옮겨감»」**이다")
    P("```", flush=True)

    P("")
    P("## 4. ㉢ **«시간 분할» — 「None − True」 대박률 차가 «구간»에 흔들리나**")
    P("")
    P("```")
    ds = sorted(r["d"] for r in ROWS3)
    cut = ds[len(ds) // 2]
    A = [r for r in ROWS3 if r["d"] < cut]
    B = [r for r in ROWS3 if r["d"] >= cut]
    P("경계 **%s** — 앞 **%s** 건 · 뒤 **%s** 건" % (cut, format(len(A), ","), format(len(B), ",")))
    P("")
    P("**RB★ — 앞·뒤 «사건 «건수»»를 «둘 다» 적는다**(유형 33 — **«비율»이 아니라 «건수»가 자다**)")
    P("   («대박 건수» / «분모» 로 적는다 — 앞의 수가 «사건 수»다)")
    P("")
    P("| 자 | 앞 None n | 앞 True n | 뒤 None n | 뒤 True n |")
    P("|---|---:|---:|---:|---:|")
    for i, nm in enumerate(TH_NM):
        an = wr([r for r in A if r["v"] is None], i)
        at = wr([r for r in A if r["v"] is True], i)
        bn = wr([r for r in B if r["v"] is None], i)
        bt = wr([r for r in B if r["v"] is True], i)
        P("| **%s** | %s / %s | %s / %s | %s / %s | %s / %s |"
          % (nm, format(an[0], ","), format(an[1], ","), format(at[0], ","), format(at[1], ","),
             format(bn[0], ","), format(bn[1], ","), format(bt[0], ","), format(bt[1], ",")))
    P("")
    P("| 자 | **앞: None−True** | 95% CI | **뒤: None−True** | 95% CI | 판정칸 |")
    P("|---|---:|---|---:|---|:--|")
    cells = []
    for i, nm in enumerate(TH_NM):
        an, at = wr([r for r in A if r["v"] is None], i), wr([r for r in A if r["v"] is True], i)
        bn, bt = wr([r for r in B if r["v"] is None], i), wr([r for r in B if r["v"] is True], i)
        d1, l1, h1_ = _ci_diff(an[0], an[1], at[0], at[1])
        d2, l2, h2_ = _ci_diff(bn[0], bn[1], bt[0], bt[1])
        ok1, ok2 = (l1 > 0 or h1_ < 0), (l2 > 0 or h2_ < 0)
        if ok1 and ok2 and (d1 > 0) != (d2 > 0):
            c = "🔴 **B** — 부호 «어긋남»"
        elif ok1 and ok2:
            c = ("🚨 **A2** — 같은 부호인데 «세기»가 «다름»(CI «안» 겹침)"
                 if (h1_ < l2 or h2_ < l1) else "✅ **A1** — 구간에 «안» 흔들림")
        elif ok1 or ok2:
            c = "⚠️ **C** — **%s**만 0 배제" % ("앞" if ok1 else "뒤")
        else:
            c = "🚨 **D** — 못 가린다"
        cells.append(c)
        P("| **%s** | **%+.2f%%p** | [%+.2f, %+.2f] | **%+.2f%%p** | [%+.2f, %+.2f] | %s |"
          % (nm, d1, l1, h1_, d2, l2, h2_, c))
    P("")
    P("**RD★ — 대박률 «네 자» «전부» 적었다** ✅ (`170` PD★ 이어감)")
    P("")
    P("🚨 **「90.2%」가 «두 곳»에 나오는데 «우연»이다**(규약 ⑦ — 같은 수가 둘이면 «멈춘다»)")
    P("   `171` 우측 절단 10,139/11,244 = **90.1725%**  ·  `172` N2(ii) 10,398/11,531 = **90.1743%**")
    P("   ⇒ **분모가 «다르고» 넷째 자리에서 갈린다** ⇒ **«우연»**")
    P("   🚨 **0.002%p 차이라 «아주» 가깝다 ⇒ «더» 위험하다** — **눈으로는 «같다»고 읽힌다**")
    P("")
    HEAD = 2                                   # 🚨 «판정»은 **+100% 자** 하나(값 보기 «전» 박음)
    P("")
    P("## ⇒ 🚨 **«판정»은 «+100%% 자» «하나»다 — %s**" % cells[HEAD])
    P("   (나머지 셋은 **«묘사»**다. 「몇 개가 A1 인가」를 **«안» 센다**)")
    P("")
    P("★ **묘사 셋 — «참고»로만:**")
    for i2, nm2 in enumerate(TH_NM):
        if i2 != HEAD:
            P("   %-8s %s" % (nm2, cells[i2]))
    if len({c.split(" ")[1] if " " in c else c for c in cells}) > 1:
        P("   ⇒ 🚨 **묘사가 «갈린다» — 「A2 «냄새»」로 «읽되» «판정»은 «안» 바꾼다**")
    P("")
    nA1 = sum(1 for c in cells if "A1" in c)
    nA2 = sum(1 for c in cells if "A2" in c)
    nB = sum(1 for c in cells if "**B**" in c)
    nC = sum(1 for c in cells if "**C**" in c)
    nD = sum(1 for c in cells if "**D**" in c)
    P("🚨 **아래 «개수»는 «참고»다 — 네 자가 «독립»이 «아니라»(⊂ 관계) «세면» «안» 된다**")
    P("   네 자 — A1 %d · A2 %d · B %d · C %d · D %d" % (nA1, nA2, nB, nC, nD))
    if "A1" in cells[HEAD]:
        P("")
        P("   ## ⇒ ✅ **「효과가 «구간에 «안» 흔들린다»(«강건성»)」**")
        P("")
        P("   ★★★ **«좋은» 소식 — `172` 가 이 칸에 «말»을 «붙여» 줬다:**")
        P("     A 가 「아무 말도 «못» 함」이었던 «이유» = **「«자료»냐 «회사»냐」를 «못» 갈라서**였다")
        P("     ✅ **`172` 가 «코드 읽기»로 「N2(ii) 90.2% = «적자» = «회사»」를 «확정»**")
        P("       ⇒ **「자료」 갈래가 «치워졌다»**")
        P("     ## ⇒ **A1 이 이제 «말»을 한다: 「«적자» 효과가 «구간»에 «안» 흔들린다」**")
        P("")
        P("🔴🔴 **«라벨» «정정**(2026-09-03 · `173`) — 「«적자»」는 «지금»이 «아니라» «1년 전»이다:**")
        P("   `103:54` `_yoy(g(q,\"eps\"), g(**q−4**,\"eps\"))` ⇒ prev = **「«1년 전» «그» 분기」**")
        P("   ## ⇒ **N2(ii) = 「«1년 전» «그» 분기의 EPS ≤ 0」** — 「«지금» 적자」도 「«적자 «상태»»」도 «아니다**")
        P("   ✅ 그중 **«이번» 분기는 «흑자» 47.0% · «적자» 53.0%**(`173` 실측)")
        P("   ⇒ ★ **「«1년 전»에 적자였고 «절반»은 «이미» 흑자로 «돌아선»」 집단**이다 = **«턴어라운드» 자리**")
        P("   🚨 **「원전의 «턴어라운드»와 닮았다」는 «이야기»다 — «안» 쟀다**")
        P("")
        P("     ★ **「«막힌» 검정을 «다시 돌리는» 것보다 «다른 경로»로 «한쪽»을 «지우는» 것이 «싸다»」**")
        P("       — 그 «경로»가 **«시뮬»이 아니라 `_yoy` «세 줄» «읽기»**였다")
        P("")
        P("   🚨 **단 «남는» 것 — 「«왜» 적자가 대박과 붙는지」는 «여전히» «안» 쟀다**")
        P("   🚨 **A 는 «하나»를 «가리키지» 않는다** — 「커버리지가 «안» 좋아졌다」·")
        P("     「남은 None 이 «같은 성질»」·「두 효과 «상쇄»」가 **«전부»** 이 칸을 낸다")
    elif "**B**" in cells[HEAD]:
        P("   🔴 **「«구간»에 달렸다」 ⇒ `168` 헤드라인을 «그대로» «못» 쓴다**")
    elif "A2" in cells[HEAD]:
        P("   🚨 **부호는 같은데 «세기»가 «변한다» — «자료»가 섞였을 수 있다**")
    P("```")
    P("")
    P("```")
    P("⛔ **못 쓸 말:**")
    P("   ⛔ 「None 을 «골라» 사라」                    ← «결정». 손글씨")
    P("   ⛔ 「`168` 이 «틀렸다»」 — 이 판은 **「«구간»에 흔들리나」만** 묻는다  ← «범위». 손글씨")
    P("   ⛔ 「기다렸다 사라」 — ㉡ 은 **«묘사»**다                              ← «범위». 손글씨")
    P("   ⛔ **Δ 쓰기** — 🔢 이 판의 자는 **«비율 %p»**, Δ 는 **«계좌 %p»**(유형 67)")
    P("   ⛔ **「«자료» 탓이었다」로 «세게» «닫기»** — **유형 78**")
    P("     ★ 「«세게» «말하고»」뿐 아니라 **「«세게» «닫고»」 싶을 때도 «멈춘다»**")
    P("```")
    P("")
    P("```")
    for ln in gates.shared_axis_note(
            4, ["같은 시장 역사 한 벌", "같은 후보 목록", "같은 검출기", "같은 `judge` 정의"]):
        P(ln)
    P("🚨 **그리고 «네 자»는 «독립»이 «아니다»** — 같은 거래를 «다른 문턱»으로 센 것이다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
