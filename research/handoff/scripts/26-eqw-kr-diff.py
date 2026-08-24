# -*- coding: utf-8 -*-
"""26 · **한국 무필터 일별 등가중이 검증 세션 +17.4% 와 갈리는 지점 찾기.**

내 구현은 **+9.09%** 다. 지시대로 **맞추지 않고 차이를 낸다.**
후보 셋을 2x2x2 로 켜고 끄며 어느 선택이 8%p 를 만드는지 본다.

- FOREIGN  : 외국법인 9xxxxx 를 뺄 것인가 (pdata_series 는 뺀다 / EXCLUDE_PATTERN 만이면 안 뺀다)
- RET      : 수익률을 fltRt 로 볼 것인가, **비수정 종가비**로 볼 것인가
             (종가비는 분할·병합에서 가짜 움직임이 섞인다 — 한국 기준가 변경 832종목)
- GAP      : 전일에 없던 종목(신규상장·거래 공백)의 그날 수익률을 넣을 것인가
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P = ROOT / ".cache" / "pdata"
EXCLUDE = re.compile(
    "스팩|SPAC|리츠|REIT|ETF|ETN|인프라|우B$|우C$|[0-9]우$|우$|우\\(전환\\)|우B\\(전환\\)")
FOREIGN = re.compile("^9[0-9]{5}$")
S, E = "20210201", "20260821"


def num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def run():
    combos = [(fg, rt, gp) for fg in (True, False)
              for rt in ("flt", "close") for gp in (False, True)]
    eq = {c: 1.0 for c in combos}
    prev = {}                     # code -> 전일 종가 (필터 무관하게 전체 보관)
    nmem = {c: [] for c in combos}
    files = sorted(x for x in P.glob("price_*.json") if S <= x.stem[6:] <= E)
    for p in files:
        try:
            recs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        cur = {}
        rows = []
        for code, r in recs.items():
            if r.get("mrktCtg") not in ("KOSPI", "KOSDAQ"):
                continue
            if EXCLUDE.search(r.get("itmsNm") or ""):
                continue
            c = num(r.get("clpr"))
            if not c or c <= 0:
                continue
            cur[code] = c
            rows.append((code, c, num(r.get("fltRt")), prev.get(code)))
        for combo in combos:
            fg, rt, gp = combo
            acc, n = 0.0, 0
            for code, c, f, pc in rows:
                if fg and FOREIGN.match(code):
                    continue
                if rt == "flt":
                    if f is None:
                        continue
                    if not gp and pc is None:
                        continue
                    v = f / 100.0
                else:
                    if pc is None or pc <= 0:
                        continue
                    v = c / pc - 1
                acc += v
                n += 1
            if n:
                eq[combo] *= (1 + acc / n)
            nmem[combo].append(n)
        prev = cur
    print("거래일 %d" % len(files))
    print("%-8s %-6s %-5s %10s %8s" % ("외국제외", "수익률", "공백포함", "총수익", "평균편입"))
    for combo in combos:
        fg, rt, gp = combo
        print("%-8s %-6s %-5s %+9.2f%% %8.0f"
              % ("예" if fg else "아니오", rt, "예" if gp else "아니오",
                 (eq[combo] - 1) * 100, sum(nmem[combo]) / len(nmem[combo])))
    print("")
    print("검증 세션 보고값: **+17.4%** (EXCLUDE_PATTERN · 문턱 없음 · 일별 리밸 · 중앙 2,407종목)")
    print("내 정본(외국제외=예 · flt · 공백포함=아니오): 위 표 첫 줄")


if __name__ == "__main__":
    sys.exit(run())
