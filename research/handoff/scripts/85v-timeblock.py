# -*- coding: utf-8 -*-
"""85v 부속 — **귀무가 «시간 구조»를 지운다.** 그래서 «달력의 대리변수»는 그냥 이긴다.

왜 이걸 재나
------------
85 의 귀무는 표본밖 라벨 1,305개를 **통째로** 섞는다. 그러면 「+20% 도달률이
2022년엔 낮고 2023년엔 높다」는 **시간 구조가 통째로 사라진다.**
반면 «관측»은 그 구조를 그대로 갖고 있다.

  → **결과율과 «같은 방향»으로 시간에 쏠린 특징은, 예측력이 0이어도 귀무를 이긴다.**

그래서 귀무를 **연도 «안»에서만 섞는 판**으로 다시 돈다(연도별 기준율 보존).
관측이 그걸 넘으면 「달력이 아니다」가 되고, 못 넘으면 **주판정이 무너진다.**

같이 재는 것
  ㉠ 승자 분위가 «연도»에 쏠려 있나
  ㉡ 귀무의 최선이 «어느 특징»인가 + 제대로 된 순열 p
  ㉢ 사전등록대로 «20칸 한 가족» 귀무
  ㉣ `atr_band ④` 와 `atr20 5분위` 가 «같은 거래»인가 (동어반복의 직접 증거)

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/85v-timeblock.py [N_NULL]
"""
from __future__ import annotations

import bisect
import importlib.util as _u
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r85", HERE / "85-entry-predictors.py")
r85 = _u.module_from_spec(_s)
_s.loader.exec_module(r85)
r84, r41 = r85.r84, r85.r41
FEATS, SPLIT, NQ, CAT = r85.FEATS, r85.SPLIT, r85.NQ, r85.CAT

N_NULL = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 300


def hr(t):
    print("\n" + "=" * 98, flush=True)
    print(t, flush=True)
    print("=" * 98, flush=True)


def best_of(ins, outs):
    """10칸을 돌아 {특징: 기준율차} 를 낸다 — 85 와 «같은 절차»."""
    bb = st.mean([y for _r, y in outs])
    per = {}
    for f in FEATS:
        rr = r85.test_one(ins, outs, f, "")
        if rr:
            per[f] = rr[0] - bb
    return per


def shuffled(pairs, rnd, blocks=None):
    """라벨만 섞는다. `blocks` 가 있으면 **블록 «안»에서만** 섞는다."""
    ys = [y for _r, y in pairs]
    if blocks is None:
        z = ys[:]
        rnd.shuffle(z)
    else:
        idx = defaultdict(list)
        for i, b in enumerate(blocks):
            idx[b].append(i)
        z = ys[:]
        for b, ii in idx.items():
            vals = [ys[i] for i in ii]
            rnd.shuffle(vals)
            for i, v in zip(ii, vals):
                z[i] = v
    return [(r, y2) for (r, _y), y2 in zip(pairs, z)]


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    by2, ev, blk, pmap = r84.load()
    rows, miss = r85.build_features(ev, pmap)

    def mfe(t):
        p = pmap[(t["scan_date"], t["code"], t["pattern"])]
        i0 = p["d"].index(t["entry_date"])
        i1 = p["d"].index(t["masks"][()]["exits"][-1][0])
        return (max(p["h"][i0:i1 + 1]) / t["entry_px"] - 1) * 100

    m = {(t["scan_date"], t["code"], t["pattern"]): mfe(t) for t in ev}
    OUTC = {"㉮ MFE≥+20%": 20.0, "㉯ MFE≥+100%": 100.0}

    def build(thr):
        ins, outs, di, do = [], [], [], []
        for t in ev:
            k = (t["scan_date"], t["code"], t["pattern"])
            if k not in rows:
                continue
            y = 1.0 if m[k] >= thr else 0.0
            if t["entry_date"] < SPLIT:
                ins.append((rows[k], y))
                di.append(t["entry_date"][:4])
            else:
                outs.append((rows[k], y))
                do.append(t["entry_date"][:4])
        return ins, outs, di, do

    packs = {nm: build(thr) for nm, thr in OUTC.items()}

    # ── ㉠ 승자 분위가 «연도»에 쏠려 있나 ────────────────────────────────
    hr("㉠ 승자 분위가 «연도»에 쏠려 있나 — 귀무가 못 보는 축")
    ins20, outs20, _di, do20 = packs["㉮ MFE≥+20%"]
    xs = sorted(r["prior6m"] for r, _y in ins20 if not r85._nan(r["prior6m"]))
    cuts = [xs[int(len(xs) * i / NQ)] for i in range(1, NQ)]
    yrs = sorted(set(do20))
    print("  표본밖 연도별 — 전체 기준율 vs `prior6m 1분위` 비중", flush=True)
    print("  %-6s %8s %9s %10s %9s %10s"
          % ("연도", "전체 n", "기준율", "1분위 n", "1분위비중", "1분위율"), flush=True)
    print("  " + "-" * 60, flush=True)
    for y in yrs:
        sub = [(r, yy) for (r, yy), d in zip(outs20, do20) if d == y]
        q1 = [yy for r, yy in sub
              if not r85._nan(r["prior6m"]) and bisect.bisect_right(cuts, r["prior6m"]) == 0]
        print("  %-6s %8d %8.2f%% %10d %8.1f%% %9s"
              % (y, len(sub), 100 * st.mean([yy for _r, yy in sub]), len(q1),
                 100.0 * len(q1) / len(sub),
                 "%8.2f%%" % (100 * st.mean(q1)) if q1 else "  —"), flush=True)
    print("\n  ★ 1분위 «비중»이 연도마다 크게 다르고 그 연도의 기준율도 다르면,", flush=True)
    print("    +8.05%p 의 일부는 **「좋은 해에 더 많이 뽑힌 것」**이다.", flush=True)
    print("    통째로 섞는 귀무는 이 축을 **못 본다** — 연도 안에서 섞어야 보인다.", flush=True)

    # ── ㉣ 동어반복의 직접 증거 ─────────────────────────────────────────
    hr("㉣ `atr_band ④` 와 `atr20 5분위` 가 «같은 거래»인가")
    ins100, outs100, _di2, _do2 = packs["㉯ MFE≥+100%"]
    xs8 = sorted(r["atr20"] for r, _y in ins100 if not r85._nan(r["atr20"]))
    c8 = [xs8[int(len(xs8) * i / NQ)] for i in range(1, NQ)]
    A = {i for i, (r, _y) in enumerate(outs100) if r["atr_band"] == "④매우큼 6%+"}
    B = {i for i, (r, _y) in enumerate(outs100)
         if not r85._nan(r["atr20"]) and bisect.bisect_right(c8, r["atr20"]) == 4}
    print("  atr_band ④ n=%d · atr20 5분위 n=%d · **겹침 %d**" % (len(A), len(B), len(A & B)),
          flush=True)
    print("  겹침 ÷ 작은 쪽 = **%.1f%%**   (자카드 %.1f%%)"
          % (100.0 * len(A & B) / min(len(A), len(B)),
             100.0 * len(A & B) / len(A | B)), flush=True)
    print("\n  ★ 크게 겹치면 10칸 중 «둘»이 사실상 한 변수다 — 「독립된 열 개」가 아니다.",
          flush=True)

    # ── ㉡㉢ 귀무 재실행 ────────────────────────────────────────────────
    obs = {}
    for nm in OUTC:
        ins, outs, _a, _b = packs[nm]
        per = best_of(ins, outs)
        bf = max(per, key=lambda f: per[f])
        obs[nm] = (bf, per[bf])
        print("\n관측 재현 — %s 최선 `%s` %+.2f%%p" % (nm, bf, per[bf] * 100), flush=True)

    for mode in ("통째로 섞기 (85 가 한 것)", "연도 «안»에서만 섞기 (내가 거는 것)"):
        hr("㉡㉢ 귀무 %d회 — **%s**" % (N_NULL, mode))
        rnd = random.Random(85085085)
        win = {nm: Counter() for nm in OUTC}
        arr = {nm: [] for nm in OUTC}
        fam = []
        for it in range(N_NULL):
            vals = []
            for nm in OUTC:
                ins, outs, di, do = packs[nm]
                bi = di if "연도" in mode else None
                bo = do if "연도" in mode else None
                per = best_of(shuffled(ins, rnd, bi), shuffled(outs, rnd, bo))
                if per:
                    b = max(per, key=lambda f: per[f])
                    win[nm][b] += 1
                    arr[nm].append(per[b])
                    vals += list(per.values())
            if vals:
                fam.append(max(vals))
            if it % 60 == 0:
                print("     %d/%d" % (it, N_NULL), flush=True)
        for nm in OUTC:
            a = sorted(arr[nm])
            o = obs[nm][1]
            nge = sum(1 for x in a if x >= o)
            pct = 100.0 * sum(1 for x in a if x < o) / len(a)
            print("\n  ▶ %s  (관측 `%s` %+.2f%%p)" % (nm, obs[nm][0], o * 100), flush=True)
            print("     귀무 최선의 «특징» 분포: %s"
                  % dict(sorted(win[nm].items(), key=lambda x: -x[1])[:5]), flush=True)
            print("     10칸 귀무: 보통 %+.2f%%p · 95%% %+.2f%%p · 최대 %+.2f%%p"
                  % (a[len(a) // 2] * 100, a[int(len(a) * .95)] * 100, a[-1] * 100),
                  flush=True)
            print("     → **%.1f 백분위** · 순열 p = (1+%d)/%d = **%.4f** → **%s**"
                  % (pct, nge, len(a) + 1, (1 + nge) / (len(a) + 1),
                     "통과" if pct >= 95 else "🚨 **미통과**"), flush=True)
        f = sorted(fam)
        print("\n  ★ 사전등록판 «20칸 한 가족»: 보통 %+.2f%%p · 95%% %+.2f%%p · 최대 %+.2f%%p"
              % (f[len(f) // 2] * 100, f[int(len(f) * .95)] * 100, f[-1] * 100), flush=True)
        for nm in OUTC:
            o = obs[nm][1]
            pct = 100.0 * sum(1 for x in f if x < o) / len(f)
            nge = sum(1 for x in f if x >= o)
            print("     %s %+.2f%%p → **%.1f 백분위** · p = %.4f → **%s**"
                  % (nm, o * 100, pct, (1 + nge) / (len(f) + 1),
                     "통과" if pct >= 95 else "🚨 **미통과**"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
