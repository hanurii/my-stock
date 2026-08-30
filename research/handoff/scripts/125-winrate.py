# -*- coding: utf-8 -*-
"""125 — **「우리 방법의 승률은 얼마인가」** (사전등록 · 값 보기 «전»)

사용자(2026-08-30): 「작업 전에 우리 방법의 **승률**을 좀 알고 싶은데요 어느 정도인가요?」

★ **아직 «안» 쟀다.** 미국 27.4년 판에서 승률을 한 번도 적은 적이 없다.

# 재는 것 — **승률 «하나»만 보면 안 되므로 넷을 같이 적는다**
```
① 거래당 승률            수익률 > 0 인 자리의 비율
② 손익비                 평균 이익% ÷ 평균 손실%
③ 거래당 기댓값          (승률 × 평균이익) − (패률 × 평균손실)
④ 해마다 계좌가 오른 비율  27년 중 몇 해가 플러스였나
🚨 ①만 보면 «반드시» 틀린다 — 승률 40% 에 손익비 2:1 이면 «돈을 번다»
```

# 견줄 것 — **사용자님의 «실제» 정산표** (public/data/scorecard.json · 2026-08-21 · 63 왕복)
```
승률 33.33% (21승 42패) · 평균이익 +7.83% · 평균손실 −6.66% · 손익비 1.18
**기댓값 −1.83%/거래** · 순손익 −502만원
```

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **AC**★ | 🚨 관문 — Σ(자리 손익) = 총수익 (0.5% 안). 아니면 이 숫자들은 무효 |
| **AD** | 승률·손익비·기댓값을 «구간»(운의 번호 40판)까지 적는다 |
| **AE** | 사용자님 실제 성적과 «같은 자»로 나란히 적는다 |

# ★ 방향을 «먼저» 적는다
```
㉮ **승률은 50% «아래»일 것이다** — 목표 +20% / 손절 −10% 이면 구조상
   「자주 조금 잃고 가끔 크게 번다」가 된다. 승률이 낮은 건 **결함이 아니라 설계다**
㉯ **손익비는 2 근처**일 것이다 (+20/−10 규칙의 직접 결과)
㉰ 🚨 **백테스트가 사용자님 실제 성적보다 «좋을» 것이다** —
   백테스트에는 재량·망설임·관문 완화가 없다. **그 차이가 «규칙 대비 실행»의 값이다**
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
r118 = _load("r118", "118-matched-placebo.py")
f92a = r102.f92a

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
WIN = (("전체 27.4년", "1999-04-01", "2026-08-21"),
       ("2012~2026 (표본 밖)", "2012-01-01", "2026-08-21"))


def summarize(rets):
    """rets = [(날짜, 수익률%, 자리크기)] → 승률·손익비·기댓값."""
    r = [x[1] for x in rets]
    w = [x for x in r if x > 0]
    l = [-x for x in r if x <= 0]
    n = len(r)
    wr = 100.0 * len(w) / n if n else 0.0
    aw = st.mean(w) if w else 0.0
    al = st.mean(l) if l else 0.0
    return {"n": n, "win_rate": wr, "avg_win": aw, "avg_loss": al,
            "payoff": (aw / al) if al > 0 else float("inf"),
            "exp": st.mean(r) if r else 0.0,
            "big": 100.0 * sum(1 for x in r if x >= 19.0) / n if n else 0.0,
            "stop": 100.0 * sum(1 for x in r if x <= -9.0) / n if n else 0.0,
            "med": st.median(r) if r else 0.0}


def band(vals):
    v = sorted(vals)
    return v[max(0, int(len(v) * 0.05))], st.median(v), v[min(len(v) - 1, int(len(v) * 0.95))]


def main() -> int:
    n_seed = 8 if "--quick" in sys.argv else 40
    print("=" * 100, flush=True)
    print("125 — **우리 방법의 승률** · 사전등록 · 운의 번호 %d판" % n_seed, flush=True)
    print("=" * 100, flush=True)
    print("🚨 승률 «하나»만 보면 반드시 틀린다 — 승률 40%%에 손익비 2:1 이면 **돈을 번다**", flush=True)
    print("🚨 방향 먼저: 승률 **50%% 아래**일 것 · 손익비 **2 근처** · 실제 성적보다 나을 것\n",
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

    out = {}
    for nm, by in (("① 우리 규칙 (성장 둔화 필터)", by_f), ("② 바탕 (필터 없음)", by2)):
        _n, ev = r118.fills_of(by)
        rs = r91.sim(ev, n_seed)
        # 🚨 관문 AC — Σ(자리 손익) 이 총수익과 맞는가
        g = max(abs(sum(r_ * t / 100.0 for _d, r_, t in x["ret_log"])
                    - x["equity_pct"] / 100.0)
                / max(1e-9, abs(x["equity_pct"] / 100.0)) for x in rs)
        print("**AC★ 관문** [%s] Σ(자리 손익) vs 총수익 · 어긋남 **%.3f%%** · **%s**"
              % (nm, g * 100, "통과" if g < 0.005 else "🚨 미통과 — 무효"), flush=True)
        if g >= 0.005:
            return 3
        out[nm] = {}
        for lab, a0, b0 in WIN:
            per = [summarize([e for e in x["ret_log"] if a0 <= e[0] <= b0])
                   for x in rs]
            per = [p for p in per if p["n"] >= 20]
            k = {f: band([p[f] for p in per])
                 for f in ("win_rate", "payoff", "exp", "avg_win", "avg_loss",
                           "big", "stop", "n", "med")}
            out[nm][lab] = k
        print("", flush=True)

    for nm in out:
        print("### %s" % nm, flush=True)
        print("  %-22s %14s %12s %12s %12s"
              % ("", "**승률**", "손익비", "**기댓값**", "거래 수"), flush=True)
        print("  " + "-" * 76, flush=True)
        for lab, _a, _b in WIN:
            k = out[nm][lab]
            print("  %-22s %6.1f%% [%.1f~%.1f] %5.2f [%.2f~%.2f] %+6.2f%% [%+.2f~%+.2f] %8.0f"
                  % (lab, k["win_rate"][1], k["win_rate"][0], k["win_rate"][2],
                     k["payoff"][1], k["payoff"][0], k["payoff"][2],
                     k["exp"][1], k["exp"][0], k["exp"][2], k["n"][1]), flush=True)
            print("     평균이익 +%.2f%% · 평균손실 −%.2f%% · **+20%% 도달 %.1f%%** · 손절 %.1f%%"
                  % (k["avg_win"][1], k["avg_loss"][1], k["big"][1], k["stop"][1]), flush=True)
        print("", flush=True)

    # ── 사용자님 «실제» 정산표 ────────────────────────────────────────
    print("=" * 100, flush=True)
    try:
        sc = json.loads((HERE.parents[2] / "public" / "data" / "scorecard.json")
                        .read_text(encoding="utf-8"))["overall"]["net"]
        print("### 견줌 — 사용자님 **실제** 정산표 (한국 · %d 왕복 · 수수료·세금 후)"
              % sc["trade_count"], flush=True)
        print("  승률 **%.2f%%** (%d승 %d패) · 평균이익 +%.2f%% · 평균손실 −%.2f%%"
              % (sc["win_rate"], sc["win_count"], sc["loss_count"],
                 sc["avg_win"], sc["avg_loss"]), flush=True)
        print("  손익비 **%.2f** · **기댓값 %+.2f%%/거래** · 순손익 %s원"
              % (sc["payoff_ratio"], sc["expectancy"],
                 "{:,}".format(sc["total_won"])), flush=True)
        print("\n  🚨 **다른 시장·다른 기간·63건이라 «직접 비교»가 아니다.**", flush=True)
        print("     같은 자로 놓는 이유는 **「규칙대로」와 「실제로」의 차이**를 보기 위해서다.",
              flush=True)
    except Exception as e:                                        # noqa: BLE001
        print("🚨 정산표를 못 읽었다: %s" % e, flush=True)

    (r91.OUT / "125-winrate.json").write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 125-winrate.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
