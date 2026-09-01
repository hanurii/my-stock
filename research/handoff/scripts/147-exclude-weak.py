# -*- coding: utf-8 -*-
r"""147 — 「빨리 손절될 것」을 «빼는» 팔. 사전등록 tasks/147-exclude-weak-fundamentals.md 그대로.

🚨 94 를 «그대로» 든다 — 후보 만들기 · roe 1분위 딱지 · 시뮬 규약을 새로 안 짠다.
   다른 것은 «한 줄»: 94 는 roe 1분위를 «먼저 담고»(우선순위),
                    147 은 roe 1분위를 **«아예 뺀다»**(배제).

  대조군  «현행»이 아니라 **「같은 수를 «무작위»로 뺀 팔」 4,000판**
  문턱    **99.375 백분위**  (N 「못 센다」 + 하한 8)
  주지표  ㉠ **빨리 손절 «비율»**(≤10 거래일 · «건수» 아님)  ·  ㉡ **세후 총액**
  ⛔ 유보 자료가 «없다» — 92·94 가 27.4년을 다 태웠다. 결과는 «개발 구간 결과»다

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/147-exclude-weak.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import math
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

# 🚨 94 를 그대로 든다 (94 가 92 를 m92 로 들고 있다)
_s = _u.spec_from_file_location("r94", HERE / "94-roe-realized.py")
r94 = _u.module_from_spec(_s)
_s.loader.exec_module(r94)
m92, r91, r41 = r94.m92, r94.r91, r94.r41
import slot_sim_lots as sl                                       # noqa: E402

OUT = ROOT / "research" / "handoff" / "data" / "147-result.json"
NPERM = 4000                 # §2 — 규약 ②(문턱 위 ≥25판) → 25/(0.05/8) = 4,000
ALPHA = 0.05 / 8             # N 「못 센다」 + 하한 8
PCTL = 100.0 * (1.0 - ALPHA)                       # 99.375
FAST_D = 10                  # ★ 주판정 — 손절이고 보유 ≤ 10 거래일
FAST_ALT = (6, 20)           # 견고성 «기술» — 🚨 판정을 «승격»시킬 수 없다
N_SEED_ARM = 200             # 배제 팔·현행 팔의 씨앗 수 (94 와 같은 규약)
# 🚨 ㉢ 을 «더하기 전» 실측(2026-09-01). 더한 뒤에도 «글자 그대로» 같아야 한다.
PRE_FIX = {"n_ev": 20708, "n_ex": 5313,
           "eq_ex": 113.62682887794125, "p_eq": 58.65,
           "fp_ex": 17.8793959299549, "p_fp": 1.775,
           "arms_hold": {"현행": 65.50182594096482, "배제": 75.09864001885833,
                         "무작위": 66.82004030922307}}


def _ord(d):
    return m92._ord(d)


def fast_stop(t, days=FAST_D):
    """★ 「빨리 손절」 = 손절로 끝났고 보유 ≤ days 거래일.
    🚨 «분위»로 정의하지 «않는다» — 분위는 자료가 정하므로 «사후»가 된다."""
    mk = t["masks"][()]
    ex = mk.get("exits") or []
    if not ex:
        return False
    last = max(e[0] for e in ex)
    # 손절인가 — 마지막 청산가가 진입가 «아래»
    lastpx = [e[2] for e in ex if e[0] == last][0]
    if lastpx >= t["entry_px"]:
        return False
    return (_ord(last) - _ord(t["entry_date"])) <= days


def measure(res, ev_by_key):
    """세 팔에서 «전부» 찍는다 — 94 항등식이 서는지 보려면 다섯이 다 필요하다."""
    keys = [k for k, kind, *_ in res["fill_log"] if kind == "pilot"]
    n = len(keys)
    if n == 0:
        return None
    hold, fast = [], {d: 0 for d in (FAST_D,) + FAST_ALT}
    for k in keys:
        t = ev_by_key.get(k)
        if t is None:
            continue
        mk = t["masks"][()]
        rd = mk.get("resolve_date") or t["entry_date"]
        hold.append(_ord(rd) - _ord(t["entry_date"]))
        for d in fast:
            if fast_stop(t, d):
                fast[d] += 1
    # ㉢ — 거래별 실현 수익(139 라벨식). «꼬리»를 재려면 «건별»이 있어야 한다
    rets = []
    for k in keys:
        tt = ev_by_key.get(k)
        if tt is None:
            continue
        mk = tt["masks"][()]
        ep = tt["entry_px"]
        rets.append(sum(sh * (px / ep * 100.0 - 100.0)
                        for _d, sh, px in (mk.get("exits") or [])))
    srt = sorted(rets, reverse=True)
    ntop = max(1, int(round(len(srt) * 0.01)))
    return {"n_buy": n, "hold_mean": st.mean(hold) if hold else 0.0,
            "ret_mean": st.mean(rets) if rets else 0.0,
            "ret_ex1": st.mean(srt[ntop:]) if len(srt) > ntop else 0.0,
            "ret_top1_share": (sum(srt[:ntop]) / sum(rets) * 100.0
                               if rets and sum(rets) != 0 else float("nan")),
            "slot_days": n * (st.mean(hold) if hold else 0.0),
            # 🚨 «비율»이다. «건수»가 아니다 (§3 급소)
            "fast_pct": {str(d): 100.0 * fast[d] / n for d in fast},
            "fast_n": {str(d): fast[d] for d in fast},
            "equity": res["equity_pct"], "mdd": res["mdd_pct"],
            "expo": res["expo_mean"]}


def main() -> int:
    print("=" * 104, flush=True)
    print("147 — 「빨리 손절될 것」을 «빼는» 팔  ·  문턱 **%.3f 백분위** (N 못 셈 · 하한 8)" % PCTL,
          flush=True)
    print("🚨 유보 자료 «없음» — 92·94 가 27.4년을 다 태웠다. 결과는 «개발 구간 결과»다", flush=True)
    print("🚨 주지표 ㉠ = 빨리 손절 **«비율»**(≤%d거래일) · ㉡ = 세후 총액" % FAST_D, flush=True)
    print("=" * 104, flush=True)

    fund = json.loads(m92.FUND.read_text(encoding="utf-8"))["by"]
    # 관문 C★ — 분위 «경계»는 92 의 «고르기 창»에서. 다시 «안» 만든다
    rowsP, _mi, _np = m92.build(tuple(range(1999, 2013)), *m92.PICK, fund)
    cuts, _nc, fq = m92.cells_for(rowsP, "roe")
    print("", flush=True)
    print("  C* 분위 경계는 «고르기 창(1999~2011)»의 것: %s"
          % " · ".join("%.4f" % c for c in cuts), flush=True)

    ev, tagged, miss = r94.build_events(fund, fq, 0)
    key_of = lambda t: (t["scan_date"], t["code"], t.get("pattern", ""))
    ev_by_key = {key_of(t): t for t in ev}
    print("  판정 창 %s ~ %s · 거래 **%s** · 그중 **roe 1분위 %s (%.1f%%)**"
          % (r94.D0, r94.D1, "{:,}".format(len(ev)), "{:,}".format(tagged),
             100.0 * tagged / len(ev)), flush=True)

    # ── §4 «먼저 확인» — 번역이 맞나 (느슨한 관문) ─────────────────────
    print("", flush=True)
    print("## §4 «먼저 확인» — 「roe 1분위가 «실제로» 빨리 손절되나」", flush=True)
    print("   🚨 이 관문은 **«느슨»하다** — 판정이 아니라 「돌릴 값이 있나」를 거른다.", flush=True)
    print("      틀리면 «돌릴 만한 판을 안 돌리는» 것이라, 99.375 가 아니라 **95% 구간**을 쓴다",
          flush=True)
    g1 = [t for t in ev if t["_roe1"]]
    g0 = [t for t in ev if not t["_roe1"]]
    for d in (FAST_D,) + FAST_ALT:
        a = sum(1 for t in g1 if fast_stop(t, d)) / max(1, len(g1))
        b = sum(1 for t in g0 if fast_stop(t, d)) / max(1, len(g0))
        se = math.sqrt(a * (1 - a) / max(1, len(g1)) + b * (1 - b) / max(1, len(g0)))
        lo, hi = (a - b) - 1.96 * se, (a - b) + 1.96 * se
        print("     ≤%2d거래일 — roe1 **%.2f%%** vs 나머지 **%.2f%%** · 차 **%+.2f%%p** "
              "[95%% %+.2f, %+.2f]%s"
              % (d, 100 * a, 100 * b, 100 * (a - b), 100 * lo, 100 * hi,
                 "   ★ **주판정 기준**" if d == FAST_D else ""), flush=True)
        if d == FAST_D:
            okG = lo > 0.0
    print("   → %s" % ("✅ **통과** — 관계가 «있고 방향이 맞다». 계속한다" if okG
                       else "🚨 **미통과 — 사용자님 물음에 «답하지 못한다». 시작하지 않는다**"),
          flush=True)
    if not okG:
        print("", flush=True)
        print("  ⏹ **시작하지 않는다**", flush=True)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps({"verdict": "§4 미통과 — 시작 안 함"},
                                  ensure_ascii=False, indent=1), encoding="utf-8")
        return 0

    # ── 세 팔 ────────────────────────────────────────────────────────
    n_ex = tagged                       # 배제하는 «수»
    print("", flush=True)
    print("## 세 팔 — 배제 %s건을 뺀다 (무작위 팔도 «같은 수»)" % "{:,}".format(n_ex), flush=True)

    ev_ex = [t for t in ev if not t["_roe1"]]
    okA = (len(ev) - len(ev_ex)) == n_ex
    print("  A* 후보 수 항등식 — %s − %s = %s  %s"
          % ("{:,}".format(len(ev)), "{:,}".format(n_ex), "{:,}".format(len(ev_ex)),
             "**통과**" if okA else "🚨 **미통과**"), flush=True)

    with r41.Cost(*r91.COST):
        cur = [sl.sim_lots(ev, seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                           reserve=False, fill_rule="truncate", cash_rule="per_slot")
               for s in range(N_SEED_ARM)]
        exc = [sl.sim_lots(ev_ex, seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                           reserve=False, fill_rule="truncate", cash_rule="per_slot")
               for s in range(N_SEED_ARM)]
        # 무작위 팔 — 139 의 「② 예측력 0 필터」 방식. «같은 수»를 무작위로 뺀다
        rnd = random.Random(147)
        rnd_arms = []
        for j in range(NPERM):
            sub = ev[:]
            rnd.shuffle(sub)
            sub = sub[n_ex:]
            rnd_arms.append(sl.sim_lots(sub, seed=j % N_SEED_ARM, slots=r91.SLOTS,
                                        risk=r91.RISK, cap=r91.CAP, reserve=False,
                                        fill_rule="truncate", cash_rule="per_slot"))
            if (j + 1) % 500 == 0:
                print("     무작위 %d/%d …" % (j + 1, NPERM), flush=True)

    # ── 관문 D★ 🚨 «완벽» 필터 (룩어헤드 · 집계에서 «뺀다») ─────────
    #    같은 수(n_ex)를 «최악»부터 뺀다 → 무작위를 «크게» 이겨야 한다.
    #    안 이기면 «자»가 고장난 것이고, 「문턱이 도달 가능한가」도 여기서 갈린다.
    def _ret(t):
        mk = t["masks"][()]
        ep = t["entry_px"]
        return sum(sh * (px / ep * 100.0 - 100.0)
                   for _d, sh, px in (mk.get("exits") or []))
    ev_perf = sorted(ev, key=_ret)[n_ex:]        # 최악 n_ex 개를 «뺀다»
    with r41.Cost(*r91.COST):
        prf = [sl.sim_lots(ev_perf, seed=s, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                           reserve=False, fill_rule="truncate", cash_rule="per_slot")
               for s in range(N_SEED_ARM)]

    m_cur = [measure(r, ev_by_key) for r in cur]
    m_exc = [measure(r, ev_by_key) for r in exc]
    m_rnd = [measure(r, ev_by_key) for r in rnd_arms]
    m_prf = [measure(r, ev_by_key) for r in prf]

    # ── 관문 E★ — 무작위 팔 «둘»끼리 ≈ 0 ─────────────────────────────
    h = NPERM // 2
    e1 = st.mean([m["equity"] for m in m_rnd[:h]])
    e2 = st.mean([m["equity"] for m in m_rnd[h:]])
    sd_r = st.stdev([m["equity"] for m in m_rnd])
    okE = abs(e1 - e2) < 0.2 * sd_r
    print("  E* 음성 — 무작위 팔 앞절반 %.2f%% vs 뒷절반 %.2f%% · 차 %.3f%%p (SD %.2f) %s"
          % (e1, e2, e1 - e2, sd_r, "**통과**" if okE else "🚨 **미통과**"), flush=True)

    # ── 판정 ────────────────────────────────────────────────────────
    def pctl_of(x, arr):
        return 100.0 * sum(1 for a in arr if a < x) / len(arr)

    eq_ex = st.mean([m["equity"] for m in m_exc])
    eq_rnd = [m["equity"] for m in m_rnd]
    p_eq = pctl_of(eq_ex, eq_rnd)
    fp_ex = st.mean([m["fast_pct"][str(FAST_D)] for m in m_exc])
    fp_rnd = [m["fast_pct"][str(FAST_D)] for m in m_rnd]
    p_fp = pctl_of(fp_ex, fp_rnd)

    # ── 🚨 ㉮㉯㉰ — 「문턱이 «도달 가능»했나」 (검증 세션 §3) ──────────
    srt_eq = sorted(eq_rnd)
    i = PCTL / 100.0 * (len(srt_eq) - 1)
    lo_i, hi_i = int(math.floor(i)), int(math.ceil(i))
    thr_eq = srt_eq[lo_i] if lo_i == hi_i else srt_eq[lo_i] + (srt_eq[hi_i] - srt_eq[lo_i]) * (i - lo_i)
    eq_prf = st.mean([m["equity"] for m in m_prf])
    okD = eq_prf > thr_eq
    print("", flush=True)
    print("## 🚨 문턱이 «도달 가능»했나 — D★ 완벽 필터로 «확인»", flush=True)
    print("  ㉮ 무작위 4,000판의 **실제** %.3f 백분위 값 = **%+.2f%%**  (순서통계량 · 정규 어림 아님)"
          % (PCTL, thr_eq), flush=True)
    print("     (참고) 정규 어림이면 %+.2f%% — 실제와 %+.2f%%p 차이"
          % (st.mean(eq_rnd) + 2.4977 * st.stdev(eq_rnd),
             st.mean(eq_rnd) + 2.4977 * st.stdev(eq_rnd) - thr_eq), flush=True)
    print("  ㉯ **D★ 완벽 필터**(같은 %s건을 «최악»부터 뺌 · 룩어헤드) = **%+.2f%%**"
          % ("{:,}".format(n_ex), eq_prf), flush=True)
    print("  ㉰ 대소 — D★ %s 문턱  →  %s"
          % (">" if okD else "<",
             "✅ **문턱이 «도달 가능»했다 → ㉡ 은 「이 자로는 «못 넘었다»」**" if okD
             else "🚨 **문턱이 «구조적으로» 도달 불가였다 → ㉡ 은 「«못 잼»」**"), flush=True)

    print("", flush=True)
    print("## 판정 — 무작위 %d판 대비 백분위 (문턱 %.3f)" % (NPERM, PCTL), flush=True)
    print("  ㉡ 세후 총액        배제 **%+.2f%%** · 무작위 중앙 %+.2f%% → **%.3f 백분위**  %s"
          % (eq_ex, st.median(eq_rnd), p_eq,
             "✅ **넘음**" if p_eq > PCTL else "❌ **못 넘음**"), flush=True)
    print("  ㉠ 빨리 손절 «비율»  배제 **%.3f%%** · 무작위 중앙 %.3f%% → **%.3f 백분위**  %s"
          % (fp_ex, st.median(fp_rnd), p_fp,
             "✅ **낮음(좋음)**" if p_fp < (100 - PCTL) else "❌ **못 낮춤**"), flush=True)
    okEq, okFp = p_eq > PCTL, p_fp < (100 - PCTL)
    cell = {(True, True): "✅ **둘 다 좋아짐 — 가장 강한 결과**",
            (True, False): "🚨 **손절은 그대로인데 돈이 늘었다 — 설명이 필요한 자리. 잡음·결함부터**",
            (False, True): "🔴 **「손절은 줄고 돈은 줄었다」 = 92 예측 그대로. «실패»**",
            (False, False): "**실패**"}
    print("  → %s" % cell[(okEq, okFp)], flush=True)

    # ── ㉢ 꼬리 — 상위 1% 를 빼면 사라지나 ──────────────────────────
    rx = st.mean([m["ret_ex1"] for m in m_exc])
    rr = [m["ret_ex1"] for m in m_rnd]
    p_rx = pctl_of(rx, rr)
    print("", flush=True)
    print("## ㉢ 꼬리 — **상위 1% 를 빼면 사라지나** (🚨 «기술»이지 «관문»이 아니다)", flush=True)
    print("  거래당 평균     배제 **%+.4f%%** · 무작위 중앙 %+.4f%%"
          % (st.mean([m["ret_mean"] for m in m_exc]),
             st.median([m["ret_mean"] for m in m_rnd])), flush=True)
    print("  **상위 1%% 제거** 배제 **%+.4f%%** · 무작위 중앙 %+.4f%% → **%.3f 백분위**"
          % (rx, st.median(rr), p_rx), flush=True)
    print("  상위 1%% 가 «이익의 몇 %%»  배제 **%.1f%%** · 무작위 중앙 **%.1f%%**"
          % (st.mean([m["ret_top1_share"] for m in m_exc]),
             st.median([m["ret_top1_share"] for m in m_rnd])), flush=True)
    print("     🚨 죽음은 「상위 1%% 빼고 «유의하게 음»」일 때만 — 그 밖엔 «기술»이다".replace("%%", "%"), flush=True)

    # ── ㉣ 회전 vs 선별 · 94 항등식 ─────────────────────────────────
    print("", flush=True)
    print("## ㉣ 회전 vs 선별 — 94 항등식(체결 × 평균보유 ≈ 일정)이 서나", flush=True)
    print("  %-10s %10s %10s %12s %10s %10s" %
          ("팔", "매수", "평균보유", "자리-일", "노출%", "빨리손절%"), flush=True)
    rows = {}
    for lab, ms in (("현행", m_cur), ("배제", m_exc), ("무작위", m_rnd)):
        n = st.mean([m["n_buy"] for m in ms]); hm = st.mean([m["hold_mean"] for m in ms])
        sd_ = st.mean([m["slot_days"] for m in ms]); ex_ = st.mean([m["expo"] for m in ms])
        fp = st.mean([m["fast_pct"][str(FAST_D)] for m in ms])
        rows[lab] = (n, hm, sd_, ex_, fp)
        print("  %-10s %10.1f %10.1f %12.0f %10.1f %10.3f" % (lab, n, hm, sd_, ex_, fp),
              flush=True)
    sdv = [rows[k][2] for k in rows]
    print("  → 자리-일 폭 **%.1f%%** (max/min−1) — %s"
          % (100 * (max(sdv) / min(sdv) - 1),
             "**노출이 맞았다**" if max(sdv) / min(sdv) < 1.05
             else "🚨 **깨졌다 — 비교가 «안 된다»**"), flush=True)

    print("", flush=True)
    print("## 견고성 (🚨 «기술»이고 판정을 «승격»시킬 수 «없다»)", flush=True)
    for d in FAST_ALT:
        a = st.mean([m["fast_pct"][str(d)] for m in m_exc])
        b = st.median([m["fast_pct"][str(d)] for m in m_rnd])
        print("     ≤%2d거래일 — 배제 %.3f%% · 무작위 중앙 %.3f%%" % (d, a, b), flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"pctl": PCTL, "nperm": NPERM, "n_ex": n_ex, "n_ev": len(ev),
         "eq_ex": eq_ex, "p_eq": p_eq, "fp_ex": fp_ex, "p_fp": p_fp,
         "okEq": okEq, "okFp": okFp, "gates": {"A": okA, "E": okE, "G4": okG},
         "thr_eq": thr_eq, "eq_perfect": eq_prf, "okD": okD,
         "ret_ex1": rx, "p_ret_ex1": p_rx,
         "ret_mean": st.mean([m["ret_mean"] for m in m_exc]),
         "top1_share": st.mean([m["ret_top1_share"] for m in m_exc]),
         "arms": {k: list(v) for k, v in rows.items()}},
        ensure_ascii=False, indent=1), encoding="utf-8")
    # ── 🔧 회귀 관문 — ㉢ 을 더했을 뿐인가 ──────────────────────────
    got = {"n_ev": len(ev), "n_ex": n_ex, "eq_ex": eq_ex, "p_eq": p_eq,
           "fp_ex": fp_ex, "p_fp": p_fp}
    bad = [(k, got[k], PRE_FIX[k]) for k in got
           if abs(got[k] - PRE_FIX[k]) > (1e-9 if isinstance(got[k], int) else 1e-9)]
    for lab, v in rows.items():
        if abs(v[1] - PRE_FIX["arms_hold"][lab]) > 1e-9:
            bad.append(("hold:" + lab, v[1], PRE_FIX["arms_hold"][lab]))
    print("", flush=True)
    print("  🔧 **회귀 관문** — ㉢ 을 «더했을 뿐»인가  %s"
          % ("**통과** (여섯 값 + 보유 셋이 «글자 그대로» 동일)" if not bad
             else "🚨 **미통과 — ㉢ 말고 «다른 게» 바뀌었다. 멈춘다**"), flush=True)
    for k, g, e in bad:
        print("     %-12s 지금 %r  vs  전 %r" % (k, g, e), flush=True)
    if bad:
        raise SystemExit("🚨 회귀 미통과 — 맞추지 말고 «왜»부터.")

    print("", flush=True)
    print("저장: %s" % OUT.name, flush=True)
    print("🚨 **유보가 «없다». 통과해도 「자격」이지 «확인»이 아니다.**", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
