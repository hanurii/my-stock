# -*- coding: utf-8 -*-
"""126 — **「승률을 50% 로 올릴 수 있는가, 없다면 손익비를 바꿔야 하는가」** (사전등록 · 값 보기 «전»)

사용자(2026-08-30):
> 「미너비니는 **50% 정도의 승률**을 유지하면서 **수익 20 / 손절 −10** 비율로 했을 때
>  수학적으로 의미 있는 자산 증식이 가능하다고 했습니다. 그래서 제 생각은
>  **승률을 수정할 수 없다면 «수익-손실 비율»을 수정해야 하고,**
>  **승률을 끌어올릴 수 있다면 50% 이상까지는 끌어올려야** 할 걸로 생각됩니다.」

# 먼저 바로잡을 것 — **우리 백테스트는 20/−10 이 아니다**
```
`91-us-out-of-sample.py:54`   STOP, TARGET = **8.0, 20.0**   ← 손절 **−8%**
그래서 평균손실이 −8.23% 였다. 미너비니 셈법(20/−10)과 «다른 자»로 재고 있었다
```

# ★ 이 판의 핵심 — **승률·손익비·기댓값은 «따로» 못 고른다**
```
목표를 낮추면    승률 ↑   손익비 ↓
손절을 넓히면    승률 ↑   손익비 ↓
→ **「승률 50% ∧ 손익비 2:1」을 «동시에» 가지려면 규칙이 아니라 «선별력»이 올라야 한다.**
   규칙만 바꾸면 한쪽을 얻고 다른 쪽을 잃는다. **이 판이 그 맞바꿈을 «숫자»로 낸다.**
```

# 격자 — 20칸
```
목표  +10 · +15 · +20 · +25 · +30 %
손절  −5 · −8 · −10 · −12.5 %
칸마다  승률 · 손익비 · 거래당 기댓값 · 연평균 · 낙폭 · 거래 수 · **필요 승률**
       (필요 승률 = 그 칸의 평균이익·평균손실로 «거래당 +5%»를 내려면 몇 % 이겨야 하나)
```

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **AF** | (묘사) 승률 **50% 이상**인 칸이 «있는가». 있다면 그 칸의 «연평균»은? |
| **AG**★ | (검정) 앞 1999~2011 에서 «연평균 최선» 칸을 고르고 → 뒤 2012~2026 에서 **현행 (20, −8)** 을 이긴다 |
| **AH** | 승률 ↔ 손익비 «맞바꿈»을 한 줄에 같이 적는다 |

🚨 **AF 는 «판정»이 아니라 «묘사»다.** 20칸을 훑어 최선을 고르면 효과가 없어도 좋아 보인다
(메모리: 「귀무 95% +87.47%p — 12칸 중 최선을 고르면 그만큼 나온다」).
**그래서 «고르기»가 걸린 AG★ 만 판정으로 쓴다.**

# ★ 방향을 «먼저» 적는다
```
㉮ **승률 50% 칸은 «있을» 것이다** — 목표 +10 / 손절 −12.5 쪽에서
㉯ 🚨 **그런데 그 칸의 «연평균»은 더 «낮을» 것이다** — 맞바꿈이라서
   → **사용자님 물음의 답이 「올릴 수 있다. 그런데 올리면 돈이 준다」가 될 것으로 본다**
㉰ 🚨 **AG★ 는 못 넘을 것으로 본다** — 한국 5.6년에서 청산 55변형 중 현행을 이긴 게 **0개**였다
   단 **그건 한국·5.6년이고 이건 미국·27.4년이라 «다시 재는 게 맞다»**
```
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
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
f92a = r102.f92a

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
FRONT = ("1999-04-01", "2011-12-31", 12.75)
BACK = ("2012-01-01", "2026-08-21", 14.64)
ALL = ("1999-04-01", "2026-08-21", 27.4)
TARGETS = (10.0, 15.0, 20.0, 25.0, 30.0)
STOPS = (5.0, 8.0, 10.0, 12.5)
CUR = (20.0, 8.0)                 # 현행
GOAL_EXP = 5.0                    # 미너비니 셈법: 0.5×20 − 0.5×10 = +5%/거래


def cut(rets, a0, b0):
    r = [x[1] for x in rets if a0 <= x[0] <= b0]
    if len(r) < 20:
        return None
    w = [x for x in r if x > 0]
    l = [-x for x in r if x <= 0]
    aw = st.mean(w) if w else 0.0
    al = st.mean(l) if l else 0.0
    need = ((GOAL_EXP + al) / (aw + al) * 100.0) if (aw + al) > 0 else float("nan")
    return {"n": len(r), "wr": 100.0 * len(w) / len(r), "aw": aw, "al": al,
            "payoff": (aw / al) if al > 0 else float("inf"),
            "exp": st.mean(r), "need": need}


def main() -> int:
    n_seed = 6 if "--quick" in sys.argv else 20
    print("=" * 108, flush=True)
    print("126 — **승률을 50%%로 올릴 수 있는가 / 없다면 손익비를 바꿔야 하는가** · 사전등록",
          flush=True)
    print("=" * 108, flush=True)
    print("🚨 바로잡음: 우리 백테스트는 **20/−8** 이었다(91:54). 20/−10 이 아니다", flush=True)
    print("★ 승률·손익비·기댓값은 «따로» 못 고른다 — 이 판은 그 **맞바꿈**을 숫자로 낸다", flush=True)
    print("🚨 방향 먼저: 50%% 칸은 «있을» 것 · **그 칸의 연평균은 더 «낮을» 것** · AG★ 못 넘을 것\n",
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

    cells, k = {}, 0
    tot = len(TARGETS) * len(STOPS)
    for tg in TARGETS:
        for sp in STOPS:
            k += 1
            r91.TARGET, r91.STOP = tg, sp        # 🚨 격자 값을 하네스에 꽂는다
            ev, _b1, _b2 = r91.replay(by_f)
            rs = r91.sim(ev, n_seed)
            row = {}
            for lab, (a0, b0, yrs) in (("all", ALL), ("front", FRONT), ("back", BACK)):
                e = [t for t in ev if a0 <= t["entry_date"] <= b0]
                if len(e) < 20:
                    continue
                sub = r91.sim(e, n_seed) if lab != "all" else rs
                eq = st.median(x["equity_pct"] for x in sub)
                md = st.median(min(v for _d, v in x["curve"]) /
                               max(1e-9, max(v for _d, v in x["curve"])) - 1.0
                               for x in sub)
                agg = [cut(x["ret_log"], a0, b0) for x in sub]
                agg = [a for a in agg if a]
                if not agg:
                    continue
                row[lab] = {f: st.median(a[f] for a in agg)
                            for f in ("n", "wr", "aw", "al", "payoff", "exp", "need")}
                row[lab]["cagr"] = ((1 + eq / 100.0) ** (1 / yrs) - 1) * 100
                row[lab]["mdd"] = md * 100
            cells[(tg, sp)] = row
            c = row.get("all", {})
            print("  %2d/%d  목표 +%-4.0f 손절 −%-4.1f  승률 %5.1f%%  손익비 %5.2f  기댓값 %+6.2f%%"
                  "  연평균 %+6.2f%%  거래 %4.0f"
                  % (k, tot, tg, sp, c.get("wr", 0), c.get("payoff", 0), c.get("exp", 0),
                     c.get("cagr", 0), c.get("n", 0)), flush=True)

    print("\n" + "=" * 108, flush=True)
    print("### 전체 27.4년 — 20칸 (연평균 높은 순)", flush=True)
    print("  %-16s %8s %8s %9s %10s %9s %9s"
          % ("목표/손절", "승률", "손익비", "기댓값", "**연평균**", "낙폭", "필요승률"), flush=True)
    print("  " + "-" * 78, flush=True)
    ok = [(c, v["all"]) for c, v in cells.items() if "all" in v]
    ok.sort(key=lambda x: -x[1]["cagr"])
    for (tg, sp), v in ok:
        mark = "  ← 현행" if (tg, sp) == CUR else ""
        print("  +%-4.0f / −%-6.1f %7.1f%% %8.2f %+8.2f%% %+9.2f%% %8.1f%% %8.1f%%%s"
              % (tg, sp, v["wr"], v["payoff"], v["exp"], v["cagr"], v["mdd"],
                 v["need"], mark), flush=True)

    print("\n### AF (묘사) — 승률 **50% 이상**인 칸", flush=True)
    hi = [(c, v["all"]) for c, v in cells.items() if "all" in v and v["all"]["wr"] >= 50.0]
    if not hi:
        best = max(ok, key=lambda x: x[1]["wr"])
        print("  **없다.** 가장 높은 칸이 목표 +%.0f / 손절 −%.1f 의 **%.1f%%** (연평균 %+.2f%%)"
              % (best[0][0], best[0][1], best[1]["wr"], best[1]["cagr"]), flush=True)
    else:
        cur = cells[CUR]["all"]
        for (tg, sp), v in sorted(hi, key=lambda x: -x[1]["cagr"]):
            print("  목표 +%.0f / 손절 −%.1f — 승률 **%.1f%%** · 연평균 %+.2f%% (현행 %+.2f%%) · %s"
                  % (tg, sp, v["wr"], v["cagr"], cur["cagr"],
                     "**현행보다 낫다**" if v["cagr"] > cur["cagr"] else "현행보다 «낮다»"),
                  flush=True)

    print("\n### AG★ (검정) — 앞에서 고르고 뒤에서 검정", flush=True)
    fr = [(c, v["front"]) for c, v in cells.items() if "front" in v]
    if fr:
        fr.sort(key=lambda x: -x[1]["cagr"])
        pick = fr[0][0]
        pb = cells[pick].get("back")
        cb = cells[CUR].get("back")
        print("  앞 구간 최선: 목표 +%.0f / 손절 −%.1f (앞 %+.2f%%)"
              % (pick[0], pick[1], fr[0][1]["cagr"]), flush=True)
        if pb and cb:
            AG = pb["cagr"] > cb["cagr"]
            print("  뒤 구간: 고른 칸 **%+.2f%%** vs 현행(+20/−8) **%+.2f%%** → **%s**"
                  % (pb["cagr"], cb["cagr"], "통과" if AG else "**미통과**"), flush=True)
            print("  (뒤 구간 승률 — 고른 칸 %.1f%% · 현행 %.1f%%)"
                  % (pb["wr"], cb["wr"]), flush=True)
        else:
            AG = None
            print("  🚨 뒤 구간 자료 부족 — 판정 불가", flush=True)
    (r91.OUT / "126-winrate-grid.json").write_text(
        json.dumps({"%.0f/%.1f" % c: v for c, v in cells.items()},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 126-winrate-grid.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
