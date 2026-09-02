# -*- coding: utf-8 -*-
"""_gatesv2 — **«내가» 고른 적대 사례** (조사 세션 · 26-09-02)

  🚨 검증 세션의 20 사례는 «값»을 흔들었다 — NaN · 경계값 · 부동소수 · 음수 · SD=0 · 맞닿은 창.
     그래서 나는 **«입력 자체가 말이 안 되는»** 쪽을 고른다. «다른 가정»에서 고르려는 것이다.
  ⚠️ 그래도 **이것도 «내» 가정 안이다** — 셋째 사람이 필요하다는 게 이 파일의 결론이다.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")

from _gates import (countable_windows, denominator_note, p_informative,  # noqa: E402
                    shared_axis_note, d_star)

FAIL = 0


def case(no, what, got, want):
    global FAIL
    ok = got == want
    if not ok:
        FAIL += 1
    print("%s **%s** %s" % ("✅" if ok else "🚨", no, what))
    print("   기대 **%s** · 실제 **%s**%s"
          % ("문다" if not want else "통과", "문다" if not got else "통과",
             "" if ok else "   ⇒ **불일치**"))


print("# `_gates` 적대 시험 — **«조사 세션»이 고른 사례**")
print("")
print("## A. `countable_windows` — «입력이 말이 안 되는» 쪽")
print("")
print("```")
case("A1", "검증 세션이 찾은 «겹치지만 안 담는» 창 (회귀 사례)",
     countable_windows({"A": ("2000", "2010"), "B": ("2005", "2015")})[0], False)
case("A2", "🆕 **창이 «뒤집힌» 것**(끝 < 시작) — 조용히 «담김»으로 읽히면 안 된다",
     countable_windows({"A": ("2010", "2000"), "B": ("2005", "2006")})[0], False)
case("A3", "🆕 **끝점의 «종류»가 섞임**(int vs str) — 비교가 «뜻»을 잃는다",
     countable_windows({"A": (1999, 2011), "B": ("2012", "2026")})[0], False)
case("A4", "🆕 **«같은» 창 두 개** — 이름만 다르면 «독립 시행 둘»이 아니다",
     countable_windows({"A": ("2000", "2010"), "B": ("2000", "2010")})[0], False)
case("A5", "음성 — 안 닿는 둘", countable_windows(
    {"앞": ("1999", "2011"), "뒤": ("2012", "2026")})[0], True)
case("A6", "음성 — **끝점만 공유**(맞닿음)", countable_windows(
    {"앞": ("1999", "2012"), "뒤": ("2012", "2026")})[0], True)
case("A7", "음성 — 창이 «하나»뿐", countable_windows({"A": ("2000", "2010")})[0], True)
print("```")
print("")
print("## B. `shared_axis_note` — «공유하는 게 없을» 때")
print("")
print("```")
lines = shared_axis_note(60, [])
bad = any("유효 n = 1" in ln and "아니다" not in ln for ln in lines)
print("\n".join(lines))
print("")
print("%s **B1** 빈 목록에 «유효 n = 1» 을 «단정»하지 않는가" % ("✅" if not bad else "🚨"))
if bad:
    FAIL += 1
print("```")
print("")
print("## C. `denominator_note` — «불가능한» 입력")
print("")
print("```")
out = denominator_note(checked=2, flagged=5, total=39)
print("\n".join(out))
over = any("250%" in ln or "%d%%" % 250 in ln for ln in out)
print("")
print("%s **C1** 검사 2 개인데 «적발 5 개» — 점추정 **250%%** 를 «그냥» 인쇄하는가" % ("🚨" if over else "✅"))
if over:
    FAIL += 1
    print("   ⇒ **불가능한 입력이 «관문 없이»** 지나간다 — `flagged <= checked` 검사가 없다")
print("```")
print("")
print("## D. `p_informative` / `d_star` — n 이 «말이 안 될» 때")
print("")
print("```")
for bad_n in (0, -5, 2.5):
    try:
        d_star(bad_n)
        print("🚨 **D(n=%r)** — «조용히» 통과했다" % (bad_n,))
        FAIL += 1
    except ValueError as e:
        print("✅ **D(n=%r)** — 물었다: %s" % (bad_n, str(e).split(" — ")[0]))
print("★ **«조용히» 고치는 것은 관문이 아니다** — n 이 «말이 안 되면» «물어야» 한다")
print("```")
print("")
print("---")
print("")
print("## ⇒ **불일치 %d 건**" % FAIL)
print("")
print("```")
print("★ 검증 세션 20 사례 = «값»을 흔듦 (NaN · 경계 · 부동소수 · SD=0)")
print("  내 사례        = «입력의 «뜻»»을 흔듦 (뒤집힘 · 종류 섞임 · 불가능한 비율 · 말 안 되는 n)")
print("⇒ **둘이 «다른 것»을 잡았다** — 그리고 둘 다 «자기가 못 고를 자리»를 남겼다")
print("🚨 **이 파일도 «내» 가정 안이다.** 다음은 «셋째 사람»이거나, 아니면 «없다»")
print("```")
