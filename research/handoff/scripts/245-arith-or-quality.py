# -*- coding: utf-8 -*-
r"""245 - **「넘은 열하나」가 «산술»인가 «질»인가**  (조사 세션 2026-09-09)

  🔎 «자»는 «이미» 있다 — **유형 95**(«극도로» 좁은 CI = «항등식» 신호)
     본보기: `185` 181c(회계) — CI 폭 **0.350%p** (다른 판 MDE 8~9%p ⇒ **25배** 좁았다)

  ⛔ **«문턱»을 «만들지» 않는다** — **«분포»를 «찍고» 「«어디»가 «갈리나»」를 «보인다**
  ⛔ **갈리는 자리가 «없으면» — 「«못» 가른다」**로 적는다.
  ⛔ **부트를 «다시» «돌리지» 않는다** — `244-per-trade.md` 의 «수»를 «읽는다**.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/245-arith-or-quality.py
"""
from __future__ import annotations

import importlib.util as _u
import re as _re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
HERE = Path(__file__).resolve().parent
RES = HERE.parent / "results"

ROW = _re.compile(
    r"^\|\s*`(?P<key>[^`]+)`\s*\|\s*(?P<arm>[^|]+?)\s*\|\s*(?P<n>[\d,]+)\s*\|"
    r"\s*\*\*(?P<pt>[+-][0-9.]+)\*\*\s*\|\s*\[(?P<lo>[+-][0-9.]+),\s*(?P<hi>[+-][0-9.]+)\]")


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


def arm_days():
    """판마다 ① 팔의 «날» 수 — «겹침» 비율의 «분모»."""
    m244 = _load("m244", "244-per-trade.py")
    m234 = m244.m234
    out = {}
    todo = [(k, m234.REG[k][0]) for k in m234.REG] + [(k, v[0]) for k, v in m244.EXTRA.items()]
    for key, fn in todo:
        try:
            built, pairs = fn()[0], fn()[1]
        except Exception:                            # noqa: BLE001
            continue
        for nm, ka, kb in pairs:
            db = {d for d, _h, _n in built[kb]}
            out[(key, nm.strip())] = len(db)
    return out


def main():  # noqa: C901
    P("# 245 - **「넘은 열하나」가 «산술»인가 «질»인가**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/245-arith-or-quality.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⛔ **부트를 «다시» «안** 돌렸다 — " + BQ + "244-per-trade.md" + BQ + " 의 «수»를 «읽었다**")
    P("")
    P(F3)
    P("🚨 **사전등록**(값 «보기» 전에 박는다)")
    P("   ✅ **「갈린다」면** → CI 폭이 **「넘은 것」과 「«안» 넘은 것」에서 «뚜렷»하게 «다르다**")
    P("   🔴 **「«못» 가른다」면** → **«두» 무리의 CI 폭이 «겹친다** ⇒ **「산술인지 질인지 «못» 가린다」**")
    P("   ⛔ **«문턱»을 «만들지» 않는다** — **«분포»를 «찍고» «겹치나»를 «본다**")
    P("")
    P("🔎 **자**: **유형 95** — «극도로» 좁은 CI = **«항등식» 신호**")
    P("   「산술」이면 차이가 **«결정»적**이라 부트에서 «거의» «안» 흔들린다 ⇒ **CI 폭이 «좁다**")
    P("   「질」이면 **«자료»에 따라 흔들린다** ⇒ **CI 폭이 «보통»**")
    P(F3)
    P("")
    P("---")
    P("")

    src = (RES / "244-per-trade.md").read_text(encoding="utf-8", errors="replace")
    rows = []
    for ln in src.splitlines():
        m = ROW.match(ln)
        if not m:
            continue
        key = m.group("key")
        arm = _re.sub(r"[*]", "", m.group("arm")).strip()
        n = int(m.group("n").replace(",", ""))
        pt = float(m.group("pt"))
        lo, hi = float(m.group("lo")), float(m.group("hi"))
        over = ("🟢 «넘음»" in ln)
        rows.append((key, arm, n, pt, lo, hi, hi - lo, over))
    days = arm_days()

    P("# 1. **CI 폭 · «겹침» — «나란히**")
    P("")
    P("| 판 | 짝 | 넘음 | 점추정 | **CI 폭** | 공통 날 | Ⓑ팔 날 | **«겹침»** |")
    P("|---|---|:--|---:|---:|---:|---:|---:|")
    for key, arm, n, pt, lo, hi, w, over in sorted(rows, key=lambda r: r[6]):
        nb = days.get((key, arm))
        ov = ("%.1f%%" % (100.0 * n / nb)) if nb else "—"
        P("| `%s` | %s | %s | %+.4f | **%.4f** | %s | %s | %s |"
          % (key, arm, "🟢" if over else "⚪", pt, w, format(n, ","),
             format(nb, ",") if nb else "—", ov))
    P("")

    A = [r[6] for r in rows if r[7]]
    B = [r[6] for r in rows if not r[7]]
    P(F3)
    P("   🟢 **넘은 %d** — CI 폭 최소 **%.4f** · 중앙 **%.4f** · 최대 **%.4f**"
      % (len(A), min(A), st.median(A), max(A)))
    P("   ⚪ **«안» 넘은 %d** — CI 폭 최소 **%.4f** · 중앙 **%.4f** · 최대 **%.4f**"
      % (len(B), min(B), st.median(B), max(B)))
    P("")
    lapA = sum(1 for a in A if min(B) <= a <= max(B))
    lapB = sum(1 for b in B if min(A) <= b <= max(A))
    P("   ★ **겹침**: 넘은 것 **%d / %d** 이 「안 넘은 것」의 «폭 범위» «안» ·"
      " 안 넘은 것 **%d / %d** 이 「넘은 것」의 «범위» «안»" % (lapA, len(A), lapB, len(B)))
    P("")
    if min(A) > max(B) or max(A) < min(B):
        P("⇒ ✅ **«두» 무리가 «안** 겹친다 — **CI 폭으로 «갈린다**")
    else:
        P("⇒ 🔴 **«두» 무리가 «겹친다** ⇒ **「산술인지 «질»인지 «CI 폭»으로는 «못» 가린다」**")
    P(F3)
    P("")
    P("---")
    P("")

    # ── «겹침» 축 ────────────────────────────────────────────────────
    P("# 2. **「날짜 «겹침»」으로 «갈리나**")
    P("")
    ovA = [100.0 * r[2] / days[(r[0], r[1])] for r in rows if r[7] and days.get((r[0], r[1]))]
    ovB = [100.0 * r[2] / days[(r[0], r[1])] for r in rows if not r[7] and days.get((r[0], r[1]))]
    P(F3)
    if ovA and ovB:
        P("   🟢 넘은 것 — 겹침 최소 **%.1f%%** · 중앙 **%.1f%%** · 최대 **%.1f%%**"
          % (min(ovA), st.median(ovA), max(ovA)))
        P("   ⚪ «안» 넘은 것 — 겹침 최소 **%.1f%%** · 중앙 **%.1f%%** · 최대 **%.1f%%**"
          % (min(ovB), st.median(ovB), max(ovB)))
        P("")
        if min(ovA) > max(ovB) or max(ovA) < min(ovB):
            P("⇒ ✅ **«겹침»으로 «갈린다**")
        else:
            P("⇒ 🔴 **«겹침»으로도 «겹친다** ⇒ **«이» 축으로도 «못» 가린다**")
    else:
        P("   («겹침»을 «못» 셌다)")
    P(F3)
    P("")
    P("---")
    P("")

    # ── 판 «묶음»으로 ────────────────────────────────────────────────
    P("# 3. **판 «묶음»으로 보면**(⛔ **«사후» 묶음**이다 — 「사전등록」이 «아니다**)")
    P("")
    fam = {"183": "같은 거래·다른 규칙", "185": "같은 거래·다른 규칙",
           "191": "같은 거래·다른 규칙", "193b": "같은 거래·다른 규칙"}
    g = defaultdict(lambda: [0, 0])
    for key, _a, _n, _p, _lo, _hi, _w, over in rows:
        k = fam.get(key, "팔을 «바꾸는» 판(고르기·거르기)")
        g[k][0] += 1
        g[k][1] += int(over)
    P(F3)
    for k, (tot, ov) in g.items():
        P("   %-30s **%d 중 %d** 이 «넘었다**" % (k, tot, ov))
    P("")
    P("   ⛔ 🚨 **이 묶음은 «수»를 «본» «뒤»에 «지었다** — **「사전등록」이 «아니다**")
    P("   ⇒ ✅ **그래서 「«근거»」가 «아니라 「«모양»」**으로만 적는다")
    P(F3)
    P("")
    P("---")
    P("")
    P("# ⚠️ **이 판이 «못** 하는 것**")
    P("")
    P(F3)
    P("⛔ ① **CI 폭은 «팔 크기»에도 «딸린다** — **「산술」의 «자»가 «순수»하지 «않다**")
    P("⛔ ② **「같은 거래·다른 규칙」 묶음은 «사후»**다(위 §3)")
    P("⛔ ③ **`237`(구조상 0)은 «표»에 «있다** — **「폭 0」이 「«좁다»」로 «읽히면» «틀린다**")
    P("⛔ ④ **부트를 «다시» «안** 돌렸다 — `244` 의 «수»를 «그대로» 읽었다")
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
