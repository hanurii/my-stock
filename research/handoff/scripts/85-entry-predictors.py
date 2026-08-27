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
BONF = 2                           # 검정 둘(㉮㉯) → 본페로니 → 97.5 백분위
NL = chr(10)
# 🚨 옛 문턱 210 은 «구조적으로 못 타는» 관문이었다(진입 전 봉 수 최소 253).
#    「0건」이 «검사 결과»가 아니라 «검사가 없었다»는 뜻이었다(유형 24).
#    검증 세션 지적(0e95711a): 가짜 통과가 과제마다 쌓이므로 «지금» 고친다.
#    300 이면 41건이 실제로 걸려 관문이 «돈다».
MIN_PRE = 300
KSTAT = []


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
    KSTAT.clear()
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
                KSTAT.append(k)
                if k < MIN_PRE:                   # 200일선 + 여유
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
    # 🚨 관문 ①′ — 「결측 0건」이 맞나 «와» 그 관문이 «탈 수 있나»는 다른 물음이다(유형 24).
    #    가격을 2016-06 부터 싣고 첫 진입이 2017-09 이라, 2016년 중반 «뒤» 상장이 아니면
    #    k<210 은 «구조적으로» 불가능하다. 그래서 min(k) 를 찍어 확인한다.
    if KSTAT:
        ks = sorted(KSTAT)
        print("   관문 ①′ 진입 전 봉 수 — **최소 %d** · P1 %d · 중앙 %d · "
              "**k<210 %d건 · k<300 %d건** → %s"
              % (ks[0], ks[len(ks) // 100], ks[len(ks) // 2],
                 sum(1 for x in ks if x < 210), sum(1 for x in ks if x < 300),
                 "관문이 «탈 수 있는» 자리에 있다" if ks[0] < MIN_PRE
                 else ("🚨 최소 k=%d > 문턱 %d → **이 관문은 «구조적으로 못 탄다». "
                       "「0건」은 «검사 결과»가 아니라 «검사가 없었다»는 뜻이다** "
                       "(유형 24)."
                       % (ks[0], MIN_PRE))),
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
        base = st.mean([y for r, y in outs if not _nan(r[feat])])
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
    # 🚨 기준율도 «같은 모집단»(non-NaN)에서 낸다 — 안 그러면 차이가 부풀 수 있다.
    base = st.mean([y for r, y in outs if not _nan(r[feat])])
    return (st.mean(sel), base, "%d분위" % (best + 1), len(sel),
            "표본안 최고 %d분위(%.3f) vs 최저 %d분위(%.3f)"
            % (best + 1, st.mean(qi[best]), worst + 1, st.mean(qi[worst])))


def _nan(v):
    return isinstance(v, float) and v != v


# ═════════════════════════════════════════════════════════════════════════
# 빠른 귀무 경로 — 라벨만 바뀌므로 «분위 배정»을 미리 계산해 둔다.
# 🚨 반드시 `test_one`(느린 경로)과 «같은 답»을 내는지 관문으로 확인한 뒤에만 쓴다.
# ═════════════════════════════════════════════════════════════════════════
def precompute(ins, outs):
    """특징 → (표본안 그룹id, 표본밖 그룹id, 그룹 목록).  NaN 은 None."""
    pre = {}
    for f in FEATS:
        if f in CAT:
            gi = [r[f] for r, _y in ins]
            go = [r[f] for r, _y in outs]
            keys = sorted({v for v in gi})
        else:
            xs = sorted(r[f] for r, _y in ins if not _nan(r[f]))
            if len(xs) < NQ * 20:
                continue
            cuts = [xs[int(len(xs) * i / NQ)] for i in range(1, NQ)]
            gi = [None if _nan(r[f]) else bisect.bisect_right(cuts, r[f]) for r, _y in ins]
            go = [None if _nan(r[f]) else bisect.bisect_right(cuts, r[f]) for r, _y in outs]
            keys = list(range(NQ))
        pre[f] = (gi, go, keys)
    return pre


def test_fast(pre, f, ys_in, ys_out):
    """`test_one` 과 «같은» 계산 — 라벨만 바뀔 때 쓴다."""
    gi, go, keys = pre[f]
    tot_i, cnt_i = {}, {}
    for g, y in zip(gi, ys_in):
        if g is None:
            continue
        tot_i[g] = tot_i.get(g, 0.0) + y
        cnt_i[g] = cnt_i.get(g, 0) + 1
    cand = [k for k in keys if cnt_i.get(k, 0) >= 30]
    if f in CAT:
        if not cand:
            return None
    elif len(cand) < 2:
        return None
    best = max(cand, key=lambda k: tot_i[k] / cnt_i[k])
    ssum = scnt = 0.0
    bsum = bcnt = 0.0
    for g, y in zip(go, ys_out):
        if g is None:
            continue
        bsum += y
        bcnt += 1
        if g == best:
            ssum += y
            scnt += 1
    if scnt < 30:
        return None
    return ssum / scnt, bsum / bcnt


def gate_fast(pre, ins, outs, name):
    """관문 — 빠른 경로가 느린 경로와 «같은 답»을 내는가."""
    ys_in = [y for _r, y in ins]
    ys_out = [y for _r, y in outs]
    worst, seen = 0.0, 0
    for f in FEATS:
        a = test_one(ins, outs, f, name)
        b = test_fast(pre, f, ys_in, ys_out) if f in pre else None
        if a is None and b is None:
            continue
        if (a is None) != (b is None):
            print("   🚨 관문 실패 — `%s` 에서 한쪽만 None (느림 %s · 빠름 %s)"
                  % (f, a is not None, b is not None), flush=True)
            return False
        worst = max(worst, abs(a[0] - b[0]), abs(a[1] - b[1]))
        seen += 1
    ok = worst < 1e-12
    print("   관문 ⑥ 빠른 귀무 경로 = 느린 경로  (%d칸 · 최대 차 %.2e) → **%s**"
          % (seen, worst, "통과" if ok else "🚨 미통과"), flush=True)
    return ok


def _shuf_year(ys, yrs, rnd, mode):
    """🚨 통째로 섞으면 «연도 구조»가 지워진다 — 표본밖 기준율이 2022 10.0% ~ 2024 34.8%
    (3.5배)로 흔들린다(검증 d2062269). 헤드라인은 «연도 안»에서만 섞는다."""
    if mode == "all":
        z = ys[:]
        rnd.shuffle(z)
        return z
    idx = {}
    for i, y in enumerate(yrs):
        idx.setdefault(y, []).append(i)
    z = ys[:]
    for _y, ii in idx.items():
        vv = [ys[i] for i in ii]
        rnd.shuffle(vv)
        for i, v in zip(ii, vv):
            z[i] = v
    return z


def profile(ins, outs, feat):
    """분위별 프로필 — «기울기»는 인용 금지지만 «보여는» 준다."""
    if feat in CAT:
        return None
    xs = sorted(r[feat] for r, _y in ins if not _nan(r[feat]))
    cuts = [xs[int(len(xs) * i / NQ)] for i in range(1, NQ)]
    def q(v):
        return bisect.bisect_right(cuts, v)
    a, b = [], []
    for i in range(NQ):
        gi = [y for r, y in ins if not _nan(r[feat]) and q(r[feat]) == i]
        go = [y for r, y in outs if not _nan(r[feat]) and q(r[feat]) == i]
        a.append(100 * st.mean(gi) if gi else float("nan"))
        b.append(100 * st.mean(go) if go else float("nan"))
    return a, b


def run_outcome(rows, ev, ykey, gmap, name, base_thresh, n_null, mode="year"):
    ins, outs, yr_in, yr_out, gi_, go_ = [], [], [], [], [], []
    for t in ev:
        k = (t["scan_date"], t["code"], t["pattern"])
        if k not in rows:
            continue
        y, yr, g = ykey(t), t["entry_date"][:4], gmap[k]
        if t["entry_date"] < SPLIT:
            ins.append((rows[k], y)); yr_in.append(yr); gi_.append(g)
        else:
            outs.append((rows[k], y)); yr_out.append(yr); go_.append(g)
    b_in = st.mean([y for _r, y in ins])
    b_out = st.mean([y for _r, y in outs])
    print(NL + "─" * 98, flush=True)
    print("▶ **%s** — 표본안 %d건(기준율 %.2f%%) · 표본밖 %d건(기준율 **%.2f%%**) · "
          "**사건 %d건**" % (name, len(ins), b_in * 100, len(outs), b_out * 100,
                            round(b_out * len(outs))), flush=True)
    print("   한 건이 **%.2f%%p** — 표에서 그보다 작은 차이는 «사건 한 건»이다."
          % (100.0 / len(outs)), flush=True)
    print("   %-11s %9s %10s %10s %11s %s"
          % ("특징", "표본밖n", "상위분위", "기준율차", "거래당평균", "고른 것"), flush=True)
    print("   " + "-" * 84, flush=True)
    res, meta = {}, {}
    for f in FEATS:
        r = test_one(ins, outs, f, name)
        if r is None:
            print("   %-11s (분위·표본 부족 → 건너뜀)" % f, flush=True)
            continue
        rate, base, pick, nn, why = r
        res[f] = rate - base
        # ★ 「돈」으로도 잰다 — 확률만 보면 «꼬리를 넓히는 칸»과 «버는 칸»을 못 가린다
        if f in CAT:
            sel_g = [g for (r0, _y), g in zip(outs, go_) if r0[f] == pick]
        else:
            xs = sorted(r0[f] for r0, _y in ins if not _nan(r0[f]))
            cuts = [xs[int(len(xs) * i / NQ)] for i in range(1, NQ)]
            qi = int(pick[0]) - 1
            sel_g = [g for (r0, _y), g in zip(outs, go_)
                     if not _nan(r0[f]) and bisect.bisect_right(cuts, r0[f]) == qi]
        meta[f] = (pick, st.mean(sel_g) if sel_g else float("nan"), nn)
        print("   %-11s %9d %9.2f%% %+9.2f%%p %+10.3f%% %s"
              % (f, nn, rate * 100, (rate - base) * 100, meta[f][1], pick), flush=True)
    if not res:
        return None
    print("   (표본밖 전체 거래당 평균 %+.3f%%)" % st.mean(go_), flush=True)
    bf = max(res, key=lambda f: res[f])
    obs = res[bf]
    print(NL + "   **관측 최선 = `%s`  %+.2f%%p** (등록 문턱 %+.2f%%p)"
          % (bf, obs * 100, base_thresh * 100), flush=True)
    pr = profile(ins, outs, bf)
    if pr:
        print("   분위 프로필 (1→5분위)  표본안 %s" % " → ".join("%.2f" % v for v in pr[0]),
              flush=True)
        print("                          표본밖 %s" % " → ".join("%.2f" % v for v in pr[1]),
              flush=True)
        print("   🚨 **표본밖이 «단조»가 아니다 → «방향»은 써도 «기울기»는 인용 금지**",
              flush=True)

    pre = precompute(ins, outs)
    if not gate_fast(pre, ins, outs, name):
        return None
    rnd = random.Random(85085085)
    ys_in = [y for _r, y in ins]
    ys_out = [y for _r, y in outs]
    null = []
    for it in range(n_null):
        zi = _shuf_year(ys_in, yr_in, rnd, mode)
        zo = _shuf_year(ys_out, yr_out, rnd, mode)
        best = -9.0
        for f in pre:
            rr = test_fast(pre, f, zi, zo)
            if rr:
                best = max(best, rr[0] - rr[1])
        null.append(best)
        if it % 1000 == 0:
            print("     귀무(%s) %d/%d" % (mode, it, n_null), flush=True)
    a = sorted(null)
    pct = 100.0 * sum(1 for x in a if x < obs) / len(a)
    thr = 100.0 * (1 - 0.05 / BONF)
    # 🚨 본페로니는 «97.5% 분위»를 요구하는데, 300판에서 그건 293번째 순서통계량이다.
    #    꼬리로 갈수록 표본 몇 개가 값을 정한다 → **판수가 모자라면 «문턱»이 흔들린다**
    #    (검증 세션 ec59b616). 백분위의 몬테카를로 95% 구간을 같이 찍는다.
    _p = pct / 100.0
    _se = 100.0 * math.sqrt(max(_p * (1 - _p), 1e-12) / len(a))
    print("   판수 %d · 백분위의 몬테카를로 95%% 구간 **[%.2f, %.2f]**"
          % (len(a), max(0.0, pct - 1.96 * _se), min(100.0, pct + 1.96 * _se)), flush=True)
    print("   **N★ 귀무 %d회 (섞기 = «%s»)** — 「%d칸 중 최선」이 우연으로: "
          "보통 %+.2f%%p · 95%% %+.2f%%p · **97.5%% %+.2f%%p** · 최대 %+.2f%%p"
          % (n_null, "연도 안" if mode == "year" else "통째로", len(FEATS),
             a[len(a) // 2] * 100, a[int(len(a) * .95)] * 100,
             a[int(len(a) * .975)] * 100, a[-1] * 100), flush=True)
    okN = pct >= thr
    okA = obs > base_thresh
    print("   → 관측 %+.2f%%p = **%.1f 백분위** · 본페로니 %d → 문턱 **%.1f** · "
          "**N %s** · **A %s**"
          % (obs * 100, pct, BONF, thr, "✅ 통과" if okN else "❌ 미통과",
             "✅ 통과" if okA else "❌ 미통과"), flush=True)
    return {"best": bf, "obs": obs, "pct": pct, "okN": okN, "okA": okA, "mode": mode,
            "base_in": b_in, "base_out": b_out, "n_in": len(ins), "n_out": len(outs),
            "all": res, "meta": {k: list(v) for k, v in meta.items()},
            "null_max": a[-1], "null_med": a[len(a) // 2],
            "null_p95": a[int(len(a) * .95)], "null_p975": a[int(len(a) * .975)],
            "profile": pr, "bonf_thr": thr}


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
    for _a in sys.argv:
        if _a.startswith("--null="):
            n_null = int(_a.split("=", 1)[1])
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

    gmap = {(t["scan_date"], t["code"], t["pattern"]): r84.gain_of(t) for t in ev}

    # ── ③ 🚨 1등과 2등이 «한 발견»인지 본다 ─────────────────────────────
    outk = [(t["scan_date"], t["code"], t["pattern"]) for t in ev
            if t["entry_date"] >= SPLIT and (t["scan_date"], t["code"], t["pattern"]) in rows]
    ins_v = sorted(rows[k]["atr20"] for t in ev
                   for k in [(t["scan_date"], t["code"], t["pattern"])]
                   if t["entry_date"] < SPLIT and k in rows)
    c5 = ins_v[int(len(ins_v) * 4 / 5)]
    A = {k for k in outk if rows[k]["atr_band"].startswith("④")}
    B = {k for k in outk if rows[k]["atr20"] >= c5}
    if A and B:
        print(NL + "🚨 **`atr_band ④` 와 `atr20 5분위` 가 «같은 발견»인가** — "
              "A %d건 · B %d건 · A∩B %d건 → **A 의 %.1f%% 가 B 안에 있다** (자카드 %.1f%%)"
              % (len(A), len(B), len(A & B), 100.0 * len(A & B) / len(A),
                 100.0 * len(A & B) / len(A | B)), flush=True)
        print("   → 1등과 2등을 «두 근거»로 세면 안 된다. 한 축이다.", flush=True)

    R = {}
    R["A"] = run_outcome(rows, ev, y20, gmap, "㉮ 「+20% 에 닿는가」", 0.05, n_null)
    R["B"] = run_outcome(rows, ev, y100, gmap, "㉯ 「더블(+100%) 하는가」",
                         0.5 * n100 / len(ev), n_null)

    # ── ⑧ 등록했던 «대칭 검정»은 이 하네스에서 답을 못 낸다 ─────────────
    mae = {}
    for t in ev:
        k = (t["scan_date"], t["code"], t["pattern"])
        p = pmap[k]
        i0 = p["d"].index(t["entry_date"])
        i1 = p["d"].index(t["masks"][()]["exits"][-1][0])
        mae[k] = (min(p["l"][i0:i1 + 1]) / t["entry_px"] - 1) * 100
    hi_ = [k for k in outk if rows[k]["atr_band"].startswith("④")]
    r_mfe = (st.mean([1.0 if m[k] >= 100 else 0.0 for k in hi_])
             / max(1e-9, st.mean([1.0 if m[k] >= 100 else 0.0 for k in outk])))
    r_mae = (st.mean([1.0 if mae[k] <= -15 else 0.0 for k in hi_])
             / max(1e-9, st.mean([1.0 if mae[k] <= -15 else 0.0 for k in outk])))
    print(NL + "🚨 **등록했던 «대칭 검정»(하방도 예측하나)은 이 하네스에서 «답을 못 낸다»**",
          flush=True)
    print("   `atr_band ④` 의 배수 — 위쪽 MFE≥+100%% **%.2f배** vs 아래쪽 MAE≤−15%% %.2f배"
          % (r_mfe, r_mae), flush=True)
    print("   → 「비대칭 엣지」로 읽으면 «틀린다». **손절 −8%% 가 아래쪽을 «검열»한다** — "
          "아래로 갈 여지가 애초에 잘려 있다(검증 d2062269).", flush=True)

    print("\n" + "=" * 98, flush=True)
    print("사전등록 §4 판정", flush=True)
    print("🚨 **사전등록 §4 는 「20칸 중 최선」이라 적혀 있는데 코드는 «결과별 10칸»을 돈다.**",
          flush=True)
    print("   검증 세션이 20칸 한 가족으로 다시 돌린 결과 — **자를 바꾸면 답이 «정확히» 뒤집힌다**",
          flush=True)
    print("     %p 로 묶으면 ㉯ 가 죽고(82.0/69.7 백분위) · 배수로 묶으면 ㉮ 가 죽는다(16.0/15.7)",
          flush=True)
    print("     기준율이 25.59%% vs 1.76%% 로 15배 달라 **어느 자도 중립이 아니다(유형 3)**.",
          flush=True)
    print("   → **정본 읽기 = 「결과별 10칸 + 본페로니 %d」.** 이건 «사전등록에 없는 읽기»이고,"
          % BONF, flush=True)
    print("     그렇게 «벗어나야만» 자에 안 휘둘린다. 이탈을 숨기지 않고 적는다.", flush=True)
    for k, nm in (("A", "㉮ +20% 도달"), ("B", "㉯ 더블")):
        v = R.get(k)
        if not v:
            print("  %s — 산출 실패" % nm)
            continue
        print("  %-14s N★ %s · A★ %s   (최선 `%s` %+.2f%%p · 귀무 %.1f 백분위 / 문턱 %.1f)"
              % (nm, "✅" if v["okN"] else "❌", "✅" if v["okA"] else "❌",
                 v["best"], v["obs"] * 100, v["pct"], v["bonf_thr"]), flush=True)
    va, vb = R.get("A"), R.get("B")
    if va and vb:
        print(NL + "★ **확률과 돈은 다른 축이다** — ㉯ 승자 `%s` 는 더블 확률을 크게 올리지만"
              % vb["best"], flush=True)
        print("   거래당 %+.3f%% 로, 더블을 노린 게 «아닌» ㉮ 승자 `%s`(%+.3f%%)보다 «못 번다»."
              % (vb["meta"][vb["best"]][1], va["best"], va["meta"][va["best"]][1]), flush=True)
        print("   → **㉯ 의 승자는 «꼬리를 넓히는» 칸이지 «기대값을 올리는» 칸이 아니다.**",
              flush=True)
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
