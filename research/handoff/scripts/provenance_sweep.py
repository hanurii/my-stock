# -*- coding: utf-8 -*-
"""출처 전수 훑기 — **결과·판정 문서가 인용한 JSON 중 「만든 스크립트가 없는」 것**을 센다.

왜 상시로 두나
--------------
[[provenance-audit-2026-08]] 의 큰 소견이 **「스크래치가 숫자를 내고 스크립트는 사라진다」**였다.
그 뒤로도 같은 형태가 세 번 더 나왔다 — 73b(관문·P0), 58b(자료 축 정정), 그리고 이 훑기.
**처방을 «검사»로 만든다.** 사람이 기억하는 대신 코드가 센다.

🚨 오탐을 줄이는 자
-------------------
스크립트가 `"paths_%d.json" % y` 처럼 «조립»하는 경우가 많다. 이름 그대로 찾으면
전부 「없음」으로 찍힌다(첫 판에서 28종 → 자를 고쳐 18종). 세 단계로 본다:
  ① 이름 그대로 · ② 숫자를 %d/%s/{} 로 바꾼 형식 문자열 · ③ 접두어 조립

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/provenance_sweep.py
"""
from __future__ import annotations

import collections
import io
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
HANDOFF = HERE.parent
OUTD = HANDOFF.parents[1] / ".cache" / "bt5y" / "out"


def load_src():
    s = ""
    for p in list(HERE.rglob("*.py")) + list(HERE.rglob("*.sh")):
        if p.name == "provenance_sweep.py":
            continue
        try:
            s += io.open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            pass
    return s


def find(j, src):
    stem = j[:-5]
    if stem in src or j in src:
        return "이름 그대로"
    for pat in (r"\d{4}", r"\d+"):
        g = re.sub(pat, "%d", stem, count=1)
        if g != stem and (g in src or g.replace("%d", "%s") in src
                          or g.replace("%d", "{}") in src):
            return "형식 문자열"
    pre = re.split(r"\d", stem)[0].rstrip("-_")
    if len(pre) >= 5 and (pre + "_%" in src or pre + "-%" in src):
        return "접두어 조립"
    return None


def main() -> int:
    src = load_src()
    cite = collections.defaultdict(set)
    for sub in ("results", "verdicts"):
        d = HANDOFF / sub
        if not d.exists():
            continue
        for md in sorted(d.glob("*.md")):
            t = io.open(md, encoding="utf-8", errors="ignore").read()
            for j in set(re.findall(r"[\w\-.]+\.json", t)):
                cite[j].add(md.name)
    orphan = [(j, sorted(v)) for j, v in sorted(cite.items()) if find(j, src) is None]
    live = [(j, d) for j, d in orphan if (OUTD / j).exists()]
    print("=" * 88)
    print("출처 전수 훑기 — 인용 JSON %d 종" % len(cite))
    print("=" * 88)
    print("  만든 스크립트를 못 찾은 것        **%d 종**" % len(orphan))
    print("  그중 **산출물이 실제로 있는 것**  **%d 종**  ← 「숫자는 있는데 만든 코드가 없다」"
          % len(live))
    print()
    for j, docs in orphan:
        mark = "🚨 산출물 있음" if (OUTD / j).exists() else "   산출물 없음"
        print("  %s  %-34s 인용: %s" % (mark, j, ", ".join(docs[:2])))
    print()
    print("★ 「산출물 없음」은 대개 문서 안의 예시 이름이거나 이미 기록된 소실이다.")
    print("★ **「산출물 있음」이 진짜 자리다** — 숫자가 문서에 살아 있는데 재현 경로가 없다.")
    return 0 if not live else 1


if __name__ == "__main__":
    raise SystemExit(main())
