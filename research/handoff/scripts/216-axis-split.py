# -*- coding: utf-8 -*-
r"""216 — **「우리 규칙」의 «축»을 «가른다**(⛔ «새로» «세지» 않는다) · 두뇌 의뢰 2026-09-07

  🚨 **왜** — `215` 가 찾은 것:
     **`criteria.py` 의 EPS 문턱을 «백테스트»는 «안» 쓴다** — **«실전 스크리너» 축**이다.
     ⇒ 그러면 `204`(72) · §G1(≥63)이 **«두» 축을 «섞어» 세었을** 수 있다 ⇒ **유형 67 «또»**.

  ⛔ **«수»를 «새로» «세지» 않는다** — **«있는» 72 를 «가르는» 것**이다(그래야 «합»이 맞는다).
  ⛔ **「어느 축이 «더» 중요한가」는 «묻지» 않는다** — **«둘» 다 «우리» 것**이다.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/216-axis-split.py
"""
from __future__ import annotations

import collections
import io
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
HANDOFF = Path(__file__).resolve().parents[1]
SRC204 = HANDOFF / "results" / "204-param-provenance.md"

# ── 축 — **«코드»로 «확인»했다**(추측 «아님») ────────────────────────────
#   🔎 backtest_volatility_pilot_us.py:43-46 이 «부르는» 것 = trend_template · cheat · vcp · power_play
#   🔎 `criteria` · `ipo_track` · `strategy_params` 는 **grep 0** — 파일럿이 **«안» 부른다**
#   🔎 91-us-out-of-sample.py 도 `strategy_params` **grep 0** — 하네스가 «자기» 상수를 «박아» 둔다
AXIS = {
    "vcp.py": ("BOTH", "파일럿 `:45` " + BQ + "from canslim_lib.vcp import evaluate_vcp" + BQ),
    "cheat.py": ("BOTH", "파일럿 `:44` " + BQ + "from canslim_lib.cheat import evaluate_cheat" + BQ),
    "power_play.py": ("BOTH", "파일럿 `:46` "
                      + BQ + "from canslim_lib.power_play import evaluate_power_play" + BQ),
    "criteria.py": ("LIVE", "파일럿 grep **0** · " + BQ + "screen_canslim.py:74" + BQ
                    + " 가 «부른다»"),
    "ipo_track.py": ("LIVE", "파일럿 grep " + BQ + "ipo_track" + BQ + " = **0**"),
    "strategy_params.py": ("LIVE", "파일럿·하네스(`91`·`201d`) grep **0** — "
                           "하네스는 " + BQ + "91:87 STOP, TARGET = 10.0, 30.0" + BQ + " 을 «자기»가 «박는다»"),
}
LABEL = {"BOTH": "🟢 **«둘» 다**", "LIVE": "🔵 **«실전»만**", "BT": "🟠 **«백테스트»만**"}


def main():          # noqa: C901
    if not SRC204.exists():
        P("🚨 **멈춘다** — " + BQ + str(SRC204) + BQ + " 가 «없다»")
        return 3
    L = io.open(SRC204, encoding="utf-8").read().split("\n")
    end = next(i for i, l in enumerate(L) if "원전과 «같다" in l and "8 / 72" in l)
    main_c, appx_c = collections.Counter(), collections.Counter()
    cell = collections.Counter()
    row = re.compile(r"\| " + BQ + r"([a-z_0-9]+\.py)" + BQ + r" \| \*\*[0-9]+\*\* \|")
    cellpat = re.compile(r"\| \*\*(Ⓐ|Ⓑ|Ⓒ|Ⓓ1|Ⓓ2|Ⓓ3)\*\* \|")
    for i, l in enumerate(L):
        m = row.match(l)
        if not m:
            continue
        if i < end:
            main_c[m.group(1)] += 1
            mc = cellpat.search(l)
            if mc:
                cell[(m.group(1), mc.group(1))] += 1
        else:
            appx_c[m.group(1)] += 1

    P("# 216 — **「우리 규칙」의 «축»을 «가른다**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/216-axis-split.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⛔ **«새로» «세지» 않았다** — " + BQ + "204" + BQ + " 의 **72 를 «가른» 것**이다")
    P("")
    P("---")
    P("")
    P("# 0. 🚨 **먼저 — 「몇 중 몇」에 «자»가 «셋»이었다**(규약 ⑦ · «신고»)")
    P("")
    P(F3)
    P("   ㉠ " + BQ + "204" + BQ + " 가 **«선언»한** 수                    **72**")
    P("   ㉡ 표 «행»을 «전부» 센 수(본문+부록)        **%d**  ← 🚨 **부록 표를 «또» 셌다**"
      % (sum(main_c.values()) + sum(appx_c.values())))
    P("   ㉢ **판정 «칸»이 «붙은» 행**만 센 수          **%d**  ← 칸 «없는» 행이 «있다**"
      % sum(cell.values()))
    P("")
    P("✅ **가른 법**: " + BQ + "204" + BQ + " 의 **「합계」 블록(줄 %d)을 «경계»**로 «본문»만 센다" % (end + 1))
    P("   ⇒ **본문 %d** ✅ ( = ㉠ 과 «같다» ) · 부록 %d(«같은» 값의 «되풀이»)"
      % (sum(main_c.values()), sum(appx_c.values())))
    P("   ⇒ ⛔ ㉢(%d)은 **«이» 판이 «안» 쓴다** — 「칸 «없는» 행」이 «무엇»인지 «안» 봤다"
      % sum(cell.values()))
    P(F3)
    P("")
    P("---")
    P("")
    P("# 1. **축 — «코드»로 «확인»했다**(⛔ «추측» «아님»)")
    P("")
    P("| 파일 | `204` 값 | **축** | 근거(`파일:줄`) |")
    P("|---|---:|:--|---|")
    for f in sorted(main_c, key=lambda k: -main_c[k]):
        ax, why = AXIS[f]
        P("| " + BQ + f + BQ + " | **%d** | %s | %s |" % (main_c[f], LABEL[ax], why))
    P("")
    both = sum(main_c[f] for f in main_c if AXIS[f][0] == "BOTH")
    live = sum(main_c[f] for f in main_c if AXIS[f][0] == "LIVE")
    bt = sum(main_c[f] for f in main_c if AXIS[f][0] == "BT")
    P(F3)
    P("## ⇒ **「몇 : 몇」**(관문 ①)")
    P("")
    P("   🟢 **«둘» 다 쓰는 것**        **%d**  (`vcp` %d · `cheat` %d · `power_play` %d)"
      % (both, main_c["vcp.py"], main_c["cheat.py"], main_c["power_play.py"]))
    P("   🔵 **«실전»만 쓰는 것**       **%d**  (`criteria` %d · `strategy_params` %d · `ipo_track` %d)"
      % (live, main_c["criteria.py"], main_c["strategy_params.py"], main_c["ipo_track.py"]))
    P("   🟠 **«백테스트»만 쓰는 것**    **%d**" % bt)
    P("   ───────────────────────────────────")
    P("   **합 %d / %d** ✅" % (both + live + bt, sum(main_c.values())))
    P(F3)
    P("")
    P("🚨 **「«백테스트»만」이 0 인 «까닭**: 하네스는 **«자기» 상수를 «박는다**")
    P("   (" + BQ + "91-us-out-of-sample.py:87" + BQ + " " + BQ + "STOP, TARGET = 10.0, 30.0" + BQ
      + " · " + BQ + ":95" + BQ + " " + BQ + "LO, HI = 0.10, 0.30" + BQ + ")")
    P("   ⇒ ★★ **그 상수들은 " + BQ + "204" + BQ + " 의 72 «밖»이다**(`208`·`209` 가 «드러낸» 그것)")
    P("   ⇒ ⇒ **「우리 규칙」에 «자»가 «둘»이 «아니라» — «셋»일 수 있다**(실전 / 검출기 / **하네스**)")
    P("")
    P("---")
    P("")
    P("# 2. **§G1(≥63)도 «같이** — «가를» 수 «있는» 만큼만")
    P("")
    P(F3)
    P("🔎 §G1 의 «계보**: " + BQ + "204" + BQ + " 72값 → " + BQ + "205" + BQ + " **+11** → "
      + BQ + "206" + BQ + " **+8** → " + BQ + "210" + BQ + " **+7**")
    P("")
    P("   " + BQ + "205" + BQ + " +11  → `criteria.py` 6 · `vcp.py` 2 · `cheat`·`pp` 각 1 · `ipo_track` 1")
    P("     ⇒ 🔵 실전만 **7** · 🟢 둘 다 **4**")
    P("   " + BQ + "206" + BQ + " +8   → `trend_template.py:233` " + BQ + "GATE_MARGIN_REF" + BQ
      + " 여덟")
    P("     ⇒ 🟢 **둘 다 8**(파일럿 `:43` 이 " + BQ + "evaluate_trend_template" + BQ + " 를 «부른다»)")
    P("   " + BQ + "210" + BQ + " +7   → `MIN_TURNOVER_EOK` **6**(파일럿 «자기» 상수) · `vcp.py` **1**")
    P("     ⇒ 🟠 **하네스/백테스트 6** · 🟢 둘 다 **1**")
    P("")
    P("## ⇒ **«값» «전체»의 «가름**(72 + 11 + 8 + 7 = **98**)")
    P("")
    P("   🟢 «둘» 다        **%d**  (= %d + 4 + 8 + 1)" % (both + 4 + 8 + 1, both))
    P("   🔵 «실전»만       **%d**  (= %d + 7)" % (live + 7, live))
    P("   🟠 «하네스»만      **%d**  (= 0 + 6)" % 6)
    P("   ───────────────────────")
    P("   **합 %d / 98** ✅" % (both + 4 + 8 + 1 + live + 7 + 6))
    P("")
    P("## 🚨 **⛔ 그러나 이것은 §G1(≥63)의 «가름»이 «아니다**")
    P("")
    P("   §G1 = **「«근거» «없이» 쓴다」인 것«만»**(Ⓓ2·Ⓓ3·Ⓓ4) — **위 98 의 «부분집합»**이다")
    P("   ⇒ 🔴 **그것을 «축»으로 «가르려면» — «각» 값의 «칸»을 «다시» 읽어야 한다**")
    P("   ⇒ ⛔ **«이» 판은 그걸 «안» 했다**(두뇌 지시 ⑤ 「«새로» «세지» 마라」) ⇒ **§G1 «가름»은 «미측정»**")
    P("")
    P("⚠️ 🚨 **그리고 위 「+11 / +8 / +7」의 «파일»별 «가름»은 «내»가 «표»를 «다시» 읽어 «센» 것**이고")
    P("   — " + BQ + "205" + BQ + "·" + BQ + "206" + BQ + "·" + BQ + "210" + BQ
      + " 이 «그렇게» «인쇄»한 것이 «아니다**")
    P("   ⇒ ⛔ **그러니 「%d / %d / 6」은 「≥」를 «붙여» 읽어야 한다**" % (both + 13, live + 7))
    P(F3)
    P("")
    P("---")
    P("")
    P("# ★★ 3. **「이 «가름»이 «어느» 문장을 «바꾸나」**(관문 ③)")
    P("")
    P(F3)
    P("## ✅ **「Ⓒ ≥ 3」 — «안» 바뀐다**")
    P("   🔎 Ⓒ 셋은 «전부» " + BQ + "strategy_params.py" + BQ + "(TARGET·STOP·SLOTS)이고 — 🔵 **«실전»만**이다")
    P("   🚨 그런데 **하네스도 «같은» 값을 «자기»가 «박는다**(" + BQ + "91:87" + BQ + ")")
    P("   ⇒ ★ **「Ⓒ 가 «어느» 축인가」는 «흐리다** — 그러나 **«수»(≥3)는 «안» 바뀐다**")
    P("")
    P("## 🔴 **「«적어도» 72」 — «분모»의 «이름»이 «바뀐다**")
    P("   ⛔ **틀린** 읽기: 「우리 규칙 «적어도» 72 개」")
    P("   ✅ **맞는** 읽기: **「우리 규칙 «적어도» 72 개 — 그중 «백테스트»가 «쓰는» 것은 %d(🟢),**"
      % both)
    P("     **«실전»만 쓰는 것이 %d(🔵)」**" % live)
    P("   ⇒ 🚨 **그리고 «셋째» 축(«하네스» «자기» 상수)은 «그» 72 «밖»이다**")
    P(F3)
    P("")
    P("---")
    P("")
    P("# 4. **관문 다섯**")
    P("")
    ok = [
        ("① 「몇 : 몇」 합 = %d / %d" % (both + live + bt, sum(main_c.values())),
         both + live + bt == sum(main_c.values())),
        ("② **«새로» «세지» 않았다** — " + BQ + "204" + BQ + " 본문 %d = «선언»한 72"
         % sum(main_c.values()), sum(main_c.values()) == 72),
        ("③ 「어느 문장이 «바뀌나」」를 «적었다** — Ⓒ ≥3 «불변» · 「72」의 «분모 이름» «바뀜»", True),
        ("④ **축을 «코드»로 «확인»했다**(추측 «아님») — 근거 칸에 `파일:줄` %d / %d"
         % (sum(1 for f in main_c if ":" in AXIS[f][1] or "grep" in AXIS[f][1]), len(main_c)),
         all((":" in AXIS[f][1] or "grep" in AXIS[f][1]) for f in main_c)),
        ("⑤ 🚨 **「자가 «셋»이었다」를 «신고»했다**(72 / %d / %d)"
         % (sum(main_c.values()) + sum(appx_c.values()), sum(cell.values())), True),
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
    P("> ## **72 = 🟢 «둘» 다 **%d** + 🔵 «실전»만 **%d** + 🟠 «백테스트»만 **%d**.**" % (both, live, bt))
    P("> ## **그리고 🚨 «셋째» 축 — «하네스»가 «자기»가 «박는» 상수 — 은 «그» 72 «밖»이다.**")
    P("")
    P("⛔ **커밋은 그쪽 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
