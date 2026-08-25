# -*- coding: utf-8 -*-
"""75b — **「하루당 효과가 유지된다」 가정을 «지금 자료로» 검사한다**

검증 세션 제안(2026-08-26 · `verdicts/75-stage1-mde-formula.md`).

75a 의 「필요 T 배」는 **효과의 하루당 크기가 유지된다**를 깔고 있다. 이 프로젝트는
그 가정이 깨진 사례를 여러 번 봤다 — [[stop-loss-edge-refuted]](손절 몫이 통째로 2021) ·
[[exit-grid-24-refuted]](플러스 여섯 칸이 6/6 전부 2021 빼면 마이너스) · 03번 L2′.

**그러니 「12.9년이면 답이 난다」를 쓰기 «전»에 그 가정을 검사한다.**
싸고, **어느 쪽이 나와도 답이 되는** 검정이다:
- 두 반쪽이 비슷 → 12.9년이 뜻을 갖는다
- 다르다 / 한 해가 다 만든다 → **12.9년은 무효**(T 배 가정이 깨진다)

재는 것: 짝비교의 **하루당 로그차** `d_i = ln(1+r_v,i) − ln(1+r_0,i)`.
누적 효과는 `exp(Σd) − 1` 이므로 **Σd 를 구간별로 쪼개면 그대로 분해**된다.

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/75b-halves.py [--quick]
"""
from __future__ import annotations

import importlib.util as _u
import json
import math
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import dataaxis as da                                         # noqa: E402

_s = _u.spec_from_file_location("r75a", HERE / "75a-mde.py")
r75a = _u.module_from_spec(_s)
_s.loader.exec_module(r75a)
r74, r41 = r75a.r74, r75a.r41

OUT = ROOT / ".cache" / "bt5y" / "out"


def daily_logdiff(cv, c0):
    """[(날짜, d)] — 같은 날짜 축에 올린 뒤 하루당 로그차."""
    av, a0 = da.align(cv, c0)
    rv, r0 = da.rets(av), da.rets(a0)
    out = []
    for i in range(min(len(rv), len(r0))):
        a, b = rv[i], r0[i]
        a = -0.9999 if a <= -1.0 else a
        b = -0.9999 if b <= -1.0 else b
        out.append((av[i][0], math.log(1 + a) - math.log(1 + b)))
    return out


def split(series):
    """연도별 Σd · 전반/후반 Σd · 전체 Σd."""
    byyear = defaultdict(float)
    for dte, v in series:
        byyear[dte[:4]] += v
    n = len(series)
    h1 = sum(v for _d, v in series[:n // 2])
    h2 = sum(v for _d, v in series[n // 2:])
    return byyear, h1, h2, h1 + h2, series[n // 2][0]


def pct(x):
    return (math.exp(x) - 1) * 100


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 `BT_Y0=2017` 을 주지 않았다 — 멈춘다.")
        return 2
    n_seed = 20 if "--quick" in sys.argv else 60
    print("=" * 100, flush=True)
    print("75b — 「하루당 효과가 유지된다」 가정 검사 (검증 세션 제안 26-08-26)", flush=True)
    print("=" * 100, flush=True)
    by2, n_all, n_sel, _x = r74.load_filtered()
    HALF, FIX = r74.HALF, r74.FIX
    made = {}
    made["H"], _ = r75a.curves_for(by2, HALF, True, "floor_entry", {}, n_seed)
    made["H-avgstop"], _ = r75a.curves_for(by2, HALF, True, "avg", {}, n_seed)
    made["H′"], _ = r75a.curves_for(by2, HALF, True, "floor_entry", FIX, n_seed)
    made["H′-avgstop"], _ = r75a.curves_for(by2, HALF, True, "avg", FIX, n_seed)
    made["P0"], _ = r75a.curves_for(by2, (1.0,), False, "floor_entry", {}, n_seed)
    print("경로 %d → 조합 %d · seed %d (자료 축과 달리 «전 판»을 쓴다)\n"
          % (n_all, n_sel, n_seed), flush=True)

    PAIRS = (("★ H-avgstop − H  (손절 축)", "H-avgstop", "H"),
             ("★ H′-avgstop − H′ (손절 축)", "H′-avgstop", "H′"),
             ("H − P0 (대조)", "H", "P0"))
    RES = {}
    for lbl, a, b in PAIRS:
        rows = [split(daily_logdiff(made[a][s], made[b][s])) for s in range(n_seed)]
        years = sorted({y for r in rows for y in r[0]})
        mid = rows[0][4]
        tot = st.median(r[3] for r in rows)
        h1 = st.median(r[1] for r in rows)
        h2 = st.median(r[2] for r in rows)
        print("─" * 100, flush=True)
        print("%s   전체 **%+.2f%%** (Σd 중앙 %.4f · seed %d판)"
              % (lbl, pct(tot), tot, n_seed), flush=True)
        print("  전반(~%s) **%+.2f%%**  ·  후반 **%+.2f%%**   →  %s"
              % (mid, pct(h1), pct(h2),
                 "**두 반쪽이 같은 부호**" if h1 * h2 > 0 else "🚨 **부호가 갈린다**"),
              flush=True)
        yr = {y: st.median(r[0].get(y, 0.0) for r in rows) for y in years}
        print("  연도별 Σd → " + " · ".join("%s %+.3f" % (y, yr[y]) for y in years),
              flush=True)
        big = max(yr, key=lambda y: abs(yr[y]))
        share = abs(yr[big]) / max(1e-12, sum(abs(v) for v in yr.values())) * 100
        wo = tot - yr[big]
        print("  **가장 큰 해 %s (Σd %+.3f · |Σd| 몫 %.1f%%)** — 빼면 전체 %+.2f%% → %s"
              % (big, yr[big], share, pct(wo),
                 "**부호 유지**" if wo * tot > 0 else "🚨 **부호 반전**"), flush=True)
        pos = sum(1 for y in years if yr[y] > 0)
        print("  부호가 «양»인 해: **%d / %d**" % (pos, len(years)), flush=True)
        RES[lbl] = {"total": tot, "h1": h1, "h2": h2, "years": yr,
                    "biggest": big, "share": share, "without_biggest": wo,
                    "pos_years": pos, "n_years": len(years)}

    print("\n" + "=" * 100, flush=True)
    print("판정 — 75a 의 「필요 T 배」가 뜻을 갖는가", flush=True)
    for lbl in RES:
        r = RES[lbl]
        ok = (r["h1"] * r["h2"] > 0 and r["without_biggest"] * r["total"] > 0
              and r["pos_years"] not in (0, r["n_years"]) or True)
        keep = r["h1"] * r["h2"] > 0 and r["without_biggest"] * r["total"] > 0
        print("  %-30s 전반·후반 부호 %s · 최대 해 빼도 부호 %s  →  **%s**"
              % (lbl, "같음" if r["h1"] * r["h2"] > 0 else "다름",
                 "유지" if r["without_biggest"] * r["total"] > 0 else "반전",
                 "가정 유지 — T 배가 뜻을 갖는다" if keep
                 else "🚨 **가정 깨짐 — 필요 연수는 무효**"), flush=True)
    (OUT / "75b-halves.json").write_text(
        json.dumps(RES, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 75b-halves.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
