# -*- coding: utf-8 -*-
"""85 — **진입 시점에 «가를 수 있나»**. 사전등록 `tasks/85-entry-predictors.md` (`9cdd6637`)

🚨 62번이 죽은 자리와 «같은 함정»이다 — 20칸을 뒤진다.
🚨 **주판정은 효과 크기가 아니라 «귀무 대조»**(라벨 섞기 300회)다.
🚨 특징을 나중에 «추가하지 않는다». 분위 경계는 표본 «안»에서만 정한다.

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/85-entry-predictors.py [--quick]
"""
from __future__ import annotations

import bisect
import importlib.util as _u
import json
import math
import random
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

_s = _u.spec_from_file_location("r84", HERE / "84-case-studies.py")
r84 = _u.module_from_spec(_s)
_s.loader.exec_module(r84)
r83, r74, r41, r61, r61b = r84.r83, r84.r74, r84.r41, r84.r83.r61, r84.r83.r61b

OUT = ROOT / ".cache" / "bt5y" / "out"
SPLIT = "2022-01-01"          # 표본 안 < SPLIT ≤ 표본 밖
NQ = 5                        # 5분위
N_NULL = 300
FEATS = ("pattern", "atr_band", "gap", "prior6m", "hi52",
         "base_depth", "ma200", "atr20", "in_pct", "logpx")
CAT = ("pattern", "atr_band")      # 범주형 — 분위 대신 «값»으로 가른다


# ═════════════════════════════════════════════════════════════════════════
# 1. 진입 «전날»까지의 특징
# ═════════════════════════════════════════════════════════════════════════
def build_features(ev, pmap):
    import us_loader
    codes = sorted({t["code"] for t in ev})
    lo = "2016-06-01"
    hi = max(t["entry_date"] for t in ev)
    print("   시세 적재 — 종목 %d개 · %s ~ %s" % (len(codes), lo, hi), flush=True)
    need = {}
    for t in ev:
        need.setdefault(t["code"], []).append(t)

    pack = json.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    sector = pack["sector"]
    monthly = pack["monthly"]
    months = sorted({m for d in monthly.values() for m in d if m >= "2016-12"})
    _sec_top, in_pct = r61b.make_flags(r61b.month_returns(monthly, sector, months), sector)

    rows, miss = {}, Counter()
    BATCH = 500
    for bi in range(0, len(codes), BATCH):
        chunk = set(codes[bi:bi + BATCH])
        ser = {c: [] for c in chunk}
        for tk, d, o, h, l, c, _v, _cu in us_loader._iter_prices(chunk, lo, hi):
            try:
                ser[tk].append((d, float(o), float(h), float(l), float(c)))
            except (TypeError, ValueError):
                continue
        for code in chunk:
            s = sorted(ser[code])
            if not s:
                miss["시계열 없음"] += len(need.get(code, []))
                continue
            dd = [x[0] for x in s]
            for t in need.get(code, []):
                # 🚨 관문 ① — 진입일 «전날»까지만 본다
                k = bisect.bisect_left(dd, t["entry_date"])
                if k < 210:                       # 200일선 + 여유
                    miss["과거 봉 부족"] += 1
                    continue
                pre = s[:k]                       # ← 진입일 «미포함»
                cl = [x[4] for x in pre]
                hh = [x[2] for x in pre]
                ll = [x[3] for x in pre]
                e = t["entry_px"]
                p = pmap[(t["scan_date"], t["code"], t["pattern"])]
                w52 = max(hh[-252:]) if len(hh) >= 252 else max(hh)
                b60h, b60l = max(hh[-60:]), min(ll[-60:])
                tr = [max(hh[i] - ll[i], abs(hh[i] - cl[i - 1]), abs(ll[i] - cl[i - 1]))
                      for i in range(len(cl) - 20, len(cl))]
                ym = r61.prev_ym(t["scan_date"][:7], 1)
                rows[(t["scan_date"], t["code"], t["pattern"])] = {
                    "pattern": t.get("pattern", p["pattern"]),
                    "atr_band": p.get("atr_band", "?"),
                    "gap": e / p["pivot"] - 1 if p.get("pivot") else 0.0,
                    "prior6m": e / cl[-126] - 1,
                    "hi52": e / w52,
                    "base_depth": (b60h - b60l) / b60h if b60h else 0.0,
                    "ma200": e / (sum(cl[-200:]) / 200) - 1,
                    "atr20": (sum(tr) / 20) / e,
                    "in_pct": in_pct.get(ym, {}).get(code, float("nan")),
                    "logpx": math.log(max(e, 1e-6)),
                }
        del ser
    print("   특징 만든 거래 **%d / %d** · 결측 %s" % (len(rows), len(ev), dict(miss)),
          flush=True)
    return rows, miss


# ═════════════════════════════════════════════════════════════════════════
# 2. 한 특징 · 한 결과 — 표본 «안»에서 고르고 «밖»에서 잰다
# ═════════════════════════════════════════════════════════════════════════
def test_one(ins, outs, feat, lab):
    """반환: (표본밖 상위분위 비율, 기준율, 방향, n_out, 설명)"""
    if feat in CAT:
        vals = sorted({r[feat] for r, _y in ins})
        grp_in = {v: [y for r, y in ins if r[feat] == v] for v in vals}
        grp_in = {v: g for v, g in grp_in.items() if len(g) >= 30}
        if not grp_in:
            return None
        best = max(grp_in, key=lambda v: st.mean(grp_in[v]))
        sel = [y for r, y in outs if r[feat] == best]
        if len(sel) < 30:
            return None
        base = st.mean([y for _r, y in outs])
        return (st.mean(sel), base, best, len(sel), "값 = %s" % best)
    xs = sorted(r[feat] for r, _y in ins if not _nan(r[feat]))
    if len(xs) < NQ * 20:
        return None
    cuts = [xs[int(len(xs) * i / NQ)] for i in range(1, NQ)]      # 표본 «안»에서만
    def q(v):
        return bisect.bisect_right(cuts, v)
    qi = {i: [y for r, y in ins if not _nan(r[feat]) and q(r[feat]) == i] for i in range(NQ)}
    qi = {i: g for i, g in qi.items() if len(g) >= 30}
    if len(qi) < 2:
        return None
    best = max(qi, key=lambda i: st.mean(qi[i]))
    worst = min(qi, key=lambda i: st.mean(qi[i]))
    sel = [y for r, y in outs if not _nan(r[feat]) and q(r[feat]) == best]
    if len(sel) < 30:
        return None
    base = st.mean([y for _r, y in outs])
    return (st.mean(sel), base, "%d분위" % (best + 1), len(sel),
            "표본안 최고 %d분위(%.3f) vs 최저 %d분위(%.3f)"
            % (best + 1, st.mean(qi[best]), worst + 1, st.mean(qi[worst])))


def _nan(v):
    return isinstance(v, float) and v != v


# ═════════════════════════════════════════════════════════════════════════
def run_outcome(rows, ev, ykey, name, base_thresh, n_null, quiet=False):
    ins, outs = [], []
    for t in ev:
        k = (t["scan_date"], t["code"], t["pattern"])
        if k not in rows:
            continue
        y = ykey(t)
        (ins if t["entry_date"] < SPLIT else outs).append((rows[k], y))
    b_in = st.mean([y for _r, y in ins])
    b_out = st.mean([y for _r, y in outs])
    print("\n" + "─" * 98, flush=True)
    print("▶ **%s** — 표본안 %d건(기준율 %.2f%%) · 표본밖 %d건(기준율 **%.2f%%**)"
          % (name, len(ins), b_in * 100, len(outs), b_out * 100), flush=True)
    print("   %-11s %10s %11s %11s %s" % ("특징", "표본밖 n", "상위분위", "기준율차", "고른 것"),
          flush=True)
    print("   " + "-" * 84, flush=True)
    res = {}
    for f in FEATS:
        r = test_one(ins, outs, f, name)
        if r is None:
            print("   %-11s (분위·표본 부족 → 건너뜀)" % f, flush=True)
            continue
        rate, base, pick, n, why = r
        res[f] = rate - base
        print("   %-11s %10d %10.2f%% %+10.2f%%p %s (%s)"
              % (f, n, rate * 100, (rate - base) * 100, pick, why), flush=True)
    if not res:
        return None
    bf = max(res, key=lambda f: res[f])
    obs = res[bf]
    print("\n   **관측 최선 = `%s`  %+.2f%%p** (문턱 %+.2f%%p)"
          % (bf, obs * 100, base_thresh * 100), flush=True)

    # ── N★ 귀무 대조 — «같은 절차»를 라벨 섞어서 ────────────────────────
    rnd = random.Random(85085085)
    ys_in = [y for _r, y in ins]
    ys_out = [y for _r, y in outs]
    null = []
    for it in range(n_null):
        zi = ys_in[:]
        zo = ys_out[:]
        rnd.shuffle(zi)
        rnd.shuffle(zo)
        i2 = [(r, z) for (r, _y), z in zip(ins, zi)]
        o2 = [(r, z) for (r, _y), z in zip(outs, zo)]
        bb = st.mean(zo)
        best = -9.0
        for f in FEATS:                      # ★ 같은 20칸을 «똑같이» 돈다
            rr = test_one(i2, o2, f, name)
            if rr:
                best = max(best, rr[0] - bb)
        null.append(best)
        if not quiet and it % 60 == 0:
            print("     귀무 %d/%d" % (it, n_null), flush=True)
    a = sorted(null)
    pct = 100.0 * sum(1 for x in a if x < obs) / len(a)
    print("   **N★ 귀무 대조 %d회** — 「%d칸 중 최선」이 우연으로: "
          "보통 %+.2f%%p · 95%% %+.2f%%p · 최대 %+.2f%%p"
          % (n_null, len(FEATS), a[len(a) // 2] * 100, a[int(len(a) * .95)] * 100,
             a[-1] * 100), flush=True)
    okN = pct >= 95.0
    okA = obs > base_thresh
    print("   → 관측 %+.2f%%p = **%.1f 백분위** · **N %s** · **A %s**"
          % (obs * 100, pct, "✅ 통과" if okN else "❌ 미통과",
             "✅ 통과" if okA else "❌ 미통과"), flush=True)
    return {"best": bf, "obs": obs, "pct": pct, "okN": okN, "okA": okA,
            "base_in": b_in, "base_out": b_out, "n_in": len(ins), "n_out": len(outs),
            "all": res, "null_max": a[-1], "null_med": a[len(a) // 2]}


def mde(n, p, lift):
    """기준율 p 인 이항에서 «lift 배» 를 5% 수준으로 가르려면 표본이 몇 배 필요한가."""
    if p <= 0 or p >= 1:
        return float("inf")
    d = p * (lift - 1.0)
    se = math.sqrt(p * (1 - p) / max(1, n))
    return (1.96 * se / d) ** 2 if d > 0 else float("inf")


def main() -> int:
    quick = "--quick" in sys.argv
    n_null = 30 if quick else N_NULL
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    print("=" * 98, flush=True)
    print("85 — 진입 시점에 «가를 수 있나» (사전등록 tasks/85 · 9cdd6637)", flush=True)
    print("=" * 98, flush=True)
    by2, ev, blk, pmap = r84.load()
    print("진입 %d건 · 표본안/밖 경계 **%s**" % (len(ev), SPLIT), flush=True)

    rows, miss = build_features(ev, pmap)

    # 결과 정의
    def mfe(t):
        p = pmap[(t["scan_date"], t["code"], t["pattern"])]
        i0 = p["d"].index(t["entry_date"])
        i1 = p["d"].index(t["masks"][()]["exits"][-1][0])
        return (max(p["h"][i0:i1 + 1]) / t["entry_px"] - 1) * 100

    m = {(t["scan_date"], t["code"], t["pattern"]): mfe(t) for t in ev}
    y20 = lambda t: 1.0 if m[(t["scan_date"], t["code"], t["pattern"])] >= 20 else 0.0
    y100 = lambda t: 1.0 if m[(t["scan_date"], t["code"], t["pattern"])] >= 100 else 0.0
    n20 = sum(y20(t) for t in ev)
    n100 = sum(y100(t) for t in ev)
    print("\n결과 정의 — ㉮ MFE≥+20%%: **%d건 (%.2f%%)**  ·  ㉯ MFE≥+100%%: **%d건 (%.2f%%)**"
          % (n20, 100 * n20 / len(ev), n100, 100 * n100 / len(ev)), flush=True)

    # 🚨 C — 답할 수 있는 물음인가 «먼저»
    n_out = sum(1 for t in ev if t["entry_date"] >= SPLIT
                and (t["scan_date"], t["code"], t["pattern"]) in rows)
    print("\n🚨 **C 판정 «먼저»** — 표본밖 %d건 · 상위 분위 ≈ %d건" % (n_out, n_out // NQ),
          flush=True)
    for nm, p0, lift in (("㉮ MFE≥20%", n20 / len(ev), 1.18), ("㉯ MFE≥100%", n100 / len(ev), 1.5)):
        need = mde(n_out // NQ, p0, lift)
        print("   %-12s 기준율 %.2f%% · %.2f배를 가르려면 **자료 %.1f배 = %.0f년** 필요"
              % (nm, p0 * 100, lift, need, need * 8.956), flush=True)

    R = {}
    R["A"] = run_outcome(rows, ev, y20, "㉮ 「+20% 에 닿는가」", 0.05, n_null)
    R["B"] = run_outcome(rows, ev, y100, "㉯ 「더블(+100%) 하는가」",
                         0.5 * n100 / len(ev), n_null)

    print("\n" + "=" * 98, flush=True)
    print("사전등록 §4 판정", flush=True)
    for k, nm in (("A", "㉮ +20% 도달"), ("B", "㉯ 더블")):
        v = R.get(k)
        if not v:
            print("  %s — 산출 실패" % nm)
            continue
        print("  %-14s N★ %s · A★ %s   (최선 `%s` %+.2f%%p · 귀무 %.1f 백분위)"
              % (nm, "✅" if v["okN"] else "❌", "✅" if v["okA"] else "❌",
                 v["best"], v["obs"] * 100, v["pct"]), flush=True)
    print("\n🚨 어느 쪽이든 «최고의 예측 변수는 X» 라고 쓰지 않는다. 쓸 수 있는 건 방향뿐이다.",
          flush=True)

    (OUT / "85-entry-predictors.json").write_text(json.dumps(
        {"split": SPLIT, "n_ev": len(ev), "n_feat": len(rows), "miss": dict(miss),
         "n20": n20, "n100": n100, "res": R, "n_null": n_null},
        ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: 85-entry-predictors.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
