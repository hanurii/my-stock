# -*- coding: utf-8 -*-
"""134 — **「+30 은 승률은 낮지만 돈을 더 번다」가 맞는가** (사전등록 · 값 보기 «전»)

사용자(2026-08-31): 「**+30 으로 설정하는 게 +20 으로 하는 것보다 승률은 낮지만 돈을 더 버는
구조라는 거죠? 이게 맞는지 확인해줘요.**」

★ 지금까지 «승률»과 «총액»은 따로 봤지만 **거래당 기댓값(평균손실 포함)은 «안 쟀다».**
   그리고 **「왜 승률이 떨어지는가」는 «설명»만 했지 «측정»한 적이 없다.**

# 두 갈래로 확인한다
```
① **산수가 맞는가**  승률 · 평균이익 · **평균손실** · 손익비 · **거래당 기댓값**
   → 「승률 ↓ · 평균이익 ↑」이 «순수익»에서 어느 쪽이 이기는지 «항등식»으로 확인

② ★★ **기전을 «측정»한다**  같은 후보를 +20 과 +30 으로 각각 결착시켜
   **「+20 에서는 «이겼는데» +30 에서는 «졌다»」로 바뀐 거래**를 «센다»
   → 예상 기전: 목표에 닿기 «전»에는 손절이 −10% 하나뿐이다.
     +25 까지 올랐다 되돌아온 거래는 +20 목표면 «절반 익절 후 본전»으로 «승»,
     +30 목표면 그냥 «−10% 손절» = **승 → 패로 바뀐다**
```

# 합격선 — 값 보기 «전»
| | 문턱 |
|---|---|
| **BH**★ | 🚨 관문 — Σ(자리 손익) = 총수익 (0.5% 안) |
| **BI**★ | 산수 확인: **승률은 +30 이 낮고**, **거래당 기댓값은 +30 이 높다** — 둘 «다» 성립해야 함 |
| **BJ** | 「+20 승 → +30 패」로 «바뀐» 거래 수와, 그 반대 방향 건수 |
| **BK** | 🚨 그 거래들의 «+20 에서의 평균 수익»을 적는다 (얼마나 «작은» 승리를 버린 것인가) |

# ★ 방향을 «먼저» 적는다
```
㉮ **BI★ 는 통과할 것이다** — 133 에서 평균이익 +21.24 → +28.65(**+7.41%p**),
   승률 42.7 → 36.6(**−6.1%p**). 평균손실이 둘 다 −10% 근처라면 산수로 +30 이 이긴다
㉯ **「승 → 패」로 바뀐 거래가 «상당수» 나올 것이다** — 그게 승률 6.1%p 의 정체다
㉰ 🚨 **그리고 그 거래들의 «+20 에서의 수익»은 «작을» 것이다** —
   즉 **버린 것은 «작은 승리»이고 얻은 것은 «큰 승리»다.** 그게 사용자님 말씀의 «구조»다
㉱ 🚨 반대 방향(+20 패 → +30 승)도 «조금» 있을 것이다. 0 이면 오히려 이상하다
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

YEARS = tuple(range(1999, 2027))
PAIR = (20.0, 30.0)
STOP = 10.0


def main() -> int:
    n_seed = 6 if "--quick" in sys.argv else 30
    print("=" * 100, flush=True)
    print("134 — **「+30 은 승률은 낮지만 돈을 더 번다」가 맞는가** · 사전등록", flush=True)
    print("=" * 100, flush=True)
    print("🚨 방향 먼저: 산수는 통과할 것 · **버린 것은 «작은 승리»일 것**\n", flush=True)

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

    r91.STOP, r91.HALF = STOP, 0.5
    stat, trade = {}, {}
    for tg in PAIR:
        r91.TARGET = tg
        ev, _b1, _b2 = r91.replay(by_f)
        # 거래 수준 — 슬롯과 무관하게 «모든 후보»의 결착 (기전 측정용)
        tm = {}
        for t in ev:
            m = t["masks"][next(iter(t["masks"]))]
            r_ = 0.0
            for _d, sh, px in m["exits"]:
                r_ += sh * (px / t["entry_px"] * 100.0 - 100.0)
            tm[(t["code"], t["scan_date"], t["entry_date"])] = r_
        trade[tg] = tm
        # 계좌 수준 — 실제 체결만
        rs = r91.sim(ev, n_seed)
        wr, aw, al, ex, ns = [], [], [], [], []
        for x in rs:
            pl = [r_ * t2 / 100.0 for _d, r_, t2 in x["ret_log"]]
            g = abs(sum(pl) - x["equity_pct"] / 100.0) / max(1e-9, abs(x["equity_pct"] / 100.0))
            if g >= 0.005:
                print("🚨 BH★ 미통과 — 항등식 %.3f%%" % (g * 100), flush=True)
                return 3
            r_ = [e[1] for e in x["ret_log"]]
            w = [v for v in r_ if v > 0]
            l = [-v for v in r_ if v <= 0]
            wr.append(100.0 * len(w) / len(r_))
            aw.append(st.mean(w) if w else 0.0)
            al.append(st.mean(l) if l else 0.0)
            ex.append(st.mean(r_))
            ns.append(len(r_))
        stat[tg] = {"wr": st.median(wr), "aw": st.median(aw), "al": st.median(al),
                    "exp": st.median(ex), "n": st.median(ns)}

    print("### BI★ — 산수 (실제 체결 · 운의 번호 %d판 중앙)" % n_seed, flush=True)
    print("  %-10s %8s %11s %11s %8s %12s %7s"
          % ("목표", "승률", "평균이익", "평균손실", "손익비", "거래당 기댓값", "매수"), flush=True)
    print("  " + "-" * 72, flush=True)
    for tg in PAIR:
        s = stat[tg]
        print("  +%-9.0f %7.1f%% %+10.2f%% %+10.2f%% %8.2f %+11.3f%% %7.0f"
              % (tg, s["wr"], s["aw"], -s["al"], s["aw"] / s["al"] if s["al"] else 0,
                 s["exp"], s["n"]), flush=True)
    lo, hi = PAIR
    okw = stat[hi]["wr"] < stat[lo]["wr"]
    oke = stat[hi]["exp"] > stat[lo]["exp"]
    print("\n  승률은 +30 이 «낮은가»        → **%s** (%.1f%% vs %.1f%%)"
          % ("예" if okw else "아니오", stat[hi]["wr"], stat[lo]["wr"]), flush=True)
    print("  거래당 기댓값은 +30 이 «높은가» → **%s** (%+.3f%% vs %+.3f%%)"
          % ("예" if oke else "아니오", stat[hi]["exp"], stat[lo]["exp"]), flush=True)
    print("  **BI★** 둘 다 성립 → **%s**" % ("통과" if (okw and oke) else "**미통과**"), flush=True)
    # 검산 — 기댓값을 승률·평균이익·평균손실로 다시 만들어 본다
    for tg in PAIR:
        s = stat[tg]
        chk = s["wr"] / 100 * s["aw"] - (1 - s["wr"] / 100) * s["al"]
        print("     검산 +%.0f: 승률x평균이익 − 패률x평균손실 = %+.3f%% (실측 %+.3f%%)"
              % (tg, chk, s["exp"]), flush=True)

    print("\n### BJ·BK — **기전: 「+20 승 → +30 패」로 바뀐 거래** (같은 후보끼리)", flush=True)
    both = set(trade[lo]) & set(trade[hi])
    w2l = [k for k in both if trade[lo][k] > 0 and trade[hi][k] <= 0]
    l2w = [k for k in both if trade[lo][k] <= 0 and trade[hi][k] > 0]
    print("   같은 후보 %s건 중" % "{:,}".format(len(both)), flush=True)
    print("     **+20 승 → +30 패**  **%s건 (%.1f%%)**"
          % ("{:,}".format(len(w2l)), 100.0 * len(w2l) / len(both)), flush=True)
    print("     +20 패 → +30 승   %s건 (%.1f%%)"
          % ("{:,}".format(len(l2w)), 100.0 * len(l2w) / len(both)), flush=True)
    if w2l:
        a = st.mean(trade[lo][k] for k in w2l)
        b = st.mean(trade[hi][k] for k in w2l)
        print("\n   ★ **버린 것의 크기** — 그 %s건의 +20 에서의 평균 수익 **%+.2f%%**"
              % ("{:,}".format(len(w2l)), a), flush=True)
        print("      (+30 으로 하면 그 거래들이 평균 %+.2f%% 가 된다)" % b, flush=True)
    keep = [k for k in both if trade[lo][k] > 0 and trade[hi][k] > 0]
    if keep:
        print("\n   ★ **얻은 것의 크기** — 둘 다 이긴 %s건에서"
              % "{:,}".format(len(keep)), flush=True)
        print("      +20 평균 %+.2f%%  →  +30 평균 **%+.2f%%**  (**%+.2f%%p**)"
              % (st.mean(trade[lo][k] for k in keep), st.mean(trade[hi][k] for k in keep),
                 st.mean(trade[hi][k] - trade[lo][k] for k in keep)), flush=True)
    tl = st.mean(trade[lo][k] for k in both)
    th = st.mean(trade[hi][k] for k in both)
    print("\n   **후보 전체 평균**  +20 %+.3f%%  →  +30 **%+.3f%%**  (%+.3f%%p)"
          % (tl, th, th - tl), flush=True)

    (r91.OUT / "134-confirm30.json").write_text(
        json.dumps({"stat": {str(k): v for k, v in stat.items()},
                    "w2l": len(w2l), "l2w": len(l2w), "both": len(both),
                    "BI": bool(okw and oke)},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 134-confirm30.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
