# -*- coding: utf-8 -*-
r"""144 — 부호 안정 관문의 «눈금»을 잰다. 사전등록 tasks/144-gate-calibration.md 그대로.

🚨 이 판은 «계기 교정»이다. 판정판이 «아니다».
   자 A·B·순열·max-T·네 칸 표 — 하나도 안 쓴다. ⛔ 뒤 구간 안 연다.

  재는 것  「부호 안정 관문에 «아무 정보도 없는» 특징을 넣으면 몇 %가 통과하는가」
  R = 100  출처 = **겨룬 여섯**(acc 는 상수라 «죽은 특징»이므로 뺌 · 넣은 값도 나란히 찍음)
  관문     A* 같은 코드 · B* 143 R1~R5 회귀 · C* 쪼갠 지점 · D* 양성 대조 · E* 음성 대조

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/144-gate-calibration.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import math
import random
import sys
from collections import Counter, defaultdict
from math import comb
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

# 🚨 143 을 «그대로» 든다 — 특징·순위·부호 통계·적재를 새로 안 짠다
_s = _u.spec_from_file_location("r143", HERE / "143-sieve.py")
r143 = _u.module_from_spec(_s)
_s.loader.exec_module(r143)

OUT = ROOT / "research" / "handoff" / "data" / "144-gate-calibration.json"
NR = 100                                    # R 개수 (사전등록 §0)
SRC6 = ("atr_band", "gap", "m6", "m12", "hi12", "logtov")     # 겨룬 여섯
SRC7 = r143.FEATURES                                          # acc 포함 — 나란히 찍기용
# 143 이 실제로 낸 R1~R5 통과 목록 (관문 B*)
B_EXPECT = {20.0: {"R3", "R4", "R5"}, 30.0: {"R3"}}
# 143 의 쪼갠 지점 (관문 C*)
H_EXPECT = {20.0: "2000-11-15", 30.0: "2000-11-29"}


def _pge(k, n, p):
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def cp_upper(k, n, a=0.05):
    """Clopper-Pearson 95% 상한 — 「관측 k 개면 참값이 얼마까지일 수 있나」."""
    if k >= n:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(200):
        m = (lo + hi) / 2.0
        s = sum(comb(n, i) * m ** i * (1 - m) ** (n - i) for i in range(0, k + 1))
        if s > a:
            lo = m
        else:
            hi = m
    return lo


def build(target, cut):
    """143 과 «같은» 적재·특징·쪼개기. 새로 안 짠다."""
    rows = r143.load_rows(target)
    codes = {t["code"] for t in rows}
    side = r143.Side(codes)
    byday = defaultdict(list)
    for t in rows:
        byday[t["entry_date"]].append({"r": t["r"], "f": r143.features(t, side), "t": t})
    alldays = sorted(byday)
    tr_days = [d for d in alldays if d < cut and len(byday[d]) >= 2]
    n_tr = sum(len(byday[d]) for d in alldays if d < cut)
    # 학습을 «다시 둘로» — 143 과 «같은» 규칙(후보 수 절반)
    h_cut, run_n = None, 0
    for d in [x for x in alldays if x < cut]:
        run_n += len(byday[d])
        if run_n >= n_tr / 2.0:
            h_cut = d
            break
    h1 = [d for d in tr_days if d < h_cut]
    h2 = [d for d in tr_days if d >= h_cut]
    return byday, tr_days, h1, h2, h_cut, alldays


def passes(byday, h1, h2, key):
    """143 의 부호 안정 관문 «그대로»."""
    s1 = r143.stat_of(h1, byday, r143.day_ranks(h1, byday, key))
    s2 = r143.stat_of(h2, byday, r143.day_ranks(h2, byday, key))
    return ((s1 > 0) == (s2 > 0) and s1 != 0 and s2 != 0), s1, s2


def run_R(byday, tr_days, h1, h2, sources, n_r, seed):
    """🚨 143 의 R 블록과 «같은» 방식 — 학습 구간 «전체»에서 뒤섞기(반쪽 경계를 가로지름)."""
    rnd = random.Random(seed)
    cells = [c for d in tr_days for c in byday[d]]
    keep, by_src, names = 0, Counter(), []
    tot_src = Counter()
    for j in range(n_r):
        src = sources[j % len(sources)]
        tot_src[src] += 1
        pool = [c["f"].get(src) for c in cells]
        rnd.shuffle(pool)
        tag = "_R%d" % (j + 1)
        for c, v in zip(cells, pool):
            c[tag] = v
        ok, _s1, _s2 = passes(byday, h1, h2, (lambda g: (lambda c: c.get(g)))(tag))
        if ok:
            keep += 1
            by_src[src] += 1
            names.append("R%d" % (j + 1))
        for c in cells:
            del c[tag]
    return keep, by_src, tot_src, names


def main() -> int:
    r143._guard()
    print("=" * 98, flush=True)
    print("144 — 부호 안정 관문의 «눈금». **계기 교정판** (판정판 아님)", flush=True)
    print("🚨 자 A·B·순열·max-T·네 칸 표 «안 씀» · 뒤 구간 «안 엶» · N 안 늘림", flush=True)
    print("=" * 98, flush=True)

    # ── 발동선을 «먼저» 찍는다 (사전등록 §5) ───────────────────────────
    need30 = 0.0
    lo, hi = 1e-9, 1.0
    for _ in range(200):
        m = (lo + hi) / 2.0
        if _pge(2, 6, m) < 0.05:
            lo = m
        else:
            hi = m
    need30 = lo
    lo, hi = 1e-9, 1.0
    for _ in range(200):
        m = (lo + hi) / 2.0
        if _pge(1, 6, m) < 0.05:
            lo = m
        else:
            hi = m
    need20 = lo
    print("", flush=True)
    print("## 발동선 — **결과 보기 «전»에 찍는다**", flush=True)
    print("   필요선  +30 의 2/6 → 귀무 <= **%.3f%%**  ·  +20 의 1/6 → 귀무 <= **%.3f%%**"
          % (100 * need30, 100 * need20), flush=True)
    for k in (0, 1, 2, 3):
        u = 100 * cp_upper(k, NR)
        print("   k=%-2d → 95%% 상한 **%.2f%%**   %s"
              % (k, u, "✅ +30 각주 가능" if u <= 100 * need30 else "❌ 각주 불가"), flush=True)
    print("   ⛔ **+20 은 k=0 이어도 상한 %.2f%% 라 필요선 %.3f%% 를 «못 맞춤» — 어떤 R 값에서도 각주 불가**"
          % (100 * cp_upper(0, NR), 100 * need20), flush=True)
    print("   🚨 이 상한은 **«독립 가정»** 위의 값이다 — 실제 상한은 더 넓을 수 있고,"
          " 그러면 발동선은 **더 엄해져야** 한다", flush=True)

    res = {"n_r": NR, "need30": need30, "need20": need20,
           "cp_upper": {str(k): cp_upper(k, NR) for k in range(0, 5)}}
    for target, cut in r143.CUT.items():
        print("", flush=True)
        print("=" * 98, flush=True)
        print("목표 **+%.0f%%** · 쪼갠 지점 %s" % (target, cut), flush=True)
        print("=" * 98, flush=True)
        byday, tr_days, h1, h2, h_cut, alldays = build(target, cut)

        # ── 관문 C* ───────────────────────────────────────────────────
        gB2 = not [d for d in alldays if d >= "2012-01-01"]
        gC = (h_cut == H_EXPECT[target])
        print("  C* 쪼갠 지점 %s (143: %s)  %s   ·  뒤 구간 %d건"
              % (h_cut, H_EXPECT[target], "**통과**" if gC else "🚨 **미통과**",
                 0 if gB2 else 1), flush=True)

        # ── 관문 D* 양성 대조 · E* 음성 대조 ─────────────────────────
        for c in [x for d in tr_days for x in byday[d]]:
            c["_POS"] = c["r"]
        h1s = set(h1)
        for d in tr_days:
            sgn = 1.0 if d in h1s else -1.0
            for c in byday[d]:
                c["_NEG"] = sgn * c["r"]
        okD, d1, d2 = passes(byday, h1, h2, lambda c: c.get("_POS"))
        okE, e1, e2 = passes(byday, h1, h2, lambda c: c.get("_NEG"))
        print("  D* 양성 대조 (부호가 «일정») — 통과해야 함 → %s  (%.5f / %.5f)"
              % ("**통과**" if okD else "🚨 **미통과 — 코드 고장**", d1, d2), flush=True)
        print("  E* 음성 대조 (부호가 «반쪽마다 뒤집힘») — 탈락해야 함 → %s  (%.5f / %.5f)"
              % ("**통과**" if not okE else "🚨 **미통과 — 무조건 통과시키는 코드**", e1, e2),
              flush=True)

        # ── 본체: R = 100 ────────────────────────────────────────────
        keep6, bysrc6, tot6, names6 = run_R(byday, tr_days, h1, h2, SRC6, NR, r143.PERM_SEED)
        keep7, _b7, _t7, _n7 = run_R(byday, tr_days, h1, h2, SRC7, NR, r143.PERM_SEED)
        # 관문 B* — 143 의 R1~R5 재현 (출처 목록이 143 과 같은 순서인 앞 5개)
        got5 = {n for n in names6 if n in {"R1", "R2", "R3", "R4", "R5"}}
        gB = (got5 == B_EXPECT[target])
        print("  B* 회귀 — 143 의 R1~R5 통과 목록 %s (143: %s)  %s"
              % (sorted(got5) or "없음", sorted(B_EXPECT[target]),
                 "**통과**" if gB else "🚨 **미통과 — 맞추지 말고 «왜»부터**"), flush=True)

        # ── 🚨 주 읽기 = **특징별 «짝지음»** (검증 세션 ④) ─────────────
        #    「귀무 통과율 하나」는 존재하지 않는다 — 여섯 개의 «서로 다른» 귀무를
        #    17개씩 섞은 «혼합»이고, 섞는 비율은 «우리가 고른» 것이다.
        #    ⇒ 특징 j 는 «자기 자신의 귀무»와 붙어야 한다.
        print("", flush=True)
        print("  ▶▶ **주 읽기 — 특징별 «짝지음»**  (각 특징이 «자기 자신의 귀무»와 붙는다)",
              flush=True)
        print("     %-9s %-8s %-12s %-10s" % ("특징", "실제", "그 특징의 R", "R 통과율"), flush=True)
        rates = []
        for s in SRC6:
            ok, _a, _b = passes(byday, h1, h2,
                                (lambda n: (lambda c: c["f"].get(n)))(s))
            rt = 100.0 * bysrc6[s] / max(1, tot6[s])
            rates.append(rt)
            print("     %-9s %-8s %-12s %6.1f%%"
                  % (s, "**남음**" if ok else "버림",
                     "%d/%d" % (bysrc6[s], tot6[s]), rt), flush=True)
        print("     🚨 실제 쪽은 특징마다 **n=1** 이다 — 짝지음은 «묘사»이고 검정이 아니다",
              flush=True)

        # ── 보조: 묶은 값 + CI 를 «두 방식»으로 ──────────────────────
        u = 100 * cp_upper(keep6, NR)
        ci_bin = 100 * 1.96 * math.sqrt((keep6 / NR) * (1 - keep6 / NR) / NR)
        m6 = sum(rates) / len(rates)
        sd6 = math.sqrt(sum((x - m6) ** 2 for x in rates) / (len(rates) - 1))
        ci_src = 1.96 * sd6 / math.sqrt(len(rates))
        print("", flush=True)
        print("  ▶ **묶은 R 통과 %d / %d = %.1f%%**   (95%% 상한 **%.2f%%**)"
              % (keep6, NR, 100.0 * keep6 / NR, u), flush=True)
        print("     🚨 **이 값은 «여섯의 혼합»이고 섞는 비율(17:17:…)은 «우리가 정한» 것이다**",
              flush=True)
        print("     CI 두 방식 — ㉠ 이항 ±%.2f%%p   ·   ㉡ **출처 SD/√6 ±%.2f%%p** (출처 SD %.1f%%p)"
              % (ci_bin, ci_src, sd6), flush=True)
        print("        → ㉡/㉠ = **%.1f배**  %s"
              % (ci_src / ci_bin if ci_bin > 0 else float("nan"),
                 "🚨 **묶기가 못 쓰는 것 — n_eff 는 100 이 아니라 «6 쪽»**"
                 if ci_src > 1.5 * ci_bin else "묶기가 크게 어긋나진 않는다"), flush=True)
        print("     (참고) acc «포함» 일곱에서 뽑으면 %d / %d = %.1f%%  "
              "🚨 **이건 «다른 선택»이 아니라 «잘못된 귀무»다** — 상수는 「정보 없는 특징」이 아니라"
              " «변하지 않는 것»이라 귀무가 아니다"
              % (keep7, NR, 100.0 * keep7 / NR), flush=True)
        note = (keep6 <= 2 and abs(target - 30.0) < 1e-9)
        print("     → 각주 발동선(k<=2 · **+30 만** · +20 은 «어떤 값에서도» 불가): %s"
              % ("✅ **발동**" if note else "❌ **발동 안 함** — 판정은 「못 잼」 그대로"), flush=True)
        res["t%d" % int(target)] = {
            "keep6": keep6, "keep7": keep7, "rate6": 100.0 * keep6 / NR,
            "cp_upper": u, "by_src": dict(bysrc6), "tot_src": dict(tot6),
            "src_rates": rates, "ci_binom": ci_bin, "ci_src": ci_src, "src_sd": sd6,
            "h_cut": h_cut, "gB": gB, "gC": gC, "gD": okD, "gE": (not okE),
            "footnote": note}
        del byday, tr_days, h1, h2

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("", flush=True)
    print("저장: %s" % OUT.name, flush=True)
    print("🚨 **이 판은 「몇 %인가」를 셌을 뿐이다. 「진짜가 낫다/못하다」는 «주장 안 한다».**",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
