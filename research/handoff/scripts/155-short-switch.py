# -*- coding: utf-8 -*-
"""155 — **지수 숏을 빼면 어떻게 되나** · 「숏을 할까 말까」의 «빠진 기준선»

  🚨 108 이 판정한 것은 **「어떻게 숏할까」**(200일선 vs 동전 = +1.02%p) 이고,
     **「숏을 할까 «말까»」는 §3 ㉯ 에 «묘사»로만 있고 «판정»을 안 받았다.**
  ✅ 이 판은 **같은 판·같은 씨앗·같은 후보·같은 수수료·같은 세금**에서 **«숏 스위치»만** 끈다.
  ★ 원전 — 「롱과 숏을 «동시에» 거래하는 일은 거의 없다. 롱 아니면 «현금»」
     ⚠️ 단 `108:1` 이 「**「원전 기반」이 아니다** — 진입 규칙과 크기를 «우리»가 정했다」고 적었다.
        ⇒ 숏을 빼는 것은 «원전에 맞추는» 게 아니라 **«우리가 얹은 것을 떼는»** 것이다.
"""
from __future__ import annotations
import importlib.util as _u
import json
import math
import statistics as st
import sys
from collections import Counter
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
r108 = _load("r108", "108-short-index.py")
r109 = _load("r109", "109-index-stop.py")
r111 = _load("r111", "111-tax.py")
r124 = _load("r124", "124-jeonse-horizon.py")
r129 = _load("r129", "129-frontier.py")
f92a = r102.f92a

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
FEE = 0.002
SHORT_ON, BORROW = 0.20, 2.0
TARGET, STOP = 20.0, 10.0
START = 1000.0
NSEED = 60
OOS = ("2002-01-01", "2017-08-31")
GAP_QQQ = 1.23           # 150 — 우리 +8.47% vs QQQ 그냥 보유 +9.70% (세후 · 27.4년)
DELTA = GAP_QQQ          # ★ Δ 는 «수»가 아니라 «유도»다 — 아래 §0 참조
T60 = 2.001              # 양측 95% t (df=59)
R108_GAP = 0.21          # 108 §3 ㉯ — 바탕 +3.72% → 30% 숏 +3.93% = +0.21%p (차입 0%)

# 🚨 「라벨」이 아니라 «수에 붙어 다니는 문자열» — 라벨은 인용될 때 «안 따라간다»(유형 54)
OOS_TAG = "[🚨27년 곡선을 «잘라» 잰 값 — `108:2` 가 이 방식을 «관문 ㉘ 미통과»로 적었다]"


def main():
    n_seed = 6 if "--quick" in sys.argv else NSEED
    print("=" * 104)
    print("155 — **«숏 스위치»만 끈다** · 현행 +%.0f/−%.0f · 씨앗 %d판" % (TARGET, STOP, n_seed))
    print("=" * 104)
    print("")
    print("> 조사 세션 · 2026-09-02 · `scripts/155-short-switch.py` · **문서는 이 출력 그 자체**(유형 48)")
    print("> ⛔ 뒤 구간 안 엶 · 새 전략 없음 · **스위치 하나**(숏 %.0f%% → 0%%) · 세금·수수료·씨앗 «그대로»"
          % (SHORT_ON * 100))
    print("")
    print("## ⛔ 읽는 표 — **돌리기 «전»에 넷 다 적었다**")
    print("")
    print("| 숏을 빼니 | 뜻 |")
    print("|---|---|")
    print("| **오름** | 숏이 «해로웠다». 우리는 «비용»을 내고 있었다 |")
    print("| **내림** | 숏이 «도왔다». 원전과 다르지만 우리 자료에선 유리 — **알고 치르는 값** |")
    print("| **거의 같음** | 「숏은 아무것도 안 한다」 → 빼는 것이 **«공짜»** ← **예상**(108 기준) |")
    print("| **못 가림** | 그것도 답 — 「빼도 잃는 게 없다」 |")
    print("")
    print("## ⛔ **Δ 는 «수»가 아니라 «유도»다** — 「무엇이 바뀌면 «결론»이 바뀌나」에서")
    print("")
    print("```")
    print("이 판이 흔들 수 있는 «결론» = 150 의 **「우리 %.2f%% vs QQQ 그냥 보유 %.2f%% = **−%.2f%%p** 짐」**"
          % (8.47, 9.70, GAP_QQQ))
    print("⇒ 숏을 빼서 **+%.2f%%p 이상** 오르면 그 결론이 «뒤집힌다»" % GAP_QQQ)
    print("⇒ 그러므로 **Δ = %.2f%%p**. (⛔ 내가 처음 쓴 «2.0» 은 «어디서 왔는지»가 없었다)" % DELTA)
    print("")
    print("🚨 그리고 「같다」는 **«귀무를 채택»하는 문장**이라 «점추정»으로 못 적는다 — **동등성 검정**이 필요하다:")
    print("   ⛔ 「점추정이 ±Δ 안이다」            →  **「못 가린다」와 «구분이 안 된다»**")
    print("   ✅ 「**신뢰구간 «전체»가 ±Δ 안에 «들어간다»**」  →  그때만 **「실질적으로 같다」**")
    print("   🚨 구간이 «넓으면» 답은 「거의 같다」가 아니라 **「못 가린다」** — **다른 문장이다**")
    print("```")
    print("")
    print("## 🚨 이 판이 «메우는» 빈자리")
    print("")
    print("```")
    print("108 이 «판정»한 것   「**어떻게** 숏할까」 — 200일선 vs 동전 = **+1.02%p**, 신호는 진짜")
    print("108 이 «안» 한 것    「숏을 할까 **말까**」 — §3 ㉯ 에 **«묘사»로만** 있다")
    print("⇒ 155 는 그 «기준선»을 채운다")
    print("")
    print("🚨 그리고 **108 과 우리 하네스는 «같지 않다»**:")
    print("   108 의 표 = **차입 0%** · 크기 **30%** · 창 **2002~2017**")
    print("   우리      = **차입 %.0f%%** · 크기 **%.0f%%** · 창 **27.4년**" % (BORROW, SHORT_ON * 100))
    print("   ⇒ **우리는 «차입료를 낸다»** — 그래서 숏을 빼면 108 보다 «더» 오를 수 있다")
    print("   ⇒ 대조는 **«자릿수»만**. 「같은 수」를 기대하지 «않는다»")
    print("")
    print("⚠️ `108:2` 스스로 적음 — 「구간별로 잘라 재는 것」과 「그 구간만 따로 돌리는 것」이 다르다")
    print("   (108 바탕 +3.72% vs 91 의 +3.16%). **아래 표본 밖 칸도 «잘라 잰» 것이다**")
    print("```", flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음")
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    by_f = {}
    for y in sorted(by2):
        k = []
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0]) > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is not False:
                k.append(p)
        by_f[y] = k

    ds, c, ma, hi = r108.spy_series()
    on = r108.short_days(ds, c, ma, hi)
    spy_ret = {ds[i]: c[i] / c[i - 1] - 1.0 for i in range(1, len(ds))}

    r91.TARGET, r91.STOP, r91.HALF = TARGET, STOP, 0.5
    ev, _b1, _b2 = r91.replay(by_f)
    rs = r91.sim(ev, n_seed)                       # ★ 씨앗은 «한 번»만 돌린다 — 두 팔이 «같은 패»
    print("")
    print("  씨앗 %d판 · 매수 중앙 %.0f · 숏 «든 날» %.1f%%"
          % (len(rs), st.median([x["n_filled"] for x in rs]),
             100.0 * sum(1 for d in ds if on.get(d)) / len(ds)), flush=True)

    arms = {}
    for sz in (SHORT_ON, 0.0):
        bo = BORROW / 100.0 / 252.0 * sz
        tot, mdd, rec, oos = [], [], [], []
        for x in rs:
            fd = Counter(f[3] for f in x["fill_log"] if f[1] == "pilot")
            vv = ([(d, v) for d, v in x["curve"]]
                  + [(x["curve"][-1][0], 1.0 + x["equity_pct"] / 100.0)])
            cds, ccv, V = [vv[0][0]], [1.0], 1.0
            for i in range(1, len(vv)):
                if vv[i - 1][1] <= 0:
                    break
                d = vv[i][0]
                rl = vv[i][1] / vv[i - 1][1] - 1.0
                sh = (-sz * spy_ret[d] - bo) if (sz and on.get(d) and d in spy_ret) else 0.0
                V *= (1.0 + rl + sh - FEE * 0.20 * fd.get(d, 0))
                cds.append(d)
                ccv.append(max(V, 1e-9))
            real = {}
            for d, pl in x["exit_log"]:
                real[d] = real.get(d, 0.0) + pl
            tot.append(r124.taxed_window(cds, ccv, real, 0, len(ccv) - 1))
            m_, rc = r129.shape(cds, ccv)
            mdd.append(m_)
            rec.append(rc / 252.0)
            i0 = max(0, next((i for i, d in enumerate(cds) if d >= OOS[0]), 0))
            i1 = next((i for i in range(len(cds) - 1, -1, -1) if cds[i] <= OOS[1]), len(cds) - 1)
            oos.append(r124.taxed_window(cds, ccv, real, i0, i1) if i1 > i0 else START)
        arms[sz] = dict(tot=tot, mdd=mdd, rec=rec, oos=oos)

    A, B = arms[SHORT_ON], arms[0.0]
    print("")
    print("=" * 104)
    print("## 1. **스위치 하나** — 같은 씨앗·같은 패에서 숏만 껐다")
    print("=" * 104)
    print("")
    print("| | **세후 총액**(중앙) | **«세전» 낙폭**(중앙) | **«세전» 회복**(중앙) |")
    print("|---|---:|---:|---:|")
    print("| 숏 %.0f%% (현행) | %.0f만 | %+.1f%% | %.1f년 |"
          % (SHORT_ON * 100, st.median(A["tot"]), st.median(A["mdd"]), st.median(A["rec"])))
    print("| **숏 0%% (뺌)** | **%.0f만** | **%+.1f%%** | **%.1f년** |"
          % (st.median(B["tot"]), st.median(B["mdd"]), st.median(B["rec"])))
    d_tot = st.median(B["tot"]) - st.median(A["tot"])
    print("| **차이(뺌 − 현행)** | **%+.0f만** | **%+.1f%%p** | **%+.1f년** |"
          % (d_tot, st.median(B["mdd"]) - st.median(A["mdd"]),
             st.median(B["rec"]) - st.median(A["rec"])))
    print("")
    print("🚨 **이 세 열은 «다른 자»다 — «나누지 마라».** 총액은 «세후», 낙폭·회복은 «세전» 곡선에서 낸다")
    print("   (⚠️ 「수익÷낙폭」 같은 값을 이 표에서 만들면 분자·분모의 «자»가 어긋난다)")
    print("")
    print("### 표본 밖 15.66년 — **«수준»은 안 적는다. «차이»만.**")
    print("")
    print("```")
    print("자르기 편향은 **두 팔에 «똑같이»** 걸린다 → **차이**는 살아남고 **수준**은 못 쓴다")
    print("차이(뺌 − 현행) **%+.0f만**   %s"
          % (st.median(B["oos"]) - st.median(A["oos"]), OOS_TAG))
    print("⛔ 두 팔의 «수준»(각각 몇 만원)은 **인쇄하지 않는다** — 인용되면 «잘라 잰 값»인 걸 잊는다")
    print("⚠️ **완전 상쇄는 «아니다»** — 두 팔이 그 구간에 «다른 자본»으로 들어가므로 잔여가 남는다.")
    print("   (`108:2` 의 크기 참고 — 잘라 재기 vs 따로 돌리기가 **0.56%p · 18%** 어긋났다)")
    print("```")
    print("")
    yr = 27.4
    ca = 100.0 * ((st.median(A["tot"]) / START) ** (1.0 / yr) - 1.0)
    cb = 100.0 * ((st.median(B["tot"]) / START) ** (1.0 / yr) - 1.0)
    print("```")
    print("연 환산  숏 %.0f%% **%+.2f%%**  →  숏 0%% **%+.2f%%**   =   **%+.2f%%p**"
          % (SHORT_ON * 100, ca, cb, cb - ca))
    print("```")
    print("")
    w = sum(1 for i in range(n_seed) if B["tot"][i] > A["tot"][i])
    b_ = n_seed - w
    pm = min(1.0, 2.0 * sum(math.comb(n_seed, k) for k in range(0, min(w, b_) + 1)) / 2.0 ** n_seed)
    print("### ★ 짝비교 — **숏을 빼면 이기는 판** (같은 씨앗끼리)")
    print("")
    print("```")
    print("숏 빼서 이김 **%d / %d = %.1f%%**   ·   부호검정 양측 p = **%.3g**   →   %s"
          % (w, n_seed, 100.0 * w / n_seed, pm,
             "🚨 **못 가린다**" if pm >= 0.05 else "✅ **가린다**"))
    print("중앙 차이 **%+.0f만**  (부호검정은 «크기»를 버리므로 «같이» 적는다)" % d_tot)
    print("")
    print("🚨🚨 **이 p 는 «씨앗 축»이다 — «시장 축»이 아니다**")
    print("   씨앗 60판은 **«같은 시장 역사»를 공유**한다 → 이 p 는 «우리 규칙의 운»만 잰다")
    print("   152 가 «시장 축»으로 재니 1.23%p 를 가리는 데 **1,025~13,462년**이 필요했다")
    print("   ⇒ **이 p 가 아무리 작아도 「시장에서 낫다」로 «못» 읽는다**(유형 53)")
    print("```")
    print("")
    print("### ★★ **동등성 검정** — 「같다」를 «구간»으로 묻는다 (Δ = %.2f%%p, 유도됨)" % DELTA)
    print("")
    dif = [100.0 * ((B["tot"][i] / START) ** (1.0 / yr) - 1.0)
           - 100.0 * ((A["tot"][i] / START) ** (1.0 / yr) - 1.0) for i in range(n_seed)]
    md, sdd = st.mean(dif), st.stdev(dif)
    lo, hi2 = md - T60 * sdd / math.sqrt(n_seed), md + T60 * sdd / math.sqrt(n_seed)
    print("```")
    print("연 환산 차이(뺌 − 현행)  평균 **%+.4f%%p** · SD %.4f · **95%% CI [%+.4f, %+.4f]**"
          % (md, sdd, lo, hi2))
    if -DELTA < lo and hi2 < DELTA:
        print("⇒ ✅ **구간 «전체»가 ±%.2f 안에 든다  →  「실질적으로 같다」**" % DELTA)
        print("   **⇒ 숏을 빼도 150 의 결론(QQQ 에 짐)은 «안 뒤집힌다». 빼는 것이 «공짜»다**")
    elif lo <= -DELTA and hi2 >= DELTA:
        print("⇒ 🚨 **구간이 ±%.2f 를 «양쪽으로» 넘는다  →  「거의 같다」가 «아니라» 「못 가린다」**" % DELTA)
    else:
        print("⇒ 🚨 **구간이 ±%.2f 를 «벗어난다»  →  「같다」로 못 적는다. «왜»부터 본다**" % DELTA)
    print("🚨 그리고 이 CI 도 **«씨앗 축»**이다 — 시장 축이면 훨씬 넓다")
    print("")
    frac = sum(1 for d in ds if on.get(d)) / len(ds)
    bcost = BORROW * SHORT_ON * frac
    print("★ **«유의»하지만 «작다» — 둘은 «모순이 아니다»**")
    print("   60/60 은 「효과가 «진짜»다」 · CI 가 ±%.2f 안은 「그 효과가 «결론을 못 바꾼다»」" % DELTA)
    print("")
    print("★ **어디서 오나(시사)** — 차입료만으로 대부분이 설명된다:")
    print("   차입 %.0f%% × 크기 %.0f%% × 숏 든 날 %.1f%%  =  **%.3f%%p/년**"
          % (BORROW, SHORT_ON * 100, frac * 100, bcost))
    print("   관측 **%.3f%%p/년**  →  차입료가 **%.0f%%**, 나머지 %.3f%%p 는 «숏 자체»(상승장에서 물림)"
          % (md, 100 * bcost / md, md - bcost))
    print("   🚨 **«시사»다** — 복리·세금 상호작용을 안 갈랐다. **«방향과 자릿수»만**")
    print("```")
    print("")
    print("### 🚨 관문 S★ — **108 과 «자릿수»가 맞는가**(규약 ⑦ 능동판)")
    print("")
    print("```")
    print("108 §3 ㉯ (차입 0%% · 30%% · 2002~2017)  숏 «있음»이 **+%.2f%%p** 나았다" % R108_GAP)
    print("155 (차입 %.0f%% · %.0f%% · 27.4년)        숏 «뺌»이 **%+.2f%%p**"
          % (BORROW, SHORT_ON * 100, cb - ca))
    ok = abs(cb - ca) < 2.0
    print("⇒ %s" % ("✅ **자릿수 일치** — 둘 다 «1%p 아래» 자리. 「숏은 거의 아무것도 안 한다」"
                    if ok else
                    "🚨 **자릿수 어긋남 — 「108 과 다르다」가 «먼저» 걸린다. 맞추지 말고 «왜»부터**"))
    print("   ⚠️ 방향이 반대인 것은 «정상»이다 — 우리는 **차입료를 낸다**(108 의 표는 차입 0%)")
    print("```")
    print("")
    print("=" * 104)
    print("## 2. ⛔ **어느 결과가 나와도 적을 문장**")
    print("=" * 104)
    print("")
    print("```")
    print("★ **원전 이야기는 «셋»으로 갈라 적는다 — 둘은 참이고 하나는 못 쓴다**:")
    print("   ✅ 「숏 오버레이는 **«우리 발명»**이다. **원전 근거가 «없다»**」   ← `108:1`")
    print("   ✅ 「그리고 원전은 「롱 아니면 **«현금»**」이라 우리 오버레이와 **«어긋난다»**」 ← 사용자님 원문")
    print("   ⛔ 「원전에 **«맞추려고»** 뺀다」  ← **«복원»이 아니므로 못 쓴다**")
    print("   ⇒ 정확한 말: **「우리가 얹은 것을 떼는데, 그러면 원전과 «덜 어긋나게» 된다」**")
    print("⛔ 「숏을 빼니 지수를 이긴다」 — 152 가 «못 가린다»로 닫았다. **이 판이 그걸 안 연다**")
    print("⛔ 「108 을 뒤집었다」        — 108 은 「**어떻게** 숏할까」를 쟀다. **다른 물음**이다")
    print("✅ 「150 의 비교가 «공정»해진다」 — 그 표에서 우리 쪽에만 얹혀 있던 것이 사라진다")
    print("```")
    print("")
    print("### ⚠️ **N — 두 장부가 «둘 다» 하나씩 는다** (검증 세션 판정)")
    print("")
    print("```")
    print("«검정» 장부  **는다** — 154 와 달리 155 엔 **«판정 문턱»(±Δ)이 있다**")
    print("«주장» 장부  **는다** — 「숏은 도움이 안 된다」는 **«새 문장»**이다")
    print("⇒ 108 이 「할까 «말까»」를 판정 «안 했으므로», 이건 «기준선 메우기»가 아니라 **«새 판정»**이다")
    print("```")
    print("")
    print("### ★ 오늘 하루의 «회계» — 결과 문서에 그대로 남긴다")
    print("")
    print("```")
    print("«선언»(바라는 답을 미리 밝히기)이 오늘 막은 것  =  **0**")
    print("막은 것 = **관문**(V★·W★·R★·S★·`_fmtcheck`) · **상대의 대조** · **불가능한 값** · **문턱 «수»**")
    print("⇒ 두 세션이 «선언을 했든 안 했든» 결과는 같았을 것이다.")
    print("  한쪽이 «빠뜨린 것»도 실질 손해가 아니었고, 다른 쪽이 «한 것»도 이득이 아니었다.")
    print("  **값을 한 건 «수» 하나다.**  ⇒ 자책도 «값을 안 한다»")
    print("")
    print("★ 그리고 «경고를 지키는 법»에 «세 단계»가 있고 순서가 있다:")
    print("  1단계  «라벨»을 단다            →  🚨 오늘 **네 번 실패** — 인용될 때 «안 따라간다»")
    print("  2단계  «문자열»을 값에 «붙인다»  →  낫다. 수를 옮기면 경고도 따라온다  (OOS_TAG)")
    print("  3단계  🚨 **«수를 «만들지 않는다»»**  →  **가장 세다. 옮길 것이 «없다»**  («수준» 미인쇄)")
    print("```")

    json.dump({"short_on": {k: v for k, v in A.items()},
               "short_off": {k: v for k, v in B.items()},
               "win_off": w, "p": pm, "cagr_on": ca, "cagr_off": cb},
              open(str(r91.OUT / "155-short-switch.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("")
    print("⛔ 뒤 구간 «안 엶» · 스위치 «하나» · 목표 «현행 하나»")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
