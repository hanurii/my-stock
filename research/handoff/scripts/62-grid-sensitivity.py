# -*- coding: utf-8 -*-
"""62 — **「상위 3섹터 / 상위 20%」가 특별한가**. 사전등록: `tasks/62-grid-sensitivity.md`

🚨 목적은 **최선 찾기가 아니라 「고원인가」**다. 최선 칸을 골라 인용하지 않는다.
실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python 62-grid-sensitivity.py
"""
from __future__ import annotations
import importlib.util as _u, json, random, statistics as st, sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]; HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim_frac as sf
_s = _u.spec_from_file_location("r61b", HERE / "61b-matched-null.py")
r61b = _u.module_from_spec(_s); _s.loader.exec_module(r61b)
r41 = r61b.r41; r61 = r61b.r61
OUT = ROOT / ".cache" / "bt5y" / "out"
N_SEED = 120; N_NULL = 60; N_SEED_NULL = 12
COST = (0.0, 0.002)          # 우대수수료 — 매수 0%, 매도 세금 0.2%
KS = (1, 2, 3, 4, 5, 11); PS = (0.10, 0.20, 0.30, 0.40, 1.00)


def flags(mret, sector, K):
    top, pct = {}, {}
    for ym, v in mret.items():
        bysec = defaultdict(list)
        for t, r in v: bysec[sector[t]].append((r, t))
        sm = {s: st.mean(x for x, _ in l) for s, l in bysec.items() if len(l) >= 5}
        top[ym] = set(sorted(sm, key=lambda s: -sm[s])[:K])
        d = {}
        for s, l in bysec.items():
            l.sort(key=lambda x: -x[0]); n = len(l)
            for i, (_r, t) in enumerate(l): d[t] = i / n
        pct[ym] = d
    return top, pct


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("BT_Y0=2017 필요"); return 2
    by, _m = r41.v39.load_paths(); r41.TARGET_FILL, r41.STOP_FILL = "limit", "market"
    for vn, fn, _l, _h in r41.VARIANTS:
        if vn == "1a": ev0, _b = r41.replay(by, fn)
    pack = json.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({y for d in monthly.values() for y in d if y >= "2016-12"})
    mret = r61b.month_returns(monthly, sector, months)

    def eq(ev, n=N_SEED):
        with r41.Cost(*COST):
            return st.median(sf.sim_frac(ev, slots=5, seed=i, sizing="cash")["equity_pct"]
                             for i in range(n))
    base = eq(ev0)
    print("=" * 86); print("62 — 격자 민감도 (사전등록 tasks/62) · 청산 1a · 우대수수료")
    print("=" * 86)
    print("R0 (필터 없음) 자산 중앙 **%+.2f%%** · 진입 %d\n" % (base, len(ev0)), flush=True)

    cache = {K: flags(mret, sector, K) for K in KS}
    grid, ent = {}, {}
    print("  자산 중앙 (%)         P=10%%      P=20%%      P=30%%      P=40%%     P=100%%", flush=True)
    for K in KS:
        top, pct = cache[K]
        row = []
        for P in PS:
            ev = []
            for e in ev0:
                s = sector.get(e["code"])
                if not s: ev.append(e); continue
                ym = r61.prev_ym(e["scan_date"][:7], 1)
                tp = top.get(ym)
                if tp is None: ev.append(e); continue
                if (s in tp) and (pct.get(ym, {}).get(e["code"], 1.0) <= P):
                    ev.append(e)
            v = eq(ev); grid[(K, P)] = v; ent[(K, P)] = len(ev)
            row.append("%+9.1f" % v)
        print("  K=%-2d %s   %s" % (K, "상위섹터" if K < 11 else "전부   ", " ".join(row)), flush=True)
    print("\n  진입 건수", flush=True)
    for K in KS:
        print("  K=%-2d          %s" % (K, " ".join("%9d" % ent[(K, P)] for P in PS)), flush=True)

    # ── 판정 ────────────────────────────────────────────────────────────
    cells25 = [(K, P) for K in KS if K <= 5 for P in PS]
    better = [c for c in cells25 if grid[c] > base]
    print("\n── 사전등록 판정 ──", flush=True)
    print("  A. K<=5 인 25칸 중 R0(%+.2f%%)보다 나은 칸: **%d / 25** → **%s**"
          % (base, len(better), "통과" if len(better) >= 20 else "미통과"), flush=True)
    nb = [(K, P) for K in (2, 3, 4) for P in (0.10, 0.20, 0.30)]
    nb_ok = [c for c in nb if grid[c] > base]
    print("  B. S3 이웃 9칸(K 2~4 × P 10~30%%) 중 나은 칸: **%d / 9** → **%s**"
          % (len(nb_ok), "통과" if len(nb_ok) == 9 else "미통과"), flush=True)
    print("     값: %s" % " · ".join("K%d/P%.0f %+.0f" % (K, P * 100, grid[(K, P)])
                                     for K, P in nb), flush=True)

    # ── C. 같은 수를 무작위로 (칸별) ────────────────────────────────────
    print("\n  C. 「같은 수를 무작위로」 대비 (칸마다 %d회)" % N_NULL, flush=True)
    bymon = defaultdict(list)
    for e in ev0: bymon[e["entry_date"][:7]].append(e)
    rnd = random.Random(620825); npass = 0
    for K in (2, 3, 4):
        for P in (0.10, 0.20, 0.30):
            top, pct = cache[K]
            real = []
            for e in ev0:
                s = sector.get(e["code"])
                if not s: real.append(e); continue
                ym = r61.prev_ym(e["scan_date"][:7], 1); tp = top.get(ym)
                if tp is None: real.append(e); continue
                if (s in tp) and (pct.get(ym, {}).get(e["code"], 1.0) <= P): real.append(e)
            cnt = defaultdict(int)
            for e in real: cnt[e["entry_date"][:7]] += 1
            null = []
            for _i in range(N_NULL):
                sel = []
                for ym, lst in bymon.items():
                    kk = cnt.get(ym, 0)
                    if kk: sel.extend(rnd.sample(lst, min(kk, len(lst))))
                null.append(eq(sel, N_SEED_NULL))
            null.sort(); p95 = null[int(N_NULL * .95)]
            ok = grid[(K, P)] > p95; npass += ok
            print("     K%d/P%.0f%%  관측 %+8.1f%%  무작위 95%% %+8.1f%%  → **%s**"
                  % (K, P * 100, grid[(K, P)], p95, "넘음" if ok else "범위 안"), flush=True)
    print("  → 넘은 칸 **%d / 9** → **%s**" % (npass, "통과" if npass >= 5 else "미통과"),
          flush=True)
    json.dump({"base": base, "grid": {"%d|%.2f" % k: v for k, v in grid.items()},
               "entries": {"%d|%.2f" % k: v for k, v in ent.items()},
               "A_better": len(better), "B_nb": len(nb_ok), "C_pass": npass},
              open(OUT / "62-grid-sensitivity.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n저장: 62-grid-sensitivity.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
