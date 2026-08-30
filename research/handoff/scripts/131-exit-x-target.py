# -*- coding: utf-8 -*-
"""131 — **청산 방식 × 목표: 「가장 수익 좋고 위험 적은」 칸 찾기** (사전등록 · 값 보기 «전»)

사용자(2026-08-30):
> 「3) **20% 전량 매도 방식 말고 하네스에 적힌 대로** 검증 한번 해줘.
>  1) 목표를 25~30 으로 올릴지 말지는 고민이 되네요. **가장 수익률이 좋고 리스크가 적은 방식**으로
>  하고 싶네요. 검증 한번 해줘요.」

# ★ 두 물음이 «얽혀» 있다 — 그래서 한 판에서 같이 잰다
```
청산 방식을 바꾸면 «얼마나 오래 들고 있나»가 바뀌고, 그러면 목표의 값어치도 바뀐다.
따로 재서 합치면 안 된다(69번 교훈: 따로 +60.65% vs 맞물려 +298.44%).
```

# 격자
```
청산   **전량(half=1.0)** · 절반+추격(0.5 = 지금까지) · 4분의1만 팔고 추격(0.25)
목표   +20 · +25 · +30
손절   **−10 고정** (129 에서 −8 vs −10 은 목표마다 교대 = 못 가림 → 정본값을 쓴다)
       = **9칸**
```

# 「가장 수익 좋고 위험 적은」을 어떻게 재나 — **세 가지를 «같이»**
```
① 세후 총액        «수익률이 좋고»
② 최대 낙폭         «리스크가 적은»
③ 회복까지 최장 기간  평생 굴리면 이게 «실제로 겪는 고통»이다
④ ★ **MAR 비율 = 연평균 ÷ |최대낙폭|** — ①과 ②를 «한 숫자»로 묶는 표준 자
   🚨 MAR 로 «줄만» 세우지 않는다. 효율 경계도 같이 적는다
```

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **AU**★ | 🚨 관문 — 전량(1.0) 판에서 **청산일 = 목표 닿은 날**인지 확인(자리가 제때 비는가) |
| **AV**★ | 🚨 관문 — 수수료 횟수 = 매수 수 · Σ(자리 손익) = 총수익 |
| **AW**★ | 앞 1999~2011 에서 «MAR 최선» 칸이 뒤 2012~2026 에서도 현행(0.5·+20)을 이기는가 |
| **AX** | 아홉 칸을 총액·낙폭·회복·MAR **네 축 전부** 적는다 |

# ★ 방향을 «먼저» 적는다
```
㉮ **전량 매도가 총액은 «낮고» 낙폭은 «얕을» 것이다** — 승자를 일찍 놓아주므로
㉯ **절반+추격(0.5)이 총액 1위일 것이다** — 지금까지 값이 그 위에서 나왔다
㉰ 🚨 **MAR 로 줄 세우면 «전량 매도»가 이길 수도 있다** — 낙폭이 얕아서
   → 그러면 답이 「총액이냐 안정이냐」로 갈리고, **그 선택은 사용자님 것이다**
㉱ 목표는 129 대로 +25~+30 이 총액 1위일 것이나, **MAR 로는 +20 이 이길 수 있다**
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
r124 = _load("r124", "124-jeonse-horizon.py")
r129 = _load("r129", "129-frontier.py")
f92a = r102.f92a

YEARS = tuple(range(1999, 2027))
YRS = 27.4
START = 1000.0
FEE = 0.002
SHORT_SIZE, BORROW = 0.20, 2.0
HALVES = ((1.0, "전량 매도"), (0.5, "절반+추격"), (0.25, "1/4만 팔고 추격"))
TARGETS = (20.0, 25.0, 30.0)
STOP = 10.0
CUR = (0.5, 20.0)
FRONT, BACK = ("1999-04-01", "2011-12-31"), ("2012-01-01", "2026-08-21")


def main() -> int:
    n_seed = 6 if "--quick" in sys.argv else 20
    print("=" * 106, flush=True)
    print("131 — **청산 방식 × 목표: 「수익 좋고 위험 적은」 칸** · 사전등록 · 운의 번호 %d판"
          % n_seed, flush=True)
    print("=" * 106, flush=True)
    print("★ 두 물음이 얽혀 있어 «한 판»에서 같이 잰다 (따로 재서 합치면 안 된다)", flush=True)
    print("🚨 방향 먼저: 전량은 총액↓ 낙폭↓ · **MAR 로 줄 세우면 전량이 이길 수도 있다**\n",
          flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, "1999-04-01", "2026-08-21", "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음", flush=True)
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    by_f = {}
    for y in sorted(by2):
        k = []
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
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
    r91.STOP = STOP
    for hv, hnm in HALVES:
        for tg in TARGETS:
            k += 1
            r91.HALF, r91.TARGET = hv, tg
            ev, _b1, _b2 = r91.replay(by_f)
            # ── 🚨 관문 AU★ — 전량 판이면 «목표 닿은 날»에 끝나는가 ──
            if hv >= 1.0:
                bad = 0
                for t in ev:
                    m = t["masks"][next(iter(t["masks"]))]
                    if m["result"] == "win" and m["exits"]:
                        if m["resolve_date"] != m["exits"][0][0]:
                            bad += 1
                print("  **AU★ 관문** [전량·목표 +%.0f] 청산일 ≠ 목표일 인 이긴 거래 **%d건** · %s"
                      % (tg, bad, "통과" if bad == 0 else "🚨 미통과 — 무효"), flush=True)
                if bad:
                    return 3
            rs = r91.sim(ev, n_seed)
            post, mds, recs, wrs, ns, fr, bk = [], [], [], [], [], [], []
            for x in rs:
                fdates = [f[3] for f in x["fill_log"] if f[1] == "pilot"]
                if len(fdates) != int(x["n_filled"]):
                    print("🚨 AV★ 미통과 — 수수료 횟수", flush=True)
                    return 4
                g = abs(sum(r_ * t2 / 100.0 for _d, r_, t2 in x["ret_log"])
                        - x["equity_pct"] / 100.0) / max(1e-9, abs(x["equity_pct"] / 100.0))
                if g >= 0.005:
                    print("🚨 AV★ 미통과 — 손익 합 %.3f%%" % (g * 100), flush=True)
                    return 5
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
                m_, rc = r129.shape(cds, ccv)
                mds.append(m_)
                recs.append(rc)
                r_ = [e[1] for e in x["ret_log"]]
                wrs.append(100.0 * sum(1 for v in r_ if v > 0) / len(r_))
                ns.append(len(r_))
                for (a0, b0), box in ((FRONT, fr), (BACK, bk)):
                    ii = [i for i, d in enumerate(cds) if a0 <= d <= b0]
                    if len(ii) > 20:
                        yy = (r102._ord(cds[ii[-1]]) - r102._ord(cds[ii[0]])) / 365.25
                        cg = ((ccv[ii[-1]] / ccv[ii[0]]) ** (1 / yy) - 1) * 100
                        mm, _rc = r129.shape(cds[ii[0]:ii[-1] + 1], ccv[ii[0]:ii[-1] + 1])
                        box.append(cg / abs(mm) if mm else 0.0)
            pv, mv = st.median(post), st.median(mds)
            cg = ((pv / START) ** (1 / YRS) - 1) * 100
            cells[(hv, tg)] = {"post": pv, "mdd": mv, "rec": st.median(recs),
                               "wr": st.median(wrs), "n": st.median(ns), "cagr": cg,
                               "mar": cg / abs(mv) if mv else 0.0,
                               "front": st.median(fr) if fr else None,
                               "back": st.median(bk) if bk else None}
            v = cells[(hv, tg)]
            print("  %d/9  %-14s +%-3.0f  세후 %7.0f만 · 낙폭 %+6.1f%% · 회복 %.1f년 · "
                  "**MAR %.2f** · 승률 %.1f%%"
                  % (k, hnm, tg, v["post"], v["mdd"], v["rec"] / 252.0, v["mar"], v["wr"]),
                  flush=True)

    print("\n" + "=" * 106, flush=True)
    print("### 아홉 칸 — 네 축 (MAR 높은 순 · **MAR = 연평균 ÷ |최대낙폭|**)", flush=True)
    print("  %-16s %5s %11s %9s %9s %8s %7s %6s"
          % ("청산", "목표", "세후 총액", "연평균", "**낙폭**", "회복(년)", "**MAR**", "승률"),
          flush=True)
    print("  " + "-" * 82, flush=True)
    nm = {h: n for h, n in HALVES}
    for (hv, tg), v in sorted(cells.items(), key=lambda x: -x[1]["mar"]):
        mark = "  ← 현행" if (hv, tg) == CUR else ""
        print("  %-16s +%-4.0f %8.0f만 %+8.2f%% %+8.1f%% %8.1f %6.2f %6.1f%%%s"
              % (nm[hv], tg, v["post"], v["cagr"], v["mdd"], v["rec"] / 252.0,
                 v["mar"], v["wr"], mark), flush=True)

    print("\n  ★ **효율 경계** — 자기보다 총액도 높고 낙폭도 얕은 칸이 «없는» 칸", flush=True)
    fr2 = [c for c, v in cells.items()
           if not any(w["post"] > v["post"] and w["mdd"] > v["mdd"]
                      for d, w in cells.items() if d != c)]
    for c in sorted(fr2, key=lambda c: -cells[c]["post"]):
        v = cells[c]
        print("     %-16s +%-4.0f  세후 %7.0f만 · 낙폭 %+6.1f%% · MAR %.2f%s"
              % (nm[c[0]], c[1], v["post"], v["mdd"], v["mar"],
                 "  ← 현행" if c == CUR else ""), flush=True)

    fl = [(c, v) for c, v in cells.items() if v["front"] is not None]
    if fl:
        fl.sort(key=lambda x: -x[1]["front"])
        pk, cu = fl[0][0], cells[CUR]
        AW = (cells[pk]["back"] > cu["back"]) if (cells[pk]["back"] and cu["back"]) else None
        print("\n  **AW★** 앞에서 «MAR 최선»으로 고른 칸(%s·+%.0f)이 뒤에서 현행을 이기는가 → **%s**"
              % (nm[pk[0]], pk[1],
                 "통과" if AW else ("미통과" if AW is not None else "판정불가")), flush=True)
        if AW is not None:
            print("        뒤 구간 MAR — 고른 칸 %.2f vs 현행 %.2f"
                  % (cells[pk]["back"], cu["back"]), flush=True)

    (r91.OUT / "131-exit-x-target.json").write_text(
        json.dumps({"%.2f/%.0f" % c: v for c, v in cells.items()},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 131-exit-x-target.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
