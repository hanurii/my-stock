# -*- coding: utf-8 -*-
"""85v 부속 2 — **한 해를 빼면 남나** · 그리고 «20칸 가족»을 «자 맞춰» 다시 건다.

두 물음
-------
  ㉠ **연도 하나를 빼도 관측이 귀무 위인가** (㉮ 는 2024 한 해에 쏠려 보인다)
  ㉡ 사전등록의 「20칸 한 가족」을 **%p 가 아니라 «배수(lift)»**로 걸면 어떻게 되나
     🚨 %p 로 걸면 기준율 25.59% 짜리와 1.76% 짜리를 «같은 자»로 재는 셈이라
        유형 3(종류가 다른 통계)이다. 배수는 자가 맞는다.
  ㉢ 검정 «둘»에 대한 다중비교 보정(본페로니 2) 을 걸면 살아남나

특징은 **한 번만 만들고 캐시**한다(가격 적재가 느리다).

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/85v-fragility.py [N_NULL]
"""
from __future__ import annotations

import bisect
import importlib.util as _u
import json
import os
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
CACHE = Path(os.environ.get("TEMP", "/tmp")) / "85v-feat-cache.json"


def hr(t):
    print("\n" + "=" * 98, flush=True)
    print(t, flush=True)
    print("=" * 98, flush=True)


def load_all():
    if CACHE.exists():
        d = json.loads(CACHE.read_text(encoding="utf-8"))
        print("캐시에서 읽음 — %d건 (%s)" % (len(d["recs"]), CACHE), flush=True)
        return d["recs"]
    by2, ev, blk, pmap = r84.load()
    rows, _miss = r85.build_features(ev, pmap)
    recs = []
    for t in ev:
        k = (t["scan_date"], t["code"], t["pattern"])
        if k not in rows:
            continue
        p = pmap[k]
        i0 = p["d"].index(t["entry_date"])
        i1 = p["d"].index(t["masks"][()]["exits"][-1][0])
        recs.append({"f": rows[k], "d": t["entry_date"],
                     "mfe": (max(p["h"][i0:i1 + 1]) / t["entry_px"] - 1) * 100})
    CACHE.write_text(json.dumps({"recs": recs}, ensure_ascii=False), encoding="utf-8")
    print("캐시 저장 — %d건 (%s)" % (len(recs), CACHE), flush=True)
    return recs


def best_of(ins, outs, want_lift=False):
    bb = st.mean([y for _r, y in outs])
    per = {}
    for f in FEATS:
        rr = r85.test_one(ins, outs, f, "")
        if rr:
            per[f] = (rr[0] / bb - 1.0) if want_lift and bb > 0 else (rr[0] - bb)
    return per


def shuffled(pairs, rnd, blocks=None):
    ys = [y for _r, y in pairs]
    z = ys[:]
    if blocks is None:
        rnd.shuffle(z)
    else:
        idx = defaultdict(list)
        for i, b in enumerate(blocks):
            idx[b].append(i)
        for _b, ii in idx.items():
            vals = [ys[i] for i in ii]
            rnd.shuffle(vals)
            for i, v in zip(ii, vals):
                z[i] = v
    return [(r, y2) for (r, _y), y2 in zip(pairs, z)]


def split(recs, thr, drop_year=None):
    ins, outs, do = [], [], []
    for r in recs:
        if drop_year and r["d"][:4] == drop_year:
            continue
        y = 1.0 if r["mfe"] >= thr else 0.0
        if r["d"] < SPLIT:
            ins.append((r["f"], y))
        else:
            outs.append((r["f"], y))
            do.append(r["d"][:4])
    return ins, outs, do


def main() -> int:
    if r41.YEARS[0] != 2017 and not CACHE.exists():
        print("🚨 BT_Y0=2017 필요")
        return 2
    recs = load_all()
    OUTC = (("㉮ MFE≥+20%", 20.0), ("㉯ MFE≥+100%", 100.0))

    # ── ㉠ 한 해 빼기 ───────────────────────────────────────────────────
    hr("㉠ **연도 하나를 빼도 남나** — 관측 vs «연도 안 섞기» 귀무 95%")
    print("  🚨 표본밖 2024 는 `prior6m 1분위` 율이 58.00%(n=50)로 튄다. 한 해씩 빼 본다.",
          flush=True)
    yrs = sorted({r["d"][:4] for r in recs if r["d"] >= SPLIT})
    for nm, thr in OUTC:
        print("\n  ▶ %s" % nm, flush=True)
        ins, outs, do = split(recs, thr)
        per = best_of(ins, outs)
        bf = max(per, key=lambda f: per[f])
        print("     빼지 않음 — 최선 `%s` **%+.2f%%p**" % (bf, per[bf] * 100), flush=True)
        print("     %-8s %-11s %11s %10s" % ("뺀 해", "그때의 최선", "값", "원래 승자"),
              flush=True)
        for y in yrs:
            i2, o2, _d2 = split(recs, thr, drop_year=y)
            p2 = best_of(i2, o2)
            if not p2:
                continue
            b2 = max(p2, key=lambda f: p2[f])
            print("     %-8s %-11s %+10.2f%%p %+9.2f%%p"
                  % (y, b2, p2[b2] * 100, p2.get(bf, float("nan")) * 100), flush=True)

    # ── ㉡㉢ 20칸 가족 — «배수»로 ────────────────────────────────────────
    hr("㉡ 사전등록 「20칸 한 가족」을 **«배수»로** 건다 (자를 맞춘다)")
    print("  🚨 %p 로 20칸을 한 가족에 넣으면 기준율 25.59%% 짜리와 1.76%% 짜리를", flush=True)
    print("     같은 자로 재는 셈 = **유형 3**. 배수(상위분위율 ÷ 기준율 − 1)면 자가 맞는다.\n",
          flush=True)
    packs = {}
    for nm, thr in OUTC:
        ins, outs, do = split(recs, thr)
        di = [r["d"][:4] for r in recs if r["d"] < SPLIT]
        per = best_of(ins, outs, want_lift=True)
        bf = max(per, key=lambda f: per[f])
        packs[nm] = (ins, outs, do, bf, per[bf], di)
        print("  관측 %s — 최선 `%s` **×%.3f** (기준율 대비 %+.1f%%)"
              % (nm, bf, 1 + per[bf], per[bf] * 100), flush=True)

    for mode in ("통째로", "연도 안"):
        rnd = random.Random(85085085)
        fam, solo = [], {nm: [] for nm, _t in OUTC}
        winners = {nm: Counter() for nm, _t in OUTC}
        for it in range(N_NULL):
            vals = []
            for nm, _thr in OUTC:
                ins, outs, do, _bf, _o, di = packs[nm]
                # 🚨 2026-08-27 수정 — 표본«안»도 연도 블록으로 섞어야 한다.
                #    처음엔 ["in"]*len(ins) 로 «한 덩어리»를 넘겨 표본안이 통째로 섞였다.
                #    (두뇌 세션 구현과 어긋났고, 이 판의 백분위를 98.3 으로 부풀렸다.
                #     같은 값을 연도 블록으로 재면 97.7 이다 — `85v-timeblock.py`.)
                b_in = None if mode == "통째로" else di
                b_out = None if mode == "통째로" else do
                per = best_of(shuffled(ins, rnd, b_in), shuffled(outs, rnd, b_out),
                              want_lift=True)
                if per:
                    b = max(per, key=lambda f: per[f])
                    winners[nm][b] += 1
                    solo[nm].append(per[b])
                    vals += list(per.values())
            if vals:
                fam.append(max(vals))
            if it % 100 == 0:
                print("     %s %d/%d" % (mode, it, N_NULL), flush=True)
        f = sorted(fam)
        print("\n  ── 섞기 «%s» ─────────────────────────────────" % mode, flush=True)
        print("  20칸 가족 귀무(배수): 보통 ×%.3f · 95%% ×%.3f · 최대 ×%.3f"
              % (1 + f[len(f) // 2], 1 + f[int(len(f) * .95)], 1 + f[-1]), flush=True)
        for nm, _thr in OUTC:
            o = packs[nm][4]
            a = sorted(solo[nm])
            pf = 100.0 * sum(1 for x in f if x < o) / len(f)
            ps = 100.0 * sum(1 for x in a if x < o) / len(a)
            ngef = sum(1 for x in f if x >= o)
            nges = sum(1 for x in a if x >= o)
            print("  %-13s ×%.3f — 가족(20칸) **%.1f 백분위** p=%.4f %s  |  "
                  "단독(10칸) %.1f 백분위 p=%.4f %s"
                  % (nm, 1 + o, pf, (1 + ngef) / (len(f) + 1),
                     "✅" if pf >= 95 else "🚨",
                     ps, (1 + nges) / (len(a) + 1),
                     "✅" if ps >= 95 else "🚨"), flush=True)
        print("  ㉢ 본페로니 2(검정 둘) — 단독 문턱을 **97.5 백분위**로 올리면:", flush=True)
        for nm, _thr in OUTC:
            o = packs[nm][4]
            a = sorted(solo[nm])
            ps = 100.0 * sum(1 for x in a if x < o) / len(a)
            print("     %-13s %.1f 백분위 → **%s**"
                  % (nm, ps, "통과" if ps >= 97.5 else "🚨 미통과"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
