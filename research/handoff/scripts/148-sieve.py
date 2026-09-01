# -*- coding: utf-8 -*-
r"""148 — 「3단」 체. 사전등록 tasks/148-three-bin-sieve.md 그대로.

🚨 145 를 «그대로» 든다 — 적재·특징·자 A/B·순열을 새로 안 짠다.
   다른 것은 «둘»:
     ① 점수  145 「백분위 × 부호」(직선)  →  148 «그날 안 3분위» 칸값 (모양을 낸다)
     ② 문턱  145 max(z_A, z_B) «목표마다»  →  148 **네 통계 한꺼번에**
             max(z_A⁺²⁰, z_B⁺²⁰, z_A⁺³⁰, z_B⁺³⁰)   ← 두 목표가 «한 번도» 안 세어졌었다

  문턱  **99.444 백분위** (N=9) · 순열 **4,500판**(규약 ②「문턱 위 ≥25판」)
  🔴 자 B 두 칸(+20 1.88 · +30 1.75)은 **「분해능 부족 — 판정 안 함」**으로 «선언»됨
     ⛔ 그래도 **max-T 에서 «빼지 않는다»** — 빼면 문턱이 내려가고 그게 «지렛대»다
  ⛔ 뒤 구간(2012~) 안 연다

🚨 관문 목록은 **`GATES` «한 곳»에서만** 쓴다 (147 유형 43).
   코드가 그걸 «읽어» 실행하고 끝에 「등록 N · 실행 N · 누락 0」을 찍는다. 누락이면 exit.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/148-sieve.py
"""
from __future__ import annotations

import bisect
import importlib.util as _u
import json
import math
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r143", HERE / "143-sieve.py")
r143 = _u.module_from_spec(_s)
_s.loader.exec_module(r143)
r91 = r143.r91

OUT = ROOT / "research" / "handoff" / "data" / "148-result.json"
SRC6 = ("atr_band", "gap", "m6", "m12", "hi12", "logtov")
NBIN = 3                              # 3단 — 「140(53)과 145(6) «사이»」가 이 판의 가설
NPERM, PERM_SEED = 4500, 143
# 🚨 F★ 을 **«정수 대역»**으로 (규약 ⑫ · 유형 38). B 를 올리는 건 «옮기는» 것이지 «고치는» 게 아니다:
#   B=4,500 아래끝 6.26 → [7,25]  ·  B=7,200 아래끝 10.02 → [11,40]  ·  «어떤 B 에서도» 정수에 안 떨어진다
#   ⇒ **B=4,500 유지 · 대역을 «수»로 못박는다**
# 🚨🚨 2026-09-01 3차 정정 — **F★ 을 «양쪽»에서 «한쪽»으로.** 진짜 원인은 «이산»이 아니었다:
#   옛 F★ [7,25] 양쪽  →  **올바른 구현을 «56.4%» 확률로 떨어뜨림**
#     (독립 극단 기대 6.26판 · SD 2.50판 → 관측 6판은 −0.11σ = «잡음 안»)
#   ⇒ **관측(이항 «난수»)을 «결정적» 괄호에 «점»으로 댄 것**이 병이었다
#   ★ F★ 이 «막으려던» 것은 «한쪽»뿐이다 —
#     잘못 구현(자마다 따로 분위) → 문턱이 «단일 검정» 분위 → C ≈ α×B = **25판**
#     올바른 구현                → C ≈ **6.3판**       ⇒ **위험한 방향은 «C 가 큰» 쪽뿐**
#   ✅ **F★ = 「C ≥ 13 이면 미통과」** — 오탐 **1.2%** · 잘못 구현 검출력 **99.69%**
#   🚨 이 관문은 «검증 세션»이 냈고, **그 «오탐률»을 «한 번도 안 쟀다»**(본인 신고)
F_TRIP = 13                 # ★ 한쪽 — C ≥ 13 이면 미통과
NFAKE, FAKE_TRIP = 100, 4
ALPHA = 0.05 / 9                      # N=9 → 99.444 백분위
PCTL = 100.0 * (1.0 - ALPHA)
# 🚨 «판정 안 함»으로 «미리» 선언된 칸 (§0③) — max-T 에는 «남긴다»
NO_JUDGE = {("30", "B"), ("20", "B")}
# 맞춘 숫자 — H★ 이 «코드로» 센다
FIT_140, FIT_145 = 53, 6

# ══════════════════════════════════════════════════════════════════════════
# 🚨 관문 목록 — **«한 곳». 문서는 이걸 «인용»한다** (유형 43)
# ══════════════════════════════════════════════════════════════════════════
GATES = ("A", "B", "C", "E", "F", "G", "H", "I", "J")
GATE_DESC = {
    "A": "학습/시험 후보 ±5%",
    "B": "뒤 구간 연도 0건",
    "C": "커닝 시험 — 미래를 넣으면 «반드시» 오르나",
    "E": "순열 = 같은 날 «안» 순서만 · 재표집 안 씀",
    "F": "max-T — 자 A 혼자 넘은 판 수가 «13 미만»인가(한쪽) + 괄호 안 위치",
    "G": "특징 자격(서로 다른 값 ≥2) + 「그날 안 칸이 모두 같은 날」 비율",
    "H": "맞춘 숫자가 140(53)과 145(6) «사이»인가",
    "I": "불변 검산 — 세 칸에 «같은 상수»를 더하면 결과가 «글자 그대로» 같은가",
    "J": "가짜 체 100개 — 4개 이상 넘으면 «못 잼»",
}


# ══════════════════════════════════════════════════════════════════════════
# 1. 3단 — 그날 «안»에서 3분위. 칸 «경계»는 자동이고 «맞추는 값»이 아니다
# ══════════════════════════════════════════════════════════════════════════
def day_bins(days, byday, key):
    """{날: [칸…]} · 🚨 **동점은 «같은» 칸**(아래 칸부터) · 결측은 «중간» 칸.

    🚨 2026-09-01 정정 — 처음 코드는 `r * NBIN // n` 로 **«정렬 뒤 위치»**를 썼다.
       그러면 **값이 «전부 같아도» 칸이 [0,1,2] 로 «갈렸고»**, 경로 파일 순서가
       «가짜 3분할»을 만들었다. `gap` 은 82% 가 피벗 정가라 «상수»인데 살아 보였다.
       ⇒ **«자기보다 «작은» 것의 수»로 칸을 준다. 동점은 «반드시» 같은 칸.**
       (G★ 이 「그날 칸이 모두 같은 날 = 0.0%」라는 «불가능한 값»으로 잡았다)
    """
    out = {}
    for d in days:
        cs = byday[d]
        vals = [key(c) for c in cs]
        idx = [i for i, v in enumerate(vals) if v is not None]
        b = [NBIN // 2] * len(cs)                       # 결측 → 중간
        if len(idx) >= 2:
            n = len(idx)
            srt = sorted(vals[i] for i in idx)
            for i in idx:
                b[i] = min(NBIN - 1, bisect.bisect_left(srt, vals[i]) * NBIN // n)
        out[d] = b
    return out


def learn_values(tr_days, byday, bins):
    """v_{j,b} = 그 칸에 든 후보의 «날 안 «중심화»된 r_» 평균.
    🚨 중심화가 핵심 — 안 하면 「그날이 좋은 날이었나」를 배운다(진입 시점에 모름)."""
    acc = {b: [0.0, 0] for b in range(NBIN)}
    for d in tr_days:
        cs = byday[d]
        m = sum(c["r"] for c in cs) / len(cs)
        for i, c in enumerate(cs):
            k = bins[d][i]
            acc[k][0] += c["r"] - m
            acc[k][1] += 1
    return {b: (acc[b][0] / acc[b][1] if acc[b][1] else 0.0) for b in acc}


def score_3bin(days, byday, vmap, binmap, shift=None):
    """점수 = Σ_j v_j(칸).  shift 가 있으면 특징마다 «같은 상수»를 더한다(I★)."""
    out = {d: [0.0] * len(byday[d]) for d in days}
    for nm, v in vmap.items():
        c0 = (shift or {}).get(nm, 0.0)
        b = binmap[nm]
        for d in days:
            row = out[d]
            for i, k in enumerate(b[d]):
                row[i] += v[k] + c0
    return out


# ══════════════════════════════════════════════════════════════════════════
# 2. 목표 하나를 «준비»만 한다 (판정은 네 통계를 «모아» 낸다)
# ══════════════════════════════════════════════════════════════════════════
def prepare(target, cut):
    rows = r143.load_rows(target)
    side = r143.Side({t["code"] for t in rows})
    byday = defaultdict(list)
    for t in rows:
        byday[t["entry_date"]].append({"r": t["r"], "f": r143.features(t, side), "t": t})
    alld = sorted(byday)
    tr = [d for d in alld if d < cut and len(byday[d]) >= 2]
    te = [d for d in alld if d >= cut and len(byday[d]) >= 2]
    n_tr = sum(len(byday[d]) for d in alld if d < cut)
    n_te = sum(len(byday[d]) for d in alld if d >= cut)

    live, flat = [], {}
    for nm in SRC6:
        u = len({c["f"].get(nm) for d in tr for c in byday[d] if c["f"].get(nm) is not None})
        if u >= 2:
            live.append(nm)
    binmap = {nm: day_bins(alld, byday, (lambda n: (lambda c: c["f"].get(n)))(nm))
              for nm in live}
    for nm in live:                       # G★ 부속 — 그날 칸이 «모두 같은» 날
        z = sum(1 for d in te if len(set(binmap[nm][d])) <= 1)
        flat[nm] = 100.0 * z / len(te)
    vmap = {nm: learn_values(tr, byday, binmap[nm]) for nm in live}

    sday, ev = r143.ref_fills(target)
    b_days = [d for d in te if 1 <= min(sday.get(d, 0), len(byday[d])) < len(byday[d])]
    return dict(byday=byday, alld=alld, tr=tr, te=te, n_tr=n_tr, n_te=n_te,
                live=live, flat=flat, binmap=binmap, vmap=vmap, sday=sday,
                b_days=b_days, cut=cut)


# ══════════════════════════════════════════════════════════════════════════
# 3. 🚨 네 통계를 «한 뽑기»로 — 두 목표의 상관이 순열에 «들어오게»
# ══════════════════════════════════════════════════════════════════════════
def joint_perm(P20, P30, nperm, seed):
    """뽑기 j 마다 난수 흐름 «하나»로 두 목표의 «그날 묶음»을 «같이» 섞는다.
    🚨 따로 섞으면 상관이 «0 으로» 만들어져 문턱이 «부풀려진다»(과보수)."""
    alld = sorted(set(P20["te"]) | set(P30["te"]))
    out = {"A20": [], "B20": [], "A30": [], "B30": []}
    for j in range(nperm):
        rnd = random.Random(seed * 1000003 + j)
        o = {"20": {}, "30": {}}
        for d in alld:
            for tag, PP in (("20", P20), ("30", P30)):
                if d in PP["byday"]:
                    w = list(range(len(PP["byday"][d])))
                    rnd.shuffle(w)
                    o[tag][d] = w
        for tag, PP in (("20", P20), ("30", P30)):
            a = r143.metric_A(PP["te"], PP["byday"], o[tag])
            b = r143.metric_B(PP["b_days"], PP["byday"], o[tag], PP["sday"])
            out["A" + tag].append(sum(a) / len(a))
            out["B" + tag].append(sum(b) / len(b) if b else 0.0)
        if (j + 1) % 500 == 0:
            print("     순열 %d/%d …" % (j + 1, nperm), flush=True)
    return out


def zof(x, arr):
    m = sum(arr) / len(arr)
    sd = math.sqrt(sum((v - m) ** 2 for v in arr) / (len(arr) - 1))
    return ((x - m) / sd if sd > 0 else 0.0), m, sd


def main() -> int:
    r143._guard()
    done = set()
    print("=" * 104, flush=True)
    print("148 — 「3단」 체 · 143 갈림표의 «셋째 갈래»  ·  문턱 **%.3f 백분위** (N=9)" % PCTL,
          flush=True)
    print("🚨 max-T 를 **네 통계**(+20 A·B · +30 A·B) 위에서 — 두 목표가 «한 번도» 안 세어졌었다",
          flush=True)
    print("🔴 자 B 두 칸은 **「분해능 부족 — 판정 안 함」**으로 «선언»됨 (max-T 에는 «남긴다»)",
          flush=True)
    print("=" * 104, flush=True)

    P = {}
    for tag, target in (("20", 20.0), ("30", 30.0)):
        P[tag] = prepare(target, r143.CUT[target])

    print("", flush=True)
    print("## 관문", flush=True)
    okA = okB = True
    for tag in ("20", "30"):
        p = P[tag]
        gap = abs(p["n_tr"] - p["n_te"]) / max(1.0, (p["n_tr"] + p["n_te"]) / 2.0) * 100.0
        okA = okA and gap <= 5.0
        okB = okB and not [d for d in p["alld"] if d >= "2012-01-01"]
        print("  A* +%s — 학습/시험 %d / %d · 어긋남 **%.1f%%**"
              % (tag, p["n_tr"], p["n_te"], gap), flush=True)
    done |= {"A", "B"}
    print("  B* 뒤 구간 연도 **0건** (두 목표 다)", flush=True)
    print("  G* 특징 자격 · 「그날 «칸»이 모두 같은 날」 비율", flush=True)
    for tag in ("20", "30"):
        p = P[tag]
        print("     +%s — 겨룸 **%d개**  %s"
              % (tag, len(p["live"]),
                 " · ".join("%s %.1f%%" % (k, v) for k, v in p["flat"].items())), flush=True)
    done.add("G")

    nfit = len(P["20"]["live"]) * (NBIN - 1)
    okH = FIT_145 < nfit < FIT_140
    print("  H* 맞춘 숫자 — 특징 %d개 × (%d−1) = **%d**  ·  %d < %d < %d  %s"
          % (len(P["20"]["live"]), NBIN, nfit, FIT_145, nfit, FIT_140,
             "**통과**" if okH else "🚨 **미통과**"), flush=True)
    done.add("H")

    okI = True
    for tag in ("20", "30"):
        p = P[tag]
        s0 = score_3bin(p["te"], p["byday"], p["vmap"], p["binmap"])
        sh = {nm: 7.0 + i for i, nm in enumerate(p["live"])}
        s1 = score_3bin(p["te"], p["byday"], p["vmap"], p["binmap"], shift=sh)
        o0 = r143.order_by(p["te"], p["byday"], s0)
        o1 = r143.order_by(p["te"], p["byday"], s1)
        same = all(o0[d] == o1[d] for d in p["te"])
        okI = okI and same
        print("  I* +%s 불변 검산 — 세 칸에 «같은 상수»를 더해도 순위가 같은가  %s"
              % (tag, "**통과**" if same else "🚨 **미통과 — 맞춘 수 주장이 틀렸다**"), flush=True)
    done.add("I")

    obs = {}
    for tag in ("20", "30"):
        p = P[tag]
        sc = score_3bin(p["te"], p["byday"], p["vmap"], p["binmap"])
        o = r143.order_by(p["te"], p["byday"], sc)
        a = r143.metric_A(p["te"], p["byday"], o)
        b = r143.metric_B(p["b_days"], p["byday"], o, p["sday"])
        obs["A" + tag] = sum(a) / len(a)
        obs["B" + tag] = sum(b) / len(b) if b else float("nan")

    print("", flush=True)
    print("## 순열 %d판 — 🚨 네 통계를 «한 뽑기»로 묶는다 (씨앗 %d)" % (NPERM, PERM_SEED),
          flush=True)
    nl = joint_perm(P["20"], P["30"], NPERM, PERM_SEED)
    done.add("E")
    zs, mom = {}, {}
    for k in ("A20", "B20", "A30", "B30"):
        zs[k], mu, sd = zof(obs[k], nl[k])
        mom[k] = (mu, sd)
    zn = {k: [(x - mom[k][0]) / mom[k][1] if mom[k][1] > 0 else 0.0 for x in nl[k]] for k in nl}
    mx = [max(zn["A20"][i], zn["B20"][i], zn["A30"][i], zn["B30"][i]) for i in range(NPERM)]
    thr = r143.pct(mx, PCTL)

    k_exc = sum(1 for z in zn["A20"] if z > thr)          # 🚨 «판 수»로 센다(비율 아님)
    exc = 100.0 * k_exc / NPERM
    lo_f = 100.0 * (1.0 - (1.0 - ALPHA) ** 0.25)
    hi_f = 100.0 * ALPHA
    okF = k_exc < F_TRIP                                  # ★ «한쪽» — C ≥ 13 이면 미통과
    zlo, zhi = 2.5392, 2.9907
    pos = (thr - zlo) / (zhi - zlo)
    print("  **max-T 문턱 z = %.4f**  (%.3f 백분위 · 문턱 위 %d판)"
          % (thr, PCTL, round(NPERM * ALPHA)), flush=True)
    print("  F* 괄호(네 통계) — 자 A(+20) 혼자 넘은 **%d판** / %d = %.3f%%"
          % (k_exc, NPERM, exc), flush=True)
    print("     ★ **한쪽 문턱 — C >= %d 이면 미통과** (오탐 1.2%% · 잘못 구현 검출력 99.69%%)  →  %s"
          % (F_TRIP, "**통과**" if okF else "🚨 **미통과 — 자마다 따로 분위를 잡았을 것**"),
          flush=True)
    print("        올바른 구현 기대 %.2f판 · 잘못 구현 기대 %.2f판  →  «위험한 방향»은 «큰» 쪽뿐"
          % (NPERM * lo_f / 100, NPERM * hi_f / 100), flush=True)
    print("     괄호 안 위치 **%.3f**  (0 = 완전상관 · 1 = k=4 독립)  →  %s"
          % (pos, "상관 쪽" if pos < 0.5 else "🚨 **독립 쪽 — 문턱이 «낮게» 잡혔는지 본다**"),
          flush=True)
    print("  ★ **실측 z 로 확정한 천장/MDE**", flush=True)
    for tag, lab, se, c in (("20", "A", 0.5795, 9.207), ("20", "B", 1.2790, 7.204),
                            ("30", "A", 0.7439, 11.407), ("30", "B", 2.0843, 10.903)):
        print("     +%s 자 %s — 천장 %.3f / MDE %.3f = **%.2f배**%s"
              % (tag, lab, c, thr * se, c / (thr * se),
                 "   🔴 «판정 안 함»" if (tag, lab) in NO_JUDGE else ""), flush=True)
    done.add("F")

    okC = True
    for tag in ("20", "30"):
        p = P[tag]
        cb = day_bins(p["alld"], p["byday"], lambda c: c["r"])
        cv = learn_values(p["tr"], p["byday"], cb)
        vm = dict(p["vmap"])
        bm = dict(p["binmap"])
        vm["_CHEAT"] = cv
        bm["_CHEAT"] = cb
        sc = score_3bin(p["te"], p["byday"], vm, bm)
        ac = r143.metric_A(p["te"], p["byday"], r143.order_by(p["te"], p["byday"], sc))
        ac = sum(ac) / len(ac)
        ok = ac > obs["A" + tag]
        okC = okC and ok
        print("  C* +%s 커닝 — 미래를 넣으면 자 A 가 %+.4f → **%+.4f**  %s"
              % (tag, obs["A" + tag], ac, "**통과**" if ok else "🚨 **미통과**"), flush=True)
    done.add("C")

    rnd = random.Random(PERM_SEED)
    over = 0
    for j in range(NFAKE):
        zz = []
        for tag in ("20", "30"):
            p = P[tag]
            fb, fv = {}, {}
            cells = [c for d in p["alld"] for c in p["byday"][d]]
            for nm in p["live"]:
                pool = [c["f"].get(nm) for c in cells]
                rnd.shuffle(pool)
                tg = "_F%s_%d_%s" % (tag, j, nm)
                for c, v in zip(cells, pool):
                    c[tg] = v
                fb[tg] = day_bins(p["alld"], p["byday"], (lambda g: (lambda c: c.get(g)))(tg))
                fv[tg] = learn_values(p["tr"], p["byday"], fb[tg])
            sc = score_3bin(p["te"], p["byday"], fv, fb)
            o = r143.order_by(p["te"], p["byday"], sc)
            a = r143.metric_A(p["te"], p["byday"], o)
            b = r143.metric_B(p["b_days"], p["byday"], o, p["sday"])
            zz.append((sum(a) / len(a) - mom["A" + tag][0]) / mom["A" + tag][1])
            if b:
                zz.append((sum(b) / len(b) - mom["B" + tag][0]) / mom["B" + tag][1])
            for c in cells:
                for tg in list(fb):
                    c.pop(tg, None)
        if max(zz) > thr:
            over += 1
        if (j + 1) % 25 == 0:
            print("     가짜 체 %d/%d …" % (j + 1, NFAKE), flush=True)
    okJ = over < FAKE_TRIP
    print("  J* 가짜 체 %d개 중 문턱을 넘은 것 **%d개** (기대 %.2f · 방아쇠 >=%d)  %s"
          % (NFAKE, over, NFAKE * ALPHA, FAKE_TRIP,
             "**통과**" if okJ else "🚨 **방아쇠 — «못 잼»으로 닫는다**"), flush=True)
    done.add("J")

    miss = [g for g in GATES if g not in done]
    print("", flush=True)
    print("  🔧 **등록 %d · 실행 %d · 누락 %d**  %s"
          % (len(GATES), len(done), len(miss), "" if not miss else ("🚨 " + ",".join(miss))),
          flush=True)
    if miss:
        raise SystemExit("🚨 관문 누락 — 적었는데 «안 돌았다»: %r" % (miss,))

    gates_ok = okA and okB and okC and okF and okH and okI and okJ
    if not gates_ok:
        print("  ⏹ **관문 미통과 — 아래 수를 «안 읽는다»**", flush=True)

    print("", flush=True)
    print("## 판정 — 네 통계 · 문턱 z = %.4f" % thr, flush=True)
    res = {"thr": thr, "pctl": PCTL, "nperm": NPERM, "nfit": nfit, "fake_over": over,
           "F_k": k_exc, "F_trip": F_TRIP, "F_exc": exc, "F_pos": pos,
           "gates": {"A": okA, "B": okB, "C": okC, "F": okF, "H": okH, "I": okI, "J": okJ}}
    for tag in ("20", "30"):
        for lab in ("A", "B"):
            k = lab + tag
            nj = (tag, lab) in NO_JUDGE
            print("  +%s 자 %s — 관측 **%+.4f%%p/날** · **z = %.4f**  → %s"
                  % (tag, lab, obs[k], zs[k],
                     "🔴 **«판정 안 함»**(선언)" if nj
                     else ("✅ **넘음**" if zs[k] > thr else "❌ **못 넘음**")), flush=True)
            res[k] = {"obs": obs[k], "z": zs[k], "no_judge": nj, "over": bool(zs[k] > thr)}
    jz = [zs[lab + tag] for tag in ("20", "30") for lab in ("A", "B")
          if (tag, lab) not in NO_JUDGE]
    verdict = ("자격 얻음" if max(jz) > thr else "자격 못 얻음")
    if not gates_ok:
        verdict = "🚨 관문 미통과 — 위 수를 «안» 읽는다"
    print("  max(판정 대상 %d칸) = **%.4f** vs 문턱 **%.4f**  →  **%s**"
          % (len(jz), max(jz), thr, verdict), flush=True)
    res["verdict"] = verdict

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("", flush=True)
    print("저장: %s" % OUT.name, flush=True)
    print("🔴 **자 B 두 칸은 «판정 안 함»이다 — 「돈이 됐나」는 이 판이 «못 잰다».**", flush=True)
    print("⛔ 뒤 구간(2012~)은 «열지 않았다».", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
