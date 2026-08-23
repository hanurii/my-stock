# -*- coding: utf-8 -*-
"""19d — `rv_1` 십분위(M35-5) + **월 체결률 표**(M35-6) + 월 축 검정력.

★ 십분위는 **판정 축이 아니라 기술**이다(M35-5).
  최대통계 보정 집합에 **넣지 않고**, 결론에 쓰지 않는다.
★ 월 표는 **표만** 낸다 — **상관을 계산하지 않는다**(두뇌 세션이 사전등록을 그 표 보기 전에 쓴다).
★ 월 축 검정력은 **20번 설계 답변용**이다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/19d-decile-and-months.py
난수 seed: 슬롯 순서 0~199
"""
from __future__ import annotations

import importlib.util
import json
import statistics as st
import sys
from collections import Counter, defaultdict
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim  # noqa: E402

spec = importlib.util.spec_from_file_location("g18", HERE / "18-slot-selection-cause.py")
g18 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g18)

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_SEED = 200
K = (1 - 0.002034) / (1 + 0.000034)


def net(g):
    return ((1 + g / 100) * K - 1) * 100


def main():
    feat = json.loads((OUT / "19-volume-features.json").read_text(encoding="utf-8"))["rows"]
    fm = {(r["scan_date"], r["code"], r["pattern"]): r for r in feat}
    tr, seen = [], set()
    for y in range(2021, 2027):
        d = json.loads((BT / ("bt_%d.json" % y)).read_text(encoding="utf-8"))
        for e in d["events"]:
            k = (e["scan_date"], e["code"], e["pattern"])
            if k in seen:
                continue
            seen.add(k)
            f = fm.get(k)
            tr.append({"code": e["code"], "pattern": e["pattern"],
                       "scan_date": e["scan_date"], "entry_date": e["entry_date"],
                       "resolve_date": e["resolve_date"] or e["entry_date"],
                       "year": e["entry_date"][:4], "month": e["entry_date"][:7],
                       "gain": e["gain_at_resolve_pct"], "result": e["result"],
                       "net": net(e["gain_at_resolve_pct"]),
                       "rv_1": (f or {}).get("rv_1")})
    cal = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))["dates"]
    lo_d = min(t["entry_date"] for t in tr)
    hi_d = max(t["resolve_date"] for t in tr)
    dates = [x for x in cal if lo_d <= x <= hi_d]
    pos_of = {d: i for i, d in enumerate(dates)}
    tr = [t for t in tr if t["entry_date"] in pos_of and t["resolve_date"] in pos_of]
    res = {"n": len(tr)}
    print("거래 %d건 · 거래일 %d" % (len(tr), len(dates)), flush=True)

    # ── M35-5 · rv_1 십분위 (기술) ──
    print("\n═══ M35-5 · `rv_1` 십분위 — **판정 축 아님, 기술** ═══", flush=True)
    have = sorted((t for t in tr if t["rv_1"] is not None), key=lambda t: t["rv_1"])
    n = len(have)
    dec = []
    for i in range(10):
        a, b = int(n * i / 10), int(n * (i + 1) / 10)
        sel = have[a:b]
        v = [t["net"] for t in sel]
        dec.append({"i": i + 1, "n": len(sel),
                    "rv_range": [sel[0]["rv_1"], sel[-1]["rv_1"]],
                    "per_trade": st.mean(v),
                    "win_rate": sum(1 for t in sel if t["result"] == "win") / len(sel) * 100})
        print("  D%-2d n=%3d · rv_1 %.2f ~ %5.2f · 거래당 %+8.4f%%p · 승률 %5.2f%%"
              % (i + 1, len(sel), sel[0]["rv_1"], sel[-1]["rv_1"],
                 dec[-1]["per_trade"], dec[-1]["win_rate"]), flush=True)
    seq = [d["per_trade"] for d in dec]
    rev = sum(1 for i in range(9) if seq[i + 1] < seq[i])
    print("  → 뒤집힘 **%d / 9쌍** · 최고 D%d(%+.3f) · 최저 D%d(%+.3f)"
          % (rev, seq.index(max(seq)) + 1, max(seq), seq.index(min(seq)) + 1, min(seq)),
          flush=True)
    print("  ※ 균형 분할이라 각 칸 %d건 — 19번 주검정(206:3,570)보다 검정력이 낫다." % dec[0]["n"],
          flush=True)
    res["deciles"] = dec
    res["decile_reversals"] = rev

    # ── M35-6 · 월 표 (상관 계산 안 함) ──
    print("\n═══ M35-6 · 월별 표 — **표만. 상관 계산 안 함** ═══", flush=True)
    by_m = defaultdict(list)
    for t in tr:
        by_m[t["month"]].append(t)
    fills = defaultdict(list)
    for s in range(N_SEED):
        fl, _, _ = g18.fill_split(tr, dates, pos_of, s)
        c = Counter(t["month"] for t in fl)
        for m in by_m:
            fills[m].append(c.get(m, 0))
    rows = []
    for m in sorted(by_m):
        cand = by_m[m]
        f = st.median(fills[m])
        rows.append({"month": m, "n_cand": len(cand), "n_fill": f,
                     "fill_rate": f / len(cand) * 100,
                     "per_trade": st.mean(t["net"] for t in cand),
                     "win_rate": sum(1 for t in cand if t["result"] == "win")
                     / len(cand) * 100})
    print("  월 %d개" % len(rows), flush=True)
    print("  %-9s %6s %6s %8s %11s %8s" % ("월", "후보", "체결", "체결률", "그달 거래당", "승률"),
          flush=True)
    for r in rows:
        print("  %-9s %6d %6.0f %7.1f%% %+10.4f%%p %7.2f%%"
              % (r["month"], r["n_cand"], r["n_fill"], r["fill_rate"],
                 r["per_trade"], r["win_rate"]), flush=True)
    res["months"] = rows

    # ── 20번 설계 답변용 · 월 축 검정력 ──
    print("\n═══ 20번 설계용 · **월 축에서 가릴 수 있는 최소 크기** ═══", flush=True)
    mv = [r["per_trade"] for r in rows]
    sd_m = st.pstdev(mv)
    print("  월 거래당의 월간 표준편차 **%.3f%%p** (월 %d개, 중앙 %+.3f)"
          % (sd_m, len(mv), st.median(mv)), flush=True)
    for nm, na in (("절반 분할", len(mv) // 2), ("상위/하위 3분위", len(mv) // 3),
                   ("상위/하위 5분위", len(mv) // 5)):
        nb = na
        se = sd_m * sqrt(1 / na + 1 / nb)
        print("  %-14s %2d vs %2d → **월 거래당 차이 %.3f%%p 이상**이어야 가린다 · MDE %.3f%%p"
              % (nm, na, nb, 1.96 * se, 2.80 * se), flush=True)
        res.setdefault("month_power", {})[nm] = {"n_a": na, "need": 1.96 * se,
                                                 "MDE": 2.80 * se}
    # 월 체결률 자체의 분포
    fr = [r["fill_rate"] for r in rows]
    print("  월 체결률 분포: 최저 %.1f%% · 중앙 %.1f%% · 최고 %.1f%% · 0%%인 달 %d개"
          % (min(fr), st.median(fr), max(fr), sum(1 for x in fr if x == 0)), flush=True)
    res["fill_rate_dist"] = {"min": min(fr), "median": st.median(fr), "max": max(fr),
                             "n_zero": sum(1 for x in fr if x == 0),
                             "sd_month_per_trade": sd_m}

    (OUT / "19d-decile-and-months.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/19d-decile-and-months.json")


if __name__ == "__main__":
    main()
