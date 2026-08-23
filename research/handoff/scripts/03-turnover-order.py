# -*- coding: utf-8 -*-
"""03 — 거래대금 순서 (페이지 주장 5).

지시서: research/handoff/tasks/03-turnover-order.md (v2 + M10 + **M11 · M12**)

**M12 반영 — 1순위가 바뀌었다.**
  정렬 규칙은 **어떤 거래의 결과도 바꾸지 않는다.** 바뀌는 것은 "슬롯에 누가 들어가느냐"뿐이라
  유니버스 전체의 거래당 통계는 두 팔이 완전히 같고, 효과는 슬롯5 축에서만 나타난다.
  그런데 그 축의 구간이 ±100%p라 **그 설계로는 원리적으로 아무것도 못 잡는다.**
  → **1순위 = 후보 3개 이상인 날에서 거래대금 상위2 vs 무작위2(5a) · 상위2 vs 하위2(5b),
    하루 한 표.** 슬롯5는 **부차·강건성**으로 내리고 판정에 쓰지 않는다.

  · **M12-1** 5a("효과 없음")에는 **최대통계를 걸지 않는다** — 보정이 주장 쪽에 유리해진다.
    주 판정은 보정 없는 개별 구간. 5b("효과 있음")는 최대통계 유지(단일 대조라 개별과 같다).
  · **M12-2** 구간과 MDE를 **같은 통계·같은 단위**로. 1순위 통계 = **날 단위 짝차이의 평균(거래당 %p)**.
    **MDE = 2.80 × (블록 부트스트랩 차이 분포의 표준편차).**
  · **M12-3** MDE 는 문턱이 아니라 **보고 항목**이다. 뒤집힌 문턱의 최선 결과는
    "유지"가 아니라 **"확인 불가(검정력 부족)"**.

**M15 렌즈 정본 — 렌즈는 넷이고, 판정의 축은 렌즈가 아니라 1순위 통계의 95% 구간이다.**
  | | 렌즈 | 통과 조건 |
  |---|---|---|
  | L1 | 같은날 비교 | 부호검정 p<0.05 **그리고** 하루 차이 중앙의 CI 가 0 제외 |
  | L2′ | **연도 안정성(leave-one-year)** | 한 해씩 빼도 1순위 통계 부호 유지 |
  | L3 | 구간 5/5 | 다섯 구간 부호 일치 |
  | L4 | 집중도 | 상위 5일 제거 후 부호 유지 |

  **원형이동 순열(옛 L2)은 03a·03b 둘 다 폐기**했다 — `03a-circular-shift-check.py` 로 확인한 대로
  귀무 분포가 관측값 위에 중심을 두어(관측이 54.1 백분위, p≈0.46) **성공할 수 없는 검정**이었다.
  같은날 통계량은 회전에 **정확히 불변**이라 아예 정의되지 않는다.

**M14-1 판정표 (의미 크기 = 거래당 ±0.5%p)**
  · 0 제외(주장 방향) → 효과있음 유지 / 효과없음 폐기
  · 0 제외(반대 방향) → 양쪽 다 폐기
  · 0 포함 & 구간 전체가 ±0.5%p 안 → 효과있음 폐기 / 효과없음 유지(동등성)
  · 0 포함 & 구간이 ±0.5%p 밖 → **판정불가 / 확인 불가(검정력 부족)**
  **연도는 `entry_date` 기준. 2026 포함 판과 "2026 제외 5년" 판을 함께 낸다.**

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/03-turnover-order.py
난수 seed: 무작위2 추출 31000 · 블록 부트스트랩 30000 · 날 안 무작위화 31500 ·
           같은건수 대조 32000 · 슬롯 순서 seed 0(부가 0~4) · 짝비교 0~399(참고용)
"""
from __future__ import annotations

import json
import random
import statistics as st
import sys
from collections import defaultdict
from math import comb, erf, sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_BOOT = 1000
N_PERM = 1000
N_CTRL = 200
N_RAND2 = 200
N_PAIR = 400
N_LEVEL = 200
BOOT_SEED, RAND2_SEED, PERM_SEED, CTRL_SEED = 30000, 31000, 31500, 32000
BLOCK_MIN, BLOCK_MAX = 20, 40
SEED5 = (0, 1, 2, 3, 4)
MDE_K = 2.80                     # α=0.05 · 검정력 80% 양측 (M12-2)
BUCKETS = [(5, 10), (10, 20), (20, 50), (50, 100), (100, 300), (300, 1e18)]
SEGMENTS = [("2021", "2021", "2021"), ("2022", "2022", "2022"), ("2023", "2023", "2023"),
            ("2024", "2024", "2024"), ("2025~26", "2025", "2026")]
net = slot_sim.net

# 옛 L2(원형이동 순열)는 이 과제에서 폐기 — 03a-circular-shift-check.py 로 확인
L2_INFO = {"status": "해당없음(폐기)",
           "why": "원형이동 귀무 분포가 관측값 위에 중심을 둔다(관측이 54.1 백분위·p≈0.46) → "
                  "성공할 수 없는 검정. 같은날 통계량은 회전에 정확히 불변이라 정의되지 않는다.",
           "evidence": "03a-circular-shift-check.json",
           "replaced_by": "L2′ 연도 안정성(leave-one-year)"}


def load():
    ev, seen = [], set()
    for y in range(2021, 2027):
        d = json.loads((BT / ("bt_%d.json" % y)).read_text(encoding="utf-8"))
        for e in d["events"]:
            if e["result"] not in ("win", "loss"):
                continue
            k = (e["scan_date"], e["code"], e["pattern"])
            if k in seen:
                continue
            seen.add(k)
            ev.append({"code": e["code"], "pattern": e["pattern"],
                       "scan_date": e["scan_date"], "entry_date": e["entry_date"],
                       "resolve_date": e["resolve_date"],
                       "gain": e["gain_at_resolve_pct"], "result": e["result"],
                       "tv": e.get("turnover_eok") or 0.0,
                       "year": e["entry_date"][:4],   # M14-3: 연도는 entry_date 기준
                       "net": net(e["gain_at_resolve_pct"])})
    return ev


def _phi(z):
    return 0.5 * (1 + erf(z / sqrt(2)))


def sign_test(diffs):
    """부호검정(양측). n ≤ 100 이면 이항 정확, 크면 정규근사(연속성 보정)."""
    n = len(diffs)
    pos = sum(1 for x in diffs if x > 0)
    k = min(pos, n - pos)
    if n <= 100:
        p = min(1.0, 2 * sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n))
        how = "이항 정확"
    else:
        z = (abs(pos - n / 2) - 0.5) / (sqrt(n) / 2)
        p = min(1.0, 2 * (1 - _phi(z)))
        how = "정규근사(연속성 보정)"
    return {"n": n, "n_positive": pos, "mean": st.mean(diffs),
            "median": st.median(diffs), "p": p, "how": how}


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    n = len(s)
    return s[int(n * lo / 100)], s[int(n * hi / 100) - 1]


def make_blocks(rnd, n_pos):
    blocks, total = [], 0
    while total < n_pos:
        L = rnd.randint(BLOCK_MIN, BLOCK_MAX)
        a = rnd.randint(0, n_pos - L)
        LL = min(L, n_pos - total)
        blocks.append((a, LL))
        total += LL
    return blocks


def block_boot_daily(day_vals, pos_of_day, n_pos, seed):
    """날 단위 값의 블록 부트스트랩. 평균(1순위 통계)과 중앙값(L1용)을 함께 낸다."""
    by_pos = defaultdict(list)
    for d, v in day_vals.items():
        by_pos[pos_of_day[d]].append(v)
    rnd = random.Random(seed)
    means, medians = [], []
    for _ in range(N_BOOT):
        acc = []
        for a, L in make_blocks(rnd, n_pos):
            for j in range(L):
                acc.extend(by_pos.get(a + j, ()))
        if acc:
            means.append(st.mean(acc))
            medians.append(st.median(acc))
    return means, medians


EQUIV = 0.5      # M14-1 의미 크기 — 거래당 ±0.5%p


def verdict_m14(lo, hi, point, claim):
    """M14-1 판정표. claim = 'effect'(효과 있음) | 'none'(효과 없음)."""
    excl = lo > 0 or hi < 0
    if excl:
        # 주장 방향인가? 5a·5b 둘 다 '상위가 낫다'가 주장 방향(양수)
        if point > 0:
            return "폐기" if claim == "none" else "유지(나머지 렌즈 충족 시)"
        return "폐기(반대 방향)"
    if -EQUIV <= lo and hi <= EQUIV:
        return "유지(동등성 확인)" if claim == "none" else "폐기(동등성)"
    return "확인 불가(검정력 부족)" if claim == "none" else "판정불가(검정력 부족)"


# ── 슬롯5 (부차) ───────────────────────────────────────────────────────────
ORDERS = [("무작위", None),
          ("거래대금 내림차순", lambda t: -t["tv"]),
          ("거래대금 오름차순", lambda t: t["tv"])]


def boot_sim(by_pos, n_pos, seed, order=None, slots=5, cap=None):
    eq = 1.0
    held = []
    for p in range(n_pos):
        if held:
            for h in held:
                if not h[3] and h[0] < p:
                    eq += h[2] * net(h[1]["gain"]) / 100
                    h[3] = True
            held = [h for h in held if h[0] >= p]
        free = slots - len(held)
        if free > 0:
            c = by_pos.get(p)
            if c:
                if len(c) > 1:
                    c = sorted(c, key=lambda t: slot_sim.order_key(seed, t))
                    if order is not None:
                        c = sorted(c, key=order)
                if cap is not None:
                    c = c[:cap]
                wgt = eq / slots
                for t in c[:free]:
                    held.append([p + t["days"], t, wgt, False])
    for h in held:
        if not h[3]:
            eq += h[2] * net(h[1]["gain"]) / 100
    return (eq - 1) * 100


def bootstrap_orders(ev, pos_of, n_pos, seeds):
    idx = defaultdict(list)
    for t in ev:
        idx[pos_of[t["entry_date"]]].append(t)
    rnd = random.Random(BOOT_SEED)
    out = {name: [] for name, _ in ORDERS}
    for _ in range(N_BOOT):
        by_pos = defaultdict(list)
        off = 0
        for a, L in make_blocks(rnd, n_pos):
            for j in range(L):
                ts = idx.get(a + j)
                if ts:
                    by_pos[off + j].extend(ts)
            off += L
        for name, o in ORDERS:
            out[name].append(st.mean([boot_sim(by_pos, n_pos, s, o) for s in seeds]))
    return out


def summarize(rows):
    if not rows:
        return {"n": 0, "win_rate": None, "mean_net": None}
    return {"n": len(rows),
            "win_rate": sum(1 for r in rows if r["result"] == "win") / len(rows) * 100,
            "mean_net": st.mean([r["net"] for r in rows])}


def run_primary(ev, pos_of, n_pos, min_k):
    """같은날 짝비교 1순위. min_k = 그날 후보 최소 개수.

    M17-1: k=3 인 날은 상위2={1,2}·하위2={2,3} 로 **2위가 양쪽에 겹쳐** 차이가 절반이 된다.
    그래서 1순위는 **k >= 4**, k >= 3 판은 부가로 나란히 싣는다."""
    byday = defaultdict(list)
    for t in ev:
        byday[t["entry_date"]].append(t)
    daysK = {d: v for d, v in sorted(byday.items()) if len(v) >= min_k}
    print("\n★ 같은날 후보 %d개 이상인 날 %d일 (거래 %d건)%s"
          % (min_k, len(daysK), sum(len(v) for v in daysK.values()),
             "   ← 1순위 (M17-1)" if min_k >= 4 else "   ← 부가 (k=3 은 2위가 양쪽에 겹침)"),
          flush=True)

    rnd = random.Random(RAND2_SEED)
    d_tr, d_tb = {}, {}
    for d, v in daysK.items():
        s = sorted(v, key=lambda t: -t["tv"])
        mt = st.mean([x["net"] for x in s[:2]])
        mb = st.mean([x["net"] for x in s[-2:]])
        mr = st.mean([st.mean([x["net"] for x in rnd.sample(v, 2)])
                      for _ in range(N_RAND2)])
        d_tr[d] = mt - mr
        d_tb[d] = mt - mb

    pos_of_day = {d: pos_of[d] for d in daysK}
    out = {}
    for tag, dv, label in (("5a", d_tr, "상위2 vs 무작위2"),
                           ("5b", d_tb, "상위2 vs 하위2")):
        vals = list(dv.values())
        s = sign_test(vals)
        bmean, bmed = block_boot_daily(dv, pos_of_day, n_pos,
                                       BOOT_SEED + (0 if tag == "5a" else 1))
        lo, hi = ci(bmean)
        mlo, mhi = ci(bmed)
        sd = st.stdev(bmean)
        claim = "none" if tag == "5a" else "effect"
        s.update({"ci_lo": lo, "ci_hi": hi, "excludes_zero": bool(lo > 0 or hi < 0),
                  "median_ci_lo": mlo, "median_ci_hi": mhi,
                  "median_ci_excludes_zero": bool(mlo > 0 or mhi < 0),
                  "boot_sd": sd, "MDE": MDE_K * sd, "n_boot": len(bmean),
                  "within_equivalence": bool(-EQUIV <= lo and hi <= EQUIV),
                  "claim": claim, "verdict_axis": verdict_m14(lo, hi, s["mean"], claim)})
        # 2026 제외 5년 판 (M14-3)
        dv5 = {d: v for d, v in dv.items() if d[:4] != "2026"}
        b5m, _ = block_boot_daily(dv5, {d: pos_of_day[d] for d in dv5}, n_pos,
                                  BOOT_SEED + 10)
        l5_, h5_ = ci(b5m)
        s["excl_2026"] = {"n_days": len(dv5), "mean": st.mean(list(dv5.values())),
                          "ci_lo": l5_, "ci_hi": h5_,
                          "excludes_zero": bool(l5_ > 0 or h5_ < 0),
                          "MDE": MDE_K * st.stdev(b5m)}
        # 최악 연도 제거 (표준 검사)
        years = sorted({d[:4] for d in dv})
        dyr = {y: st.mean([v for d, v in dv.items() if d[:4] != y]) for y in years}
        worst = min(dyr, key=lambda y: dyr[y])
        s["drop_year"] = {"by_year": dyr, "worst_year": worst, "value": dyr[worst],
                          "sign_holds": dyr[worst] > 0}
        # 구간 5/5
        seg = {}
        for sn, y0, y1 in SEGMENTS:
            g = [v for d, v in dv.items() if y0 <= d[:4] <= y1]
            seg[sn] = {"n_days": len(g), "mean": st.mean(g) if g else None}
        s["segments"] = seg
        s["segment_signs"] = [1 if (seg[sn]["mean"] or 0) > 0 else -1
                              for sn, _, _ in SEGMENTS]
        out[tag] = s
        print("[%s k>=%d] %s — 날 %d · 양수 %d · **평균 %+.4f%%p** · 중앙 %+.4f%%p · 부호검정 p=%.4f (%s)"
              % (tag, min_k, label, s["n"], s["n_positive"], s["mean"], s["median"], s["p"],
                 s["how"]), flush=True)
        print("     블록 부트스트랩 %d회 · 평균 95%% 구간 %+.4f ~ %+.4f · **0 제외 %s** · "
              "SD %.4f · **MDE %.4f%%p**"
              % (s["n_boot"], lo, hi, "예" if s["excludes_zero"] else "아니오", sd,
                 s["MDE"]), flush=True)
        print("     중앙값 95%% 구간 %+.4f ~ %+.4f (0 제외 %s) · ±0.5%%p 안 %s · "
              "**M14-1 판정축: %s**"
              % (mlo, mhi, "예" if s["median_ci_excludes_zero"] else "아니오",
                 "예" if s["within_equivalence"] else "아니오", s["verdict_axis"]),
              flush=True)
        print("     2026 제외 5년: 날 %d · 평균 %+.4f%%p · 95%% %+.4f ~ %+.4f (0 제외 %s)"
              % (s["excl_2026"]["n_days"], s["excl_2026"]["mean"],
                 s["excl_2026"]["ci_lo"], s["excl_2026"]["ci_hi"],
                 "예" if s["excl_2026"]["excludes_zero"] else "아니오"), flush=True)
        print("     구간별 평균 %s (부호 %d/5) · 최악 연도 %s 제거 시 %+.4f%%p (부호 %s)"
              % ({k: (None if v["mean"] is None else round(v["mean"], 3))
                  for k, v in seg.items()},
                 sum(1 for x in s["segment_signs"] if x > 0), worst, dyr[worst],
                 "유지" if dyr[worst] > 0 else "뒤집힘"), flush=True)

    # L2(원형이동)는 폐기 — 03a-circular-shift-check.py 로 확인한 결과를 참조로만 싣는다.
    print("[L2] 원형이동 순열 폐기 — %s" % L2_INFO["why"], flush=True)

    # L4 집중도: 가설을 가장 크게 떠받치는 날 5일 제거
    for tag, dv in (("5a", d_tr), ("5b", d_tb)):
        srt = sorted(dv.items(), key=lambda kv: -kv[1])
        rest = [v for d, v in dv.items() if d not in {k for k, _ in srt[:5]}]
        # M19-2: 중앙값 통계에도 L4 를 건다(평균과 중앙값이 갈리면 꼬리가 두껍다는 신호).
        rest_neg = [v for d, v in dv.items() if d not in {k for k, _ in srt[-5:]}]
        out[tag]["drop_top5_days"] = {
            "mean_after": st.mean(rest), "sign_holds": st.mean(rest) > 0,
            "removed": [d for d, _ in srt[:5]],
            "median_full": st.median(list(dv.values())),
            "median_after_drop_top5": st.median(rest),
            "median_after_drop_bottom5": st.median(rest_neg),
            "median_sign_holds": st.median(rest) < 0}
        print("[L4 %s k>=%d] 상위 5일 제거 → 평균 %+.4f → %+.4f%%p (%s)"
              % (tag, min_k, out[tag]["mean"], st.mean(rest),
                 "부호 유지" if st.mean(rest) > 0 else "부호 뒤집힘"), flush=True)
        print("        (M19-2) 중앙값 %+.4f → 상위5일 제거 %+.4f · 하위5일 제거 %+.4f"
              % (out[tag]["drop_top5_days"]["median_full"],
                 out[tag]["drop_top5_days"]["median_after_drop_top5"],
                 out[tag]["drop_top5_days"]["median_after_drop_bottom5"]), flush=True)
    # ── 렌즈 넷 요약 (M15) ──
    for tag in ("5a", "5b"):
        s2 = out[tag]
        lens = {
            "L1_same_day": {"pass": bool(s2["p"] < 0.05 and s2["median_ci_excludes_zero"]),
                            "p": s2["p"], "median_ci": [s2["median_ci_lo"],
                                                        s2["median_ci_hi"]]},
            "L2p_year_stability": {"pass": bool(s2["drop_year"]["sign_holds"]),
                                   "worst_year": s2["drop_year"]["worst_year"],
                                   "value": s2["drop_year"]["value"]},
            "L3_segments": {"pass": all(x > 0 for x in s2["segment_signs"]),
                            "signs": s2["segment_signs"]},
            "L4_concentration": {"pass": bool(s2["drop_top5_days"]["sign_holds"]),
                                 "mean_after": s2["drop_top5_days"]["mean_after"]},
        }
        s2["lenses"] = lens
        s2["n_lenses_passed"] = sum(1 for v in lens.values() if v["pass"])
        print("[렌즈 %s k>=%d] L1 %s · L2′ %s · L3 %s · L4 %s → **%d/4** (판정축: %s)"
              % (tag, min_k, *["통과" if lens[k]["pass"] else "미통과"
                        for k in ("L1_same_day", "L2p_year_stability", "L3_segments",
                                  "L4_concentration")],
                 s2["n_lenses_passed"], s2["verdict_axis"]), flush=True)
    return out, daysK


def main():
    ev = load()
    cal = json.loads((BT / "regime_long.json").read_text(encoding="utf-8"))["dates"]
    lo_d = min(t["entry_date"] for t in ev)
    hi_d = max(t["resolve_date"] for t in ev)
    all_dates = [d for d in cal if lo_d <= d <= hi_d]
    pos_of = {d: i for i, d in enumerate(all_dates)}
    bad = [t for t in ev if t["entry_date"] not in pos_of or t["resolve_date"] not in pos_of]
    if bad:
        print("⚠ 달력에 없는 날짜 %d건 제외" % len(bad), flush=True)
        ev = [t for t in ev if t["entry_date"] in pos_of and t["resolve_date"] in pos_of]
    for t in ev:
        t["days"] = pos_of[t["resolve_date"]] - pos_of[t["entry_date"]]
    n_pos = len(all_dates)
    tvs = sorted(t["tv"] for t in ev)
    print("확정 %d건 · 거래대금 최소 %.2f억 · 중앙 %.2f억 · 최대 %.0f억 · 20억 미만 %d건"
          % (len(ev), tvs[0], tvs[len(tvs) // 2], tvs[-1], sum(1 for x in tvs if x < 20)),
          flush=True)
    print("달력 %d거래일 (%s ~ %s)" % (n_pos, all_dates[0], all_dates[-1]), flush=True)
    res = {"n": len(ev), "tv_min": tvs[0], "tv_median": tvs[len(tvs) // 2],
           "tv_max": tvs[-1], "n_below_20eok": sum(1 for x in tvs if x < 20),
           "n_calendar": n_pos, "mde_k": MDE_K}

    # ── 1순위(k>=4) + 부가(k>=3) ──
    res["primary_by_k"] = {}
    for min_k in (4, 3):
        out, daysK = run_primary(ev, pos_of, n_pos, min_k)
        res["primary_by_k"]["k>=%d" % min_k] = {
            "n_days": len(daysK),
            "n_trades": sum(len(v) for v in daysK.values()), **out}
    res["primary"] = res["primary_by_k"]["k>=4"]      # 1순위는 k>=4
    res["L2_substitute"] = L2_INFO
    res["equivalence_bound"] = EQUIV

    # ── 5b-4 거래대금 구간표 ──
    print("\n[5b-4] 거래대금 구간별", flush=True)
    buckets = {}
    years = sorted({t["year"] for t in ev})
    for lo2, hi2 in BUCKETS:
        name = ("%g~%g억" % (lo2, hi2)) if hi2 < 1e17 else "300억+"
        g = [t for t in ev if lo2 <= t["tv"] < hi2]
        s = summarize(g)
        s["segments"] = {sn: summarize([t for t in g if y0 <= t["year"] <= y1])
                         for sn, y0, y1 in SEGMENTS}
        vals = {y: (st.mean([t["net"] for t in g if t["year"] != y])
                    if [t for t in g if t["year"] != y] else None) for y in years}
        worst = min((y for y in vals if vals[y] is not None), key=lambda y: vals[y])
        s["drop_year"] = {"by_year": vals, "worst_year": worst, "value": vals[worst]}
        buckets[name] = s
        print("  %-10s n=%4d 승률 %5.1f%% 거래당 %+7.3f%% · 최악연도 %s 제거 %+7.3f%% · 구간별 %s"
              % (name, s["n"], s["win_rate"] or 0, s["mean_net"] or 0, worst,
                 vals[worst], {k: (v["n"], None if v["mean_net"] is None
                                   else round(v["mean_net"], 2))
                               for k, v in s["segments"].items()}), flush=True)
    res["buckets"] = buckets
    res["below20"] = summarize([t for t in ev if t["tv"] < 20])
    print("  ※ 20억 미만 합계 n=%d 승률 %.1f%% 거래당 %+.3f%% (페이지: 승률 26.9%%)"
          % (res["below20"]["n"], res["below20"]["win_rate"] or 0,
             res["below20"]["mean_net"] or 0), flush=True)

    # ── 부차: 슬롯5 (판정 미사용) ──
    print("\n[부차·판정 미사용] 슬롯5 세 정렬", flush=True)
    bands, paired = {}, {}
    for name, o in ORDERS:
        bands[name] = slot_sim.band(ev, n_runs=N_LEVEL, order=o)
        print("  %-14s 중앙 %+7.1f%% (5~95%% %+7.1f~%+7.1f) 체결 %.0f"
              % (name, bands[name]["median"], bands[name]["p5"], bands[name]["p95"],
                 bands[name]["n_filled"]), flush=True)
    for name, o in ORDERS[1:]:
        d = [slot_sim.sim(ev, seed=i, order=o)["equity_pct"]
             - slot_sim.sim(ev, seed=i, order=None)["equity_pct"] for i in range(N_PAIR)]
        paired[name] = {"win_pct": sum(1 for x in d if x > 0) / N_PAIR * 100,
                        "diff_median": st.median(d)}
        print("  (강건성 참고·문턱 없음) %-14s 무작위 대비 우세율 %.1f%% · 차이중앙 %+.1f%%p"
              % (name, paired[name]["win_pct"], paired[name]["diff_median"]), flush=True)
    print("  블록 부트스트랩 (복제 내 seed 고정) …", flush=True)
    b1 = bootstrap_orders(ev, pos_of, n_pos, seeds=(0,))
    print("  블록 부트스트랩 (복제당 seed 5개 평균) …", flush=True)
    b5 = bootstrap_orders(ev, pos_of, n_pos, seeds=SEED5)
    boot = {}
    for tag, bb in (("seed1", b1), ("seed5", b5)):
        boot[tag] = {}
        for name, _ in ORDERS[1:]:
            d = [bb[name][i] - bb["무작위"][i] for i in range(len(bb["무작위"]))]
            lo3, hi3 = ci(d)
            boot[tag][name] = {"diff_median": st.median(d), "ci_lo": lo3, "ci_hi": hi3,
                               "excludes_zero": bool(lo3 > 0 or hi3 < 0),
                               "boot_sd": st.stdev(d), "MDE": MDE_K * st.stdev(d)}
            print("  [%s] %-14s 차이 중앙 %+7.2f%%p · 95%% %+7.2f ~ %+7.2f · 0제외 %s · MDE %.2f%%p"
                  % (tag, name, st.median(d), lo3, hi3,
                     "예" if boot[tag][name]["excludes_zero"] else "아니오",
                     boot[tag][name]["MDE"]), flush=True)
    res["slot5"] = {"bands": bands, "paired_reference_only": paired, "bootstrap": boot}

    # ── 같은 건수 대조 (하루 2건만) ──
    print("\n[같은 건수 대조] 하루 2건만 사는 판 — 상위2 vs 무작위2", flush=True)
    idx = defaultdict(list)
    for t in ev:
        idx[pos_of[t["entry_date"]]].append(t)
    top_eq = [boot_sim(idx, n_pos, s, order=lambda t: -t["tv"], cap=2)
              for s in range(N_CTRL)]
    rand_eq = [boot_sim(idx, n_pos, s, order=None, cap=2) for s in range(N_CTRL)]
    dd = [top_eq[i] - rand_eq[i] for i in range(N_CTRL)]
    dl, dh = ci(dd)
    res["same_count_control"] = {
        "top2_median": st.median(top_eq), "rand2_median": st.median(rand_eq),
        "diff_median": st.median(dd), "diff_ci": [dl, dh],
        "excludes_zero": bool(dl > 0 or dh < 0)}
    print("  상위2만 중앙 %+.1f%% · 무작위2만 중앙 %+.1f%% · 차이 중앙 %+.1f%%p "
          "(5~95%% %+.1f~%+.1f) 0제외 %s"
          % (st.median(top_eq), st.median(rand_eq), st.median(dd), dl, dh,
             "예" if res["same_count_control"]["excludes_zero"] else "아니오"), flush=True)

    (OUT / "03-turnover-order.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/03-turnover-order.json")


if __name__ == "__main__":
    main()
