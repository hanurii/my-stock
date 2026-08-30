# -*- coding: utf-8 -*-
"""113 — **손절이 −8%인데 계좌 낙폭이 −46%인 이유** (사용자 물음 2026-08-30)

> 「미너비니는 최대 손절을 −10% 이상 가져가지 않는다고 했는데 최대 낙폭이 −46%나 되는 이유가 뭡니까」

# 재는 것 — 넷
```
㉮ 손절이 «실제로» −8%에서 끝나나          손절 거래의 손실 분포
㉯ 계좌 낙폭이 «언제» 났나                 −46% 구간의 시작·끝·걸린 날
㉰ 그 기간에 «무슨 일»이 있었나            승률 · 연속 손실 · 매수 수
㉱ 산수와 맞나                            (1−x)^n = 0.54 를 푼 n 과 견준다
```
🚨 판정 아님. **기전 진단**이다.
"""
from __future__ import annotations

import importlib.util as _u
import math
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pyr_trigger as pt                                          # noqa: E402
_s = _u.spec_from_file_location("r91", HERE / "91-us-out-of-sample.py")
r91 = _u.module_from_spec(_s)
_s.loader.exec_module(r91)

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))


def main() -> int:
    n_seed = 12 if "--quick" in sys.argv else 60
    print("=" * 100, flush=True)
    print("113 — **손절이 −8%%인데 계좌 낙폭이 −46%%인 이유** · 기전 진단", flush=True)
    print("=" * 100, flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음", flush=True)
        return 2

    # ── ㉮ 손절이 «실제로» 얼마에서 끝나나 ───────────────────────────
    losses, wins = [], []
    for p in [q for y in sorted(by2) for q in by2[y]]:
        t = pt.resolve_trade(p, ft="limit", fs="market", stop=r91.STOP,
                             target=r91.TARGET, shares=(1.0,), add_stop="floor_entry")
        m = t["masks"][()]
        epx = t["entry_px"]
        if not epx or not m["exits"]:
            continue
        w = sum(x[1] for x in m["exits"]) or 1.0
        r = (sum(x[1] * x[2] for x in m["exits"]) / w / epx - 1.0) * 100.0
        (wins if r > 0 else losses).append(r)
    ls = sorted(losses)
    print("# ㉮ **손절이 «실제로» −8%%에서 끝나나** (규약 손절 −%.0f%%)" % r91.STOP,
          flush=True)
    print("  지는 거래 %s건 · 평균 **%+.2f%%** · 중앙 %+.2f%%"
          % ("{:,}".format(len(ls)), st.mean(ls), st.median(ls)), flush=True)
    print("  더 깨진 쪽 — 하위25%% %+.2f%% · 하위10%% %+.2f%% · **최악 %+.2f%%**"
          % (ls[len(ls) // 4], ls[len(ls) // 10], ls[0]), flush=True)
    worse = 100.0 * sum(1 for x in ls if x < -r91.STOP - 0.5) / len(ls)
    print("  🚨 규약(−%.0f%%)보다 **더 깨진 비율 = %.1f%%**  (갭 하락 · 시장가 체결)"
          % (r91.STOP, worse), flush=True)
    print("  이기는 거래 %s건 · 평균 %+.2f%%\n"
          % ("{:,}".format(len(wins)), st.mean(wins)), flush=True)

    # ── ㉯㉰ 낙폭이 언제·어떻게 났나 ─────────────────────────────────
    ev, _x, _y = r91.replay(by2)
    rs = r91.sim(ev, n_seed)
    print("# ㉯ **−46%% 낙폭이 «언제» 났나** (운의 번호 %d판)" % n_seed, flush=True)
    spans = []
    for x in rs:
        cv = [(d, v) for d, v in x["curve"]]
        peak, pd_, mdd, s, e = cv[0][1], cv[0][0], 0.0, cv[0][0], cv[0][0]
        for d, v in cv:
            if v > peak:
                peak, pd_ = v, d
            dd = v / peak - 1.0
            if dd < mdd:
                mdd, s, e = dd, pd_, d
        spans.append((mdd * 100, s, e))
    spans.sort()
    med = spans[len(spans) // 2]
    print("  낙폭 중앙 **%.1f%%** — 대표 경로: **%s → %s**" % (med[0], med[1], med[2]), flush=True)
    from collections import Counter
    cs = Counter(s[1][:4] for s in spans)
    print("  낙폭이 «시작»한 해 — %s"
          % (" · ".join("%s년 %d판" % (y, n) for y, n in cs.most_common(4))), flush=True)
    ce = Counter(s[2][:4] for s in spans)
    print("  낙폭이 «바닥»친 해 — %s"
          % (" · ".join("%s년 %d판" % (y, n) for y, n in ce.most_common(4))), flush=True)

    # 그 구간의 승률
    a, b = med[1], med[2]
    sub = [t for t in ev if a <= t["entry_date"] <= b]
    rr = []
    for t in sub:
        m = t["masks"][()]
        rr.append(1 if m["result"] == "win" else 0)
    days = (r91._ord(b) - r91._ord(a))
    print("\n# ㉰ **그 기간에 무슨 일이 있었나** (%s ~ %s · %d일 ≈ %.1f년)"
          % (a, b, days, days / 365.0), flush=True)
    print("  그 사이 매수 후보 %s건 · **이긴 비율 %.1f%%** (전 기간 %.1f%%)"
          % ("{:,}".format(len(sub)), 100.0 * sum(rr) / max(1, len(rr)),
             100.0 * len(wins) / (len(wins) + len(ls))), flush=True)
    print("  운의 번호 %d판 중 그 기간의 «최대 연속 손실» 중앙 = **%d회**"
          % (n_seed, st.median(x["max_loss_streak"] for x in rs)), flush=True)

    # ── ㉱ 산수와 맞나 ──────────────────────────────────────────────
    print("\n# ㉱ **산수와 맞나**", flush=True)
    print("  5칸이니 한 종목 −8%%면 계좌는 **−1.6%%**", flush=True)
    print("  다섯 칸이 «모두» 손절 → 한 바퀴에 계좌 **−8%%**", flush=True)
    n = math.log(1 - abs(med[0]) / 100.0) / math.log(0.92)
    print("  −%.0f%% 가 되려면 그 바퀴가 **%.1f 번** 겹쳐야 한다  ((1−0.08)^n = %.2f)"
          % (abs(med[0]), n, 1 - abs(med[0]) / 100.0), flush=True)
    print("  보유 중앙 34일이니 %.1f 바퀴 ≈ **%.0f 거래일 ≈ %.1f 년**"
          % (n, n * 34, n * 34 / 252.0), flush=True)
    print("  실제 낙폭 기간 = **%.1f 년**  →  %s"
          % (days / 365.0, "산수와 «같은 자릿수»" if 0.3 < (days / 365.0) / (n * 34 / 252.0) < 3
             else "🚨 산수와 «어긋난다» — 다른 기전이 있다"), flush=True)

    print("\n" + "=" * 100, flush=True)
    print("★ 읽는 법 — **손절은 «한 종목»의 상한이지 «계좌»의 상한이 아니다.**", flush=True)
    print("  계좌 낙폭 = (한 바퀴 손실) × (연속으로 깨진 바퀴 수)", flush=True)
    print("  🚨 그리고 우리는 **「연속으로 깨지면 규모를 줄인다」를 «안 켰다»** —", flush=True)
    print("     미너비니는 그걸 «한다»고 말한다(노출 사다리). 77·99 에서 재봤고 도움이 안 됐다.",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
