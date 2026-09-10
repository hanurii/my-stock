# -*- coding: utf-8 -*-
r"""234z - **「전」/「후」 판정칸을 «한» 표로** (조사 세션 2026-09-08)

  ⛔ 손으로 «옮기지» 않는다 - **«원본» 결과 md 와 `234-*.md` 를 «읽어» «같은» 규칙으로 «다시» 매긴다**.
     («전» 칸을 원본이 «어떤» 낱말로 적었든 - **CI 로 «다시» 매긴다** ⇒ 「자」가 «하나»가 된다)

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/234z-compare.py
"""
from __future__ import annotations

import re as _re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
P = print
BQ = chr(96)
F3 = BQ * 3
RES = Path(__file__).resolve().parent.parent / "results"
DELTA = 1.23

ROW = _re.compile(r"^\|\s*(?P<arm>[^|]+?)\s*\|.*?\*\*(?P<pt>[+-][0-9.]+)%p\*\*\s*\|"
                  r"\s*\[(?P<lo>[+-][0-9.]+),\s*(?P<hi>[+-][0-9.]+)\]")

PAIRS = [("220", "220-fa-four.md"), ("229", "229-roe-threshold.md"),
         ("228", "228-rev-leads.md"), ("220b", "220b-pe-clean.md"),
         ("231b", "231b-pullback-judge.md"), ("218", "218-nq-four.md"),
         ("227b", "227b-noliq-judge.md"), ("208", "208-mde-second-probe.md"),
         ("183", "183-data-axis.md"), ("185", "185-oneaxis.md"),
         ("191", "191-alpha-data-axis.md"), ("193b", "193b-pivot-prevhigh.md"),
         ("201d", "201d-rs-threshold.md")]


def cell(lo, hi):
    if lo >= DELTA:
        return "1"
    if hi <= -DELTA:
        return "2"
    if lo <= 0 <= hi:
        return "5"
    if -DELTA <= lo and hi <= DELTA:
        return "4a"
    return "4b"


def tok(a):
    a = _re.sub(r"[*🔎 ]", "", a)
    a = _re.split(r"[−\-]", a)[0]
    a = _re.sub(r"묘사|블록|[0-9]+~[0-9]+", "", a)
    return a.strip()


def rows(fn):
    p = RES / fn
    if not p.exists():
        return None
    out = []
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = ROW.match(ln)
        if m:
            out.append((tok(m.group("arm")), float(m.group("pt")),
                        float(m.group("lo")), float(m.group("hi"))))
    return out


def main():  # noqa: C901
    P("# 234z - **「전」/「후」 판정칸 — «한» 표**")
    P("")
    P("> 조사 세션 · " + BQ + "research/handoff/scripts/234z-compare.py" + BQ
      + " · **문서는 이 출력 그 자체**(유형 48)")
    P("> ★ **«전» 칸도 «다시» 매겼다** — 원본이 «어떤» 낱말을 썼든 **CI 로 «같은» 규칙**을 댄다")
    P("")
    P("---")
    P("")
    P("| 판 | 팔 | «전» 점추정 | «전» 칸 | «후» 점추정 | «후» 칸 | 바뀌나 |")
    P("|---|---|---:|:--|---:|:--|:--|")
    tot = chg = unm = 0
    per = {}
    for key, orig in PAIRS:
        aft = rows("234-%s.md" % key) if key != "201d" else rows("233-201d-fixed.md")
        bef = rows(orig)
        if not aft or not bef:
            P("| %s | — | — | — | — | — | ⚪ **파일 «없음»** |" % key)
            continue
        bmap = {}
        for t, pt, lo, hi in bef:
            bmap.setdefault(t, []).append((pt, cell(lo, hi)))
        seen = Counter()
        nc = nt = 0
        for t, pt, lo, hi in aft:
            i = seen[t]
            seen[t] += 1
            b = bmap.get(t)
            if not b or i >= len(b):
                unm += 1
                P("| %s | %s | — | ⚪ «못 찾음» | %+.3f | **%s** | ⚪ |" % (key, t, pt, cell(lo, hi)))
                continue
            pb, cb = b[i]
            ca = cell(lo, hi)
            nt += 1
            tot += 1
            ch = ca != cb
            nc += ch
            chg += ch
            P("| %s | %s | %+.3f | %s | **%+.3f** | **%s** | %s |"
              % (key, t, pb, cb, pt, ca, "🚨 **바뀜**" if ch else "같음"))
        per[key] = (nt, nc)
    P("")
    P(F3)
    for k, (nt, nc) in per.items():
        P("   %-5s **%d 행 «중» %d** 바뀜" % (k, nt, nc))
    P("")
    P("   ★★ **모두 %d 행 «중» %d** 이 판정칸이 «바뀌었다**" % (tot, chg))
    P("   ⚪ 짝을 «못» 찾은 행 **%d**" % unm)
    P(F3)
    P("")
    P("---")
    P("")
    P("# ⚠️ **못 하는 것**")
    P("")
    P(F3)
    P("⛔ ① 짝 맞추기는 **팔 «이름»의 «앞» 토막**으로 했다 — **«어긋날» 수 있다**(⚪ 로 표시)")
    P("⛔ ② **블록 짝**은 «파일 안 차례»로 맞췄다 — **차례가 «다르면» «어긋난다**")
    P("⛔ ③ **«전» 칸을 «다시» 매긴 것**이라 — **원본이 «적은» 낱말과 «다를» 수 있다**")
    P("⛔ ④ MDE·CI **인용 금지**가 «산다** — 「전/후 나란히」 자리에서«만**")
    P(F3)
    P("")
    P("⛔ **커밋은 두뇌 몫입니다.**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
