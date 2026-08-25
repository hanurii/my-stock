# -*- coding: utf-8 -*-
"""64 — **61·62번을 「거래당」으로 다시 잰다.**

🚨 63번이 보였다: 자산은 「종목의 질」과 「5칸이 무엇을 집었나」가 섞인 값이다.
   관문이 좋은지 물으려면 **거래당**으로 물어야 한다.

관문의 «본질»은 두 무리로 가르는 것이다 → **통과 무리 vs 탈락 무리**의 거래당 차이를 잰다.
(부분집합 대 전체가 아니라 «서로 겹치지 않는» 두 무리라 견줌이 깨끗하다.)
"""
from __future__ import annotations
import importlib.util as _u, json, random, statistics as st, sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]; HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
_s = _u.spec_from_file_location("r61b", HERE / "61b-matched-null.py")
r61b = _u.module_from_spec(_s); _s.loader.exec_module(r61b)
r41 = r61b.r41; r61 = r61b.r61
OUT = ROOT / ".cache" / "bt5y" / "out"
COST = (0.0, 0.002); N_BOOT = 2000; BSEED = 640825
KS = (1, 2, 3, 4, 5, 11); PS = (0.10, 0.20, 0.30, 0.40, 1.00)


def boot_diff(a_vals, a_keys, b_vals, b_keys):
    """두 무리의 평균 차이 — 날짜 블록으로 재표집."""
    A, B = defaultdict(list), defaultdict(list)
    for v, k in zip(a_vals, a_keys): A[k].append(v)
    for v, k in zip(b_vals, b_keys): B[k].append(v)
    ks = sorted(set(A) | set(B)); rnd = random.Random(BSEED); ms = []
    for _ in range(N_BOOT):
        pick = [rnd.choice(ks) for _ in ks]
        av = [v for k in pick for v in A.get(k, ())]
        bv = [v for k in pick for v in B.get(k, ())]
        if av and bv: ms.append(st.mean(av) - st.mean(bv))
    ms.sort(); n = len(ms)
    return ms[int(n * .025)], ms[int(n * .975)]


def main() -> int:
    if r41.YEARS[0] != 2017: print("BT_Y0=2017 필요"); return 2
    by, _m = r41.v39.load_paths(); r41.TARGET_FILL, r41.STOP_FILL = "limit", "market"
    for vn, fn, _l, _h in r41.VARIANTS:
        if vn == "1a": ev0, _b = r41.replay(by, fn)
    pack = json.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({y for d in monthly.values() for y in d if y >= "2016-12"})
    mret = r61b.month_returns(monthly, sector, months)
    with r41.Cost(*COST): allpt = r41.per_trade(ev0)
    pt = {id(e): v for e, v in zip(ev0, allpt)}
    print("=" * 94)
    print("64 — 61·62번을 **거래당**으로 다시 잰다 (청산 1a · 우대수수료 · 9년)")
    print("=" * 94)
    print("전체 %d건 거래당 **%+.4f%%**\n" % (len(ev0), st.mean(allpt)), flush=True)

    cache = {K: r61b.make_flags(mret, sector, K) if False else None for K in KS}
    # make_flags 는 K 를 안 받으므로 여기서 직접 만든다
    def flags(K):
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
    for K in KS: cache[K] = flags(K)

    RES = {}
    print("  칸        통과 n   **통과 거래당**   탈락 n   탈락 거래당   **차이**      95%% 구간        판정",
          flush=True)
    for K in KS:
        top, pct = cache[K]
        for P in PS:
            if K == 11 and P == 1.00: continue
            A, B = [], []
            for e in ev0:
                s = sector.get(e["code"]); ok = True
                if s:
                    ym = r61.prev_ym(e["scan_date"][:7], 1); tp = top.get(ym)
                    if tp is not None:
                        ok = (s in tp) and (pct.get(ym, {}).get(e["code"], 1.0) <= P)
                (A if ok else B).append(e)
            av = [pt[id(e)] for e in A]; bv = [pt[id(e)] for e in B]
            if len(A) < 200 or len(B) < 200: continue
            d = st.mean(av) - st.mean(bv)
            lo, hi = boot_diff(av, [e["entry_date"] for e in A],
                               bv, [e["entry_date"] for e in B])
            ok = (lo > 0) or (hi < 0)
            print("  K%-2d P%3.0f%%  %6d   %+9.4f%%   %6d   %+9.4f%%   %+8.4f%%p [%+7.4f ~%+7.4f]  **%s**"
                  % (K, P * 100, len(A), st.mean(av), len(B), st.mean(bv), d, lo, hi,
                     "0 배제" if ok else "0 포함"), flush=True)
            RES["K%d|P%.2f" % (K, P)] = {"nA": len(A), "ptA": st.mean(av),
                                         "nB": len(B), "ptB": st.mean(bv),
                                         "diff": d, "lo": lo, "hi": hi, "excl0": ok}
    n_ok = sum(1 for v in RES.values() if v["excl0"])
    n_pos = sum(1 for v in RES.values() if v["diff"] > 0)
    print("\n── 정리 ──", flush=True)
    print("  칸 %d개 중 — 차이가 «플러스» %d개 · **95%% 구간이 0 을 배제 %d개**"
          % (len(RES), n_pos, n_ok), flush=True)
    best = max(RES, key=lambda k: RES[k]["diff"])
    print("  (참고) 차이가 가장 큰 칸 %s %+.4f%%p — **고르지 않는다**"
          % (best, RES[best]["diff"]), flush=True)
    json.dump(RES, open(OUT / "64-pertrade-recheck.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n저장: 64-pertrade-recheck.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
