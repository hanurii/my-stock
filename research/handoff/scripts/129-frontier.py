# -*- coding: utf-8 -*-
"""129 — **목표 × 손절을 «두 축»으로 + 「지수 + N일선」** (사전등록 · 값 보기 «전»)

사용자(2026-08-30):
> 「앞으로는 **미국으로 갑니다**. … 그리고 **사용자 × 목표축**을 아직 안 봤다면 봐줘요.
>  … 그리고 **지수 + 200일선**도 재줘요.」

# ★ 「사용자 자」가 무엇인지 다시 정한다 — **평생 굴리는 전제로 바뀌었다**
```
사용자님 기준   「bad case 일 때 손실을 최대한 막으면서 수익률은 최대한 끌어올린다」
사용자님 지평   「주식투자를 **평생** 할 계획. 중간에 빼더라도 **다 빼진 않는다**」

→ 평생 굴리는 사람에게 «bad case» 는 «3년 뒤 최종금액»이 아니라
  **«얼마나 깊이 빠지고, 얼마나 오래 못 회복하는가»** 다.
→ 그래서 이 판은 **세후 총액 × 최대 낙폭 × 회복까지 걸린 최장 기간** 셋을 «같이» 낸다.
🚨 **한 숫자로 줄 세우지 않는다.** 사용자님 목표가 «두 가지의 동시» 최적화이므로.
```

# 무엇을 재나
```
A부  목표 +15·+20·+25·+30·+40  ×  손절 −5·−8·−10·−12.5   = **20칸**
     (지수 숏 ③ 얹음 · 수수료 왕복 0.2% · 세후 · 1,000만원)
B부  **지수 + N일선**   SPY·QQQ  ×  N = 100·150·200·250   = 8칸
     (선 아래면 현금 · 현금 이자 연 2% · 세후 · 팔 때마다 실현)
C부  둘을 «같은 표»에 놓는다
```

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **AQ**★ | 🚨 관문 — 수수료 횟수 = 매수 수 · Σ(자리 손익) = 총수익 (0.5% 안) |
| **AR** | 20칸을 **총액 × 낙폭 × 회복기간** 세 축으로 «전부» 적는다 |
| **AS**★ | 앞 1999~2011 에서 «총액 최선» 칸이 뒤 2012~2026 에서도 현행(+20/−10)을 이기는가 |
| **AT** | B부가 A부의 «어느 칸과» 견줄 만한지 — 낙폭이 비슷한 칸끼리 놓는다 |

# ★ 방향을 «먼저» 적는다
```
㉮ **목표가 클수록 낙폭이 깊을 것이다** — 더 오래 들고 있으므로
㉯ **+30 계열이 총액 1위를 지킬 것이다** — 126 에서 그랬다(단 그건 세전·숏 없음)
㉰ 🚨 **그래서 «지배하는» 칸은 없을 것이다** — 총액 1위와 낙폭 1위가 갈릴 것이고,
   그러면 답은 「이 칸이 최고」가 아니라 **«고를 수 있는 경계»**가 된다
㉱ 🚨 **B부(지수+N일선)는 낙폭이 «훨씬» 얕고 총액은 «훨씬» 낮을 것이다** —
   124 에서 3년 원금손실 5.7% 로 압도적이었으나 중앙은 꼴찌였다
㉲ **N=200 이 특별할 이유는 없다** — 널리 쓰이는 값일 뿐이다. 100~250 이 다 비슷하면
   그건 「200 이 좋다」가 아니라 **「이 축이 둔감하다」**는 뜻이고 그게 더 든든하다
```
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _load(mod, fn):
    s = _u.spec_from_file_location(mod, HERE / fn)
    m = _u.module_from_spec(s)
    s.loader.exec_module(m)
    return m


r91 = _load("r91", "91-us-out-of-sample.py")
r102 = _load("r102", "102-implement-principles.py")
r103 = _load("r103", "103-code33-strength.py")
r108 = _load("r108", "108-short-index.py")
r109 = _load("r109", "109-index-stop.py")
r111 = _load("r111", "111-tax.py")
r124 = _load("r124", "124-jeonse-horizon.py")
f92a = r102.f92a

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
YRS = 27.4
START = 1000.0
FEE = 0.002
SHORT_SIZE, BORROW = 0.20, 2.0
TARGETS = (15.0, 20.0, 25.0, 30.0, 40.0)
STOPS = (5.0, 8.0, 10.0, 12.5)
CUR = (20.0, 10.0)
MAS = (100, 150, 200, 250)
FRONT, BACK = ("1999-04-01", "2011-12-31"), ("2012-01-01", "2026-08-21")


def shape(ds, cv):
    """최대 낙폭(%) 과 **회복까지 걸린 최장 기간(거래일)**."""
    peak, worst, pi, longest = cv[0], 0.0, 0, 0
    for i, v in enumerate(cv):
        if v >= peak:
            longest = max(longest, i - pi)
            peak, pi = v, i
        else:
            worst = min(worst, v / peak - 1.0)
    longest = max(longest, len(cv) - 1 - pi)
    return worst * 100, longest


def ma_arm(ds, c, n, cash=2.0):
    """지수 + N일선 — 곡선과 «판 날의 실현손익»."""
    m, run_ = [None] * len(c), []
    for i in range(len(c)):
        run_.append(c[i])
        if len(run_) > n:
            run_.pop(0)
        m[i] = (sum(run_) / n) if i >= n - 1 else None
    v, out, inm, basis, real = 1.0, [1.0], True, 1.0, {}
    cd, ns = cash / 100.0 / 252.0, 0
    for i in range(1, len(c)):
        v *= (c[i] / c[i - 1]) if inm else (1.0 + cd)
        out.append(v)
        if inm and m[i] is not None and c[i] < m[i]:
            inm = False
            ns += 1
            real[ds[i]] = real.get(ds[i], 0.0) + (v - basis)
        elif (not inm) and m[i] is not None and c[i] > m[i]:
            inm, basis = True, v
    return out, real, ns


def main() -> int:
    n_seed = 6 if "--quick" in sys.argv else 20
    print("=" * 110, flush=True)
    print("129 — **목표 × 손절을 «두 축»으로 + 「지수 + N일선」** · 사전등록", flush=True)
    print("=" * 110, flush=True)
    print("★ 평생 굴리는 사람에게 «bad case» 는 «3년 뒤 금액»이 아니라 **«낙폭과 회복기간»** 이다",
          flush=True)
    print("🚨 **한 숫자로 줄 세우지 않는다** — 사용자님 목표가 «두 가지의 동시» 최적화이므로\n",
          flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음", flush=True)
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    by_f = {}
    for y in sorted(by2):
        k = []
        for p in by2[y]:
            rec = fund.get(p["code"])
            arq = (rec or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0])
                          > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is not False:
                k.append(p)
        by_f[y] = k

    ds, c, ma, hi = r108.spy_series()
    on = r108.short_days(ds, c, ma, hi)
    spy_ret = {ds[i]: c[i] / c[i - 1] - 1.0 for i in range(1, len(ds))}
    bo = BORROW / 100.0 / 252.0 * SHORT_SIZE

    cells, k = {}, 0
    for tg in TARGETS:
        for sp in STOPS:
            k += 1
            r91.TARGET, r91.STOP = tg, sp
            ev, _b1, _b2 = r91.replay(by_f)
            rs = r91.sim(ev, n_seed)
            post, mds, recs, wrs, ns = [], [], [], [], []
            fr, bk = [], []
            for x in rs:
                fdates = [f[3] for f in x["fill_log"] if f[1] == "pilot"]
                if len(fdates) != int(x["n_filled"]):
                    print("🚨 AQ★ 미통과 — 수수료 횟수", flush=True)
                    return 3
                g = abs(sum(r_ * t / 100.0 for _d, r_, t in x["ret_log"])
                        - x["equity_pct"] / 100.0) / max(1e-9, abs(x["equity_pct"] / 100.0))
                if g >= 0.005:
                    print("🚨 AQ★ 미통과 — 손익 합 %.3f%%" % (g * 100), flush=True)
                    return 4
                fd = Counter(fdates)
                vals = [(d, v) for d, v in x["curve"]] + [(x["curve"][-1][0],
                                                           1.0 + x["equity_pct"] / 100.0)]
                cds, ccv, V = [vals[0][0]], [1.0], 1.0
                for i in range(1, len(vals)):
                    if vals[i - 1][1] <= 0:
                        break
                    d = vals[i][0]
                    rl = vals[i][1] / vals[i - 1][1] - 1.0
                    sh = (-SHORT_SIZE * spy_ret[d] - bo) if (on.get(d) and d in spy_ret) else 0.0
                    V *= (1.0 + rl + sh - FEE * 0.20 * fd.get(d, 0))
                    cds.append(d)
                    ccv.append(max(V, 1e-9))
                real = {}
                for d, pl in x["exit_log"]:
                    real[d] = real.get(d, 0.0) + pl
                post.append(r124.taxed_window(cds, ccv, real, 0, len(ccv) - 1))
                m_, rc = shape(cds, ccv)
                mds.append(m_)
                recs.append(rc)
                r_ = [e[1] for e in x["ret_log"]]
                wrs.append(100.0 * sum(1 for v in r_ if v > 0) / len(r_))
                ns.append(len(r_))
                for lab, (a0, b0), box in (("f", FRONT, fr), ("b", BACK, bk)):
                    ii = [i for i, d in enumerate(cds) if a0 <= d <= b0]
                    if len(ii) > 20:
                        box.append(ccv[ii[-1]] / ccv[ii[0]])
            cells[(tg, sp)] = {"post": st.median(post), "mdd": st.median(mds),
                               "rec": st.median(recs), "wr": st.median(wrs),
                               "n": st.median(ns),
                               "front": st.median(fr) if fr else None,
                               "back": st.median(bk) if bk else None}
            v = cells[(tg, sp)]
            print("  %2d/20  +%-4.0f / −%-5.1f  세후 %7.0f만 · 낙폭 %+6.1f%% · 회복 %4.0f일 · "
                  "승률 %4.1f%% · 매수 %4.0f"
                  % (k, tg, sp, v["post"], v["mdd"], v["rec"], v["wr"], v["n"]), flush=True)

    print("\n" + "=" * 110, flush=True)
    print("### A부 — 20칸 · **세후 총액 × 최대 낙폭 × 회복기간** (총액 높은 순)", flush=True)
    print("  %-14s %11s %10s %11s %8s %7s"
          % ("목표/손절", "**세후 총액**", "**낙폭**", "**회복(년)**", "승률", "매수"), flush=True)
    print("  " + "-" * 70, flush=True)
    ok = sorted(cells.items(), key=lambda x: -x[1]["post"])
    for (tg, sp), v in ok:
        mark = "  ← 현행" if (tg, sp) == CUR else ""
        print("  +%-4.0f / −%-6.1f %8.0f만 %9.1f%% %9.1f년 %7.1f%% %7.0f%s"
              % (tg, sp, v["post"], v["mdd"], v["rec"] / 252.0, v["wr"], v["n"], mark),
              flush=True)

    print("\n  ★ **효율 경계** — 「자기보다 총액도 높고 낙폭도 얕은 칸이 «없는»」 칸만", flush=True)
    front = [c for c, v in cells.items()
             if not any(w["post"] > v["post"] and w["mdd"] > v["mdd"]
                        for d, w in cells.items() if d != c)]
    for c in sorted(front, key=lambda c: -cells[c]["post"]):
        v = cells[c]
        print("     +%-4.0f / −%-5.1f   세후 %7.0f만 · 낙폭 %+6.1f%% · 회복 %.1f년%s"
              % (c[0], c[1], v["post"], v["mdd"], v["rec"] / 252.0,
                 "  ← 현행" if c == CUR else ""), flush=True)

    fr = [(c, v) for c, v in cells.items() if v["front"]]
    if fr:
        fr.sort(key=lambda x: -x[1]["front"])
        pk, cu = fr[0][0], cells[CUR]
        AS = cells[pk]["back"] > cu["back"] if (cells[pk]["back"] and cu["back"]) else None
        print("\n  **AS★** 앞에서 고른 칸(+%.0f/−%.1f)이 뒤에서 현행을 이기는가 → **%s**"
              % (pk[0], pk[1],
                 "통과" if AS else ("미통과" if AS is not None else "판정불가")), flush=True)
        if AS is not None:
            print("        뒤 구간 배수 — 고른 칸 %.2f배 vs 현행 %.2f배"
                  % (cells[pk]["back"], cu["back"]), flush=True)

    # ── B부 — 지수 + N일선 ──────────────────────────────────────────
    print("\n" + "=" * 110, flush=True)
    print("### B부 — **지수 + N일선** (세후 · 현금 이자 연 2%)", flush=True)
    print("  %-18s %11s %10s %11s %8s" % ("", "**세후 총액**", "**낙폭**", "**회복(년)**", "매도횟수"),
          flush=True)
    print("  " + "-" * 62, flush=True)
    bpart = {}
    for tk in ("SPY", "QQQ"):
        d_, c_ = r109.load(tk)
        cv0 = [x / c_[0] for x in c_]
        a0 = r124.taxed_window(d_, cv0, {}, 0, len(cv0) - 1)
        m0, r0 = shape(d_, cv0)
        bpart["%s 그냥 보유" % tk] = (a0, m0, r0, 1)
        print("  %-18s %8.0f만 %9.1f%% %9.1f년 %8d" % ("%s 그냥 보유" % tk, a0, m0, r0 / 252.0, 1),
              flush=True)
        for n in MAS:
            cv, real, nsell = ma_arm(d_, c_, n)
            a = r124.taxed_window(d_, cv, real, 0, len(cv) - 1) * ((1 - FEE) ** (nsell + 1))
            m_, rc = shape(d_, cv)
            bpart["%s + %d일선" % (tk, n)] = (a, m_, rc, nsell)
            print("  %-18s %8.0f만 %9.1f%% %9.1f년 %8d"
                  % ("%s + %d일선" % (tk, n), a, m_, rc / 252.0, nsell), flush=True)

    print("\n  **AT** 낙폭이 비슷한 칸끼리 — 우리 규칙 중 «낙폭이 지수+선 과 비슷한» 칸", flush=True)
    for nm, (a, m_, rc, _n) in sorted(bpart.items(), key=lambda x: -x[1][0])[:4]:
        near = min(cells.items(), key=lambda x: abs(x[1]["mdd"] - m_))
        print("     %-18s 낙폭 %+6.1f%% · 세후 %7.0f만   ↔  우리 +%.0f/−%.1f 낙폭 %+6.1f%% · 세후 %7.0f만"
              % (nm, m_, a, near[0][0], near[0][1], near[1]["mdd"], near[1]["post"]), flush=True)

    (r91.OUT / "129-frontier.json").write_text(
        json.dumps({"grid": {"%.0f/%.1f" % c: v for c, v in cells.items()},
                    "ma": {k2: list(v) for k2, v in bpart.items()}},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 129-frontier.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
