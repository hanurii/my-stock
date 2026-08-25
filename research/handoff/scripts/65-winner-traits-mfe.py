# -*- coding: utf-8 -*-
"""65 — 큰 승자는 「살 때」 알 수 있었나 + 청산에서 얼마를 남기고 나오나."""
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
COST = (0.0, 0.002); N_BOOT = 2000; BSEED = 650825


def boot_diff(av, ak, bv, bk):
    A, B = defaultdict(list), defaultdict(list)
    for v, k in zip(av, ak): A[k].append(v)
    for v, k in zip(bv, bk): B[k].append(v)
    ks = sorted(set(A) | set(B)); rnd = random.Random(BSEED); ms = []
    for _ in range(N_BOOT):
        p = [rnd.choice(ks) for _ in ks]
        a = [v for k in p for v in A.get(k, ())]; b = [v for k in p for v in B.get(k, ())]
        if a and b: ms.append(st.mean(a) - st.mean(b))
    ms.sort(); n = len(ms)
    return ms[int(n * .025)], ms[int(n * .975)]


def main() -> int:
    if r41.YEARS[0] != 2017: print("BT_Y0=2017 필요"); return 2
    by, _m = r41.v39.load_paths(); r41.TARGET_FILL, r41.STOP_FILL = "limit", "market"
    for vn, fn, _l, _h in r41.VARIANTS:
        if vn == "1a": ev0, _b = r41.replay(by, fn)
    pmap = {(p["scan_date"], p["code"], p["pattern"]): p for ps in by.values() for p in ps}
    pack = json.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({y for d in monthly.values() for y in d if y >= "2016-12"})
    mret = r61b.month_returns(monthly, sector, months)
    pctm = {}
    for ym, v in mret.items():
        bysec = defaultdict(list)
        for t, r in v: bysec[sector[t]].append((r, t))
        d = {}
        for sn, l in bysec.items():
            l.sort(key=lambda x: -x[0]); n = len(l)
            for i, (_r, t) in enumerate(l): d[t] = i / n
        pctm[ym] = d
    with r41.Cost(*COST): pt = r41.per_trade(ev0)
    pairs = list(zip(ev0, pt))
    N = len(pairs); TOPN = max(1, N // 100)
    thr = sorted(pt, reverse=True)[TOPN - 1]
    print("=" * 92)
    print("65 — 큰 승자의 사전 특징 + MFE (9년 · 청산 1a · 우대수수료)")
    print("=" * 92)
    print("신호 %d건 · 「큰 승자」= 상위 1%% (%d건, 총수익 >= %+.1f%%)\n" % (N, TOPN, thr), flush=True)

    def feat(e):
        ym = r61.prev_ym(e["scan_date"][:7], 1)
        q = pctm.get(ym, {}).get(e["code"])
        p = pmap.get((e["scan_date"], e["code"], e["pattern"]))
        ab = p.get("atr_band") if p else None
        return {"pattern": e["pattern"], "rs": q, "sector": sector.get(e["code"]),
                "atr": ab, "year": e["entry_date"][:4]}

    F = {id(e): feat(e) for e, _v in pairs}

    def axis(name, keyfn, order=None):
        g = defaultdict(list)
        for e, v in pairs:
            k = keyfn(F[id(e)])
            if k is None: continue
            g[k].append((e, v))
        ks = order or sorted(g, key=lambda k: -len(g[k]))
        print("\n── %s ──" % name, flush=True)
        print("  %-22s %7s %9s %12s   %s" % ("값", "n", "큰승자%", "거래당", "전진검정(그 값만 vs 나머지)"), flush=True)
        out = {}
        for k in ks:
            if k not in g or len(g[k]) < 150: continue
            sub = g[k]; big = sum(1 for _e, v in sub if v >= thr)
            av = [v for _e, v in sub]; ak = [e["entry_date"] for e, _v in sub]
            rest = [(e, v) for kk in g if kk != k for e, v in g[kk]]
            bv = [v for _e, v in rest]; bk = [e["entry_date"] for e, _v in rest]
            lo, hi = boot_diff(av, ak, bv, bk)
            ok = (lo > 0) or (hi < 0)
            print("  %-22s %7d %8.2f%% %+11.4f%%   %+7.4f%%p [%+6.3f ~%+6.3f] **%s**"
                  % (str(k)[:20], len(sub), 100.0 * big / len(sub), st.mean(av),
                     st.mean(av) - st.mean(bv), lo, hi, "0 배제" if ok else "0 포함"), flush=True)
            out[str(k)] = {"n": len(sub), "big_pct": 100.0 * big / len(sub),
                           "pt": st.mean(av), "diff": st.mean(av) - st.mean(bv),
                           "lo": lo, "hi": hi, "excl0": ok}
        n_ok = sum(1 for v in out.values() if v["excl0"])
        print("  → 칸 %d개 중 **0 배제 %d개**" % (len(out), n_ok), flush=True)
        return out

    RES = {}
    RES["pattern"] = axis("A-1. 패턴", lambda f: f["pattern"])
    RES["rs"] = axis("A-2. 6개월 수익률 순위(업종 내)",
                     lambda f: None if f["rs"] is None else
                     ("0~10%" if f["rs"] < .1 else "10~30%" if f["rs"] < .3 else
                      "30~60%" if f["rs"] < .6 else "60~100%"),
                     order=["0~10%", "10~30%", "30~60%", "60~100%"])
    RES["atr"] = axis("A-3. 진입 시점 변동성(atr_band)", lambda f: f["atr"],
                      order=["①조용 <2.5%", "②보통 2.5~4%", "③큼 4~6%", "④매우큼 6%+"])
    RES["sector"] = axis("A-4. 섹터", lambda f: f["sector"])

    # ── ★ 사용자 가설의 «곧은» 검정 — 1등급 vs 2·3등급을 «직접» 견준다 ─────
    print(chr(10) + "=" * 92, flush=True)
    print("★ 사용자 가설 — 「1등 말고 2·3등」을 **직접** 견준다", flush=True)
    print("=" * 92, flush=True)
    g1 = [(e, v) for e, v in pairs if F[id(e)]["rs"] is not None and F[id(e)]["rs"] < .10]
    g2 = [(e, v) for e, v in pairs if F[id(e)]["rs"] is not None and .10 <= F[id(e)]["rs"] < .30]
    a = [v for _e, v in g1]; b = [v for _e, v in g2]
    lo, hi = boot_diff(b, [e["entry_date"] for e, _v in g2],
                       a, [e["entry_date"] for e, _v in g1])
    print("  1등급(상위 0~10%%)  n=%5d  거래당 %+.4f%%  ·  큰승자 %.2f%%"
          % (len(g1), st.mean(a), 100.0 * sum(1 for _e, v in g1 if v >= thr) / len(g1)),
          flush=True)
    print("  2·3등급(10~30%%)    n=%5d  거래당 %+.4f%%  ·  큰승자 %.2f%%"
          % (len(g2), st.mean(b), 100.0 * sum(1 for _e, v in g2 if v >= thr) / len(g2)),
          flush=True)
    ok = (lo > 0) or (hi < 0)
    print("  → **2·3등급 − 1등급 = %+.4f%%p** [95%% %+.4f ~ %+.4f] → **%s**"
          % (st.mean(b) - st.mean(a), lo, hi, "0 배제 — 가설 지지" if ok else "0 포함 — 못 가림"),
          flush=True)
    RES["hypothesis"] = {"g1_n": len(g1), "g1_pt": st.mean(a), "g2_n": len(g2),
                         "g2_pt": st.mean(b), "diff": st.mean(b) - st.mean(a),
                         "lo": lo, "hi": hi, "excl0": ok}
    if ok:
        print(chr(10) + "  연도 검정 — 한 해를 빼면:", flush=True)
        bad = []
        base = st.mean(b) - st.mean(a)
        for y in sorted({e["entry_date"][:4] for e, _v in pairs}):
            aa = [v for e, v in g1 if e["entry_date"][:4] != y]
            bb = [v for e, v in g2 if e["entry_date"][:4] != y]
            d = st.mean(bb) - st.mean(aa)
            f = "🚨 부호 반전" if (d < 0) != (base < 0) else ""
            print("    %s 제외 → %+.4f%%p %s" % (y, d, f), flush=True)
            if f: bad.append(y)
        print("    → **%s**" % ("부호 반전 없음 (10/10)" if not bad else "🚨 " + ",".join(bad)),
              flush=True)
        RES["hypothesis"]["year_flip"] = bad

    # ── B. MFE ──────────────────────────────────────────────────────────
    print("\n" + "=" * 92); print("B. **청산에서 얼마를 남기고 나오나** (MFE)"); print("=" * 92, flush=True)
    for vn, fn, lab, _h in r41.VARIANTS:
        if vn not in ("0회차", "1a", "1c"): continue
        ev, _b = r41.replay(by, fn)
        with r41.Cost(*COST): v = r41.per_trade(ev)
        mfe, real, ratio = [], [], []
        for e, rv in zip(ev, v):
            p = pmap.get((e["scan_date"], e["code"], e["pattern"]))
            if not p: continue
            ep = p["entry_price"]
            last = e["legs"][-1][0]
            try: j = p["d"].index(last)
            except ValueError: j = len(p["h"]) - 1
            mx = max(p["h"][:j + 1]) if j >= 0 else ep
            m = (mx / ep - 1) * 100
            mfe.append(m); real.append(rv)
            if m > 1: ratio.append(rv / m)
        big = [(m, r) for m, r in zip(mfe, real) if r >= thr]
        print("\n  [%s]" % lab[:34], flush=True)
        print("    전체 %d건 — 최고 미실현 중앙 **%+.2f%%** · 실현 중앙 %+.2f%% · "
              "실현/최고 중앙 **%.0f%%**"
              % (len(mfe), st.median(mfe), st.median(real), 100 * st.median(ratio)), flush=True)
        if big:
            print("    큰 승자 %d건 — 최고 미실현 중앙 **%+.1f%%** · 실현 중앙 %+.1f%% "
                  "→ **%.0f%% 를 챙긴다**"
                  % (len(big), st.median(m for m, _r in big), st.median(r for _m, r in big),
                     100 * st.median(r / m for m, r in big if m > 1)), flush=True)
    json.dump(RES, open(OUT / "65-winner-traits.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("\n저장: 65-winner-traits.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
