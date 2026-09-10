# -*- coding: utf-8 -*-
r"""233b - **「블록 20~40」은 «무슨» 단위인가** (조사 세션 2026-09-08)

  🚨 두뇌 물음 «셋»에 **«코드»로** 답한다(⛔ 추측 «금지»):
     ① `23c` 의 블록 20~40 은 «무슨» 단위인가
     ② 그 «수»는 «어디»서 왔나 - **파일:줄** · 거기에 «단위»가 «적혀» 있나(㊈)
     ③ 「«전»」의 자리로 20~40 자리는 «달력»으로 «며칠»인가 - **«실측»**

  ⛔ 이 각본은 **«아무것»도 «돌리지» 않는다**(부트 «없음»).

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/233b-block-unit.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import re as _re
import statistics as st
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
HERE = Path(__file__).resolve().parent

UNIT = _re.compile(r"20\s*~\s*40\s*거래일|거래일 달력|블록 20~40|20~40거래일")


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


def main():  # noqa: C901
    P("# 233b - **「블록 20~40」은 «무슨» 단위인가**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/233b-block-unit.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⛔ **부트 «없음»** — «읽고» «세기»만 했다")
    P("")
    P("---")
    P("")

    # ── ① · ② ────────────────────────────────────────────────────────
    P("# 1. ①② **단위가 «적혀» 있나 · «어디»서 왔나**")
    P("")
    P(F3)
    files = sorted(HERE.glob("*.py"))
    hits = []
    for f in files:
        if f.name.startswith("233"):
            continue                     # 🚨 자기참조 배제
        for i, ln in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if UNIT.search(ln):
                hits.append((f.name, i, ln.strip()[:120]))
    P("   훑은 각본 **%d** · 「단위」를 «적은» 줄 **%d**" % (len(files), len(hits)))
    P("")
    for h in hits:
        P("   %s:%d" % (h[0], h[1]))
        P("        %s" % h[2])
    P("")
    if hits:
        P("⇒ ✅ **「거래일」이라고 «적혀» 있다** — **추측이 «아니라» «문서»다**")
    else:
        P("⇒ 🔴 **«적힌» 곳이 «없다** — ㊈ 대로 「우리가 «고른» 칸에 «없다」")
    P(F3)
    P("")

    P(F3)
    P("## **상수가 «처음» 나오는 각본**(번호 «작은» 차례)")
    const = []
    for f in files:
        if f.name.startswith("233"):
            continue
        for i, ln in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if _re.search(r"BLOCK_MIN,\s*BLOCK_MAX\s*=\s*20,\s*40", ln):
                const.append((f.name, i))
                break
    for nm, i in const[:6]:
        P("   %s:%d" % (nm, i))
    P("   … 모두 **%d 각본**" % len(const))
    P("")
    P("## **`183` 이후 계보는 «무엇»이라 적었나**")
    fam = []
    for nm in ("183-data-axis.py", "201d-rs-threshold.py", "220-fa-four.py",
               "231b-pullback-judge.py"):
        p = HERE / nm
        if not p.exists():
            continue
        for i, ln in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if "BLOCKS" in ln and "20" in ln and "40" in ln:
                fam.append((nm, i, ln.strip()[:100]))
                break
    for nm, i, ln in fam:
        P("   %s:%d   %s" % (nm, i, ln))
    P("")
    P("   🚨 **`183` 이후엔 「거래일」이라는 «말»이 «그» 줄에 «없다** — **«수»만 «옮겨» 왔다**")
    P(F3)
    P("")
    P("---")
    P("")

    # ── ③ ────────────────────────────────────────────────────────────
    P("# 2. ③ **「«전»」의 20~40 «자리»는 «달력»으로 «며칠»인가** — **«실측»**")
    P("")
    r91 = _load("r91", "91-us-out-of-sample.py")
    CA2 = Path(str(r91.OUT / "201d-arms2.json"))
    if not CA2.exists():
        P("🚨 " + BQ + "201d-arms2.json" + BQ + " 이 «없다** — `233` 을 «먼저» 돌려야 한다")
        return 1
    d_ = json.loads(CA2.read_text(encoding="utf-8"))
    cal = d_["cal"]
    posc = {d: i for i, d in enumerate(cal)}
    arms = d_["arms"]
    entry = sorted({row[0] for v in arms.values() for row in v})
    P(F3)
    P("   달력(모든 거래일) **%s**  ·  «전» 자리(진입일) **%s**"
      % (format(len(cal), ","), format(len(entry), ",")))
    P("")
    P("| 블록 길이(«자리») | 달력 «거래일» 중앙 | 평균 | P10 | P90 |")
    P("|---|---:|---:|---:|---:|")
    for L in (20, 40, 80):
        spans = []
        for i in range(0, len(entry) - L):
            spans.append(posc[entry[i + L]] - posc[entry[i]])
        if not spans:
            continue
        spans.sort()
        P("| %d | **%.0f** | %.1f | %.0f | %.0f |"
          % (L, st.median(spans), sum(spans) / len(spans),
             spans[int(len(spans) * .10)], spans[int(len(spans) * .90)]))
    P("")
    P(F3)
    P("")
    P(F3)
    sp20 = sorted(posc[entry[i + 20]] - posc[entry[i]] for i in range(0, len(entry) - 20))
    sp40 = sorted(posc[entry[i + 40]] - posc[entry[i]] for i in range(0, len(entry) - 40))
    P("   ★★ **「블록 20~40 «자리»」는 «실제»로 «달력» %.0f~%.0f 거래일**(중앙)"
      % (st.median(sp20), st.median(sp40)))
    P("   ⇒ ★ **「이름」은 20~40 인데 «실제»는 «그» %.2f~%.2f 배**였다"
      % (st.median(sp20) / 20.0, st.median(sp40) / 40.0))
    P("")
    P("   ⇒ 🚨 **«넓은» 블록은 «묶음»을 «더» 잡아 CI 를 «좁힌다**")
    P("      ⇒ ⇒ ★★★ 그러면 **「«전»의 MDE 가 «과소»였다」**가 되고 —")
    P("           **「MDE 가 «올랐다»」로 «적으면» «틀린다** ⇒ **「«옳은» MDE 가 «더» 크다」**이다")
    P("   ⛔ **단 이건 «셈»이 «아니라» «논증»이다** — **「블록이 넓으면 CI 가 좁다」를 «이» 자료로")
    P("      «재지는» «않았다**(재려면 블록 길이를 «바꿔» 여러 번 돌려야 한다)")
    P(F3)
    P("")
    P("---")
    P("")
    P("# ⚠️ **이 판이 «못» 하는 것**")
    P("")
    P(F3)
    P("⛔ ① **「블록이 «넓으면» CI 가 «좁다」를 «안** 쟀다 — **«논증»이지 «측정»이 «아니다**")
    P("⛔ ② §1 은 **«우리»가 «고른» 칸**(handoff/scripts/*.py)만 봤다(㊈)")
    P("⛔ ③ **`183` 이후가 「자리」로 «뜻»을 «바꾼» 것이 «고의»인지 «모른다** — **적힌 곳이 «없다**")
    P("⛔ ④ 이 수는 **`201d` 의 자료 «하나»**다")
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
