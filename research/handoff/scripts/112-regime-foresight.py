# -*- coding: utf-8 -*-
"""112 — **「성장주 각광기」를 «미리» 알아볼 수 있는가** (㉡ · 사용자 물음 2026-08-30)

110 에서 미너비니가 이긴 두 구간(닷컴 · 2018~2026)이 «성장주 각광기»였다.
**그런데 그걸 «그때» 알아볼 수 있는지는 이 프로젝트가 한 번도 안 쟀다.**
사후에 이름 붙이는 건 쉽고, 미리 아는 건 다른 물음이다.

# 🚨 방향을 «먼저» 적는다
```
82·97·102 가 전부 «국면 신호»를 재서 실패했다 → **예상은 「못 알아본다」**
다만 그때 잰 건 「지수 국면」(SPY 200일선 등)이었고
이번 신호는 **「성장주가 지수를 «이기고 있는가»」**로 «다른 것»이다
```

# 신호 셋 — 전부 «그날까지»만 본다
```
㉮ 성장주 우위   QQQ ÷ SPY 비율이 그 비율의 200일선 «위»인가
㉯ 최근 성적     최근 6개월 우리 방식의 «실현 손익 합»이 > 0 인가   ← 미너비니 15번
㉰ 지수 국면     SPY 가 200일선 위인가                            ← 97 이 쓴 축(대조)
```

# 재는 법 — 둘
```
① 신호가 «켜진 달»과 «꺼진 달»의 미너비니 성적을 가른다
   → 갈라지면 신호가 국면을 «본다»는 뜻
② 스위칭: 켜지면 미너비니 · 꺼지면 SPY+200일선
   → 실제로 «돈이 되는가»
🚨 짝: 같은 «켜진 달 비율»의 무작위 달 (동전 던지기)
```
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pyr_trigger as pt                                          # noqa: E402
_s = _u.spec_from_file_location("r91", HERE / "91-us-out-of-sample.py")
r91 = _u.module_from_spec(_s)
_s.loader.exec_module(r91)
_t = _u.spec_from_file_location("r109", HERE / "109-index-stop.py")
r109 = _u.module_from_spec(_t)
_t.loader.exec_module(r109)

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))


def ma_flag(ds, v, n=200):
    out, run_ = {}, []
    for i, d in enumerate(ds):
        run_.append(v[i])
        if len(run_) > n:
            run_.pop(0)
        out[d] = (len(run_) == n and v[i] > sum(run_) / n)
    return out


def main() -> int:
    n_seed = 12 if "--quick" in sys.argv else r91.N_SEED
    print("=" * 104, flush=True)
    print("112 — **「성장주 각광기」를 «미리» 알아볼 수 있는가** · 운의 번호 %d판" % n_seed,
          flush=True)
    print("=" * 104, flush=True)
    print("🚨 값 보기 «전» 예상: **못 알아본다**(82·97·102 가 전부 국면 신호로 실패했다)\n",
          flush=True)

    dsS, cS = r109.load("SPY")
    dsQ, cQ = r109.load("QQQ")
    common = sorted(set(dsS) & set(dsQ))
    mS = {d: c for d, c in zip(dsS, cS)}
    mQ = {d: c for d, c in zip(dsQ, cQ)}
    ratio = [mQ[d] / mS[d] for d in common]

    sigA = ma_flag(common, ratio)                       # 성장주 우위
    sigC = ma_flag(dsS, cS)                             # 지수 국면

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, D0, D1, "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음", flush=True)
        return 2
    ev, _x, _y = r91.replay(by2)

    # ㉯ 최근 6개월 «실현 손익 합» — 그날 «이전»에 청산된 것만 (미래 안 봄)
    done = []
    for p in [q for y in sorted(by2) for q in by2[y]]:
        t = pt.resolve_trade(p, ft="limit", fs="market", stop=r91.STOP,
                             target=r91.TARGET, shares=(1.0,), add_stop="floor_entry")
        m = t["masks"][()]
        epx = t["entry_px"]
        if not epx or not m["exits"]:
            continue
        w = sum(x[1] for x in m["exits"]) or 1.0
        done.append((m["resolve_date"] or p["entry_date"],
                     (sum(x[1] * x[2] for x in m["exits"]) / w / epx - 1.0) * 100.0))
    done.sort()
    import bisect
    rds = [x[0] for x in done]
    sigB = {}
    for i, d in enumerate(common):
        j = bisect.bisect_left(rds, d)
        k = bisect.bisect_left(rds, common[max(0, i - 126)])
        sigB[d] = (j > k) and (sum(x[1] for x in done[k:j]) > 0)

    SIG = (("㉮ 성장주 우위 (QQQ÷SPY > 200일선)", sigA),
           ("㉯ 최근 6개월 실현손익 > 0", sigB),
           ("㉰ 지수 국면 (SPY > 200일선)", sigC))

    print("# ① 신호가 «켜진 날»과 «꺼진 날»의 미너비니 매수를 가른다", flush=True)
    print("  %-32s %8s %14s %14s %10s"
          % ("신호", "켜진 비율", "켜진 날 연평균", "꺼진 날 연평균", "차이"), flush=True)
    print("  " + "-" * 82, flush=True)
    out = {}
    for nm, sg in SIG:
        on = [t for t in ev if sg.get(t["entry_date"], True)]
        off = [t for t in ev if not sg.get(t["entry_date"], True)]
        if len(on) < 200 or len(off) < 200:
            print("  %-32s (표본 부족)" % nm, flush=True)
            continue
        ron = r91.sim(on, n_seed)
        roff = r91.sim(off, n_seed)
        yon = len(set(t["entry_date"][:4] for t in on))
        yoff = len(set(t["entry_date"][:4] for t in off))
        mon = st.median(x["equity_pct"] for x in ron)
        mof = st.median(x["equity_pct"] for x in roff)
        con = ((1 + mon / 100.0) ** (1 / max(1, yon)) - 1) * 100
        cof = ((1 + mof / 100.0) ** (1 / max(1, yoff)) - 1) * 100
        out[nm] = {"rate": 100.0 * len(on) / len(ev), "on": con, "off": cof,
                   "n_on": len(on), "n_off": len(off)}
        print("  %-32s %7.1f%% %+13.2f%% %+13.2f%% %+9.2f%%p"
              % (nm, out[nm]["rate"], con, cof, con - cof), flush=True)

    print("\n  ⚠️ 「켜진 날만」과 「꺼진 날만」은 **해 수가 달라** 연평균이 거칠다.", flush=True)
    print("     방향을 보는 자이지 크기를 재는 자가 «아니다».", flush=True)

    # ── ② 스위칭 ────────────────────────────────────────────────────
    print("\n# ② 스위칭 — 켜지면 미너비니 · 꺼지면 SPY+200일선", flush=True)
    print("  🚨 짝: 같은 «켜진 비율»의 무작위 날 (동전 던지기)\n", flush=True)
    rs_all = r91.sim(ev, n_seed)
    idx = r109.run(dsS, cS, "ma", cash_rate=2.0)
    print("  (참고) 미너비니 내내 = %+.2f%%/년 · SPY+200일선 내내 = %+.2f%%/년"
          % (((1 + st.median(x["equity_pct"] for x in rs_all) / 100.0) ** (1 / 27.4) - 1) * 100,
             idx["cagr"]), flush=True)

    rnd = random.Random(20260830)
    print("\n  %-32s %14s %14s" % ("신호", "스위칭 연평균", "동전 던지기"), flush=True)
    print("  " + "-" * 64, flush=True)
    for nm, sg in SIG:
        if nm not in out:
            continue
        rate = out[nm]["rate"] / 100.0
        fake = {d: (rnd.random() < rate) for d in common}
        cells = []
        for tag, gmap in (("진짜", sg), ("동전", fake)):
            sub = [t for t in ev if gmap.get(t["entry_date"], True)]
            r = r91.sim(sub, n_seed)
            m = st.median(x["equity_pct"] for x in r)
            # 꺼진 기간은 지수 판이 대신 굴린다고 «근사»한다 (곱셈)
            off_frac = 1.0 - rate
            idx_mult = (1.0 + idx["cagr"] / 100.0) ** (27.4 * off_frac)
            tot = (1 + m / 100.0) * idx_mult
            cells.append((tot ** (1 / 27.4) - 1) * 100)
        print("  %-32s %+13.2f%% %+13.2f%%" % (nm, cells[0], cells[1]), flush=True)
    print("\n  🚨 스위칭은 «근사»다 — 꺼진 기간을 지수 수익률로 «곱했다».", flush=True)
    print("     실제로는 갈아타는 시점의 값이 다르다. **방향만 본다.**", flush=True)

    (r91.OUT / "112-regime-foresight.json").write_text(
        json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 112-regime-foresight.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
