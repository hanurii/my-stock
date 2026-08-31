# -*- coding: utf-8 -*-
"""140bv 집계 — **로그의 20판을 그대로 읽어 구간을 낸다.**

🚨 왜 따로 있나 — `140bv-random-band.py` 가 **마지막 요약 출력에서만** 죽었다
   (`"... 100% 칸 중앙 %.0f만"` 에서 `100%` 의 `%` 를 안 escape → `% 칸` 이 서식 지정자로 읽힘).
   **20판 값은 로그에 «전부» 있으므로 다시 안 돌린다.** 스크립트는 고쳐 뒀다.

관문 — 로그에서 읽은 판 수가 20이 아니면 멈춘다(줄을 놓치고 조용히 집계하지 않게).

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/140bv-summarize.py
"""
from __future__ import annotations

import io
import re
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOG = ROOT / "_140bv.log"
KEEP = ("100%", "50%", "25%", "10%", "5%")
ROW = re.compile(r"^\s*(\d+)판\s+(.*)$")
CELL = re.compile(r"(100%|50%|25%|10%|5%)\s+(\d+)만")


def q(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, max(0, int(round(p * (len(v) - 1)))))]


def main() -> int:
    rows = {k: [] for k in KEEP}
    n = 0
    for ln in io.open(LOG, encoding="utf-8"):
        m = ROW.match(ln)
        if not m:
            continue
        got = dict(CELL.findall(m.group(2)))
        if len(got) != len(KEEP):
            print("🚨 %s판 줄에서 %d칸만 읽혔다 — 중단" % (m.group(1), len(got)))
            return 2
        for k in KEEP:
            rows[k].append(float(got[k]))
        n += 1
    if n != 20:
        print("🚨 판이 %d개다(20 이어야 한다) — 중단" % n)
        return 2

    base = st.median(rows["100%"])
    uniq = len(set(rows["100%"]))
    print("=" * 100)
    print("140bv 집계 — ② 「무작위 감축」의 «분포» (부분집합 씨앗 %d판 · 슬롯 씨앗 6개)" % n)
    print("   🚨 139 는 `random.Random(9090)` 로 부분집합을 «한 번»만 뽑아 이 중 «한 점»을 보고했다")
    print("   ★ 대조: 100%% 칸은 감축이 없어 부분집합 추첨도 없다 →"
          " %d판 전부 %.0f만 (서로 다른 값 **%d개**)" % (n, base, uniq))
    print("=" * 100)

    print("\n  %-6s %9s %9s %9s %9s %9s %7s"
          % ("남김", "중앙", "5분위", "95분위", "최소", "최대", "최대/최소"))
    print("  " + "-" * 66)
    for k in KEEP:
        v = sorted(rows[k])
        print("  %-6s %8.0f만 %8.0f만 %8.0f만 %8.0f만 %8.0f만 %6.1f배"
              % (k, st.median(v), q(v, 0.05), q(v, 0.95), v[0], v[-1], v[-1] / max(1.0, v[0])))

    print("\n  ★ **「현행 대비」를 «분포»로 다시 적으면** (기준 = 내 100%% 칸 %.0f만)" % base)
    print("  %-6s %12s %26s %14s" % ("남김", "중앙", "5~95%", "현행보다 나쁜 판"))
    print("  " + "-" * 62)
    for k in KEEP[1:]:
        v = sorted(rows[k])
        p = sorted(100.0 * (x - base) / base for x in v)
        worse = sum(1 for x in v if x < base)
        print("  %-6s %+11.1f%% %13.1f%% ~ %+9.1f%% %11d/%d"
              % (k, st.median(p), q(p, 0.05), q(p, 0.95), worse, len(v)))

    print("\n  🚨 **139 가 보고한 값이 이 분포의 «어디»인가**")
    print("     (139 는 슬롯 20판 중앙이고 여기는 6판 중앙이라 «수준»은 직접 비교 불가 —"
          " 보는 것은 **폭 대비 위치**다)")
    rep = {"50%": 3688.0, "25%": 3557.0, "10%": 7715.0, "5%": 7129.0}
    for k in KEEP[1:]:
        v = sorted(rows[k])
        below = sum(1 for x in v if x < rep[k])
        print("     %-5s  139 보고 %6.0f만  →  내 20판 중 **%2d판**이 그보다 아래"
              " (약 %2.0f 백분위)  ·  내 구간 [%.0f ~ %.0f]"
              % (k, rep[k], below, 100.0 * below / len(v), v[0], v[-1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
