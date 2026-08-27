# -*- coding: utf-8 -*-
"""86v 부속 — **㉱ 의 「규칙을 쓰면 낫다」에 «가짜약» 대조를 붙인다.**

왜
--
86 의 ㉱ 는 네 «뜻 있는» 규칙을 무작위(a)와 견줬고 셋이 이겼다. 그래서
**「규칙을 쓴 것이지 그 규칙이 아니다」**로 닫았다. 그런데 그 문장은
**「아무 «뜻 있는» 규칙이나 낫다」**를 뜻하고, 그건 아직 안 재 봤다.

빠진 대조가 있다 — **«뜻 없는» 결정적 규칙**.
`mk()` 가 하는 일은 결국 **「후보의 20%를 «먼저» 놓고 나머지는 난수」**다.
그 20%를 **아무 뜻 없는 기준**(종목코드 해시)으로 골라도 같은 이득이 나오면,
㉱ 가 잰 것은 «특징»이 아니라 **「결정적으로 20%를 앞세우는 것」 자체**다.

  ㉠ 가짜약 12개 — `hash(salt|code) % 5 == 0` 인 20% 를 먼저 (뜻 없음 · 결정적)
  ㉡ 알파벳 앞쪽 20% 를 먼저 (뜻 없음 · 결정적 · 해시와 다른 결)
  ㉢ 「20% 를 «뒤»로」 — 방향을 뒤집어도 이득이 나오나 (나오면 방향조차 무의미)
  ㉣ 두뇌 세션 물음: 대조군을 «1분위 먼저»로 통일한 것이 중립인가 → 양방향을 다 돈다

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/86v-placebo.py [N_SEED]
"""
from __future__ import annotations

import hashlib
import importlib.util as _u
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r86", HERE / "86-slots-and-tails.py")
r86 = _u.module_from_spec(_s)
_s.loader.exec_module(r86)
r85, r84, r74, r41, sl = r86.r85, r86.r84, r86.r74, r86.r41, r86.sl

NS = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 200
TIE = r86.TIE


def hr(t):
    print("\n" + "=" * 100, flush=True)
    print(t, flush=True)
    print("=" * 100, flush=True)


def key(t):
    return (t["scan_date"], t["code"], t["pattern"])


def pairstat(eq, beq):
    pr = sorted(((1 + x / 100) / (1 + y / 100) - 1) * 100 for x, y in zip(eq, beq))
    return pr[len(pr) // 2], 100.0 * sum(1 for x in pr if x > 0) / len(pr)


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    by2, ev, blk, pmap = r84.load()
    rows, _m = r85.build_features(ev, pmap)
    ins = [rows[key(t)] for t in ev if t["entry_date"] < r85.SPLIT and key(t) in rows]
    cuts = {}
    for f in TIE:
        xs = sorted(r[f] for r in ins if not r85._nan(r[f]))
        cuts[f] = xs[int(len(xs) / 5)]

    base = r86.run(ev, 5, NS, cap=r74.CAP)
    beq = [r["equity_pct"] for r in base]
    print("기준선 (a) 무작위 — 자산 중앙 %+.2f%%" % st.median(beq), flush=True)

    def mk_feat(f, hi_first):
        c = cuts[f]

        def fn(seed, t):
            r = rows.get(key(t))
            v = None if r is None else r[f]
            rank = 1 if (v is None or r85._nan(v)) else (
                0 if ((v >= c) if hi_first else (v < c)) else 1)
            return (rank, sl.order_key(seed, t))
        return fn

    def mk_hash(salt, first=True):
        def fn(seed, t):
            h = int(hashlib.md5(("%s|%s" % (salt, t["code"])).encode()).hexdigest()[:8], 16)
            sel = (h % 5 == 0)
            rank = (0 if sel else 1) if first else (1 if sel else 0)
            return (rank, sl.order_key(seed, t))
        return fn

    def frac_sel(fn):
        return 100.0 * sum(1 for t in ev if fn(0, t)[0] == 0) / len(ev)

    # ── ㉠㉡ 가짜약 ──────────────────────────────────────────────────────
    hr("㉠㉡ **가짜약 대조** — «뜻 없는» 결정적 규칙도 이기나")
    print("  %-30s %7s %11s %11s %10s"
          % ("규칙", "고른 %", "자산중앙", "짝 중앙", "이기는 판"), flush=True)
    print("  " + "-" * 74, flush=True)
    pl = []
    for i in range(12):
        fn = mk_hash("salt%d" % i)
        rs = r86.run(ev, 5, NS, order_fn=fn, cap=r74.CAP)
        eq = [r["equity_pct"] for r in rs]
        m, w = pairstat(eq, beq)
        pl.append((m, w))
        print("  %-30s %6.1f%% %+10.2f%% %+10.2f%% %9.1f%%"
              % ("가짜약 #%d (해시 20%% 먼저)" % i, frac_sel(fn), st.median(eq), m, w),
              flush=True)

    def alpha(seed, t):
        return (0 if t["code"][:1] <= "C" else 1, sl.order_key(seed, t))
    rs = r86.run(ev, 5, NS, order_fn=alpha, cap=r74.CAP)
    eq = [r["equity_pct"] for r in rs]
    ma, wa = pairstat(eq, beq)
    print("  %-30s %6.1f%% %+10.2f%% %+10.2f%% %9.1f%%"
          % ("알파벳 A~C 먼저", frac_sel(alpha), st.median(eq), ma, wa), flush=True)

    a = sorted(m for m, _w in pl)
    n = len(a)
    print("\n  ★ **가짜약 12판** — 보통 %+.2f%% · 최소 %+.2f%% · **최대 %+.2f%%** · "
          "이기는 판이 50%% 넘은 판 %d/12"
          % (a[n // 2], a[0], a[-1], sum(1 for _m, w in pl if w > 50)), flush=True)
    print("     (알파벳판 %+.2f%% 도 같은 자리에 놓고 본다)" % ma, flush=True)

    # ── ㉣ 특징 넷 × 양방향 ────────────────────────────────────────────
    hr("㉣ 두뇌 물음 — 대조군을 «1분위 먼저»로 통일한 것이 중립인가 (양방향을 다 돈다)")
    print("  %-30s %7s %11s %11s %10s %s"
          % ("규칙", "고른 %", "자산중앙", "짝 중앙", "이기는 판", "가짜약 대비"), flush=True)
    print("  " + "-" * 88, flush=True)
    F = {}
    for f in TIE:
        for hi in (False, True):
            fn = mk_feat(f, hi)
            rs = r86.run(ev, 5, NS, order_fn=fn, cap=r74.CAP)
            eq = [r["equity_pct"] for r in rs]
            m, w = pairstat(eq, beq)
            F[(f, hi)] = m
            pct = 100.0 * sum(1 for x in a if x < m) / n
            print("  %-30s %6.1f%% %+10.2f%% %+10.2f%% %9.1f%% %10s"
                  % ("%s %s 먼저" % (f, "5분위" if hi else "1분위"), frac_sel(fn),
                     st.median(eq), m, w,
                     "%.0f 백분위" % pct), flush=True)
    print("\n  ★ 「가짜약 대비」가 50 근처면 그 규칙은 **가짜약과 구분 안 된다**.", flush=True)
    print("    등록된 (b) `prior6m 1분위` 가 가짜약 분포의 어디인가가 ㉱ 의 진짜 판정이다.",
          flush=True)
    pb = F[("prior6m", False)]
    pct = 100.0 * sum(1 for x in a if x < pb) / n
    print("\n  → **(b) prior6m 1분위 %+.2f%% = 가짜약 12판 중 %.0f 백분위**" % (pb, pct),
          flush=True)
    if pct < 90:
        print("     🚨 **가짜약과 구분되지 않는다** — ㉱ 의 P★ 는 «특징»이 아니라",
              flush=True)
        print("        **「결정적으로 20%를 앞세우는 것」 자체**를 잰 것일 수 있다.", flush=True)
    else:
        print("     → 가짜약 위에 있다. 「규칙을 쓴 것」 이상의 무언가가 있다.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
