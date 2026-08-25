# -*- coding: utf-8 -*-
"""71 — **한국 이식: 단 한 번의 검정**. 사전등록: `tasks/71-korea-transfer.md`

🚨 한국에서 어떤 값도 다시 고르지 않는다. 사전등록 §2 를 그대로 쓴다.
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import slot_sim_frac as sf                                    # noqa: E402

_s = _u.spec_from_file_location("r41", HERE / "41-round1-exits.py")
r41 = _u.module_from_spec(_s)
_s.loader.exec_module(r41)

OUT = ROOT / ".cache" / "bt5y" / "out"
SUB = ROOT / ".cache" / "bt5y" / "sub"
COST = (0.0, 0.002)
TOPQ = 0.27          # 업종 상위 27% (미국 3/11 을 그대로)
LO, HI = 0.10, 0.30  # 그룹 내 2·3등급
STOP = 8.0
YEARS = tuple(range(2021, 2027))


def prev_ym(ym, k):
    y, mth = int(ym[:4]), int(ym[5:])
    mth -= k
    while mth <= 0:
        mth += 12
        y -= 1
    return "%04d-%02d" % (y, mth)


def main() -> int:
    by = {}
    for y in YEARS:
        f = SUB / ("krpath_%d.json" % y)
        if not f.exists():
            print("🚨 %s 없음" % f.name)
            return 2
        by[y] = json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
    pack = json.loads((OUT / "71-monthly-kr.json").read_text(encoding="utf-8"))
    monthly, sector, kospi = pack["monthly"], pack["sector"], pack["kospi"]
    ks = sorted(kospi)
    print("=" * 92)
    print("71 — **한국 이식** (사전등록 tasks/71 · 규칙 고정)")
    print("=" * 92)
    print("경로 %d건 · 종목 %d · 업종 라벨 %d"
          % (sum(len(v) for v in by.values()), len(monthly), len(sector)), flush=True)

    months = sorted({m for d in monthly.values() for m in d})
    sec_top, in_pct = {}, {}
    for ym in months:
        base = prev_ym(ym, 6)
        bysec = defaultdict(list)
        for t, d in monthly.items():
            a, b = d.get(base), d.get(ym)
            s = sector.get(t)
            if not a or not b or a <= 0 or not s:
                continue
            bysec[s].append((b / a - 1, t))
        sm = {s: st.mean(x for x, _ in l) for s, l in bysec.items() if len(l) >= 5}
        if not sm:
            continue
        k = max(1, int(round(len(sm) * TOPQ)))
        sec_top[ym] = set(sorted(sm, key=lambda s: -sm[s])[:k])
        pct = {}
        for s, l in bysec.items():
            l.sort(key=lambda x: -x[0])
            n = len(l)
            for i, (_r, t) in enumerate(l):
                pct[t] = i / n
        in_pct[ym] = pct
    print("업종 순위 %d개월 · 상위 %.0f%% = 중앙 **%d개 업종**"
          % (len(sec_top), TOPQ * 100, st.median(len(v) for v in sec_top.values())), flush=True)

    r41.TARGET_FILL, r41.STOP_FILL = "limit", "market"
    ev0, _b = r41.replay(by, lambda p: r41.resolve_half_then_trail(p, STOP, 20.0))

    def q_of(e):
        return in_pct.get(prev_ym(e["scan_date"][:7], 1), {}).get(e["code"])

    def sel(e):
        s = sector.get(e["code"])
        if not s:
            return True                       # 제3군 = 통과 (미국과 같다)
        ym = prev_ym(e["scan_date"][:7], 1)
        tp = sec_top.get(ym)
        if tp is None:
            return True
        q = q_of(e)
        return (s in tp) and (q is not None and LO <= q < HI)

    SEL = [e for e in ev0 if sel(e)]
    print("진입 전수 %d → **조합 %d건 (%.1f%%)**"
          % (len(ev0), len(SEL), 100.0 * len(SEL) / len(ev0)), flush=True)

    def band(ev, n=200):
        with r41.Cost(*COST):
            rs = [sf.sim_frac(ev, slots=5, seed=i, sizing="cash") for i in range(n)]
        return sorted(x["equity_pct"] for x in rs), rs

    lo_d = min(e["entry_date"] for e in ev0).replace("-", "")
    hi_d = max((e["resolve_date"] or e["entry_date"]) for e in ev0).replace("-", "")
    kd = [d for d in ks if lo_d <= d <= hi_d]
    kos = (kospi[kd[-1]] / kospi[kd[0]] - 1) * 100
    print("KOSPI 대용 같은 창 (%s~%s) **%+.2f%%**" % (kd[0], kd[-1], kos), flush=True)

    print("\n" + "─" * 92, flush=True)
    for nm, ev in (("전수(필터 없음)", ev0), ("**조합**", SEL)):
        eq, rs = band(ev)
        print("  %-18s 진입 %6d · 체결 %3d · 자산중앙 **%+9.2f%%** · 운나쁠때 %+9.2f%% · MDD %.1f%%"
              % (nm, len(ev), st.median(x["n_filled"] for x in rs), st.median(eq), eq[10],
                 st.median(x["mdd_pct"] for x in rs)), flush=True)
    eqS, rsS = band(SEL)
    obs = st.median(eqS)
    print("\n  A. 조합 %+.2f%% vs KOSPI %+.2f%%  →  **%s**"
          % (obs, kos, "통과 — 지수 초과" if obs > kos else "**미통과**"), flush=True)

    bym = defaultdict(list)
    for e in ev0:
        bym[e["entry_date"][:7]].append(e)
    cnt = defaultdict(int)
    for e in SEL:
        cnt[e["entry_date"][:7]] += 1
    rnd = random.Random(710825)
    null = []
    for _ in range(200):
        s2 = []
        for ym, lst in bym.items():
            k2 = cnt.get(ym, 0)
            if k2:
                s2.extend(rnd.sample(lst, min(k2, len(lst))))
        null.append(st.median(band(s2, 12)[0]))
    null.sort()
    p95 = null[int(200 * .95)]
    print("  B. 무작위 200판 — 보통 %+.2f%% · **95%% %+.2f%%** · 최대 %+.2f%% → 관측 %+.2f%% **%s**"
          % (null[100], p95, null[-1], obs, "통과" if obs > p95 else "**미통과**"), flush=True)

    with r41.Cost(*COST):
        pt = {id(e): v for e, v in zip(ev0, r41.per_trade(ev0))}
    g1 = [pt[id(e)] for e in ev0 if (q_of(e) is not None and q_of(e) < LO)]
    g2 = [pt[id(e)] for e in ev0 if (q_of(e) is not None and LO <= q_of(e) < HI)]
    print("  C. 1등급 n=%d %+.4f%% vs 2·3등급 n=%d %+.4f%% → **%s**"
          % (len(g1), st.mean(g1), len(g2), st.mean(g2),
             "통과 — 2·3등급이 높다" if st.mean(g2) > st.mean(g1) else "**미통과**"), flush=True)

    def ma(w):
        return {ks[i]: (None if i + 1 < w else
                        kospi[ks[i]] >= st.mean(kospi[d] for d in ks[max(0, i - w + 1):i + 1]))
                for i in range(len(ks))}
    f200 = ma(200)
    ON = {}
    for ym in sorted({"%s-%s" % (d[:4], d[4:6]) for d in kd}):
        pv = [d for d in ks if d < ym[:4] + ym[5:] + "01"]
        ON[ym] = True if not pv else (f200.get(pv[-1]) is not False)

    def sw(curve, cost=0.002):
        dv = {d.replace("-", ""): v for d, v in curve}
        eq, prev, last = 1.0, None, None
        for i in range(1, len(kd)):
            d0, d1 = kd[i - 1], kd[i]
            on = ON.get("%s-%s" % (d1[:4], d1[4:6]), True)
            if last is not None and on != last:
                eq *= (1 - cost)
            last = on
            if on:
                a, b = dv.get(d0), dv.get(d1)
                r = (b / a - 1) if (a and b and a > 0) else \
                    ((b / prev - 1) if (prev and b and prev > 0) else 0.0)
                if b:
                    prev = b
            else:
                r = kospi[d1] / kospi[d0] - 1
            eq *= (1 + r)
        return (eq - 1) * 100

    v = st.median(sw(x["curve"]) for x in rsS[:40])
    onr = 100.0 * sum(1 for x in ON.values() if x) / len(ON)
    print("  D. 국면 스위칭(KOSPI>200MA · 전환비용 0.2%%) **%+.2f%%** (방법 쓴 달 %.0f%%) "
          "vs 스위칭 없음 %+.2f%% → **%s**"
          % (v, onr, obs, "통과" if v > obs else "**미통과**"), flush=True)

    (OUT / "71-korea-transfer.json").write_text(json.dumps(
        {"kospi": kos, "combo": obs, "null_p95": p95, "null_max": null[-1],
         "g1": st.mean(g1), "g2": st.mean(g2), "switch": v,
         "n_sel": len(SEL), "n_all": len(ev0)}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print("\n저장: 71-korea-transfer.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
