# -*- coding: utf-8 -*-
"""86 — **추첨운 · 꼬리 · 칸 수**. 사전등록 `tasks/86-slots-and-tails.md` (`03c1963a`)

🚨 58번이 이미 자료 축에서 「칸을 늘려 더 번다」를 **전부 0 포함**으로 닫았다.
   **86번은 그걸 다시 안 잰다.** 새로 묻는 것은 ①분포 폭 ②**상위 30 승자 체결률**
   ③무작위 대신 «규칙»으로 고르기.
🚨 「최적 칸 수는 N」이라고 «쓰지 않는다». 적을 수 있는 것은 곡선의 모양뿐이다.

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/86-slots-and-tails.py [--quick]
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import slot_sim_lots as sl                                    # noqa: E402

_s = _u.spec_from_file_location("r85", HERE / "85-entry-predictors.py")
r85 = _u.module_from_spec(_s)
_s.loader.exec_module(r85)
r84, r83, r74, r41 = r85.r84, r85.r83, r85.r84.r74, r85.r84.r41

OUT = ROOT / ".cache" / "bt5y" / "out"
COST, RISK = r74.COST, r74.RISK
N_SEED = 200
SLOTS_GRID = (3, 4, 5, 6, 8, 10, 12, 16, 20)
START = "2026-03-16"          # 2026-03-15(일) 다음 거래일
TIE = ("prior6m", "hi52", "logpx", "base_depth")   # (b) 와 대조군 셋


def run(ev, slots, n_seed, order_fn=None, cap=None):
    cap = cap if cap is not None else 1.0 / slots
    with r41.Cost(*COST):
        return [sl.sim_lots(ev, seed=s, slots=slots, risk=RISK, cap=cap,
                            reserve=False, fill_rule="truncate",
                            cash_rule="per_slot", order_fn=order_fn)
                for s in range(n_seed)]


def fills_of(rs):
    c = Counter()
    for r in rs:
        for key, kind, _k, _d, _p, _a, _t in r["fill_log"]:
            if kind == "pilot":
                c[key] += 1
    return c


def summ(rs, n):
    eq = sorted(r["equity_pct"] for r in rs)
    return {"med": st.median(eq), "p5": eq[int(n * .05)], "p95": eq[int(n * .95)],
            "lo": eq[0], "hi": eq[-1], "width": eq[int(n * .95)] - eq[int(n * .05)],
            "mdd": st.median(r["mdd_pct"] for r in rs),
            "filled": st.median(r["n_filled"] for r in rs)}


def main() -> int:
    quick = "--quick" in sys.argv
    n_seed = 20 if quick else N_SEED
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    print("=" * 100, flush=True)
    print("86 — 추첨운 · 꼬리 · 칸 수 (사전등록 tasks/86 · 03c1963a)", flush=True)
    print("=" * 100, flush=True)
    by2, ev, blk, pmap = r84.load()
    key = lambda t: (t["scan_date"], t["code"], t["pattern"])
    gain = {key(t): r84.gain_of(t) for t in ev}
    top30 = {key(t) for t in sorted(ev, key=r84.gain_of, reverse=True)[:30]}
    print("진입 %d건 · seed %d" % (len(ev), n_seed), flush=True)

    # ── 관문 ① — order_fn=None 이면 기존과 «완전히» 같은가 ──────────────
    a = run(ev, 5, min(20, n_seed), order_fn=None, cap=r74.CAP)
    b = run(ev, 5, min(20, n_seed), order_fn=sl.order_key, cap=r74.CAP)
    w = max(abs(x["equity_pct"] - y["equity_pct"]) for x, y in zip(a, b))
    print("\n관문 ①  order_fn=None ≡ order_key  %.3e → **%s**"
          % (w, "통과" if w < 1e-12 else "🚨 미통과"), flush=True)
    if w >= 1e-12:
        return 3

    # ══ ㉮ 2026-03-15 에 «시작»했다면 ═══════════════════════════════════
    ev2 = [t for t in ev if t["entry_date"] >= START]
    bad = sum(1 for t in ev2 if t["entry_date"] < START)
    print("\n" + "=" * 100, flush=True)
    print("【㉮】 **2026-03-15(일)에 «계좌를 열었다»면**  🚨 서술 · 검정 아님", flush=True)
    print("=" * 100, flush=True)
    print("   관문 ③  진입일이 전부 ≥ %s 인가 — 위반 %d건 → **%s**"
          % (START, bad, "통과" if bad == 0 else "🚨 미통과"), flush=True)
    print("   그 뒤 진입 후보 **%d건** (전 구간 %d건의 %.1f%%) · 자료 끝 2026-08-21 = 약 5.4개월"
          % (len(ev2), len(ev), 100.0 * len(ev2) / len(ev)), flush=True)
    rs2 = run(ev2, 5, n_seed, cap=r74.CAP)
    s2 = summ(rs2, n_seed)
    eq2 = sorted(r["equity_pct"] for r in rs2)
    print("\n   %d판의 결과 — **중앙 %+.2f%%**" % (n_seed, s2["med"]), flush=True)
    print("     최저 %+.2f%% · 5%% %+.2f%% · 25%% %+.2f%% · 75%% %+.2f%% · 95%% %+.2f%% · 최고 %+.2f%%"
          % (s2["lo"], s2["p5"], eq2[int(n_seed * .25)], eq2[int(n_seed * .75)],
             s2["p95"], s2["hi"]), flush=True)
    print("     **돈을 잃은 판 %.1f%%** · 체결 중앙 **%d건** · MDD 중앙 %.1f%%"
          % (100.0 * sum(1 for x in eq2 if x < 0) / n_seed, s2["filled"], s2["mdd"]),
          flush=True)
    print("   🚨 보유 중앙이 20일이므로 5.4개월은 «여섯 차례» 남짓이다. n 이 작다.", flush=True)
    f2 = fills_of(rs2)
    tt = sorted(((gain[k], k) for k in f2 if f2[k] >= n_seed * 0.2), reverse=True)
    print("\n   자주 체결된 종목(200판 중 20%%↑) 상위/하위", flush=True)
    for g, k in tt[:4] + tt[-3:]:
        print("     %-6s %s  %+8.2f%%  (체결 %.0f%%)"
              % (k[1], k[0], g, 100.0 * f2[k] / n_seed), flush=True)

    # ══ ㉯㉱ 칸 수 격자 ═════════════════════════════════════════════════
    print("\n" + "=" * 100, flush=True)
    print("【㉯㉱】 **칸 수** — 「운이 주나」(seed 축) · 「꼬리를 놓치지 않게 되나」", flush=True)
    print("=" * 100, flush=True)
    print("   🚨 「더 버나」는 58번이 자료 축에서 이미 닫았다(전부 0 포함). 여기선 안 잰다.",
          flush=True)
    print("\n   %4s %7s %11s %11s %11s %9s %9s %11s"
          % ("칸", "체결", "자산중앙", "5% 하단", "95% 상단", "**폭**", "MDD", "상위30체결"),
          flush=True)
    print("   " + "-" * 84, flush=True)
    G = {}
    for k in SLOTS_GRID:
        rs = run(ev, k, n_seed)
        s = summ(rs, n_seed)
        f = fills_of(rs)
        s["top30"] = 100.0 * sum(f.get(x, 0) for x in top30) / (n_seed * len(top30))
        s["all"] = 100.0 * sum(f.values()) / (n_seed * len(ev))
        G[k] = s
        print("   %4d %7d %+10.2f%% %+10.2f%% %+10.2f%% %8.1f %8.1f%% %10.1f%%"
              % (k, s["filled"], s["med"], s["p5"], s["p95"], s["width"], s["mdd"],
                 s["top30"]), flush=True)
    print("\n   관문 ⑤ 양성 대조 — 칸을 늘리면 체결이 «실제로» 느는가: %d → %d 건 → **%s**"
          % (G[SLOTS_GRID[0]]["filled"], G[SLOTS_GRID[-1]]["filled"],
             "통과" if G[SLOTS_GRID[-1]]["filled"] > G[SLOTS_GRID[0]]["filled"] else "🚨 미통과"),
          flush=True)
    w0, w1 = G[SLOTS_GRID[0]]["width"], G[SLOTS_GRID[-1]]["width"]
    print("   ① 폭   %.1f → %.1f  (**%.0f%% 감소**)  · 단조인가: **%s**"
          % (w0, w1, 100.0 * (1 - w1 / w0),
             "예" if all(G[SLOTS_GRID[i]]["width"] > G[SLOTS_GRID[i + 1]]["width"]
                         for i in range(len(SLOTS_GRID) - 1)) else "아니오"), flush=True)
    print("   ② 하단 %+.2f%% → %+.2f%%   ·   ③ 상위30 체결률 %.1f%% → **%.1f%%** (전체 %.1f%% → %.1f%%)"
          % (G[SLOTS_GRID[0]]["p5"], G[SLOTS_GRID[-1]]["p5"], G[SLOTS_GRID[0]]["top30"],
             G[SLOTS_GRID[-1]]["top30"], G[SLOTS_GRID[0]]["all"], G[SLOTS_GRID[-1]]["all"]),
          flush=True)

    # ══ ㉰ 꼬리 30건은 어떻게 생겼나 (서술) ═════════════════════════════
    print("\n" + "=" * 100, flush=True)
    print("【㉰】 **꼬리 30건의 «모양»**  🚨 서술 — 새 검정 «안» 한다(85번이 이미 했다)",
          flush=True)
    print("=" * 100, flush=True)
    rows, _miss = r85.build_features(ev, pmap)
    tops = [rows[k] for k in top30 if k in rows]
    rest = [rows[k] for k in rows if k not in top30]
    print("\n   %-11s %13s %13s %s" % ("특징", "꼬리 30건", "나머지", "배수/차"), flush=True)
    print("   " + "-" * 62, flush=True)
    for f in r85.FEATS:
        if f in r85.CAT:
            ca = Counter(x[f] for x in tops).most_common(1)[0]
            cb = Counter(x[f] for x in rest)
            n_b = 100.0 * cb.get(ca[0], 0) / len(rest)
            print("   %-11s %12.0f%% %12.1f%% %s (%s)"
                  % (f, 100.0 * ca[1] / len(tops), n_b, "%.1f배" % (100.0 * ca[1] / len(tops) / max(n_b, 1e-9)),
                     ca[0]), flush=True)
            continue
        a_ = st.median(x[f] for x in tops if not r85._nan(x[f]))
        b_ = st.median(x[f] for x in rest if not r85._nan(x[f]))
        print("   %-11s %13.3f %13.3f %+13.3f" % (f, a_, b_, a_ - b_), flush=True)
    hold = []
    for k in top30:
        t = next(x for x in ev if key(x) == k)
        p = pmap[k]
        i0 = p["d"].index(t["entry_date"])
        i1 = p["d"].index(t["masks"][()]["exits"][-1][0])
        hold.append(i1 - i0 + 1)
    print("\n   보유 — 꼬리 중앙 **%d거래일** vs 전체 중앙 %d거래일"
          % (st.median(hold), st.median(
              [pmap[key(t)]["d"].index(t["masks"][()]["exits"][-1][0])
               - pmap[key(t)]["d"].index(t["entry_date"]) + 1 for t in ev])), flush=True)
    yr = Counter(next(x for x in ev if key(x) == k)["entry_date"][:4] for k in top30)
    print("   연도 — %s" % dict(sorted(yr.items())), flush=True)
    print("   🚨 판정은 85번을 가리킨다: 「더블 예측」은 문턱을 넘지만 **동어반복**이고 "
          "**거래당 돈으로는 꼴찌**다.", flush=True)

    # ══ ㉱ 무작위 대신 «규칙»으로 고르기 ════════════════════════════════
    print("\n" + "=" * 100, flush=True)
    print("【㉱】 **무작위 대신 «규칙»으로 고르기** — (b) prior6m vs (c) 대조군 셋", flush=True)
    print("=" * 100, flush=True)
    ins = [(rows[key(t)], 0) for t in ev if t["entry_date"] < r85.SPLIT and key(t) in rows]
    cuts = {}
    for f in TIE:
        xs = sorted(r[f] for r, _y in ins if not r85._nan(r[f]))
        cuts[f] = xs[int(len(xs) / 5)]              # 1분위 경계 (표본 «안»에서)

    def mk(f, hi_first):
        c = cuts[f]
        def fn(seed, t):
            r = rows.get(key(t))
            v = None if r is None else r[f]
            if v is None or r85._nan(v):
                rank = 1
            else:
                rank = 0 if ((v >= c) if hi_first else (v < c)) else 1
            return (rank, sl.order_key(seed, t))
        return fn

    base = run(ev, 5, n_seed, cap=r74.CAP)
    beq = [r["equity_pct"] for r in base]
    print("\n   %-22s %11s %11s %11s %s"
          % ("고르는 규칙", "자산중앙", "짝 중앙", "이기는 판", "순서 바뀐 체결"), flush=True)
    print("   " + "-" * 76, flush=True)
    print("   %-22s %+10.2f%% %11s %11s %s"
          % ("(a) 무작위 — 기준선", st.median(beq), "—", "—", "—"), flush=True)
    R = {}
    for f in TIE:
        rs = run(ev, 5, n_seed, order_fn=mk(f, hi_first=False), cap=r74.CAP)
        eq = [r["equity_pct"] for r in rs]
        pr = sorted(((1 + x / 100) / (1 + y / 100) - 1) * 100 for x, y in zip(eq, beq))
        pw = 100.0 * sum(1 for x in pr if x > 0) / len(pr)
        fa, fb = fills_of(base), fills_of(rs)
        chg = sum(abs(fb.get(k, 0) - fa.get(k, 0)) for k in set(fa) | set(fb))
        R[f] = {"med": st.median(eq), "pair": pr[len(pr) // 2], "win": pw, "chg": chg}
        tag = " ★(b)" if f == "prior6m" else "  (c)"
        print("   %-22s %+10.2f%% %+10.2f%% %10.1f%% %10d"
              % (tag + " " + f + " 1분위 먼저", R[f]["med"], R[f]["pair"], pw, chg), flush=True)
    print("\n   관문 ④ 양성 대조 — 규칙이 «실제로» 순서를 바꾸는가: 바뀐 체결 %d건 → **%s**"
          % (R["prior6m"]["chg"], "통과" if R["prior6m"]["chg"] > 0 else "🚨 미통과"), flush=True)
    okP = R["prior6m"]["pair"] > 0 and R["prior6m"]["win"] > 50
    okN = all(R["prior6m"]["pair"] > R[f]["pair"] for f in TIE if f != "prior6m")
    print("   **P★** 짝 중앙 %+.2f%% · 이기는 판 %.1f%% → **%s**"
          % (R["prior6m"]["pair"], R["prior6m"]["win"], "통과" if okP else "미통과"), flush=True)
    print("   **N★** (b) 가 대조군 셋을 «전부» 넘는가 → **%s**  (대조군 짝 중앙 %s)"
          % ("통과" if okN else "미통과",
             " · ".join("%s %+.2f%%" % (f, R[f]["pair"]) for f in TIE if f != "prior6m")),
          flush=True)
    print("\n   🚨 **prior6m 은 85번이 «같은 자료»에서 골랐다** — 표본 밖 검정이 «아니다».",
          flush=True)

    (OUT / "86-slots-and-tails.json").write_text(json.dumps(
        {"n_ev": len(ev), "start": START, "n_ev_start": len(ev2),
         "start_summ": s2, "grid": {str(k): v for k, v in G.items()},
         "tie": R, "okP": okP, "okN": okN, "n_seed": n_seed},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 86-slots-and-tails.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
