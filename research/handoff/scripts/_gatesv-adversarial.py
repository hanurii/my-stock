# -*- coding: utf-8 -*-
"""검증 세션 → `_gates.py` «음성 대조». 조사 세션이 «안 고른» 것을 «내가» 고른다.
   물음: 「이 관문이 «물지 «말아야»» 할 것에 무는가(오탐) · «물어야» 할 것을 «놓치는가»(위음성)」"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _gates as G

NAN = float("nan")
rows = []
def t(label, ok_expected, ok_actual, why=""):
    verdict = "✅" if ok_expected == ok_actual else "🚨"
    rows.append((verdict, label, "통과" if ok_actual else "물음",
                 "통과여야" if ok_expected else "물어야", why))

print("=" * 96)
print("_gates.py 음성/적대 대조 — **검증 세션이 «고른» 사례**")
print("=" * 96)

# ── ① countable_windows ────────────────────────────────────────────────
t("① 창 하나뿐", True, G.countable_windows({"A": (0.0, 10.0)})[0])
t("① 서로 안 닿는 두 창", True, G.countable_windows(
    {"A": (0.0, 10.0), "B": (20.0, 30.0)})[0])
t("① 맞닿은 두 창(끝점만 공유)", True, G.countable_windows(
    {"A": (0.0, 10.0), "B": (10.0, 20.0)})[0])
t("① 담는 창(전체+조각)", False, G.countable_windows(
    {"전체": (0.0, 27.4), "a": (0.0, 3.0), "b": (3.0, 18.7), "c": (18.7, 27.4)})[0])
t("① 🚨 **겹치지만 «안 담는»** 두 창", False, G.countable_windows(
    {"A": (2000.0, 2010.0), "B": (2005.0, 2015.0)})[0],
  "겹치는 창도 «독립 시행»이 아니다 — 담김만 보면 «놓친다»")

# ── ③ p_informative ────────────────────────────────────────────────────
t("③ 작은 효과(d=1.0, n=60)", True, G.p_informative(1.0, 1.0, 60)[0])
t("③ 문턱 «바로 아래»(d=3.10, n=60)", True, G.p_informative(3.10, 1.0, 60)[0])
t("③ 문턱 «바로 위»(d=3.20, n=60)", False, G.p_informative(3.20, 1.0, 60)[0])
t("③ 효과가 «음»(d=−8.9)", False, G.p_informative(-8.9, 1.0, 60)[0], "abs 를 쓰므로 정상")
t("③ SD = 0", False, G.p_informative(1.0, 0.0, 60)[0], "분산 0 = 완전 결정적")
t("③ 🚨 **효과가 NaN**", False, G.p_informative(NAN, 1.0, 60)[0],
  "⚠️ 검증 세션 예상은 «조용히 통과»였는데 **틀렸다** — 통과가 «이른 갈래»뿐이라 NaN 은 «떨어져» 문다 ✅")

# ── ④⑤⑥ 값 관문 ───────────────────────────────────────────────────────
t("④ 범위 «경계값» 0", True, G.range_gate("x", 0.0, 0.0, 100.0)[0])
t("④ 범위 밖(−35.6)", False, G.range_gate("x", -35.6, 0.0, 100.0)[0])
t("④ NaN", False, G.range_gate("x", NAN, 0.0, 100.0)[0], "비교가 False → 문다 ✅")
t("⑤ 등식 «부동소수» 오차(1e-12)", True, G.identity_gate("i", 27.4, 27.4 + 1e-12)[0])
t("⑤ 등식 «진짜» 어긋남", False, G.identity_gate("i", 27.4, 26.0)[0])
t("⑤ NaN", False, G.identity_gate("i", NAN, 27.4)[0], "비교가 False → 문다 ✅")
t("⑥ 자릿수 0(면제)", True, G.digit_gate("x", 0.0, 1e2, 1e5)[0])
t("⑥ 자릿수 1000배 어긋남", False, G.digit_gate("x", 0.5, 1e2, 1e5)[0])
t("⑥ NaN", False, G.digit_gate("x", NAN, 1e2, 1e5)[0], "비교가 False → 문다 ✅")

w = max(len(r[1]) for r in rows)
for v, lab, act, exp, why in rows:
    print("  %s %-*s  실제 **%-4s** / 기대 **%-6s**%s" % (v, w, lab, act, exp, ("   ← " + why) if why else ""))

bad = [r for r in rows if r[0] == "🚨"]
print()
print("=" * 96)
print("  검사 **%d** 개 · **불일치 %d 개**" % (len(rows), len(bad)))
for _v, lab, act, exp, why in bad:
    print("    🚨 %s — 실제 «%s» / 기대 «%s»  :  %s" % (lab, act, exp, why))
print("=" * 96)
raise SystemExit(1 if bad else 0)
