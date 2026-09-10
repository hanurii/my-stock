# -*- coding: utf-8 -*-
"""_facts_seed — 장부 «첫» 씨앗 (26-09-10)

  ★ 「인용 금지」가 «붙은» 파일이 **79** 개다. 그 «라벨»은 «인용»될 때 «안» 따라간다(유형 54).
    ⇒ **«이미» «퍼진» 수**를 장부에 «올려» **«철회»로** 두면 — 「조회」가 «가로챈다».

  🚨 **여기 «넣지» «않는» 것**(유형 101 — 「«못» 쓸 수는 «아예» «적지» 않는다」):
     `196b` 의 **0.79%** — **«한 번»도 «안» 퍼졌다** ⇒ «가로챌» 것이 «없다** ⇒ **«안** 넣는다
     ⇒ ★ 가른 자: **「그 수가 «이미» «퍼졌나»」**. «안» 퍼진 수를 넣으면 **«장부»가 «퍼뜨린다»**

  ⚠️ **일곱 «전부» `provenance="doc"`** 이다 — «스크립트»를 «돌려» 낸 것이 «아니라»
     **«문서 줄»에서 «읽은»** 것이다. ⇒ **«약하다». `audit()` 이 «세어» 찍는다.**
     ⇒ ★ **«올릴» 자리**: 그 판을 «다시» 돌릴 때 `provenance="script"` 로 «바꾼다**
"""
from __future__ import annotations

import _facts as F

ASOF = "2026-09-09"
ADDED = "2026-09-10"

# ── ① «살아» 있는 수 ────────────────────────────────────────────────────────────
LIVE = [
    dict(key="235.mde-min.acct-pp-year.us27y", value=2.56, unit="%p",
         measures="가릴 수 있는 최소 효과(MDE)", ruler="계좌 %p/해",
         scope="미국 27.4년 · 여덟 짝 · 고친 자",
         defn="자료 축 블록 부트스트랩 · 여덟 짝 · `232c` 단위 결함 «고친 뒤»",
         doc="results/_STATUS.md:113"),
    dict(key="188.delta-gap.acct-pp-year.us27y", value=1.23, unit="%p",
         measures="메워야 할 격차(Δ)", ruler="계좌 %p/해",
         scope="미국 27.4년 · 우리 vs QQQ",
         defn="세후 연환산 차 — 결정을 «바꾸는» 크기로 «지정»된 값",
         doc="results/190-what-is-closed.md:554"),
    dict(key="150.cagr.aftertax-pct.us27y-ours", value=8.47, unit="%",
         measures="연환산 수익률(세후)", ruler="계좌 %/해",
         scope="미국 27.4년 · 우리 전략(+30/−10)",
         defn="세후 · 숏 «제거» 뒤 · 슬롯 5칸",
         doc="results/150-final-tally.md:30"),
    dict(key="150.cagr.aftertax-pct.us27y-qqq", value=9.70, unit="%",
         measures="연환산 수익률(세후)", ruler="계좌 %/해",
         scope="미국 27.4년 · QQQ 그냥 보유",
         defn="세후 · 파라미터 «0 개»인 «유일한» 기준(유형 30·50)",
         doc="results/150-final-tally.md:32"),
]

# ── ② «퍼진» 뒤 «철회»된 수 — 「조회」가 «가로챈다» ──────────────────────────────
RETRACTED = [
    dict(key="188.mde-min.acct-pp-year.us27y", value=1.793, unit="%p",
         measures="가릴 수 있는 최소 효과(MDE)", ruler="계좌 %p/해",
         scope="미국 27.4년 · 여덟 짝 · 고친 자",
         defn="⚠️ «옛» 자 — `boot_eq` 의 「자리」가 `183` 이후 「진입일만」이었다",
         doc="results/190-what-is-closed.md:18",
         supersede_by="235.mde-min.acct-pp-year.us27y",
         reason="`232c` — `boot_eq` 「자리」가 「진입일만」인데 「보유」는 「거래일」이라 «단위»가 «달랐다». "
                "«고친» 자로 «다시» 낸 수는 `235.mde-min.acct-pp-year.us27y` = 2.56 이다."),
    dict(key="110.return-per-drawdown.ratio.us27y-vs-qqq", value=1.59, unit="배",
         measures="수익÷낙폭 비(우리÷QQQ)", ruler="수익÷낙폭",
         scope="미국 27.4년 · «옛» 규칙(+20/−8)",
         defn="⚠️ «옛» 규칙의 수 — 제목이 「손절 −8%」다(`110-fair-fight.md`)",
         doc="results/190-what-is-closed.md:227",
         reason="«옛» 규칙(+20/−8)의 수다. «현행»(+30/−10 · 숏 «없음»)으로는 «다시» «안» 냈다. "
                "⛔ 「현행이면 1.07배」도 «여기» «올리지» 않는다 — 그 수의 «자격»을 «내»가 «확인»하지 «못했다». "
                "⇒ 「현행 규칙의 수」가 «필요»하면 `192b-risk-mde.md` 를 «직접» 읽는다."),
    dict(key="23c.null-max95.acct-pp.ratchet12", value=87.47, unit="%p",
         measures="귀무 최대 95% 분위", ruler="계좌 %p",
         scope="래칫 12칸 격자",
         defn="⚠️ 출처가 «결과 문서»에 «없고» `scripts/23c-boot-and-maxstat.py` 에«만» 있었다",
         doc="results/190-what-is-closed.md:4519",
         reason="`183a` — 재표집이 «가장자리»를 «덜» 써 귀무가 «좁게» 나온다 ⇒ «참» 문턱은 «이보다» «크다». "
                "⇒ 「87.47」이라는 «수»를 «인용»하지 «말고» 「«참» 문턱은 «이보다» «크다»」로 «바꿔» 쓴다. "
                "★ «규칙»(「고르기 금지」)은 «안» 흔들린다 — «수치 문턱»으로 «쓰인» 적이 «없다."),
]


def main():
    n = 0
    for r in LIVE:
        F.put(provenance="doc", asof=ASOF, added=ADDED,
              **{k: v for k, v in r.items()})
        n += 1
    for r in RETRACTED:
        sup = r.pop("supersede_by", None)
        reason = r.pop("reason")
        F.put(provenance="doc", asof=ASOF, added=ADDED, **r)
        if sup:
            F.supersede(r["key"], sup)
            F.retract(r["key"], reason)
            # supersede 뒤 retract — «까닭»을 «남기고» 상태는 「철회」로 «굳힌다»
        else:
            F.retract(r["key"], reason)
        n += 1
    print("올린 항목: %d" % n)


if __name__ == "__main__":
    main()
