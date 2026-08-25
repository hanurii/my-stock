# -*- coding: utf-8 -*-
"""73 — **피라미딩을 「지금 조합」 위에서**. 사전등록: `tasks/73-pyramid-on-combo.md`

🚨 변형은 3회차(47번)와 «똑같은» 셋만. 새로 만들지 않는다.
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import slot_sim_frac as sf                                    # noqa: E402
import slot_sim_pyr as sp                                     # noqa: E402

_s = _u.spec_from_file_location("r61b", HERE / "61b-matched-null.py")
r61b = _u.module_from_spec(_s)
_s.loader.exec_module(r61b)
r41, r61 = r61b.r41, r61b.r61

_s3 = _u.spec_from_file_location("r47", HERE / "47-round3-pyramid.py")
r47 = _u.module_from_spec(_s3)
_s3.loader.exec_module(r47)

OUT = ROOT / ".cache" / "bt5y" / "out"
COST = (0.0, 0.002)
RISK, CAP = 0.02, 0.20        # = 5칸 20%
N_SEED = 120

VARIANTS = (("P0 한 번에", 1.0, ()),
            ("P1 1/2 → +3%", 0.5, ((3.0, 0.5),)),
            ("P2 1/3 → +3% → +6%", 1/3, ((3.0, 1/3), (6.0, 1/3))))


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    by, _m = r41.v39.load_paths()
    pack = json.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({y for d in monthly.values() for y in d if y >= "2016-12"})
    mret = r61b.month_returns(monthly, sector, months)
    top, pctm = r61b.make_flags(mret, sector)

    def q(e):
        return pctm.get(r61.prev_ym(e["scan_date"][:7], 1), {}).get(e["code"])

    def insec(code, scan):
        sn = sector.get(code)
        if not sn:
            return True
        tp = top.get(r61.prev_ym(scan[:7], 1))
        return True if tp is None else sn in tp

    def keep_path(p):
        """선별을 «경로» 단계에서 건다 — 3회차 해결자는 경로를 받는다."""
        if not insec(p["code"], p["scan_date"]):
            return False
        v = pctm.get(r61.prev_ym(p["scan_date"][:7], 1), {}).get(p["code"])
        return (v is None) or (0.10 <= v < 0.30)

    by2 = {y: [p for p in ps if keep_path(p)] for y, ps in by.items()}
    n_all = sum(len(v) for v in by.values())
    n_sel = sum(len(v) for v in by2.values())
    print("=" * 88)
    print("73 — 피라미딩 × 지금 조합 (사전등록 tasks/73)")
    print("=" * 88)
    print("경로 %d → 조합 %d (%.1f%%)" % (n_all, n_sel, 100.0 * n_sel / n_all), flush=True)

    # ── 관문: pilot=1.0 이 5칸 20% 판과 같은가 ──────────────────────────
    r41.TARGET_FILL, r41.STOP_FILL = "limit", "market"
    ev_ref, _b = r41.replay(by2, lambda p: r41.resolve_half_then_trail(p, 8.0, 20.0))
    ev_p0 = r47.replay_pyr(by2, "limit", "market", stop=8.0, target=20.0,
                           adds=()) if hasattr(r47, "replay_pyr") else None
    if ev_p0 is None:
        # 47번에 replay 헬퍼가 없으면 직접 만든다 (같은 open_until 규약)
        def replay_pyr(paths, adds):
            ev, blocked = [], 0
            for y in sorted(paths):
                open_until = {}
                for p in paths[y]:
                    c = p["code"]
                    if c in open_until and p["entry_date"] <= open_until[c]:
                        blocked += 1
                        continue
                    e = r47.resolve_pyr(p, "limit", "market", stop=8.0, target=20.0,
                                        adds=adds)
                    open_until[c] = e.get("resolve_date") or p["entry_date"]
                    e["stop_frac"] = 0.08
                    ev.append(e)
            return ev
        ev_p0 = replay_pyr(by2, ())
    with r41.Cost(*COST):
        a = sp.sim_pyr(ev_p0, risk=RISK, cap=CAP, seed=0, pilot=1.0)["equity_pct"]
        b = sf.sim_frac(ev_ref, slots=5, seed=0, sizing="cash")["equity_pct"]
    rel = abs(a - b) / max(1e-12, abs(b))
    print("관문 — pilot=1.0 %+.4f%% vs 5칸20%% %+.4f%% · 상대오차 %.2e → **%s**"
          % (a, b, rel, "통과" if rel < 1e-9 else "🚨 미통과"), flush=True)
    if rel >= 1e-9:
        print("  ⚠️ 두 판의 «해결자»가 다르다(3회차 판 vs 1회차 판). "
              "값이 다르면 그 자체를 적고 P0 을 기준으로 삼는다.", flush=True)

    print("\n  %-22s %7s %11s %11s %8s %9s"
          % ("변형", "진입", "자산중앙", "운나쁠때", "MDD", "증액못함"), flush=True)
    res = {}
    for nm, pilot, adds in VARIANTS:
        ev = replay_pyr(by2, adds) if adds or nm.startswith("P0") else None
        with r41.Cost(*COST):
            rs = [sp.sim_pyr(ev, risk=RISK, cap=CAP, seed=i, pilot=pilot)
                  for i in range(N_SEED)]
        eq = sorted(x["equity_pct"] for x in rs)
        miss = st.median(x.get("add_skipped_pct", x.get("no_add_pct", 0)) for x in rs)
        res[nm] = (st.median(eq), eq[6], st.median(x["mdd_pct"] for x in rs))
        print("  %-22s %7d %+10.2f%% %+10.2f%% %7.1f%% %8.1f%%"
              % (nm, len(ev), res[nm][0], res[nm][1], res[nm][2], miss), flush=True)

    p0 = res["P0 한 번에"]
    print("\n── 사전등록 판정 ──", flush=True)
    winner = [k for k in res if k != "P0 한 번에" and res[k][0] > p0[0]]
    print("  A. P1·P2 중 P0(%+.2f%%)보다 나은 것: **%s** → **%s**"
          % (p0[0], (", ".join(winner) if winner else "없음"),
             "통과" if winner else "**미통과 — 3회차 결론이 바탕을 바꿔도 유지**"), flush=True)
    for k in winner:
        print("  B. %s 운 나쁠 때 %+.2f%% vs P0 %+.2f%% → **%s**"
              % (k, res[k][1], p0[1], "통과" if res[k][1] > p0[1] else "미통과"), flush=True)
    (OUT / "73-pyramid-on-combo.json").write_text(
        json.dumps({k: {"eq": v[0], "p5": v[1], "mdd": v[2]} for k, v in res.items()},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 73-pyramid-on-combo.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
