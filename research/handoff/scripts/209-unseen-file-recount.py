# -*- coding: utf-8 -*-
r"""209 — **「«안» 본 파일」 «목록» 자체를 «다시» 센다** · 두뇌 의뢰 2026-09-07

  🚨 **왜** — `208` 이 «드러냈다»:
     `91-us-out-of-sample.py:95` **`LO, HI = 0.10, 0.30`** 이 **임의값**인데
     `190` §G 에 «등재»조차 «안» 돼 있었고 —
     **`204` ㉠ 의 「«아직» 안 본 파일」 «목록»에 «들어 있지도» «않았다**.
     ⇒ ★ **㊂ 의 «또» 한 얼굴**: **「«빠진» 것을 «세는» 목록이 «스스로» «빠졌다»」**

  ⛔⛔ **가장 중요한 한정 — 「몇 개인가」에 «자»가 «둘»이다**(유형 67):
     ㉠ `204` 의 **72** = 검출기 `DEFAULT_PARAMS` «안»의 값 + `strategy_params.py`
     ㉡ 이 판의 «수»   = 모듈 «상수»(`UPPER = 숫자`) — **«딕셔너리» «안»은 «안» 센다**
     ⇒ 🚨 **두 수를 «더하거나» «비교하면» «안» 된다**

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/209-unseen-file-recount.py
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

# `204` §㉠ 이 «본» 것 / 「안 봤다」고 «적은» 것 — «그대로» 옮긴다
SEEN = ("strategy_params.py", "criteria.py", "vcp.py", "cheat.py",
        "power_play.py", "ipo_track.py")
LISTED_UNSEEN = ("_gates.py", "slot_sim.py", "slot_sim_us.py",
                 "screen_canslim.py", "screen_trend_template.py", "trend_template.py")
PATS = ("scripts/*.py", "scripts/canslim_lib/*.py", "scripts/autobuy/*.py",
        "research/handoff/scripts/*.py")
CONST = re.compile(r"^\s*[A-Z_][A-Z0-9_]*\s*=\s*-?[0-9]")


def main():
    P("# 209 — **「«안» 본 파일」 «목록»이 «스스로» «빠져» 있었다**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/209-unseen-file-recount.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("")
    P("---")
    P("")
    P("# 0. 🚨 **«먼저» — 「몇 개인가」에 «자»가 «둘»이다**(유형 67)")
    P("")
    P(F3)
    P("㉠ " + BQ + "204" + BQ + " 의 **72** = 검출기 " + BQ + "DEFAULT_PARAMS" + BQ
      + " «안»의 값 + " + BQ + "strategy_params.py" + BQ)
    P("㉡ **이 판의 수** = 모듈 «상수»(" + BQ + "UPPER = 숫자" + BQ + ") — **«딕셔너리» «안»은 «안» 센다**")
    P("")
    P("## ⇒ 🚨 **두 수를 «더하거나» «비교하면» «안» 된다** — **«겹치는» 것도 «놓치는» 것도 있다**")
    P("   ⇒ ⛔ 그래서 이 판은 **§G1 의 «수»를 «갱신»하지 «않는다** (**≥ 56 «그대로»**)")
    P("   ⇒ ✅ 이 판이 답하는 것은 **「«목록»이 «맞았나」」 «하나»**다")
    P(F3)
    P("")
    P("---")
    P("")

    rows = []
    for pat in PATS:
        for f in sorted(glob.glob(str(ROOT / pat))):
            try:
                txt = io.open(f, encoding="utf-8").read()
            except Exception:                      # noqa: BLE001
                continue
            n = sum(1 for ln in txt.split("\n") if CONST.match(ln))
            if n:
                rel = os.path.relpath(f, str(ROOT)).replace("\\", "/")
                rows.append((rel, os.path.basename(f), n))

    seen = [r for r in rows if r[1] in SEEN]
    listed = [r for r in rows if r[1] in LISTED_UNSEEN and r[1] not in SEEN]
    unlisted = [r for r in rows if r[1] not in SEEN and r[1] not in LISTED_UNSEEN]

    P("# 1. **센 것**(자 ㉡ — 모듈 상수)")
    P("")
    P(F3)
    P("   훑은 자리: " + " · ".join(BQ + p + BQ for p in PATS))
    P("")
    P("   **모듈 상수를 «가진» 파일 = %d** · **그런 상수 = %d**"
      % (len(rows), sum(r[2] for r in rows)))
    P("")
    P("   ✅ " + BQ + "204" + BQ + " 가 **«본»** 파일         **%2d** · 상수 **%3d**"
      % (len(seen), sum(r[2] for r in seen)))
    P("   🟡 " + BQ + "204" + BQ + " 가 「안 봤다」고 **«적은»** **%2d** · 상수 **%3d**"
      % (len(listed), sum(r[2] for r in listed)))
    P("   🚨 **«목록»에도 «없던»**            **%2d** · 상수 **%3d**"
      % (len(unlisted), sum(r[2] for r in unlisted)))
    P("   ────────────────────────────────────────────")
    P("   **합 %d / %d 파일**" % (len(seen) + len(listed) + len(unlisted), len(rows)))
    P(F3)
    P("")
    P("⚠️ **`204` 가 「본」 파일이 %d 개로만 잡히는 «까닭**: 검출기 값들은 "
      % len(seen) + BQ + "DEFAULT_PARAMS" + BQ + " **«딕셔너리» «안»**에 있어")
    P("   **이 자(모듈 상수)에 «안» 걸린다** ⇒ ★ **«바로» 그게 자 ㉠·㉡ 이 «다른» 까닭**이다")
    P("")
    P("---")
    P("")
    P("# 2. 🚨 **«목록»에도 «없던» 파일 — 상수 «많은» 순 열둘**")
    P("")
    P(F3)
    for f, _b, n in sorted(unlisted, key=lambda r: -r[2])[:12]:
        P("   %3d  %s" % (n, f))
    P(F3)
    P("")
    P("🔎 **`208` 이 짚은 그 파일**: " + BQ + "research/handoff/scripts/91-us-out-of-sample.py" + BQ)
    hit = [r for r in rows if r[1] == "91-us-out-of-sample.py"]
    if hit:
        P("   ⇒ 모듈 상수 **%d** 개 · **«목록»에 «없었다**" % hit[0][2])
    else:
        P("   ⇒ ⚠️ 이 자로는 «안» 잡힌다(" + BQ + "LO, HI = 0.10, 0.30" + BQ
          + " 은 **«한» 줄에 «둘»**이라 " + BQ + "UPPER = 숫자" + BQ + " 꼴이 «아니다»)")
        P("   ⇒ ★★ **그러면 이 자 «자체»도 «빠뜨린다** — **자를 «바꿔도» «빠지는» 것이 «남는다**")
    P("")
    P("---")
    P("")
    P("# ⇒ **맺음 — 이 판이 «말하는» 것과 «말하지» «않는» 것**")
    P("")
    P(F3)
    P("✅ **말하는 것** — **「«안» 본 파일」 «목록»이 «틀렸다**")
    P("   `204` ㉠ 이 「남았다」고 적은 것은 **%d 파일**인데 — **목록에도 «없던» 것이 %d 파일**이다"
      % (len(LISTED_UNSEEN), len(unlisted)))
    P("")
    P("⛔ **말하지 «않는» 것**")
    P("   ⛔ **§G1 의 «수»를 «갱신»하지 «않는다»** — **≥ 56 «그대로»**(자가 «다르다»)")
    P("   ⛔ **「상수 %d 개가 «전부» 임의값」이 «아니다** — **«까닭»을 «안» 읽었다**"
      % sum(r[2] for r in rows))
    P("     (Ⓒ·Ⓐ·Ⓑ 도 «섞여» 있다 — `204` 가 72개를 «읽는» 데 든 품을 %d 개에 «안» 들였다)"
      % sum(r[2] for r in rows))
    P("   ⛔ **자 ㉡ 도 «빠뜨린다** — " + BQ + "LO, HI = 0.10, 0.30" + BQ
      + " 처럼 **«한» 줄에 «둘»**인 꼴은 «안» 잡힌다")
    P(F3)
    P("")
    P("> ## ★★★ **㊂ 의 «또» 한 얼굴 — 「«빠진» 것을 «세는» 목록이 «스스로» «빠졌다».**")
    P("> ## **그리고 «그것»을 «드러낸» 것은 「목록을 «다시» 읽기」가 «아니라» — «판»을 «하나» «돌린» 것이었다.**")
    P("")
    P("⛔ **커밋은 그쪽 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
