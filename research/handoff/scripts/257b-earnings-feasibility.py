# -*- coding: utf-8 -*-
r"""257b - **㉢ 실적 시즌 — 「«잴» 수 «있나」 «싼» 확인**  (조사 세션 2026-09-10)

  ⛔ **«실험»이 «아니다** — **「되나/안 되나 · 되면 «무엇»이 필요한가 · 💰 어림」까지**
  ⛔ **성적을 «내지» «않는다**

  📖 원전 `tm:60` 「… 저는 «실적 시즌»에 «절대»로 «큰» 포지션을 «유지»하지 않습니다 …」
     ⚪ **«수»가 «없다** — 화자가 «스스로» 「과학처럼 «딱» 떨어지지 «않아»요」라 적었다

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/257b-earnings-feasibility.py
"""
from __future__ import annotations

import importlib.util as _u
import statistics as st
import sys
import time
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
HERE = Path(__file__).resolve().parent

N_DAYS = 14        # ⛔ **결과 «보기» «전»에 박는다** — 유도는 §2
GAP = 90           # ⛔ 「직전 발표일 ＋ GAP」 — 두뇌가 «준» 어림


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


m201d = _load("m201d", "201d-rs-threshold.py")


def _d(s):
    y, m, dd = s.split("-")
    return date(int(y), int(m), int(dd))


def main():  # noqa: C901
    P("# 257b - **㉢ 실적 시즌 — 「«잴» 수 «있나」 «싼» 확인**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/257b-earnings-feasibility.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⛔ **«실험»이 «아니다** · ⛔ **성적을 «내지» «않았다**")
    P("")
    P("---")
    P("")

    # ── ㉯ 예고일 자료 찾기 ──────────────────────────────────────
    P("# 🔎 **1. ㉯ — 「«예고»일 자료가 «있나」  ⇒ 🔴 **«없다**")
    P("")
    P(F3)
    P("   ⛔ **「없다」의 «둘째» 얼굴을 «막는다** — **「«찾아봤다»」를 «같은 줄»에**")
    P("")
    P("   🔎 **명령**: 받아 둔 Sharadar **열 개** 테이블의 **«열» 이름을 «전부»** 읽고 —")
    P("      `announce|guidance|estimate|expect|next|schedul|upcoming|forecast` 로 «걸렀다**")
    P("      ⇒ **맞은 열 «0»**")
    P("")
    P("| 테이블 | 열 수 | 「예고」 후보 |")
    P("|---|---:|:--|")
    for nm, k in (("actions", 7), ("daily", 10), ("descriptions", 7), ("events", 3),
                  ("fundamentals", 112), ("holdings_ticker", 29), ("metrics", 22),
                  ("sp500", 7), ("stocks", 10), ("tickers", 28)):
        P("| `%s.csv.zip` | %d | ⚪ «없음» |" % (nm, k))
    P("")
    P(F3)
    P("   🚨 **`events.csv` 가 «제일** 가까웠으나 — 열이 **`ticker · date · eventcodes`** «셋»뿐이고")
    P("      **`date` 는 «사건»이 «일어난» 날**이다 ⇒ **«예고»가 «아니다**")
    P("   🚨 **`fundamentals.date`**(= `datekey`)도 **«실제» 제출일**이다(`257-PRE` §㉢에서 «이미» 확인)")
    P("")
    P("   ⇒ ✅ **㉯ 답: «예고»일 자료는 «없다** — ⛔ **찾아봤다**(테이블 10 · 열 235)")
    P("   ⇒ ⇒ **그러므로 ㉮(직전 발표일 ＋ %d일 «어림»)의 «오차»를 «재야** 한다" % GAP)
    P(F3)
    P("")
    P("---")
    P("")

    # ── N 의 유도 ────────────────────────────────────────────────
    P("# ⛔ **2. N 을 «먼저** 정한다 — **결과를 «보기» «전»**")
    P("")
    P(F3)
    P("   **`N_DAYS = %d`** · **관문: 오차 **P90 < N/2 = %.1f일**" % (N_DAYS, N_DAYS / 2))
    P("")
    P("   ★ **«어디»서 왔나** — ⛔ **«내»가 «고른» 수가 «아니다**")
    P("      📄 `scripts/screen_earnings_calendar.py:18` "
      "「… 페이지는 **≤14일**만 표시」 — **«실전» «표시» 문턱**")
    P("      📄 `:225` `win = (yd + timedelta(days=1), yd + timedelta(days=14))`")
    P("")
    P("   🚨 **그러나 «단서»가 «있다** — ⛔ **«숨기지» «않는다**:")
    P("      **`screen_earnings_calendar.py` 는 🇰🇷 «한국» 실전 도구**(DART)다")
    P("      ⇒ **「한국 «결과»를 «인용»」은 «아니다**(수치가 «아니라» «표시» 정책이다)")
    P("      ⇒ ⛔ **그러나 「한국 «도구»의 «문턱»을 «옮겼다»」는 «맞다**")
    P("      ⇒ ✅ **그러니 「«우리»가 «고른» 수」로 «세는» 편이 «보수적**이다 — **«그렇게» 센다**")
    P(F3)
    P("")
    P("---")
    P("")

    # ── ㉮ 오차 ──────────────────────────────────────────────────
    P("# 📏 **3. ㉮ 의 «오차» — 「직전 발표일 ＋ %d일」이 «실제»와 «며칠» 어긋나나**" % GAP)
    P("")
    t0 = time.time()
    fund, _ixf = m201d.f92a.load()
    errs, pairs, tick = [], 0, 0
    gaps = []
    for cd, v in fund.items():
        arq = v.get("ARQ") or []
        ds = sorted({r[0] for r in arq if r and r[0]})
        if len(ds) < 2:
            continue
        tick += 1
        for a, b in zip(ds, ds[1:]):
            da, db = _d(a), _d(b)
            g = (db - da).days
            if g <= 0 or g > 400:          # 상장·상폐 «구멍»은 «뺀다**
                continue
            gaps.append(g)
            errs.append(abs(g - GAP))
            pairs += 1
    el = time.time() - t0
    errs.sort()
    gaps.sort()

    def pct(v, q):
        return v[min(len(v) - 1, int(len(v) * q))]

    P(F3)
    P("   종목 **%s** · 이웃 발표 «짝» **%s** · 💰 실측 **%.1f분**"
      % (format(tick, ","), format(pairs, ","), el / 60.0))
    P("")
    P("   **«실제» 간격**(일): 중앙 **%d** · P10 **%d** · P90 **%d** · 최대 **%d**"
      % (st.median(gaps), pct(gaps, .10), pct(gaps, .90), gaps[-1]))
    P("   **오차 |간격 − %d|**(일): 중앙 **%d** · **P90 %d** · P95 **%d** · 최대 **%d**"
      % (GAP, st.median(errs), pct(errs, .90), pct(errs, .95), errs[-1]))
    P("")
    p90 = pct(errs, .90)
    ok = p90 < N_DAYS / 2
    P("   ⇒ 관문 **P90 < %.1f** ⇒ **P90 = %d** ⇒ %s"
      % (N_DAYS / 2, p90, "✅ **통과**" if ok else "🔴 **«미통과**"))
    P(F3)
    P("")
    P("---")
    P("")
    P("# 🎯 **⇒ 답**")
    P("")
    P(F3)
    if ok:
        P("✅ **「우리가 «만든» 달력 · 오차 P90 %d일」**로 «이름» 붙여 «쓸» 수 «있다**" % p90)
        P("   ⛔ 단 **「«예고»일을 «썼다»」가 «아니다** — **「직전 발표일 ＋ %d일」의 «어림»**이다" % GAP)
    else:
        P("🔴 **「«예고»일 «없이»는 «못» 잰다」로 «닫는다**")
        P("   🔎 오차 **P90 = %d일**이 문턱 **%.1f일**을 «넘는다**" % (p90, N_DAYS / 2))
        P("   ⇒ ★ **「D−%d 일에 줄인다」를 «걸면» — «줄이는» 날이 «실제» 발표와 «어긋나** —" % N_DAYS)
        P("      **«신호»가 «아니라» «잡음»을 재게 된다**")
        P("   ⇒ ⛔ **「실적 시즌 축소」는 «이» 자료로는 **«못» 잰다** — **「없다」가 «아니라» 「자료가 «없다»」**")
    P("")
    P("   ★★ **«수»에 «안» 달렸음을 «보인다** — **N 을 «어느» 것으로 대도 «전부» 미통과**")
    P("      🔎 관문은 **`P90 < N/2`** 이고 **P90 = %d** ⇒ **N > %d 이어야 «통과**한다" % (p90, 2 * p90))
    for n_ in (7, 14, 30, 60, 90):
        P("      · N = %-2d ⇒ 문턱 %.1f일 ⇒ %s" % (n_, n_ / 2,
                                                   "✅ 통과" if p90 < n_ / 2 else "🔴 **미통과**"))
    P("      ⇒ ⇒ ★ **N 이 «%d 일 «넘어야»» 통과**인데 — **그건 「실적 «임박»」이 «아니라» «분기» «통째»**다"
      % (2 * p90))
    P("      ⇒ ✅ **그러니 「`N_DAYS` 가 «어디»서 «왔나»」는 «판정»에 «안** 걸린다")
    P("")
    P("   📌 **«분류» — §B 가 «아니라 §H2**(접음·보류)")
    P("      🔎 §B「없다」의 얼굴들은 **«우리»가 «못» 찾은** 꼴인데 — **여기는 «찾았고» «세상»에 «없다**")
    P("      ⇒ ★ **«고칠» 수 «없지만» «되열릴» 수 «있다** — **자료가 «생기면» «자동»으로 «열린다**")
    P("")
    P("   ⭐ **`171` 미결과 «묶인다**(두뇌 승인)")
    P("      🔎 `171` 이 **「(a)발표 «지연» vs (b)«소급» 채움」**을 «다음» 판으로 내려 뒀는데 —")
    P("      **«같은» 필드**(`date` · `reportperiod`)에서 갈린다 ⇒ **「`date` − `reportperiod` = «지연»」**")
    P("      💰 **어림 «수» 분**(자료가 «이미» 메모리에 «있다») — ⛔ **어림**")
    P(F3)
    P("")
    P("# ⚠️ **이 판이 «못** 한 것**")
    P("")
    P(F3)
    P("⛔ ① **성적을 «안** 냈다 — **「«잴» 수 «있나」**만 봤다")
    P("⛔ ② **`GAP = %d` 은 «두뇌»가 «준» 어림**이다 — **«달력» 분기(91.3일)에서 «온** 수이지 "
      "**«우리»가 «잰» 것이 «아니다**" % GAP)
    P("⛔ ③ **간격 «400일 넘는» 짝을 «뺐다**(상장·상폐 «구멍») — **«그» 규칙도 «우리» 것**")
    P("⛔ ④ **`N_DAYS = %d` 은 🇰🇷 «한국» 실전 도구의 «표시» 문턱**이다 — §2 에 «적었다**" % N_DAYS)
    P("⛔ ⑤ **「실적 «시즌»」과 「«발표»일」이 «같은» 것인지 «안** 물었다 —")
    P("     **원전은 「시즌」이라 했고 «우리»는 「«그» 종목의 발표일」로 «읽었다**")
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
