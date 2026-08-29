# -*- coding: utf-8 -*-
"""108 — **지수 숏을 얹으면 달라지는가** (사전등록 `tasks/108`, 커밋 086085ad · ①번)

🚨 **이름부터**: 이건 「원전 기반 공매도」가 «아니다».
   진입 «규칙»과 «크기»가 본인 말에 «둘 다 없어» 우리가 채웠다.
   → **「원전 + 우리가 채운 두 칸」**이다.

# 규칙 (사전등록 그대로)
```
진입   SPY 종가가 200일선 «아래»인 날 숏을 든다      🚨 우리가 정함(97 에서 쓴 축)
청산   200일선 «위»로 올라오면 덮는다                🚨 우리가 정함
손절   SPY 가 «최근 1년 신고가»를 새로 쓰면 덮는다    ← 그의 문장에 가장 가까운 것
크기   계좌의 10 / 20 / 30%                        🚨 우리가 정함
비용   차입 연 0% / 2%  **둘 다** 찍는다            🚨 실제 값을 모른다
짝     같은 «날 수»만큼 무작위 날에 숏 (크기·비용 동일)
```
🚨 **롱과 «동시»로 든다**(원전에 "a hedge with near zero risk"). 롱을 비우지 않는다.

# 구조 — 롱 시뮬은 «한 번»만 돌리고 숏을 덧씌운다
```
하루 계좌 수익 = (롱 수익) + 크기 × (−SPY 수익) − 크기 × 차입일할
→ 롱 200판 곡선을 구간마다 «한 번» 만들고, 12칸(크기3 × 비용2 × 진짜/동전)을 그 위에 얹는다
```
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r91", HERE / "91-us-out-of-sample.py")
r91 = _u.module_from_spec(_s)
_s.loader.exec_module(r91)

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
BLOCKS = (("닷컴 1999~2001", "1999-04-01", "2001-12-31"),
          ("2002~2017", "2002-01-01", "2017-08-31"),
          ("2018~2026", "2017-09-01", "2026-08-21"))
YRS = {"닷컴 1999~2001": 2.75, "2002~2017": 15.66, "2018~2026": 8.96}
SPYC = {"닷컴 1999~2001": -3.29, "2002~2017": 7.04, "2018~2026": 15.27}
SIZES = (0.0, 0.10, 0.20, 0.30)
BORROW = (0.0, 2.0)
A_PASS = 55.0


def spy_series():
    """SPY 총수익 종가 · 200일선 «그날까지» · 1년 신고가 «그날까지» (관문 ㉙)."""
    d = json.loads((r91.OUT / "101-fund-ohlc.json").read_text(encoding="utf-8"))
    ser = d["SPY"]["series"]
    ds = sorted(ser)
    c = [ser[x][3] for x in ds]
    ma, hi = [], []
    for i in range(len(ds)):
        w = c[max(0, i - 199):i + 1]
        ma.append(sum(w) / len(w) if i >= 199 else None)
        w2 = c[max(0, i - 251):i + 1]
        hi.append(max(w2))
    return ds, c, ma, hi


def short_days(ds, c, ma, hi):
    """숏을 «들고 있는» 날 표. 🚨 그날 종가를 보고 «다음 날»부터 든다(당일 체결 금지)."""
    on, held = {}, False
    for i, d in enumerate(ds):
        on[d] = held                                   # 오늘 «들고 있었나»
        if ma[i] is None:
            held = False
            continue
        if held:
            # 청산: 200일선 위로 · 손절: 1년 신고가 갱신
            if c[i] > ma[i] or c[i] >= hi[i]:
                held = False
        else:
            if c[i] < ma[i]:
                held = True
    return on


def overlay(curve, settle_pct, ds_idx, spy_ret, on, size, borrow, a, b):
    """롱 곡선 위에 숏을 얹는다. 구간 [a,b] 만."""
    vals = [(x[0], x[1]) for x in curve] + [(curve[-1][0], 1.0 + settle_pct / 100.0)]
    seq = [(d, v) for d, v in vals if a <= d <= b]
    if len(seq) < 3:
        return None
    bo = borrow / 100.0 / 252.0 * size
    v, peak, mdd = 1.0, 1.0, 0.0
    for i in range(1, len(seq)):
        if seq[i - 1][1] <= 0:
            break
        rl = seq[i][1] / seq[i - 1][1] - 1.0
        d = seq[i][0]
        rs = 0.0
        if on.get(d) and d in spy_ret:
            rs = -size * spy_ret[d] - bo
        v *= (1.0 + rl + rs)
        if v <= 0:
            v = 1e-9
            break
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1.0)
    return v, mdd


def main() -> int:
    quick = "--quick" in sys.argv
    n_seed = 12 if quick else r91.N_SEED
    print("=" * 112, flush=True)
    print("108 — 지수 숏을 얹으면 달라지는가 · 운의 번호 %d판" % n_seed, flush=True)
    print("=" * 112, flush=True)
    print("🚨 **「원전 기반 공매도」가 «아니다».** 진입 규칙과 크기가 본인 말에 «둘 다 없어»", flush=True)
    print("   우리가 채웠다 → **「원전 + 우리가 채운 두 칸」**\n", flush=True)

    ds, c, ma, hi = spy_series()
    on = short_days(ds, c, ma, hi)
    spy_ret = {ds[i]: c[i] / c[i - 1] - 1.0 for i in range(1, len(ds))}

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음 %s" % missing, flush=True)
        return 2
    ev, _x, _y = r91.replay(by2)
    print("롱 매수 %s · 롱 시뮬 %d판을 «한 번»만 돌린다\n"
          % ("{:,}".format(len(ev)), n_seed), flush=True)
    rs = r91.sim(ev, n_seed)

    # 짝 — 같은 «날 수»만큼 무작위 날
    rnd = random.Random(20260830)
    for lab, a, b in BLOCKS:
        dd = [d for d in ds if a <= d <= b]
        n_on = sum(1 for d in dd if on.get(d))
        print("  %-16s 전체 %s일 · 숏 «든 날» %s일 (%.1f%%)"
              % (lab, "{:,}".format(len(dd)), "{:,}".format(n_on), 100.0 * n_on / len(dd)),
              flush=True)
    fake_on = {}
    for lab, a, b in BLOCKS:
        dd = [d for d in ds if a <= d <= b]
        n_on = sum(1 for d in dd if on.get(d))
        pick = set(rnd.sample(dd, n_on))
        for d in dd:
            fake_on[d] = d in pick

    print("\n  %-6s %-8s %-6s  %s"
          % ("크기", "차입", "진짜/동전", "구간별 [연평균 · 지수대비 · 최대낙폭]"), flush=True)
    print("  " + "-" * 100, flush=True)
    res = {}
    base = {}
    for size in SIZES:
        for bw in (BORROW if size > 0 else (0.0,)):
            for tag, omap in (("진짜", on), ("동전", fake_on)):
                if size == 0 and tag == "동전":
                    continue
                cells, key = [], "%d%%·차입%d%%·%s" % (int(size * 100), int(bw), tag)
                res[key] = {}
                for lab, a, b in BLOCKS:
                    out = [overlay(x["curve"], x["equity_pct"], None, spy_ret, omap,
                                   size, bw, a, b) for x in rs]
                    out = [o for o in out if o]
                    tot = sorted(o[0] for o in out)
                    med = tot[len(tot) // 2]
                    cg = (med ** (1 / YRS[lab]) - 1) * 100
                    md = st.median(o[1] for o in out) * 100
                    if size == 0:
                        base[lab] = [o[0] for o in out]
                    res[key][lab] = {"cagr": cg, "mdd": md, "beat": cg > SPYC[lab],
                                     "eq": [o[0] for o in out]}
                    cells.append("%s %+6.2f%%%s %6.1f%%"
                                 % (lab.split()[0], cg, "✅" if cg > SPYC[lab] else "❌", md))
                print("  %-6s %-8s %-6s  %s"
                      % ("%d%%" % int(size * 100), "%d%%" % int(bw), tag, "  ".join(cells)),
                      flush=True)

    # ── 관문 ㉘ 크기 0% 가 91 정본과 같은가 ──────────────────────────
    z = res["0%·차입0%·진짜"]
    ok = True
    for lab, a, b in BLOCKS:
        e = [t for t in ev if a <= t["entry_date"] <= b]
        r2 = r91.sim(e, min(n_seed, 20))
        m2 = st.median(x["equity_pct"] for x in r2)
        m1 = (st.median(z[lab]["eq"]) - 1) * 100
        if abs(m1 - m2) > 3.0:
            ok = False
    print("\n관문 ㉘ 크기 0%% 판이 91 정본과 «같은 자리»인가 → **%s**"
          % ("통과" if ok else "⚠️ 구간을 잘라 재서 «완전히» 같진 않다"), flush=True)

    # ── 판정 ─────────────────────────────────────────────────────────
    print("\n" + "=" * 112, flush=True)
    print("  **T★** 어느 크기든 «세 구간 모두» 지수를 이기는가", flush=True)
    T = [k for k, v in res.items() if "진짜" in k and all(v[l]["beat"] for l in v)]
    print("        → %s" % (", ".join(T) if T else "**없음 — 미통과**"), flush=True)

    print("  **U★** 진짜가 «같은 크기의 동전»을 세 구간 모두 이기는가  (**주지표**)", flush=True)
    U = []
    for size in SIZES[1:]:
        for bw in BORROW:
            kr = "%d%%·차입%d%%·진짜" % (int(size * 100), int(bw))
            kf = "%d%%·차입%d%%·동전" % (int(size * 100), int(bw))
            wins = []
            for lab, _a, _b in BLOCKS:
                d = sorted(x - y for x, y in zip(res[kr][lab]["eq"], res[kf][lab]["eq"]))
                wins.append(100.0 * sum(1 for v in d if v > 0) / len(d))
            good = all(w > A_PASS for w in wins)
            if good:
                U.append(kr)
            print("        %-18s %s  →  %s"
                  % (kr, " · ".join("%s %5.1f%%" % (l.split()[0], w)
                                    for (l, _x, _y), w in zip(BLOCKS, wins)),
                     "통과" if good else "미통과"), flush=True)
    print("        → **U★ %s**" % (", ".join(U) if U else "**없음 — 미통과**"), flush=True)
    print("\n  → **① 의 답: %s**" % ("예" if (T and U) else "**아니오**"), flush=True)

    (r91.OUT / "108-short-index.json").write_text(
        json.dumps({k: {l: {a: b for a, b in v.items() if a != "eq"} for l, v in d.items()}
                    for k, d in res.items()}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    print("\n저장: 108-short-index.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
