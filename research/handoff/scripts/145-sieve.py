# -*- coding: utf-8 -*-
r"""145 — 관문을 «떼고» 부호를 학습 «전체»에서 뽑는다. 사전등록 tasks/145-no-gate-sieve.md 그대로.

🚨 143 과 다른 것은 «한 줄»이다:
   143  부호를 학습 앞·뒤 절반에서 각각 뽑아 «같으면» 채택  →  살아남은 것만 씀
   145  부호를 학습 «전체»에서 한 번 뽑아  →  **여섯을 «전부» 쓴다**

   문턱  max(z_A, z_B) 순열분포의 **99.000 백분위**  (N=5 = {140·142-a·142-b·143·145})
   F★    자 A 혼자 넘는 비율이 **0.501% ~ 1.000%** 사이
   H★    🆕 **가짜 체 100개** — 4개 이상이 문턱을 넘으면 «못 잼»으로 닫고 결과를 «안 읽는다»
   ⛔ 뒤 구간(2012~) 안 연다

🚨 돌리는 중 아무것도 안 바꾼다.
   **단 «등록된 설계를 읽지 못하는» 구현 결함은 고친다** — 그건 설계 변경이 아니라 «집행»이다.

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/145-sieve.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import math
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

# 🚨 143 을 «그대로» 든다 — 특징·순위·부호통계·자 A/B·순열·적재를 새로 안 짠다
_s = _u.spec_from_file_location("r143", HERE / "143-sieve.py")
r143 = _u.module_from_spec(_s)
_s.loader.exec_module(r143)
r91 = r143.r91
import slot_sim_lots as sl                                       # noqa: E402

OUT = ROOT / "research" / "handoff" / "data" / "145-result.json"
SRC6 = ("atr_band", "gap", "m6", "m12", "hi12", "logtov")     # 겨룬 여섯 (acc 는 기여 불가)
NFAKE, FAKE_TRIP = 100, 4                    # H★ — 가짜 체 100개 · 방아쇠 «4개 이상»
ALPHA = 0.05 / 5                             # N=5 · 자 둘은 max 가 흡수 → 99.000 백분위
PCTL = 100.0 * (1.0 - ALPHA)
H_EXPECT = {20.0: 2003 * 0 or "2003-11-19", 30.0: "2003-11-26"}   # 143 과 같은 쪼갠 지점


def build(target, cut):
    """143 과 «같은» 적재·특징. 🚨 관문이 없으므로 학습을 «둘로» 안 쪼갠다."""
    rows = r143.load_rows(target)
    side = r143.Side({t["code"] for t in rows})
    byday = defaultdict(list)
    for t in rows:
        byday[t["entry_date"]].append({"r": t["r"], "f": r143.features(t, side), "t": t})
    alldays = sorted(byday)
    tr_days = [d for d in alldays if d < cut and len(byday[d]) >= 2]
    te_days = [d for d in alldays if d >= cut and len(byday[d]) >= 2]
    n_tr = sum(len(byday[d]) for d in alldays if d < cut)
    n_te = sum(len(byday[d]) for d in alldays if d >= cut)
    return byday, alldays, tr_days, te_days, n_tr, n_te


def zscore(x, lst):
    m = sum(lst) / len(lst)
    sd = math.sqrt(sum((v - m) ** 2 for v in lst) / (len(lst) - 1))
    return ((x - m) / sd if sd > 0 else 0.0), m, sd


def main() -> int:
    r143._guard()
    print("=" * 98, flush=True)
    print("145 — 관문을 «떼고» 부호를 학습 «전체»에서 뽑는다  ·  N = 5 (99.000 백분위)", flush=True)
    print("🚨 143 과 다른 것은 «한 줄»뿐 · ⛔ 뒤 구간 «안 엶»", flush=True)
    print("=" * 98, flush=True)

    res = {"alpha": ALPHA, "pctl": PCTL, "n_fake": NFAKE, "trip": FAKE_TRIP}
    for target, cut in r143.CUT.items():
        print("", flush=True)
        print("=" * 98, flush=True)
        print("목표 **+%.0f%%** · 쪼갠 지점 %s" % (target, cut), flush=True)
        print("=" * 98, flush=True)
        byday, alldays, tr_days, te_days, n_tr, n_te = build(target, cut)

        # ── 관문 A★ B★ G★ ────────────────────────────────────────────
        gap = abs(n_tr - n_te) / max(1.0, (n_tr + n_te) / 2.0) * 100.0
        gA = gap <= 5.0
        gB = not [d for d in alldays if d >= "2012-01-01"]
        print("", flush=True)
        print("## 관문", flush=True)
        print("  A* 학습/시험 후보 %d / %d · 어긋남 %.1f%%   %s"
              % (n_tr, n_te, gap, "**통과**" if gA else "🚨 **미통과**"), flush=True)
        print("  B* 뒤 구간 연도 %d건                       %s"
              % (0 if gB else 1, "**통과**" if gB else "🚨 **미통과**"), flush=True)
        print("  D* ⛔ **없다** — 관문을 뗐으므로 «해당 없음»(관문이 «줄었다»)", flush=True)
        live, dead = [], []
        for nm in r143.FEATURES:
            u = len({c["f"].get(nm) for d in tr_days for c in byday[d]
                     if c["f"].get(nm) is not None})
            (live if u >= 2 else dead).append(nm)
        print("  G* 특징 자격 — 겨룰 수 있는 것 **%d개** · 기여 불가 %d개 %s"
              % (len(live), len(dead), ("(%s)" % ",".join(dead)) if dead else ""), flush=True)
        if dead:
            print("     ⛔ 기여 불가는 「뺐다」가 «아니라» **「기여할 수 «없었다»」** — 상수라 순위가 «전부 0.5»",
                  flush=True)
        use = [f for f in SRC6 if f in live]

        # ── 🆕 G★ «한 층 아래» 틈 (검증 세션 조건 ①) — 묘사 · 판정 아님 ──
        #    G★ 은 «전역» 서로 다른 값을 보는데 점수는 «그날 안» 순위다.
        #    전역으로 4개여도 «그날» 후보가 다 같은 값이면 그 날 기여는 0 이다.
        print("     🆕 «그날 안 순위가 모두 같은 날»의 비율  (묘사 — 「G* 통과 = 기여함」이 «아님»)",
              flush=True)
        flat = {}
        for nm in use:
            key = (lambda n: (lambda c: c["f"].get(n)))(nm)
            z = 0
            for d in te_days:
                rk = r143.rank_within([key(c) for c in byday[d]])
                if max(rk) - min(rk) < 1e-12:
                    z += 1
            flat[nm] = 100.0 * z / len(te_days)
            print("        %-9s %5.1f%%  (시험 %d일 중 %d일)" % (nm, flat[nm], len(te_days), z),
                  flush=True)

        # ── 부호 — 🚨 학습 «전체»에서 «한 번». 여섯을 «전부» 쓴다 ────────
        print("", flush=True)
        print("## 부호 — 학습 «전체»에서 한 번 (관문 «없음» → 여섯을 «전부» 쓴다)", flush=True)
        signs, detail = {}, []
        for nm in use:
            key = (lambda n: (lambda c: c["f"].get(n)))(nm)
            s = r143.stat_of(tr_days, byday, r143.day_ranks(tr_days, byday, key))
            signs[nm] = 1.0 if s > 0 else -1.0
            detail.append((nm, s))
            print("  %-9s 학습 전체 %12.5f  →  **%+d**" % (nm, s, int(signs[nm])), flush=True)
        print("  → **쓰는 특징 %d개 «전부»** (143 은 1개·2개만 썼다)" % len(signs), flush=True)

        # ── 채점 · 자 A/B · 순열 ────────────────────────────────────
        sday, ev = r143.ref_fills(target)
        b_days = [d for d in te_days
                  if 1 <= min(sday.get(d, 0), len(byday[d])) < len(byday[d])]
        sc = r143.score_of(te_days, byday, signs)
        order = r143.order_by(te_days, byday, sc)
        A = r143.metric_A(te_days, byday, order)
        B = r143.metric_B(b_days, byday, order, sday)
        Abar, Bbar = sum(A) / len(A), (sum(B) / len(B)) if B else float("nan")

        print("", flush=True)
        print("## 순열 귀무 %d판 (씨앗 %d · 같은 날 «안» 순서만)"
              % (r143.NPERM, r143.PERM_SEED), flush=True)
        an, bn = r143.perm_null(te_days, b_days, byday, sday, r143.NPERM, r143.PERM_SEED)
        zA, mA, sA = zscore(Abar, an)
        zB, mB, sB = zscore(Bbar, bn)
        zan = [(x - mA) / sA if sA > 0 else 0.0 for x in an]
        zbn = [(x - mB) / sB if sB > 0 else 0.0 for x in bn]
        mx = [max(a, b) for a, b in zip(zan, zbn)]
        thr = r143.pct(mx, PCTL)

        # ── 관문 F★ ─────────────────────────────────────────────────
        exc = 100.0 * sum(1 for z in zan if z > thr) / len(zan)
        lo_f, hi_f = 100.0 * (1.0 - math.sqrt(1.0 - ALPHA)), 100.0 * ALPHA
        gF = lo_f <= exc <= hi_f
        zlo, zhi = 2.3263, 2.5750
        pos = (thr - zlo) / (zhi - zlo)
        print("  **max-T 문턱 z = %.4f**  (%.3f 백분위 · 문턱 위 %d판)"
              % (thr, PCTL, round(r143.NPERM * ALPHA)), flush=True)
        print("  F* 괄호 — 자 A 혼자 넘는 비율 **%.3f%%**  (있어야 할 곳 %.3f%% ~ %.3f%%)  %s"
              % (exc, lo_f, hi_f, "**통과**" if gF else "🚨 **미통과 — 구현이 틀렸다**"), flush=True)
        print("     F* 부속 «괄호 안 위치» = **%.3f**  (0 = 완전상관 쪽 · 1 = 독립 쪽)" % pos,
              flush=True)

        # ── 관문 C★ 커닝 시험 ────────────────────────────────────────
        sc_c = r143.score_of(te_days, byday, signs, extra={"_CHEAT": 1.0})
        Ac = sum(r143.metric_A(te_days, byday,
                               r143.order_by(te_days, byday, sc_c))) / len(te_days)
        gC = Ac > Abar
        print("  C* 커닝 시험 — 미래(r)를 넣으면 자 A 가 %+.4f → **%+.4f**  %s"
              % (Abar, Ac, "**통과**" if gC else "🚨 **미통과 — 죽은 코드**"), flush=True)
        print("  E* 순열 = 같은 날 «안» 순서만 · 재표집 «안» 씀            **통과**(구조상)", flush=True)

        # ── 🆕 관문 H★ — 가짜 체 100개 ────────────────────────────────
        print("", flush=True)
        print("## H* 가짜 체 **%d개** (뒤섞은 특징 여섯 · 같은 자·같은 문턱)" % NFAKE, flush=True)
        rnd = random.Random(r143.PERM_SEED)
        cells = [c for d in te_days for c in byday[d]] + \
                [c for d in tr_days for c in byday[d]]
        fz, over = [], 0
        for j in range(NFAKE):
            fsign = {}
            for nm in use:
                tag = "_F%d_%s" % (j, nm)
                pool = [c["f"].get(nm) for c in cells]
                rnd.shuffle(pool)
                for c, v in zip(cells, pool):
                    c[tag] = v
                key = (lambda g: (lambda c: c.get(g)))(tag)
                s = r143.stat_of(tr_days, byday, r143.day_ranks(tr_days, byday, key))
                fsign[tag] = 1.0 if s > 0 else -1.0
            # 🚨 가짜 «특징»을 그대로 쓰려면 score_of 가 c["f"] 를 보므로 직접 합산한다
            fsc = {d: [0.0] * len(byday[d]) for d in te_days}
            for tag, sg in fsign.items():
                rk = r143.day_ranks(te_days, byday, (lambda g: (lambda c: c.get(g)))(tag))
                for d in te_days:
                    for i, x in enumerate(rk[d]):
                        fsc[d][i] += sg * x
            fo = r143.order_by(te_days, byday, fsc)
            fA = sum(r143.metric_A(te_days, byday, fo)) / len(te_days)
            fB = r143.metric_B(b_days, byday, fo, sday)
            fB = sum(fB) / len(fB) if fB else 0.0
            zfa = (fA - mA) / sA if sA > 0 else 0.0
            zfb = (fB - mB) / sB if sB > 0 else 0.0
            m = max(zfa, zfb)
            fz.append(m)
            if m > thr:
                over += 1
            for c in cells:
                for tag in fsign:
                    c.pop(tag, None)
        exp_over = NFAKE * ALPHA
        print("  가짜 체 max z — 중앙 **%+.4f** · 평균 %+.4f · SD %.4f  (귀무 max 중앙 %+.4f)"
              % (st.median(fz), sum(fz) / len(fz),
                 st.pstdev(fz), st.median(mx)), flush=True)
        print("  문턱을 넘은 가짜 체 = **%d개** / %d   (기대 %.1f개 · 방아쇠 **>=%d**)"
              % (over, NFAKE, exp_over, FAKE_TRIP), flush=True)
        trip = over >= FAKE_TRIP
        print("  → %s" % ("🚨 **방아쇠 발동 — 이 판을 «못 잼»으로 닫고 결과를 «안 읽는다»**" if trip
                          else "**발동 안 함** — 결과를 읽어도 된다"), flush=True)

        gates_ok = gA and gB and gC and gF and (not trip)
        if trip:
            print("", flush=True)
            print("  ⏹ **못 잼 (H* 방아쇠)** — 아래 수를 «안 읽는다»", flush=True)
            res["t%d" % int(target)] = {"verdict": "못 잼 (H* 방아쇠)", "fake_over": over}
            del byday
            continue

        # ── 네 칸 표 (143 것 «그대로») ────────────────────────────────
        okA, okB = zA > thr, zB > thr
        print("", flush=True)
        print("## 네 칸 표 (143 것 «그대로»)", flush=True)
        print("  자 A  분모 **%d일**  ·  관측 **%+.4f%%p/날**  ·  **z = %.4f**  → %s"
              % (len(te_days), Abar, zA, "**넘음**" if okA else "**못 넘음**"), flush=True)
        print("  자 B  분모 **%d일**  ·  관측 **%+.4f%%p/날**  ·  **z = %.4f**  → %s"
              % (len(b_days), Bbar, zB, "**넘음**" if okB else "**못 넘음**"), flush=True)
        print("  max(z_A, z_B) = **%.4f**  vs  문턱 **%.4f**  →  %s"
              % (max(zA, zB), thr,
                 "✅ **자격 얻음**" if max(zA, zB) > thr else "❌ **자격 못 얻음**"), flush=True)
        cell = {(True, True): "✅ **고르는 능력이 있고 «돈으로도» 바뀐다** — 가장 강한 결과",
                (True, False): "**「능력은 있는데 «고를 기회»가 없다」** → 처방이 «체»가 아니라 «자리»로. "
                               "🚨 B 는 훨씬 무디니 「돈이 안 된다」로 «못» 읽는다",
                (False, True): "🚨 **설명이 필요한 자리** — 능력을 못 보였는데 돈이 됐다? 잡음·결함부터 의심",
                (False, False): "**못 넘음.** 갈림표로 읽는다"}
        print("  → %s" % cell[(okA, okB)], flush=True)
        if okB and not okA and abs(target - 30.0) < 1e-9:
            print("  🚨 **단서(결과 «전»에 정해 둔 것)** — 「+30 B «만» 통과했다」면 그 통과는",
                  flush=True)
            print("     **«천장의 49% 이상인 효과만 보이는» 칸에서 나온 것이다** (천장/MDE 2.03 배)",
                  flush=True)

        # ── 동반 지표 · 묘사 ────────────────────────────────────────
        srt = sorted(A, reverse=True)
        ntop = max(1, int(round(len(A) * 0.01)))
        A_not = srt[ntop:]
        print("", flush=True)
        print("## 동반 지표", flush=True)
        print("  ㉠ 중앙 **%+.4f%%p**  ·  ㉡ 「양(+)인 날」 비율 **%.1f%%**"
              % (st.median(A), 100.0 * sum(1 for x in A if x > 0) / len(A)), flush=True)
        print("  ㉢ 상위 1%%(%d날) 제거 후 평균 **%+.4f%%p**"
              % (ntop, sum(A_not) / len(A_not)), flush=True)
        print("     🚨 «기술»이지 «관문»이 아니다 — 죽음은 「상위 1%% 빼고 «유의하게 음»」일 때만", flush=True)
        nar = [a for d, a in zip(te_days, A) if sday.get(d, 0) >= 1]
        if nar:
            print("  ㉣ 좁힌 자 A (체결이 있던 날 %d일) 평균 **%+.4f%%p**  vs 전체 **%+.4f%%p**"
                  % (len(nar), sum(nar) / len(nar), Abar), flush=True)
        grp = defaultdict(list)
        for d, a in zip(te_days, A):
            k = len(byday[d])
            grp[2 if k == 2 else 3 if k <= 4 else 5].append(a)
        for g in sorted(grp):
            v = grp[g]
            print("  ㉤ k %s — 날 %4d · 평균 **%+.4f%%p**"
                  % ({2: "= 2  ", 3: "= 3~4", 5: ">= 5 "}[g], len(v), sum(v) / len(v)), flush=True)

        v = ("자격 얻음" if max(zA, zB) > thr else "자격 못 얻음")
        if not gates_ok:
            v = "🚨 관문 미통과 — 위 수를 «안» 읽는다"
        print("", flush=True)
        print("  ▶ **판정(+%.0f%%) : %s**" % (target, v), flush=True)
        res["t%d" % int(target)] = {
            "verdict": v, "signs": {k: int(s) for k, s in signs.items()},
            "Abar": Abar, "Bbar": Bbar, "zA": zA, "zB": zB, "thr": thr,
            "okA": okA, "okB": okB, "n_a": len(te_days), "n_b": len(b_days),
            "Fexc": exc, "Fpos": pos, "fake_over": over, "fake_med": st.median(fz),
            "median": st.median(A),
            "pos_rate": 100.0 * sum(1 for x in A if x > 0) / len(A),
            "A_ex1": sum(A_not) / len(A_not),
            "flat_pct": flat,
            "gates": {"A": gA, "B": gB, "C": gC, "F": gF, "H": not trip}}
        del byday, ev

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("", flush=True)
    print("저장: %s" % OUT.name, flush=True)
    print("⛔ 뒤 구간(2012~)은 «열지 않았다».", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
