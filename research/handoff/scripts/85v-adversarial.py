# -*- coding: utf-8 -*-
"""85v — **85번(진입 시점 예측)을 무너뜨리러 간다.** 검증 세션.

두뇌 세션이 지목한 셋 + 사전등록과 «어긋난 곳» + 내가 찾은 것을 «내 코드»로 잰다.

무엇을 재나
-----------
  ㉮ 귀무의 «최선»이 어느 특징에서 오나 (두뇌 물음 ①)  + «제대로 된» 순열 p 값
  ㉯ 사전등록은 「20칸 중 최선」인데 코드는 「10칸 중 최선」 — 등록대로 다시 돈다
  ㉰ 동어반복 판별 — 승자 칸이 «돈»을 더 버나 (두뇌 물음 ②의 실무판)
  ㉱ 대칭 검정 — 같은 칸이 «아래쪽»도 예측하나 (두뇌 물음 ②의 등록판)
  ㉲ prior6m 의 «분위 프로필» — 단조인가 아니면 1분위만 튄 것인가 (두뇌 물음 ③)
  ㉳ 표본안 효과 vs 표본밖 효과 — «같은 자»로 다시 견준다 (두뇌 물음 ③)
  ㉴ 승자 칸이 «몇 건»에 걸려 있나 — 사건 수를 센다
  ㉵ 결측 0건이 맞나 — k 분포를 찍는다 (두뇌 물음)
  ㉶ base 가 NaN 을 품는 문제의 «크기» (두뇌 물음)

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/85v-adversarial.py [null20]
"""
from __future__ import annotations

import bisect
import importlib.util as _u
import math
import random
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r85", HERE / "85-entry-predictors.py")
r85 = _u.module_from_spec(_s)
_s.loader.exec_module(r85)
r84, r41 = r85.r84, r85.r41
FEATS, SPLIT, NQ = r85.FEATS, r85.SPLIT, r85.NQ


def hr(t):
    print("\n" + "=" * 98, flush=True)
    print(t, flush=True)
    print("=" * 98, flush=True)


def split_io(rows, ev, ykey):
    ins, outs = [], []
    for t in ev:
        k = (t["scan_date"], t["code"], t["pattern"])
        if k not in rows:
            continue
        (ins if t["entry_date"] < SPLIT else outs).append((rows[k], ykey(t)))
    return ins, outs


# ═════════════════════════════════════════════════════════════════════════
# ㉮㉯ 귀무 — 어느 특징이 이기나 · 등록대로 «20칸»
# ═════════════════════════════════════════════════════════════════════════
def null_study(ins20, outs20, ins100, outs100, obs20, obs100, n_null=300):
    hr("㉮㉯ 귀무 대조 — 「어느 특징이 이기나」 · 그리고 사전등록의 «20칸»")
    print("  85 는 결과마다 «10칸 중 최선»을 따로 돌린다.", flush=True)
    print("  🚨 사전등록 §4 는 **「20칸 중 최선」의 분포**라고 적혀 있다 — 다시 돈다.\n", flush=True)
    rnd = random.Random(85085085)
    win20, win100 = Counter(), Counter()
    n20, n100, n20_ge, n100_ge = [], [], 0, 0
    both = []
    for it in range(n_null):
        packs = []
        for ins, outs in ((ins20, outs20), (ins100, outs100)):
            zi = [y for _r, y in ins]
            zo = [y for _r, y in outs]
            rnd.shuffle(zi)
            rnd.shuffle(zo)
            i2 = [(r, z) for (r, _y), z in zip(ins, zi)]
            o2 = [(r, z) for (r, _y), z in zip(outs, zo)]
            bb = st.mean(zo)
            per = {}
            for f in FEATS:
                rr = r85.test_one(i2, o2, f, "")
                if rr:
                    per[f] = rr[0] - bb
            packs.append(per)
        p20, p100 = packs
        if p20:
            b = max(p20, key=lambda f: p20[f])
            win20[b] += 1
            n20.append(p20[b])
            n20_ge += (p20[b] >= obs20)
        if p100:
            b = max(p100, key=lambda f: p100[f])
            win100[b] += 1
            n100.append(p100[b])
            n100_ge += (p100[b] >= obs100)
        # ★ 사전등록판 — 20칸을 «한 가족»으로 본다
        if p20 or p100:
            both.append(max(list(p20.values()) + list(p100.values())))
        if it % 60 == 0:
            print("     귀무 %d/%d" % (it, n_null), flush=True)

    for nm, w, arr, obs, nge in (("㉮ MFE≥20%", win20, n20, obs20, n20_ge),
                                 ("㉯ MFE≥100%", win100, n100, obs100, n100_ge)):
        a = sorted(arr)
        print("\n  ▶ %s" % nm, flush=True)
        print("     귀무의 «최선»이 어느 특징이었나: %s"
              % dict(sorted(w.items(), key=lambda x: -x[1])), flush=True)
        top = w.most_common(1)[0]
        print("     → 1위 `%s` 가 %d/%d (**%.1f%%**)"
              % (top[0], top[1], sum(w.values()), 100.0 * top[1] / sum(w.values())),
              flush=True)
        print("     10칸 귀무: 보통 %+.2f%%p · 95%% %+.2f%%p · 최대 %+.2f%%p"
              % (a[len(a) // 2] * 100, a[int(len(a) * .95)] * 100, a[-1] * 100), flush=True)
        print("     🚨 **제대로 된 순열 p 값** = (1 + 귀무≥관측) / (1 + N) = "
              "(1 + %d) / %d = **%.4f**" % (nge, len(a) + 1, (1 + nge) / (len(a) + 1)),
              flush=True)

    b = sorted(both)
    print("\n  ★ **사전등록판 — 「20칸 중 최선」** (두 결과를 한 가족으로)", flush=True)
    print("     보통 %+.2f%%p · 95%% %+.2f%%p · 최대 %+.2f%%p"
          % (b[len(b) // 2] * 100, b[int(len(b) * .95)] * 100, b[-1] * 100), flush=True)
    for nm, obs in (("㉮ +8.05%p", obs20), ("㉯ +4.81%p", obs100)):
        pct = 100.0 * sum(1 for x in b if x < obs) / len(b)
        nge2 = sum(1 for x in b if x >= obs)
        print("     %s → **%.1f 백분위** · 순열 p = %.4f → **%s**"
              % (nm, pct, (1 + nge2) / (len(b) + 1),
                 "통과" if pct >= 95 else "🚨 미통과"), flush=True)
    return win20, win100


# ═════════════════════════════════════════════════════════════════════════
# ㉰㉱㉴ 승자 칸을 «해부»한다
# ═════════════════════════════════════════════════════════════════════════
def dissect(rows, ev, pmap, ins20, outs20, ins100, outs100):
    hr("㉴ 승자 칸이 «몇 건»에 걸려 있나 — 사건 수를 센다")
    for nm, feat, pick, outs in (("㉮ +20%", "prior6m", None, outs20),
                                 ("㉯ +100%", "atr_band", "④매우큼 6%+", outs100)):
        if feat in r85.CAT:
            sel = [y for r, y in outs if r[feat] == pick]
        else:
            xs = sorted(r[feat] for r, _y in (ins20 if nm.startswith("㉮") else ins100)
                        if not r85._nan(r[feat]))
            cuts = [xs[int(len(xs) * i / NQ)] for i in range(1, NQ)]
            sel = [y for r, y in outs
                   if not r85._nan(r[feat]) and bisect.bisect_right(cuts, r[feat]) == 0]
        pos = int(sum(sel))
        allpos = int(sum(y for _r, y in outs))
        print("  %-9s `%-9s` 표본밖 n=%d · **사건 %d건** (표본밖 전체 사건 %d 중 %.0f%%)"
              % (nm, feat, len(sel), pos, allpos, 100.0 * pos / max(1, allpos)), flush=True)
        print("            → 한 건이 비율을 **%.3f%%p** 움직인다"
              % (100.0 / len(sel)), flush=True)

    hr("㉰ 동어반복 판별 ① — 승자 칸이 «돈»을 더 버나 (실무판)")
    print("  84번의 요지는 「꼬리가 전부」였다. 그러면 물어야 할 것은", flush=True)
    print("  「더블 «확률»이 높은가」가 아니라 **「그 칸을 사면 «더 버는가»」**다.\n", flush=True)

    def gain(t):
        return sum(f * (px / t["entry_px"] - 1) * 100
                   for _d, f, px in t["masks"][()]["exits"])

    ok = [t for t in ev if (t["scan_date"], t["code"], t["pattern"]) in rows
          and t["entry_date"] >= SPLIT]
    g_all = [gain(t) for t in ok]
    print("  표본밖 전체 %d건 — 거래당 평균 **%+.3f%%** · 중앙 %+.3f%%"
          % (len(ok), st.mean(g_all), st.median(g_all)), flush=True)
    print("  %-28s %6s %11s %11s %9s %9s"
          % ("칸", "n", "거래당평균", "중앙", "승률", "≥+50%"), flush=True)
    print("  " + "-" * 80, flush=True)
    cells = []
    xs = sorted(r["prior6m"] for r, _y in ins20 if not r85._nan(r["prior6m"]))
    cuts6 = [xs[int(len(xs) * i / NQ)] for i in range(1, NQ)]
    cells.append(("prior6m 1분위 (㉮ 승자)",
                  lambda r: bisect.bisect_right(cuts6, r["prior6m"]) == 0))
    cells.append(("atr_band ④매우큼 (㉯ 승자)",
                  lambda r: r["atr_band"] == "④매우큼 6%+"))
    xs8 = sorted(r["atr20"] for r, _y in ins100 if not r85._nan(r["atr20"]))
    cuts8 = [xs8[int(len(xs8) * i / NQ)] for i in range(1, NQ)]
    cells.append(("atr20 5분위 (㉯ 2등)",
                  lambda r: bisect.bisect_right(cuts8, r["atr20"]) == 4))
    for nm, fn in cells:
        g = [gain(t) for t in ok if fn(rows[(t["scan_date"], t["code"], t["pattern"])])]
        if not g:
            continue
        print("  %-28s %6d %+10.3f%% %+10.3f%% %8.1f%% %8.1f%%"
              % (nm, len(g), st.mean(g), st.median(g),
                 100.0 * sum(1 for x in g if x > 0) / len(g),
                 100.0 * sum(1 for x in g if x >= 50) / len(g)), flush=True)
    print("\n  ★ 「더블 확률은 높은데 거래당 평균이 «안» 높다」면 그건 **변동 폭**이지 엣지가 아니다.",
          flush=True)

    hr("㉱ 동어반복 판별 ② — 같은 칸이 «아래쪽»도 예측하나 (대칭 검정)")
    print("  MFE(최대 유리) 의 짝은 MAE(최대 불리)다. 변동성이면 **양쪽 다** 커야 한다.\n",
          flush=True)

    def mae(t):
        p = pmap[(t["scan_date"], t["code"], t["pattern"])]
        i0 = p["d"].index(t["entry_date"])
        i1 = p["d"].index(t["masks"][()]["exits"][-1][0])
        return (min(p["l"][i0:i1 + 1]) / t["entry_px"] - 1) * 100

    print("  %-28s %6s %11s %11s %11s"
          % ("칸", "n", "MAE 평균", "MAE≤−15%", "MFE≥+100%"), flush=True)
    print("  " + "-" * 74, flush=True)
    base_mae = [mae(t) for t in ok]
    print("  %-28s %6d %+10.2f%% %10.2f%% %10.2f%%"
          % ("표본밖 전체(기준)", len(ok), st.mean(base_mae),
             100.0 * sum(1 for x in base_mae if x <= -15) / len(ok),
             100.0 * sum(1 for _r, y in outs100 for _ in [0] if y) / len(outs100)),
          flush=True)
    for nm, fn in cells:
        sub = [t for t in ok if fn(rows[(t["scan_date"], t["code"], t["pattern"])])]
        if not sub:
            continue
        ma = [mae(t) for t in sub]
        k100 = sum(outs100[i][1] for i, t in enumerate(ok) if fn(rows[
            (t["scan_date"], t["code"], t["pattern"])])) if len(ok) == len(outs100) else None
        print("  %-28s %6d %+10.2f%% %10.2f%% %10.2f%%"
              % (nm, len(sub), st.mean(ma),
                 100.0 * sum(1 for x in ma if x <= -15) / len(sub),
                 100.0 * (k100 / len(sub)) if k100 is not None else float("nan")),
              flush=True)
    print("\n  ★ 「MFE 도 크고 MAE 도 큰」 칸이면 **동어반복(변동 폭)** 이 확정된다.", flush=True)


# ═════════════════════════════════════════════════════════════════════════
# ㉲㉳ prior6m — 프로필과 «같은 자» 비교
# ═════════════════════════════════════════════════════════════════════════
def prior6m_study(ins20, outs20, ins100, outs100):
    hr("㉲ `prior6m` 의 «분위 프로필» — 단조인가, 1분위만 튄 것인가 (두뇌 물음 ③)")
    for nm, ins, outs in (("㉮ MFE≥+20%", ins20, outs20),
                          ("㉯ MFE≥+100%", ins100, outs100)):
        xs = sorted(r["prior6m"] for r, _y in ins if not r85._nan(r["prior6m"]))
        cuts = [xs[int(len(xs) * i / NQ)] for i in range(1, NQ)]

        def q(v):
            return bisect.bisect_right(cuts, v)
        print("\n  ▶ %s" % nm, flush=True)
        print("     %-6s %8s %9s   |  %8s %9s"
              % ("분위", "표본안 n", "비율", "표본밖 n", "비율"), flush=True)
        prof_i, prof_o = [], []
        for i in range(NQ):
            gi = [y for r, y in ins if not r85._nan(r["prior6m"]) and q(r["prior6m"]) == i]
            go = [y for r, y in outs if not r85._nan(r["prior6m"]) and q(r["prior6m"]) == i]
            prof_i.append(st.mean(gi) if gi else float("nan"))
            prof_o.append(st.mean(go) if go else float("nan"))
            print("     %d분위 %8d %8.2f%%   |  %8d %8.2f%%"
                  % (i + 1, len(gi), 100 * prof_i[-1], len(go), 100 * prof_o[-1]),
                  flush=True)
        mono_i = _mono(prof_i)
        mono_o = _mono(prof_o)
        print("     → 표본안 단조? **%s** · 표본밖 단조? **%s**" % (mono_i, mono_o), flush=True)

    hr("㉳ 표본안 효과 vs 표본밖 효과 — **같은 자로** 다시 견준다 (두뇌 물음 ③)")
    print("  🚨 85 의 표는 표본안을 「최고분위 vs 최저분위」로, 표본밖을 「최고분위 vs 기준율」로",
          flush=True)
    print("     적는다 — **다른 자**다. 같은 자(둘 다 «기준율 대비»)로 다시 낸다.\n", flush=True)
    print("  %-11s %-8s %11s %11s %8s"
          % ("특징", "고른 분위", "표본안 대비", "표본밖 대비", "밖÷안"), flush=True)
    print("  " + "-" * 60, flush=True)
    bi = st.mean([y for _r, y in ins20])
    bo = st.mean([y for _r, y in outs20])
    for f in FEATS:
        if f in r85.CAT:
            continue
        xs = sorted(r[f] for r, _y in ins20 if not r85._nan(r[f]))
        if len(xs) < NQ * 20:
            continue
        cuts = [xs[int(len(xs) * i / NQ)] for i in range(1, NQ)]

        def q(v, c=cuts):
            return bisect.bisect_right(c, v)
        qi = {i: [y for r, y in ins20 if not r85._nan(r[f]) and q(r[f]) == i]
              for i in range(NQ)}
        qi = {i: g for i, g in qi.items() if len(g) >= 30}
        if len(qi) < 2:
            continue
        best = max(qi, key=lambda i: st.mean(qi[i]))
        sel = [y for r, y in outs20 if not r85._nan(r[f]) and q(r[f]) == best]
        if len(sel) < 30:
            continue
        e_in = st.mean(qi[best]) - bi
        e_out = st.mean(sel) - bo
        print("  %-11s %-8s %+10.2f%%p %+10.2f%%p %7.2f%s"
              % (f, "%d분위" % (best + 1), e_in * 100, e_out * 100,
                 e_out / e_in if e_in else float("nan"),
                 "  ← 승자" if f == "prior6m" else ""), flush=True)
    print("\n  ★ 「밖÷안」이 1 을 크게 넘으면 «표본안에서 고른 이유»가 밖의 크기를 못 설명한다.",
          flush=True)
    print("    고른 근거(안)보다 잰 값(밖)이 크면, 그 크기는 **고르기가 아니라 운**에서 온다.",
          flush=True)


def _mono(p):
    up = all(p[i] <= p[i + 1] + 1e-12 for i in range(len(p) - 1))
    dn = all(p[i] >= p[i + 1] - 1e-12 for i in range(len(p) - 1))
    return "예(증가)" if up else ("예(감소)" if dn else "**아니오**")


# ═════════════════════════════════════════════════════════════════════════
# ㉵㉶ 결측 · base
# ═════════════════════════════════════════════════════════════════════════
def hygiene(rows, ev, outs20):
    hr("㉵㉶ 결측 0건이 맞나 · `base` 가 NaN 을 품는 문제의 «크기»")
    n_nan = Counter()
    for r in rows.values():
        for f in FEATS:
            if r85._nan(r[f]):
                n_nan[f] += 1
    print("  특징별 NaN: %s" % (dict(n_nan) or "없음"), flush=True)
    tot = len(outs20)
    nn = sum(1 for r, _y in outs20 if r85._nan(r["in_pct"]))
    if nn:
        b_all = st.mean([y for _r, y in outs20])
        b_ok = st.mean([y for r, y in outs20 if not r85._nan(r["in_pct"])])
        print("  표본밖 `in_pct` NaN %d/%d (%.1f%%) — 기준율 전체 %.2f%% vs 비결측 %.2f%% "
              "= **차 %+.2f%%p**"
              % (nn, tot, 100.0 * nn / tot, b_all * 100, b_ok * 100,
                 (b_all - b_ok) * 100), flush=True)
        print("  → `in_pct` 칸의 «기준율차»는 그만큼 부풀거나 깎인다. 승자 칸은 NaN 이 0이라 무관.",
              flush=True)
    else:
        print("  → NaN 이 없다. `base` 의 NaN 문제는 **이번 자료에서 발화하지 않는다**.",
              flush=True)


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    by2, ev, blk, pmap = r84.load()
    rows, miss = r85.build_features(ev, pmap)
    print("결측 %s · 특징 %d/%d" % (dict(miss) or "없음", len(rows), len(ev)), flush=True)

    def mfe(t):
        p = pmap[(t["scan_date"], t["code"], t["pattern"])]
        i0 = p["d"].index(t["entry_date"])
        i1 = p["d"].index(t["masks"][()]["exits"][-1][0])
        return (max(p["h"][i0:i1 + 1]) / t["entry_px"] - 1) * 100

    m = {(t["scan_date"], t["code"], t["pattern"]): mfe(t) for t in ev}

    def y20(t):
        return 1.0 if m[(t["scan_date"], t["code"], t["pattern"])] >= 20 else 0.0

    def y100(t):
        return 1.0 if m[(t["scan_date"], t["code"], t["pattern"])] >= 100 else 0.0

    ins20, outs20 = split_io(rows, ev, y20)
    ins100, outs100 = split_io(rows, ev, y100)
    print("표본안 %d · 표본밖 %d" % (len(ins20), len(outs20)), flush=True)

    hygiene(rows, ev, outs20)
    dissect(rows, ev, pmap, ins20, outs20, ins100, outs100)
    prior6m_study(ins20, outs20, ins100, outs100)
    if "null20" in sys.argv:
        null_study(ins20, outs20, ins100, outs100, 0.0805, 0.0481)
    else:
        print("\n(귀무 재실행은 `null20` 인자로)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
