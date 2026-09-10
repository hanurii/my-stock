# -*- coding: utf-8 -*-
r"""232b - **«어느» CI 가 «양성 대조»를 «통과»하나** (조사 세션 2026-09-08)

  🚨 `232` §3 이 낸 것: **편향이 |1.5~2.1| SD 로 «크다**.
     편향이 그만큼 크면 **«백분위» CI 는 «틀린» 자**다(백분위는 「편향 없음」을 «전제»한다).
     표준 «고침» = **기본(basic) CI = [2*점추정 - hi, 2*점추정 - lo]**.

  ⇒ ★ **«고르는» 자는 «주장»이 아니라 «양성 대조»다**:
     **「두 배 -> 칸 1 · 절반 -> 칸 5」를 «맞히는» CI 가 «맞는» CI**다(232-PRE §2 사전등록 ①).

  ⛔ 이 판은 **«새» 부트를 «돌리지» 않는다** - `232`·`232a` 가 «낸» 수를 «읽어» «다시» 판정한다.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/232b-which-ci.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import re as _re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
HERE = Path(__file__).resolve().parent
RES = HERE.parent / "results"
DELTA = 1.23
MDE_REF = 5.393

ROW = _re.compile(
    r"^\|\s*(?P<arm>[^|]+?)\s*\|\s*\*\*(?P<pt>[+-][0-9.]+)%p\*\*\s*\|"
    r"\s*\[(?P<lo>[+-][0-9.]+),\s*(?P<hi>[+-][0-9.]+)\]")


def _load(nm, fn):
    s = _u.spec_from_file_location(nm, HERE / fn)
    m = _u.module_from_spec(s)
    sys.modules[nm] = m
    s.loader.exec_module(m)
    return m


def cell_of(lo, hi):
    if lo >= DELTA:
        return "1"
    if hi <= -DELTA:
        return "2"
    if lo <= 0 <= hi:
        return "5"
    if -DELTA <= lo and hi <= DELTA:
        return "4a"
    return "4b"


def rows_of(fn):
    out = []
    for ln in (RES / fn).read_text(encoding="utf-8", errors="replace").splitlines():
        m = ROW.match(ln)
        if m:
            out.append((m.group("arm"), float(m.group("pt")),
                        float(m.group("lo")), float(m.group("hi"))))
    return out


def main():  # noqa: C901
    P("# 232b - **«어느» CI 가 «양성 대조»를 «통과»하나**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/232b-which-ci.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> ⛔ **«새» 부트를 «안» 돌렸다** - " + BQ + "232" + BQ + "·" + BQ + "232a" + BQ
      + " 가 «낸» 수를 «읽어» «다시» 판정했다")
    P("")
    P("---")
    P("")

    # ── 0. «몇» 건이 «실제로» 자산곡선에 «들어가나» ─────────────────────
    P("# 0. 🚨 **먼저 - 자산곡선은 «몇» 건으로 지어지나**")
    P("")
    r91 = _load("r91", "91-us-out-of-sample.py")
    m232 = None
    d_ = json.loads(Path(str(r91.OUT / "231-arms.json")).read_text(encoding="utf-8"))
    base = [tuple(x) for x in d_["base"]]
    extra = [tuple(x) for x in d_["extra"]]
    m220 = _load("m220", "220-fa-four.py")
    m232 = _load("m232", "232-instrument-check.py")
    bec = m232.boot_eq_count
    all_d = sorted({d for d, _h, _n in (base + extra)})
    pos = {d: i for i, d in enumerate(all_d)}
    n_pos = len(all_d)

    def admitted(lst, tg):
        bp = defaultdict(list)
        for j, (d, h, nt) in enumerate(lst):
            bp[pos[d]].append((h, nt, tg[j]))
        return bec(bp, n_pos)[1]

    g1 = admitted(base, [0] * len(base))
    g2 = admitted(base + extra, [0] * len(base) + [1] * len(extra))
    P(F3)
    P("   **① 돌파«만»**   거래 **%s** 중 슬롯을 «얻은» 것 = **%s**  (**%.1f%%**)"
      % (format(len(base), ","), format(g1[0], ","), 100.0 * g1[0] / len(base)))
    P("   **Ⓟ 돌파+풀백**  거래 **%s** 중 슬롯을 «얻은» 것 = **%s**  (base %s + **풀백 %s**)"
      % (format(len(base) + len(extra), ","), format(g2[0] + g2[1], ","),
         format(g2[0], ","), format(g2[1], ",")))
    P("")
    P("   ★★ **«처치»의 «실체» = 풀백 %s 건 중 «슬롯»을 얻은 «%s» 건**"
      % (format(len(extra), ","), format(g2[1], ",")))
    P("   ⇒ 🚨 `231b` 가 «잰» 것은 **271 건이 «아니라» %s 건의 차이**다" % format(g2[1], ","))
    P(F3)
    P("")
    P("---")
    P("")

    # ── 1. 양성 대조에 «두» CI 를 «둘 다» 대 본다 ──────────────────────
    P("# 1. ★★★ **양성 대조 - «두» CI 를 «둘 다» 댄다**")
    P("")
    P(F3)
    P("사전등록 ①(232-PRE §2): **㉠ 두 배 -> 칸 1 · ㉡ 절반 -> 칸 5** 를 «맞히는» CI 가 «맞는» CI")
    P("   백분위 CI = [lo, hi]  ·  **기본(basic) CI = [2*점추정 - hi, 2*점추정 - lo]**")
    P(F3)
    P("")
    P("| 팔 | 참효과(구성상) | 백분위 CI | 칸 | 기본 CI | 칸 | 기대 칸 | 백분위 | 기본 |")
    P("|---|---:|---:|:--|---:|:--|:--|:--|:--|")
    want = {chr(0x24C1) + chr(0x3260): "1", chr(0x24C1) + chr(0x3261): "5",
            chr(0x24BA) + chr(0x3260): "1", chr(0x24BA) + chr(0x3261): "5"}
    okp = okb = tot = 0
    for arm, pt, lo, hi in rows_of("232-instrument-check.md"):
        key = _re.sub(r"[* ]", "", arm)
        key = key.split()[0] if key else key
        base_key = key[:2]
        if base_key not in want:
            continue
        cp = cell_of(lo, hi)
        blo, bhi = 2 * pt - hi, 2 * pt - lo
        cb = cell_of(blo, bhi)
        w = want[base_key]
        tot += 1
        okp += (cp == w)
        okb += (cb == w)
        P("| **%s** | %+.3f | [%+.3f, %+.3f] | **%s** | [%+.3f, %+.3f] | **%s** | **%s** | %s | %s |"
          % (arm, pt, lo, hi, cp, blo, bhi, cb, w,
             "✅" if cp == w else "🔴", "✅" if cb == w else "🔴"))
    P("")
    P(F3)
    P("   **%d 중 %d** — «백분위» CI 가 기대 칸을 «맞힘»" % (tot, okp))
    P("   **%d 중 %d** — **«기본» CI 가 기대 칸을 «맞힘»**" % (tot, okb))
    P("")
    if okb > okp:
        P("⇒ ★★★ **«기본»(basic) CI 가 «양성 대조»를 «더» 잘 통과한다**")
        P("   ⛔ 다만 **«완벽»하지 «않다** — «틀린» 칸이 %d 개 «남는다**" % (tot - okb))
    elif okp > okb:
        P("⇒ **«백분위» CI 가 «더» 낫다** - 편향이 커도 «백분위»를 «쓴다**")
    else:
        P("⇒ 🚨 **«둘»이 «같다** - 이 대조로는 **«못» 고른다**")
    P(F3)
    P("")
    P("---")
    P("")

    # ── 2. «두» CI 로 «다시» 판정 ─────────────────────────────────────
    P("# 2. **가문 판들을 «두» CI 로 «다시» 판정**")
    P("")
    P("| 판 | 팔 | 점추정 | 백분위 칸 | **기본 칸** | 바뀌나 |")
    P("|---|---|---:|:--|:--|:--|")
    fam = ["201d-rs-threshold.md", "218-nq-four.md", "220-fa-four.md", "220b-pe-clean.md",
           "227b-noliq-judge.md", "228-rev-leads.md", "229-roe-threshold.md",
           "231b-pullback-judge.md"]
    nchg = ntot = 0
    for f in fam:
        if not (RES / f).exists():
            continue
        for arm, pt, lo, hi in rows_of(f):
            cp = cell_of(lo, hi)
            cb = cell_of(2 * pt - hi, 2 * pt - lo)
            ntot += 1
            ch = cp != cb
            nchg += ch
            P("| %s | %s | %+.3f | %s | **%s** | %s |"
              % (f.replace(".md", ""), arm, pt, cp, cb, "🚨 **바뀜**" if ch else "같음"))
    P("")
    P(F3)
    P("   **%d 행 «중» %d** 이 **판정칸이 «바뀐다**" % (ntot, nchg))
    P(F3)
    P("")
    P("---")
    P("")
    P("# ⚠️ **이 판이 «못» 하는 것**")
    P("")
    P(F3)
    P("⛔ ① **양성 대조는 " + BQ + "231b" + BQ + " «한» 판의 팔로«만** 했다 -")
    P("     «다른» 판에 **«기본» CI 를 대는 것은 «방법»의 «옮김»**이다(유형 68 «신고»)")
    P("⛔ ② **기본 CI 도 «완벽»하지 «않다** - §1 의 «틀린» 칸을 «적었다**")
    P("⛔ ③ **BCa·studentized 는 «안** 해 봤다 - **«둘»만 견줬다**")
    P("⛔ ④ 이 판은 **「풀백이 «좋냐»」를 «묻지» 않았다** · **§B 를 «고치지» «않았다**")
    P("⛔ ⑤ **판정을 «바꾸는» 것은 «검증»의 몫**이다 - 여기선 **«수»만 «놓았다**")
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
