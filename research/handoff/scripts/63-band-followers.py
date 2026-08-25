# -*- coding: utf-8 -*-
"""63 — **1등이 아니라 2·3등인가**. 사전등록: `tasks/63-band-followers.md`"""
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
COST = (0.0, 0.002); K = 3; N_SEED = 120; N_BOOT = 2000; BSEED = 630825
BANDS = ((0.0, 0.10), (0.10, 0.20), (0.20, 0.30), (0.30, 0.40),
         (0.40, 0.60), (0.60, 1.00))


def boot(vals, keys):
    byk = defaultdict(list)
    for v, k in zip(vals, keys): byk[k].append(v)
    ks = sorted(byk); rnd = random.Random(BSEED); ms = []
    for _ in range(N_BOOT):
        pick = [rnd.choice(ks) for _ in ks]
        ms.append(st.mean(v for k in pick for v in byk[k]))
    ms.sort()
    return ms[int(N_BOOT * .025)], ms[int(N_BOOT * .975)]


def main() -> int:
    if r41.YEARS[0] != 2017: print("BT_Y0=2017 필요"); return 2
    by, _m = r41.v39.load_paths(); r41.TARGET_FILL, r41.STOP_FILL = "limit", "market"
    for vn, fn, _l, _h in r41.VARIANTS:
        if vn == "1a": ev0, _b = r41.replay(by, fn)
    pack = json.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({y for d in monthly.values() for y in d if y >= "2016-12"})
    mret = r61b.month_returns(monthly, sector, months)
    top, pct = r61b.make_flags(mret, sector)
    # 6개월 수익률 값도 꺼내 둔다 (B용)
    r6 = {ym: dict(v) for ym, v in mret.items()}

    pmap = {(p["scan_date"], p["code"], p["pattern"]): p for ps in by.values() for p in ps}
    print("=" * 92); print("63 — **1등이 아니라 2·3등인가** (K=%d · 청산 1a · 우대수수료 · 9년)" % K)
    print("=" * 92, flush=True)
    with r41.Cost(*COST): allpt = r41.per_trade(ev0)
    pt_of = {id(e): v for e, v in zip(ev0, allpt)}

    rows = []
    for lo, hi in BANDS:
        sel = []
        for e in ev0:
            s = sector.get(e["code"])
            if not s: continue
            ym = r61.prev_ym(e["scan_date"][:7], 1)
            tp = top.get(ym)
            if tp is None or s not in tp: continue
            q = pct.get(ym, {}).get(e["code"])
            if q is None or not (lo <= q < hi): continue
            sel.append(e)
        v = [pt_of[id(e)] for e in sel]
        keys = [e["entry_date"] for e in sel]
        blo, bhi = boot(v, keys)
        w = [x for x in v if x > 0]; l = [x for x in v if x <= 0]
        # B: 이미 오른 폭 — ① 순위를 만든 6개월(거의 항등식) ② «진입 직전 20일»(다른 창)
        r6v, r20 = [], []
        for e in sel:
            ym = r61.prev_ym(e["scan_date"][:7], 1)
            x = r6.get(ym, {}).get(e["code"])
            if x is not None: r6v.append(x * 100)
            p = pmap.get((e["scan_date"], e["code"], e["pattern"]))
            if p and len(p["c"]) > 0:
                # 경로는 진입일부터라 «직전» 값이 없다 → 피벗 대비 진입가로 대신한다
                r20.append((p["entry_price"] / p["pivot"] - 1) * 100)
        with r41.Cost(*COST):
            eq = st.median(sf.sim_frac(sel, slots=5, seed=i, sizing="cash")["equity_pct"]
                           for i in range(N_SEED)) if len(sel) > 200 else float("nan")
        rows.append((lo, hi, len(sel), st.mean(v), blo, bhi,
                     100.0 * len(w) / len(v), st.mean(w), st.mean(l),
                     st.median(r6v) if r6v else float("nan"),
                     st.median(r20) if r20 else float("nan"), eq))
    print("\n  구간        진입   **거래당**       95%% 구간        승률   평균승   평균패   "
          "6M상승(중앙)  자산", flush=True)
    for lo, hi, n, m, blo, bhi, wr, aw, al, m6, _m20, eq in rows:
        print("  %3.0f~%3.0f%%  %6d   %+8.4f%%  [%+7.3f ~%+7.3f]  %5.1f%%  %+6.2f%%  %+6.2f%%"
              "   %+8.1f%%   %+8.1f%%"
              % (lo * 100, hi * 100, n, m, blo, bhi, wr, aw, al, m6, eq), flush=True)

    b0, b1, b2 = rows[0], rows[1], rows[2]
    print("\n── 사전등록 판정 ──", flush=True)
    a1 = (b0[3] < b1[3]) and (b0[3] < b2[3])
    print("  A1. 0~10%% 거래당(%+.4f%%)이 10~20%%(%+.4f%%)·20~30%%(%+.4f%%) «둘 다»보다 낮은가 → **%s**"
          % (b0[3], b1[3], b2[3], "그렇다 — 통과" if a1 else "아니다 — **기각**"), flush=True)
    # A2 — 짝이 아니라 독립 두 무리라 구간 겹침으로 본다
    ov1 = not (b0[5] < b1[4] or b1[5] < b0[4])
    ov2 = not (b0[5] < b2[4] or b2[5] < b0[4])
    print("  A2. 95%% 구간이 겹치지 않는가 — vs 10~20%% **%s** · vs 20~30%% **%s**"
          % ("안 겹침" if not ov1 else "겹침", "안 겹침" if not ov2 else "겹침"), flush=True)
    b1ok = b0[9] == max(r[9] for r in rows)
    print("  B1. 0~10%%의 「이미 오른 폭」이 가장 큰가 (%+.1f%%) → **%s** "
          "(⚠️ 순위를 만든 그 수익률이라 거의 항등식 — 확인용)"
          % (b0[9], "그렇다" if b1ok else "아니다"), flush=True)
    print("\n  참고 — 피벗 대비 진입가(갭업 정도) 구간별:", flush=True)
    for lo, hi, _n, _m, _a, _b, _w, _aw, _al, _m6, m20, _eq in rows:
        print("    %3.0f~%3.0f%%  %+.3f%%" % (lo * 100, hi * 100, m20), flush=True)
    json.dump({"bands": [{"lo": r[0], "hi": r[1], "n": r[2], "pt": r[3],
                          "lo95": r[4], "hi95": r[5], "win": r[6], "avgw": r[7],
                          "avgl": r[8], "r6": r[9], "gap": r[10], "eq": r[11]}
                         for r in rows], "A1": a1, "B1": b1ok},
              open(OUT / "63-band-followers.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n저장: 63-band-followers.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
