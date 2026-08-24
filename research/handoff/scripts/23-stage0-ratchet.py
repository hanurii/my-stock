# -*- coding: utf-8 -*-
"""23 · **0단계-A 산수 관문** + **0단계-B 검정력·상한**.

지시서 `research/handoff/tasks/23-ratchet-stop.md`

★ 경로 재생 관문 통과(3,776/3,776 정확 일치, `23-gate-path-identity.py`) 후에만 돌린다.
★ 같은 날 순서는 **고르지 않고 괄호로 묶는다** — `[보수적, 낙관적]`.
    보수적 = 기존 손절 먼저 → 그날은 트리거 발동 못 함
    낙관적 = 트리거 먼저 → 손절선이 올라간 채로 그날을 본다(목표 우선)
★ 청산가는 하네스 관례 그대로 **그날 종가**다(목표가·손절가가 아니다).
    → 두뇌 세션의 "이득 10.40%p · 비용 20%p"는 **S에서 청산된다는 가정**이다.
      아래는 **가정판(요청된 틀)**과 **실측판(종가 청산)**을 **둘 다** 낸다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/23-stage0-ratchet.py
난수 seed: 날짜 블록 부트스트랩 230000
"""
from __future__ import annotations

import json
import random
import statistics as st
from collections import defaultdict
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"

TARGET, STOP = 20.0, 10.0
TRIGGERS = [5.0, 8.0, 10.0, 15.0]
NEWSTOPS = [("본전(0%)", lambda t: 0.0), ("+3%", lambda t: 3.0),
            ("트리거의 절반", lambda t: t / 2.0)]
N_BOOT = 1000
DAY_SEED = 230000
BLOCK_MIN, BLOCK_MAX = 20, 40
MDE_K = 2.80
K = (1 - 0.002034) / (1 + 0.000034)


def net(g):
    return ((1 + g / 100) * K - 1) * 100


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def blocks(rnd, n, lo, hi):
    out, tot = [], 0
    while tot < n:
        L = rnd.randint(lo, hi)
        a = rnd.randint(0, n - L)
        LL = min(L, n - tot)
        out.append((a, LL))
        tot += LL
    return out


def base_replay(p):
    h, l, c = p["h_pct"], p["l_pct"], p["c_pct"]
    for i in range(len(h)):
        ht = h[i] is not None and h[i] >= TARGET
        hs = l[i] is not None and l[i] <= -STOP
        if ht and hs:
            return ("ambiguous", i, c[i])
        if ht:
            return ("win", i, c[i])
        if hs:
            return ("ambiguous" if i == 0 else "loss", i, c[i])
    return ("unresolved", len(h) - 1, c[-1])


def ratchet(p, trig, news, mode):
    """mode='pess' → 손절 먼저 · mode='opt' → 트리거 먼저(그 다음 목표, 그 다음 손절).
    반환: (result, exit_idx, gain_close, armed_idx or None, ambiguous_days)"""
    h, l, c = p["h_pct"], p["l_pct"], p["c_pct"]
    armed = False
    armed_i = None
    amb = 0
    for i in range(len(h)):
        hi_, lo_ = h[i], l[i]
        ht = hi_ is not None and hi_ >= TARGET
        htr = hi_ is not None and hi_ >= trig
        lvl = news if armed else -STOP
        hs = lo_ is not None and lo_ <= lvl
        if mode == "pess":
            # 1) 기존(또는 이미 올라간) 손절선 먼저
            if hs and ht:
                amb += 1
                return ("ambiguous", i, c[i], armed_i, amb)
            if hs:
                return ("ambiguous" if (i == 0 and not armed) else "loss",
                        i, c[i], armed_i, amb)
            if ht:
                return ("win", i, c[i], armed_i, amb)
            # 2) 하루가 끝난 뒤에 발동
            if htr and not armed:
                # 같은 날 트리거와 (올라갈 손절선) 둘 다 걸리면 순서 모호
                if lo_ is not None and lo_ <= news:
                    amb += 1
                armed, armed_i = True, i
        else:  # opt — 트리거 먼저
            if htr and not armed:
                if lo_ is not None and lo_ <= news:
                    amb += 1
                armed, armed_i = True, i
                lvl = news
                hs = lo_ is not None and lo_ <= lvl
            if ht:
                if hs:
                    amb += 1
                return ("win", i, c[i], armed_i, amb)
            if hs:
                return ("ambiguous" if (i == 0 and not armed) else "loss",
                        i, c[i], armed_i, amb)
    return ("unresolved", len(h) - 1, c[-1], armed_i, amb)


def main():
    paths = {}
    for y in range(2021, 2027):
        d = json.loads((OUT / ("paths_%d.json" % y)).read_text(encoding="utf-8"))
        for p in d["paths"]:
            paths[(p["scan_date"], p["code"], p["pattern"])] = p
    ev, seen = [], set()
    for y in range(2021, 2027):
        d = json.loads((BT / ("bt_%d.json" % y)).read_text(encoding="utf-8"))
        for e in d["events"]:
            k = (e["scan_date"], e["code"], e["pattern"])
            if k in seen:
                continue
            seen.add(k)
            ev.append(e)
    P = [paths[(e["scan_date"], e["code"], e["pattern"])] for e in ev]
    for p, e in zip(P, ev):
        p["_entry_date"] = e["entry_date"]
    n = len(P)
    base = [base_replay(p) for p in P]
    base_net = [net(b[2]) for b in base]
    print("경로 %d건 · 기준선 재생 완료" % n, flush=True)
    from collections import Counter
    print("기준선 결과 분포: %s" % dict(Counter(b[0] for b in base)), flush=True)
    res = {"n": n, "base_dist": dict(Counter(b[0] for b in base)),
           "base_per_trade": st.mean(base_net)}
    print("기준선 거래당(순수익) **%+.4f%%p**" % st.mean(base_net), flush=True)

    dates = sorted({p["_entry_date"] for p in P})
    by_date = defaultdict(list)
    for idx, p in enumerate(P):
        by_date[p["_entry_date"]].append(idx)
    rnd = random.Random(DAY_SEED)
    blk = [blocks(rnd, len(dates), BLOCK_MIN, BLOCK_MAX) for _ in range(N_BOOT)]

    # ═══════════ 0단계-B(1)(2) — 상한과 비용의 표본 ═══════════
    print("\n" + "=" * 70, flush=True)
    print("0단계-B · **낙관적 상한**과 **비용의 표본**", flush=True)
    print("=" * 70, flush=True)
    lost = [i for i in range(n) if base[i][0] in ("loss", "ambiguous")]
    reached10 = [i for i in lost
                 if max(x for x in P[i]["h_pct"][:base[i][1] + 1] if x is not None) >= 10.0]
    print("  기준선 손절/모호 %d건 · 그중 한때 +10%% 이상 **%d건 (%.1f%%)**"
          % (len(lost), len(reached10), len(reached10) / len(lost) * 100), flush=True)
    gains10 = [-base_net[i] for i in reached10]
    up = sum(gains10) / n
    print("  **낙관적 상한** — 그 %d건이 전부 0%%로 끝난다면 거래당 **%+.4f%%p**"
          % (len(reached10), up), flush=True)
    print("    (그 %d건의 실제 순수익 평균 %+.3f%%p)"
          % (len(reached10), st.mean([base_net[i] for i in reached10])), flush=True)
    # 비용의 표본
    won = [i for i in range(n) if base[i][0] == "win"]
    cost_n = 0
    for i in won:
        h, l = P[i]["h_pct"], P[i]["l_pct"]
        e = base[i][1]
        seen10 = False
        for j in range(e + 1):
            if not seen10 and h[j] is not None and h[j] >= 10.0:
                seen10 = True
                continue
            if seen10 and l[j] is not None and l[j] <= 0.0:
                cost_n += 1
                break
    print("  **비용의 표본** — +10%%를 찍은 뒤 본전 아래로 갔다가 결국 +20%% 도달: **%d건**"
          % cost_n, flush=True)
    res["upper_bound"] = {"n_lost": len(lost), "n_reached10": len(reached10),
                          "per_trade_pp": up, "cost_sample_n": cost_n,
                          "n_win": len(won)}

    # ═══════════ 0단계-A — 12칸 산수 관문 ═══════════
    print("\n" + "=" * 70, flush=True)
    print("0단계-A · **산수 관문 12칸** — [보수적, 낙관적]", flush=True)
    print("=" * 70, flush=True)
    print("  ⚠️ 청산가는 하네스 관례 그대로 **그날 종가**다. 아래 '실측'이 그 값이고,", flush=True)
    print("     '가정판'은 지시서 틀대로 **S에서 정확히 청산된다고 놓은** 값이다.\n", flush=True)
    print("  %-8s %-13s %6s %6s %8s %8s %10s %10s"
          % ("트리거", "새손절", "이득건", "비용건", "손익분기", "산수판정",
             "실측거래당", "구간95%"), flush=True)
    cells = []
    for trig in TRIGGERS:
        for lab, f in NEWSTOPS:
            news = f(trig)
            if news >= trig:
                continue
            row = {"trigger": trig, "stop_label": lab, "stop_pct": news}
            for mode in ("pess", "opt"):
                r = [ratchet(p, trig, news, mode) for p in P]
                rn = [net(x[2]) for x in r]
                d = [rn[i] - base_net[i] for i in range(n)]
                # 이득/비용 건수(요청된 틀)
                gain_n = sum(1 for i in range(n)
                             if base[i][0] in ("loss", "ambiguous") and r[i][3] is not None)
                cost_n2 = sum(1 for i in range(n)
                              if base[i][0] == "win" and r[i][0] != "win")
                changed = sum(1 for x in d if abs(x) > 1e-9)
                amb_days = sum(x[4] for x in r)
                # 가정판 손익분기
                avg_gain = news - (-STOP)                     # S에서 청산 가정
                avg_cost = TARGET - news
                be = gain_n * avg_gain / avg_cost if avg_cost > 0 else None
                verdict = ("짐" if (be is not None and cost_n2 > be * 1.10) else
                           "경계" if (be is not None and cost_n2 > be * 0.90) else "안 짐")
                # 실측 거래당 차이 + 날짜 블록 구간
                pt = st.mean(d)
                bs = []
                for bl in blk:
                    a = []
                    for s_, L in bl:
                        for j in range(L):
                            a.extend(d[i] for i in by_date[dates[s_ + j]])
                    if a:
                        bs.append(st.mean(a))
                lo_, hi_ = ci(bs)
                row[mode] = {"gain_n": gain_n, "cost_n": cost_n2, "breakeven": be,
                             "verdict": verdict, "per_trade_diff": pt,
                             "ci": [lo_, hi_], "n_changed": changed,
                             "ambiguous_days": amb_days,
                             "MDE": MDE_K * st.stdev(bs)}
            cells.append(row)
            pe, op = row["pess"], row["opt"]
            print("  %-8s %-13s [%d,%d] [%d,%d] %8s %8s  [%+.3f,%+.3f]  [%+.2f~%+.2f]"
                  % ("+%g%%" % trig, lab,
                     pe["gain_n"], op["gain_n"], pe["cost_n"], op["cost_n"],
                     ("%.0f" % pe["breakeven"]) if pe["breakeven"] else "—",
                     pe["verdict"] + "/" + op["verdict"],
                     pe["per_trade_diff"], op["per_trade_diff"],
                     pe["ci"][0], pe["ci"][1]), flush=True)
    res["cells"] = cells

    # ═══════════ 0단계-B(3) — MDE ═══════════
    print("\n" + "=" * 70, flush=True)
    print("0단계-B(3) · **거래당 축 MDE**(짝지은 차이의 날짜 블록 부트스트랩)", flush=True)
    print("=" * 70, flush=True)
    mdes = [c[m]["MDE"] for c in cells for m in ("pess", "opt")]
    print("  12칸 × 2모드 MDE 최소 %.4f · 중앙 %.4f · 최대 %.4f %%p"
          % (min(mdes), st.median(mdes), max(mdes)), flush=True)
    print("  ⚠️ 짝지은 차이라 대부분의 거래에서 0이다 → **비짝 MDE(~2.2%p)보다 훨씬 작다.**",
          flush=True)
    res["MDE_paired"] = {"min": min(mdes), "median": st.median(mdes), "max": max(mdes)}

    (OUT / "23-stage0-ratchet.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/23-stage0-ratchet.json", flush=True)


if __name__ == "__main__":
    main()
