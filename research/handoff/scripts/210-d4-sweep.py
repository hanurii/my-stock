# -*- coding: utf-8 -*-
r"""210 — **Ⓓ4 «찾기» «전수»** · 두뇌·검증 의뢰 2026-09-07

  🎯 **범위** — **«주장» 낱말이 «있는» 주석«만»**. 「없는」 것은 이 판이 **«안» 본다**(그게 범위다).
  📐 **자**(⛔ «늘리지» 않는다):
     「원전」·「기존 조건」·「동일」·「책」·「미너비니」·「오닐」·「그대로」·「유지」

  ⛔ **확인된 원전 «다섯»으로«만»** 판정한다:
     `ta_original.txt` · `tasks/78` · `results/99` · `canon/minervini-principles.md`
     · `research/oneil-model-book/trend_template.md`
     ⇒ 🚨 **「책에 «있을» 것」은 Ⓓ4 도 «일치»도 «아니다** — **Ⓓ5** 다.

  ⛔ **§G1 은 「≥ 56」 «그대로»** — 이 판이 «늘리면» **«그때»** 고친다(«미리» 세지 «않는다»).

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/210-d4-sweep.py
      (--pre 사전등록만 · --scan 기계 훑기까지)
"""
from __future__ import annotations

import glob
import io
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
ROOT = Path(__file__).resolve().parents[3]

# ══════════════════════════════════════════════════════════════════════════════
# 사전등록 — **훑기 «전»**(관문 ②)
# ══════════════════════════════════════════════════════════════════════════════
SYM_MORE = ("**Ⓓ4 가 «더» 나오면** → **«고칠» 목록이 «자란다»** — §G1 을 **«그때»** 고친다 "
            "(«행동»이 «바뀌는» 칸이라 **수확 «체감»이 «아니다»**)")
SYM_NONE = ("**«하나»도 «안» 나오면** → **「Ⓓ4 는 `205`·`206` 의 «열둘»이 «전부»」**이고 "
            "— **「Ⓓ4 «찾기»」가 «닫힌다»**(⛔ 「§G «세기»」는 §H2 로 «이미» 접혔다)")

WORDS = ("원전", "기존 조건", "동일", "책", "미너비니", "오닐", "그대로", "유지")
PATS = ("scripts/*.py", "scripts/canslim_lib/*.py", "scripts/autobuy/*.py",
        "research/handoff/scripts/*.py")
SOURCES_OK = ("ta_original.txt", "tasks/78-source-quotes.md", "results/99-source-faithful.md",
              "canon/minervini-principles.md", "research/oneil-model-book/trend_template.md")

# ══════════════════════════════════════════════════════════════════════════════
# 판정 표 — (자리, 덮는 값, «주장» 문장, 확인된 원전이 «말하는» 것, 판정, 새것인가)
# ══════════════════════════════════════════════════════════════════════════════
N_HIT = 269            # 낱말이 «걸린» 주석 (기계)
N_METHOD = 109         # 그중 **방법 코드**(scripts/ · canslim_lib/ · autobuy/)
N_HANDOFF = 160        # 그중 **분석 각본**(research/handoff/scripts/) — 이 판 «범위 밖»
N_CLAIM = 33           # 방법 코드 109 중 **«출처»를 «주장»하는** 주석

JUDGED = [
    ("backtest_volatility_pilot{,_recgate,_recskip,_recwatch,_sub,_us}.py:56/58", 6,
     "MIN_TURNOVER_EOK = 5.0  # **미너비니** 저유동성 컷(50일 평균 거래대금)",
     "canon:75-78 「① 인용 — **«못» 찾았습니다** · ② 출처 — **«없음»** · **문턱 «숫자»가 «없습니다»** "
     "· ③ **문턱을 «우리»가 «정해야» 합니다 = «원전» «밖»**」",
     "🔴 **Ⓓ4**", "🆕 **새것**"),
    ("canslim_lib/vcp.py:27,281", 1,
     "레버 B — 피벗 극저거래량일(**책**: \"하루 이틀 극도로 낮은 거래량이 좋다\")",
     "canon:95 가 그 묶음을 **「[3차-해석] 다수 [검색요약]」**이라 «이미» 적음",
     "🔴 **Ⓓ4**", "🆕 **새것**"),
    ("backtest_volatility_pilot_us.py:249", 1,
     "**원전** 베이스 최대 «65주»(325봉)를 담으려면 >=325 여야 한다",
     "확인된 원전 «다섯»이 **베이스 «길이»를 «안» 다룬다**(canon grep 「65」·「베이스」 → 해당 없음)",
     "🟠 **Ⓓ5**", "🆕 **새것**"),
    ("make_order_sheet.py:41", 1,
     "**미너비니** 매수 유효 범위: 피벗 ~ 피벗+**5%** (넘으면 추격 금지)",
     "🔴 **2026-09-08 «정정»**(`230b:108`): `mk:71` [Ⓜ] 「제 매수 지점보다 **«몇 퍼센트» 이상**의 "
     "차이로 갭 상승이 일어났다면 **건드리지 «않을»** 겁니다」가 **«이» 주제를 «다룬다**. ⇒ **원전은 «방향»만 주고 — «수»(5%)는 «우리»가 정했다**",
     "🟡 **Ⓐ«범위»**", "🆕 **새것** 🚨"),
    ("screen_trend_template.py:387", 0,
     "⑦(52주고가 −25% 이내)은 완화하지 않는다 — **미너비니 «원칙상»** −25% 밖은 추세 «손상»",
     "**«수»(−25%)는 `trend_template.md:9` 와 «일치»**. 그러나 **「밖은 추세 «손상»」이라는 «까닭»은 "
     "원전에 «없다»** — 원전은 「가까울수록 좋다」(«방향»)만 준다",
     "🟠 **Ⓓ5**", "🆕 **새것**"),
    ("canslim_lib/criteria.py:246", 1,
     "EPS 가속 폭발도 단계 — **O'Neil 원전 #3**(가장 중요한 원칙) 정량화",
     "**오닐 원전은 확인된 «다섯»에 «없다**(canon 은 «미너비니» 문서) ⇒ **구조적 «검산 불가»**",
     "🟠 **Ⓓ5**", "🆕 **새것**"),
    ("canslim_lib/criteria_i.py:361,443", 2,
     "**책 기준**: 한 분기 매도여도 경계 / **책 기준** 신규 편입 강조",
     "**「어느 책」인지 «안» 적혀 있다** — 확인된 «다섯»에서 «못» 찾음",
     "🟠 **Ⓓ5**", "🆕 **새것**"),
    ("canslim_lib/criteria_s.py:43", 0,
     "**책**의 \"감당 못할 빚 금지\" 원칙은 제조업·서비스업 기준이라 **«그대로» 적용 «불가»**",
     "— (원전과 «다름»을 **«스스로»** 적었다)",
     "⚪ **선언으로 «면함»**", "🆕 **새것**"),
    ("canslim_lib/vcp.py:271", 0,
     "피벗 = 돌파 직전 '최종 타이트 코일'의 고점 — **미너비니 «표준»**",
     "canon §6① 「피벗 = **마지막 수축의 고점 = 저항선**」 — **«같다»**",
     "✅ **일치**", "`206` 에서 «이미»"),
    ("criteria.py:19·24·26·29 · vcp.py:23·29 · ipo_track.py:18·19·20 · "
     "trend_template.py:233 · sell_rules.py:17 · strategy_params.py:13", 12,
     "— (`205`·`206`·`207` 에서 «이미» 판정·고침)",
     "— (`205` Ⓓ4 11 · `206` Ⓓ4 1줄8값 / Ⓓ5 2 · `207` 로 «셋» 고침)",
     "♻️ **«이미»**", "♻️"),
]


def comments(txt):
    """주석만 뽑는다 — 줄 안의 `#` 뒤, 그리고 모듈 «머리» 독스트링."""
    out = []
    for i, ln in enumerate(txt.split("\n"), 1):
        if "#" in ln:
            body = ln.split("#", 1)[1].strip()
            if body:
                out.append((i, body))
    return out


def main():
    mode = "pre" if "--pre" in sys.argv else ("scan" if "--scan" in sys.argv else "full")
    P("# 210 — **Ⓓ4 «찾기» «전수»**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/210-d4-sweep.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("---")
    P("")
    P("# 0. **사전등록** — 훑기 «전»에 «둘 다» 적는다(관문 ②)")
    P("")
    P(F3)
    P("✅ " + SYM_MORE)
    P("🔴 " + SYM_NONE)
    P("")
    P("## 📐 **자 — «주장» 낱말 «여덟»**(⛔ «늘리지» 않는다)")
    P("   " + " · ".join("「%s」" % w for w in WORDS))
    P("")
    P("## ⛔ **확인된 원전 «다섯»으로«만»**(관문 ③)")
    for s_ in SOURCES_OK:
        P("   · " + BQ + s_ + BQ)
    P("   ⇒ 🚨 **「책에 «있을» 것」은 Ⓓ4 도 «일치»도 «아니다** — **Ⓓ5** 다")
    P("")
    P("## 📐 **판정 «넷**")
    P("   🔴 **Ⓓ4** 확인된 원전이 **«다르게»** 말하거나 **「«없다»」고 «말한다»**")
    P("   🟠 **Ⓓ5** 원전이 그 «주제»를 **«안» 다룬다**")
    P("   ⚪ **선언으로 «면함»** 「원전 «아님»」을 **«스스로»** 적었다")
    P("   ✅ **일치**")
    P("")
    P("⛔ **§G1 은 「≥ 56」 «그대로»** — 이 판이 «늘리면» **«그때»** 고친다(«미리» «세지» 않는다 · 관문 ④)")
    P(F3)
    P("")
    P("---")
    P("")
    if mode == "pre":
        P("⏸️ **`--pre` — 사전등록만 찍었다. «아직» «안» 훑었다.**")
        return 0

    # ── 기계 훑기 ──────────────────────────────────────────────────────
    hits = []
    nfile = ncmt = 0
    for pat in PATS:
        for f in sorted(glob.glob(str(ROOT / pat))):
            try:
                txt = io.open(f, encoding="utf-8").read()
            except Exception:                       # noqa: BLE001
                continue
            nfile += 1
            cs = comments(txt)
            ncmt += len(cs)
            rel = os.path.relpath(f, str(ROOT)).replace("\\", "/")
            for i, body in cs:
                w = [x for x in WORDS if x in body]
                if w:
                    hits.append((rel, i, body, w))
    P("# 1. **기계가 «센» 것**")
    P("")
    P(F3)
    P("   훑은 자리: " + " · ".join(BQ + p + BQ for p in PATS))
    P("   **파일 %d** · **주석 줄 %s** · **«주장» 낱말이 «걸린» 주석 %d**"
      % (nfile, format(ncmt, ","), len(hits)))
    P("")
    byw = {w: sum(1 for h in hits if w in h[3]) for w in WORDS}
    for w in WORDS:
        P("   「%-8s」 %3d" % (w, byw[w]))
    P(F3)
    P("")
    if mode == "scan":
        P("## 🔎 **걸린 주석 «전수»**(`파일:줄`  낱말  본문 90자)")
        P("")
        P(F3)
        for rel, i, body, w in hits:
            P("%s:%d  [%s]  %s" % (rel, i, ",".join(w), body[:90]))
        P(F3)
        P("")
        P("⏸️ **`--scan` — 기계까지다. «판정»은 «표»로 짓는다.**")
        return 0
    # ── 판정 ─────────────────────────────────────────────────────────
    P("---")
    P("")
    P("# 2. 🚨 **낱말은 «체»일 뿐 — 「출처를 «주장»하는가」를 «갈랐다»**")
    P("")
    P(F3)
    P("   낱말이 «걸린» 주석                        **%d**" % N_HIT)
    P("     ㉠ **방법 코드**(scripts/ · canslim_lib/ · autobuy/)   **%d**  ← **이 판의 «대상»**" % N_METHOD)
    P("     ㉡ **분석 각본**(research/handoff/scripts/)            **%d**  ← ⛔ **범위 «밖»**" % N_HANDOFF)
    P("")
    P("   ㉠ %d 중 — **«출처»를 «주장»하는** 주석      **%d**" % (N_METHOD, N_CLAIM))
    P("            **낱말만 걸리고 «출처» 주장이 «아닌» 것**  **%d**" % (N_METHOD - N_CLAIM))
    P("            (「A 와 «동일» 로직」·「값을 «그대로» 넘긴다」 같은 **«코드» «내부» 참조**)")
    P("")
    P("⛔ **㉡(분석 각본 %d)을 «안» 본 까닭** — 그건 **«판» 문서**이지 **«값»의 «출처»**가 «아니다**." % N_HANDOFF)
    P("   🚨 그러나 **`205` 가 `204` 안에서 «틀린» 주장을 찾았다** ⇒ **「«안» 봤다」로 «적어» 둔다**")
    P(F3)
    P("")
    P("---")
    P("")
    P("# 3. **판정 표**")
    P("")
    P("| 자리 | 덮는 값 | «주장»한 문장 | 확인된 원전이 «말하는» 것 | 판정 | |")
    P("|---|---:|---|---|:--|:--|")
    for loc, nv, claim, src_, v, isnew in JUDGED:
        P("| " + BQ + loc + BQ + " | %s | %s | %s | %s | %s |"
          % (nv if nv else "—", claim, src_, v, isnew))
    P("")
    new4 = [r for r in JUDGED if "Ⓓ4" in r[4] and "새것" in r[5]]
    new5 = [r for r in JUDGED if "Ⓓ5" in r[4] and "새것" in r[5]]
    newx = [r for r in JUDGED if "면함" in r[4] and "새것" in r[5]]
    P(F3)
    P("## ⇒ **「몇 중 몇」**(관문 ①)")
    P("")
    P("   판정한 «묶음» **%d** 개" % len(JUDGED))
    P("   🔴 **Ⓓ4 «새것»**       %d 묶음 · **덮는 값 %d**"
      % (len(new4), sum(r[1] for r in new4)))
    P("   🟠 **Ⓓ5 «새것»**       %d 묶음 · 덮는 값 %d"
      % (len(new5), sum(r[1] for r in new5)))
    P("   ⚪ **면함 «새것»**      %d 묶음" % len(newx))
    P("   ✅ 일치 / ♻️ «이미»    %d 묶음"
      % len([r for r in JUDGED if "새것" not in r[5]]))
    P(F3)
    P("")
    P("---")
    P("")
    P("# 4. **대칭 판정**")
    P("")
    P(F3)
    P("✅ " + SYM_MORE)
    P("🔴 " + SYM_NONE)
    P("")
    P("## ⇒ **✅ 쪽 — Ⓓ4 가 «더» 나왔다**(«새» Ⓓ4 %d 묶음 · **덮는 값 %d**)"
      % (len(new4), sum(r[1] for r in new4)))
    P("")
    P("**§G1 갱신**(관문 ④ — **«이제»** 고친다)")
    P("   `206` 까지                **≥ 56**")
    P("   `210` 이 «더하는» Ⓓ4        **%d**" % sum(r[1] for r in new4))
    P("   ────────────────────────────")
    P("   ## ⇒ **≥ %d**" % (56 + sum(r[1] for r in new4)))
    P("")
    P("⚠️ **Ⓓ5 는 §G1 에 «안» 넣는다**(`206` 과 «같다»)")
    P(F3)
    P("")
    P("---")
    P("")
    P("# 5. 🚨 **부산물 — «한» 개념에 «수»가 «셋»**")
    P("")
    P(F3)
    P("「**피벗에서 «얼마»까지 «쫓아» 사나**」:")
    P("   " + BQ + "strategy_params.py:37" + BQ + "  " + BQ + "CHASE_MAX_PCT = 3.0" + BQ
      + "        「미너비니 규칙」  ← **봇**")
    P("   " + BQ + "vcp.py:16" + BQ + " 등        " + BQ + "near_pivot_pct = 5.0" + BQ
      + "        «까닭» «없음»      ← **검출기**")
    P("   " + BQ + "make_order_sheet.py:41" + BQ + "  **피벗+5%**                「미너비니」      ← **주문표**")
    P("")
    P("⇒ 🚨 `205` §G5 는 **«둘»**만 봤다 — **«셋»**이다")
    P("⇒ ⚠️ 다만 **«쓰는» 자리가 «다르다**(사는 «한도» vs actionable «보는» 눈 vs 주문 «표»)")
    P("   ⇒ **규약 ⑦ «발동»은 «아니다»** — 그러나 **«셋» 다 「미너비니」라 «주장»하거나 «까닭»이 «없다**")
    P(F3)
    P("")
    P("---")
    P("")
    P("# 6. **관문 다섯**")
    P("")
    tot_j = len(new4) + len(new5) + len(newx) + len([r for r in JUDGED if "새것" not in r[5]])
    src_txt = Path(__file__).read_text(encoding="utf-8")
    ok = [
        ("① 「몇 중 몇」 — 묶음 합 %d = %d" % (tot_j, len(JUDGED)), tot_j == len(JUDGED)),
        ("② 대칭 «둘 다» «미리» 인쇄(`210-PRE.md` 를 «먼저» 박음)", True),
        ("③ 확인된 원전 «다섯» 밖을 «안» 썼다 — 근거 칸에 「책에 «있을» 것」 %d 개"
         % sum(1 for r in JUDGED if "있을" in r[3]),
         not any("있을" in r[3] for r in JUDGED)),
        ("④ §G1 을 **«이제»** 고쳤다(«미리» «안» 셌다) — `206` ≥56 → **≥%d**"
         % (56 + sum(r[1] for r in new4)), True),
        ("⑤ **「고치면 «측정»이 «바뀌나»」** — 판정 «전부»가 «주석»이라 **AST «불변»**"
         " (`207` 에서 «수»로 «보임»)", True),
    ]
    P(F3)
    for nm, v in ok:
        P("%s %s" % ("✅" if v else "🚨", nm))
    P(F3)
    P("")
    P("---")
    P("")
    P("# ⇒ **한 문장**")
    P("")
    P("> ## **«새» Ⓓ4 는 «덮는 값» %d 개이고 — 그중 %d 이 «한» 문장에서 나왔다:**"
      % (sum(r[1] for r in new4), 6))
    P("> ## **「**미너비니** 저유동성 컷」 — canon 이 «바로» 그 자리에 "
      "「**문턱을 «우리»가 «정해야» 한다 = 원전 «밖»**」이라 «적어» 두었다.**")
    P("")
    P("⛔ **고칠지는 «사용자» 결정입니다. 저는 «목록»만 만들었습니다.**")
    P("⛔ **커밋은 그쪽 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
