# -*- coding: utf-8 -*-
"""19 · 0단계 — 진입 전에 알 수 있는 거래량 값을 붙인다.

지시서: research/handoff/tasks/19-volume-axis.md (사전등록)

★ 오염 필드 `rel_vol_entry_LOOKAHEAD_DO_NOT_FILTER` = `rel_volume(s, ni)` 는
  **진입일 당일 종가**가 나와야 정해진다. 진입은 그날 **시가**다 → 미래를 본다.
  **1·2단계 어디에도 쓰지 않는다.** 여기서는 **재현 관문의 대조 대상**으로만 쓴다
  (두뇌 세션 승인 · 조건 셋: 값을 흘리지 않음 · 일치율을 수치로 · 불일치면 멈춤).

붙이는 값(전부 ni−1 이하만 사용):
  rv_1   = rel_volume(s, ni−1)
  rv_2   = rel_volume(s, ni−2)
  rv_5   = ni−5 ~ ni−1 의 rel_volume 평균
  dryup  = (ni−5~ni−1 평균 거래량) ÷ (ni−50~ni−6 평균 거래량)

정의는 `canslim_lib.pivot_backtest.rel_volume` 을 **그대로 import** 해서 쓴다(재구현하지 않는다).

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/19-volume-axis.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from bisect import bisect_left
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts"))
import slot_sim  # noqa: E402
from canslim_lib.pdata_series import build_series  # noqa: E402
from canslim_lib.pivot_backtest import rel_volume  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
PDATA = ROOT / ".cache" / "pdata"
WARM, TAIL = 430, 300
CONTAM = "rel_vol_entry_LOOKAHEAD_DO_NOT_FILTER"
BUCKETS = [("<1.0", 0.0, 1.0), ("1.0~1.5", 1.0, 1.5), ("1.5~2.0", 1.5, 2.0),
           ("2.0~3.0", 2.0, 3.0), ("≥3.0", 3.0, 1e18)]
NETF = None


def iter_pdata(s, e):
    a, b = s.replace("-", ""), e.replace("-", "")
    for p in sorted(PDATA.glob("price_*.json")):
        d = p.stem[6:]
        if not (a <= d <= b):
            continue
        try:
            recs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        yield "%s-%s-%s" % (d[:4], d[4:6], d[6:]), recs


def main():
    global NETF
    K = (1 - 0.002034) / (1 + 0.000034)          # 17번 정본 비용(우대)
    NETF = lambda gg: ((1 + gg / 100) * K - 1) * 100

    rows, diag = [], Counter()
    for y in range(2021, 2027):
        d = json.loads((BT / ("bt_%d.json" % y)).read_text(encoding="utf-8"))
        prm = d["params"]
        w = (datetime.strptime(prm["start"], "%Y-%m-%d")
             - timedelta(days=WARM)).strftime("%Y-%m-%d")
        le = (datetime.strptime(prm["end"], "%Y-%m-%d")
              + timedelta(days=TAIL)).strftime("%Y-%m-%d")
        need = {e["code"] for e in d["events"]}
        print("[%d] 시계열 %s ~ %s · 종목 %d …" % (y, w, le, len(need)), flush=True)
        full = build_series((dt, {c: r for c, r in recs.items() if c in need})
                            for dt, recs in iter_pdata(w, le))
        for e in d["events"]:
            s = full.get(e["code"])
            if not s:
                diag["series_missing"] += 1
                continue
            ds = s["dates"]
            i = bisect_left(ds, e["entry_date"])
            ni = i if (i < len(ds) and ds[i] == e["entry_date"]) else None
            if ni is None:
                diag["entry_date_missing"] += 1
                continue
            vol = s["volumes"]
            rec = {"code": e["code"], "pattern": e["pattern"],
                   "scan_date": e["scan_date"], "entry_date": e["entry_date"],
                   "year": e["entry_date"][:4], "gain": e["gain_at_resolve_pct"],
                   "result": e["result"], "resolve_date": e["resolve_date"],
                   "days_held": e.get("days_held"),
                   "_contam_recorded": e.get(CONTAM),
                   "_contam_recomputed": rel_volume(s, ni) if ni < len(vol) else None}
            rec["rv_1"] = rel_volume(s, ni - 1) if ni - 1 >= 0 else None
            rec["rv_2"] = rel_volume(s, ni - 2) if ni - 2 >= 0 else None
            v5 = [rel_volume(s, j) for j in range(ni - 5, ni) if j >= 0]
            v5 = [x for x in v5 if x is not None]
            rec["rv_5"] = st.mean(v5) if len(v5) == 5 else None
            if ni - 50 >= 0:
                a = [v for v in vol[ni - 5:ni] if v]
                b = [v for v in vol[ni - 50:ni - 5] if v]
                rec["dryup"] = (st.mean(a) / st.mean(b)) if (a and b) else None
            else:
                rec["dryup"] = None
            rows.append(rec)
        del full
        print("[%d]   누적 %d" % (y, len(rows)), flush=True)

    n = len(rows)
    print("\n═══ 0-1 · 재현 관문 (오염 필드는 대조 대상일 뿐 입력이 아니다) ═══", flush=True)
    both = [r for r in rows if r["_contam_recorded"] is not None
            and r["_contam_recomputed"] is not None]
    same = [r for r in both
            if abs(r["_contam_recorded"] - r["_contam_recomputed"]) < 5e-3]
    diff = [r for r in both if r not in same]
    print("  대조 가능 %d / %d · **일치 %d (%.4f%%)** · 불일치 %d"
          % (len(both), n, len(same), len(same) / len(both) * 100, len(diff)), flush=True)
    if diff:
        dv = sorted(abs(r["_contam_recorded"] - r["_contam_recomputed"]) for r in diff)
        print("  불일치 절대차: 중앙 %.4f · 최대 %.4f · 상위 5건 %s"
              % (st.median(dv), max(dv), [round(x, 3) for x in dv[-5:]]), flush=True)
        by_y = Counter(r["year"] for r in diff)
        print("  불일치 연도별: %s" % dict(sorted(by_y.items())), flush=True)
    gate_ok = len(diff) == 0
    print("  → 재현 관문 **%s**" % ("통과" if gate_ok else "**실패 — 여기서 멈춘다**"),
          flush=True)

    print("\n═══ 0-2 · 결측률 (조용히 버리지 않는다) ═══", flush=True)
    miss = {}
    for k in ("rv_1", "rv_2", "rv_5", "dryup"):
        m = sum(1 for r in rows if r[k] is None)
        miss[k] = {"n_missing": m, "pct": m / n * 100}
        print("  %-6s 결측 %4d / %d = **%.2f%%**" % (k, m, n, m / n * 100), flush=True)
    print("  시계열 없음 %d · 진입일 없음 %d" % (diag["series_missing"],
                                          diag["entry_date_missing"]), flush=True)

    print("\n═══ 0-3 · 구간별 **건수만** (성적은 1단계에서) ═══", flush=True)
    have = [r for r in rows if r["rv_1"] is not None]
    bk = {}
    for nm, lo, hi in BUCKETS:
        sel = [r for r in have if lo <= r["rv_1"] < hi] if nm != "<1.0" else \
              [r for r in have if r["rv_1"] < 1.0]
        bk[nm] = len(sel)
        print("  %-8s n = %4d (%.1f%%)" % (nm, len(sel), len(sel) / len(have) * 100),
              flush=True)
    ge = sum(1 for r in have if r["rv_1"] >= 1.5)
    lt = len(have) - ge
    print("  주검정 분할: rv_1 ≥ 1.5 **%d건** vs < 1.5 **%d건**" % (ge, lt), flush=True)

    print("\n═══ 0-4 · 조건 ①이 넘으려면 얼마가 필요한가 (성적 미사용) ═══", flush=True)
    sd = st.pstdev([NETF(r["gain"]) for r in have])
    se = sd * sqrt(1 / ge + 1 / lt)
    print("  거래당 순수익 표준편차 **%.2f%%p** · 두 집단 차이의 표준오차 **%.4f%%p**"
          % (sd, se), flush=True)
    print("  → **차이가 %.3f%%p 이상이어야 95%% 구간이 0을 배제한다**(1.96 × SE)"
          % (1.96 * se), flush=True)
    print("  → **MDE(2.80 × SE) = %.3f%%p**" % (2.80 * se), flush=True)

    out = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    (OUT / "19-volume-features.json").write_text(
        json.dumps({"n": n, "rows": out}, ensure_ascii=False), encoding="utf-8")
    (OUT / "19-volume-axis-stage0.json").write_text(
        json.dumps({"n": n, "gate": {"comparable": len(both), "same": len(same),
                                     "diff": len(diff), "passed": gate_ok},
                    "missing": miss, "buckets": bk,
                    "split": {"ge1_5": ge, "lt1_5": lt},
                    "precheck": {"sd": sd, "se": se, "need_for_ci": 1.96 * se,
                                 "MDE": 2.80 * se}},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 19-volume-features.json · 19-volume-axis-stage0.json")


if __name__ == "__main__":
    main()
