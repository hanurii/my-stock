# -*- coding: utf-8 -*-
"""82v 부속 — **82 가 찍은 두 숫자를 «내 경로»로 그대로 재현**하고, 그 둘이
«한 판짜리 통계»임을 보인다.

  ㉠ E 의 0/10 은 `head_curves[100]` 한 판이다 → seed 100 이 정말 0/10 인가
  ㉡ B 의 관측 +110.92% 는 `seed 0~4` 한 판이다 → 그 값이 «자기 분포»의 어디인가

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/82v-anchor.py
"""
from __future__ import annotations

import bisect
import importlib.util as _u
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r82", HERE / "82-index-switch.py")
r82 = _u.module_from_spec(_s)
_s.loader.exec_module(r82)
r74, r41, sl = r82.r74, r82.r41, r82.sl

N = 200


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 BT_Y0=2017 필요")
        return 2
    by2, *_ = r74.load_filtered()
    pmap = {(p["scan_date"], p["code"], p["pattern"]): p
            for ps in by2.values() for p in ps}
    ev0, _b, _s2 = r74.replay_masks(by2, (1.0,), "floor_entry")
    cal, v = r82.load_index("US500")
    ipx_d = dict(zip(cal, v))
    ci = sorted(ipx_d)

    def ipx(d):
        return ipx_d[ci[max(0, bisect.bisect_right(ci, d) - 1)]]

    on, first = r82.month_flags(cal, r82.ma_above(cal, v, 200))
    idx_hold, no_entry, _n = r82.spans(cal, on)
    ev_sw, _c, _bk, _g = r82.cut_events(ev0, pmap, no_entry, idx_hold, cal)

    with r41.Cost(*r82.COST):
        sw = [sl.sim_lots(ev_sw, seed=s, slots=r82.SLOTS, risk=r82.RISK, cap=r82.CAP,
                          reserve=False, fill_rule="truncate", cash_rule="per_slot")
              for s in range(N)]
        base = [sl.sim_lots(ev0, seed=s, slots=r82.SLOTS, risk=r82.RISK, cap=r82.CAP,
                            reserve=False, fill_rule="truncate", cash_rule="per_slot")
                for s in range(N)]
    head = [r82.overlay_fold(r82.settled_curve(r), idx_hold, ipx,
                             r82.HEADLINE_COST, cal)[0] for r in sw]
    eqs = [r82.eq_of(c) for c in head]

    w0, w1 = base[0]["curve"][0][0], base[0]["curve"][-1][0]
    yi = r82._year_factors([(d, ipx(d) / ipx(w0)) for d in cal if w0 <= d <= w1])

    def wins(cv):
        yo = r82._year_factors(cv)
        ys = sorted(set(yo) & set(yi))
        return sum(1 for y in ys if r82._prod(yo, skip=y) > r82._prod(yi, skip=y)), len(ys)

    print("=" * 96)
    print("㉠ E — 82 는 `head_curves[len//2]` = **seed %d** 한 판을 쓴다" % (N // 2))
    w100, ny = wins(head[N // 2])
    print("   내 seed %d → **%d / %d**   (82 가 적은 값: 0 / 10) → **%s**"
          % (N // 2, w100, ny, "재현" if (w100, ny) == (0, 10) else "🚨 불일치"))
    allw = [wins(c)[0] for c in head]
    ge8 = sum(1 for x in allw if x >= 8)
    ge9 = sum(1 for x in allw if x >= 9)
    print("   seed %d판 전체 — ≥8/10 인 판 **%d개(%.1f%%)** · ≥9/10 **%d개(%.1f%%)** · 최대 %d"
          % (N, ge8, 100.0 * ge8 / N, ge9, 100.0 * ge9 / N, max(allw)))
    print("   ★ 즉 「E = 0/10」은 **성질이 아니라 한 판**이다.")
    print("     70번의 「9/9」도 이 자료에서 %.1f%% 확률로 나온다 — 「정반대」로 못 읽는다."
          % (100.0 * ge9 / N))

    print("\n" + "=" * 96)
    print("㉡ B — 82 의 관측 +110.92%% 는 **seed 0~4** 한 판이다")
    obs5 = st.median(eqs[:5])
    print("   내 seed 0~4 중앙 → **%+.2f%%**   (82 가 적은 값: +110.92%%) → **%s**"
          % (obs5, "재현" if abs(obs5 - 110.92) < 0.02 else "🚨 불일치"))
    print("   seed %d판 중앙(참값 자리) → **%+.2f%%**" % (N, st.median(eqs)))
    rnd = random.Random(7)
    boot = sorted(st.median(rnd.sample(eqs, 5)) for _ in range(20000))
    pct = 100.0 * sum(1 for x in boot if x <= obs5) / len(boot)
    print("   「seed 5개 중앙」의 분포(2만번 재표집): 중앙 %+.2f%% · 5%% %+.2f%% · 95%% %+.2f%%"
          % (st.median(boot), boot[1000], boot[19000]))
    print("   → **82 가 쓴 +110.92%% 는 자기 분포의 %.1f 백분위**다 (아래쪽 꼬리)." % pct)
    print("\n   ★ 무작위 대조(300판)도 «seed 5개 중앙»이므로 같은 잡음을 갖는다.")
    print("     그러니 «중앙끼리» 견줘야 한다:")
    print("       진짜 깃발 중앙 %+.2f%%   vs   무작위 섞기 보통 +144.79%% · 회전 보통 +180.66%%"
          % st.median(boot))
    print("     → 「진짜가 무작위의 보통값에도 못 미친다」는 **한 판을 분포와 견준 것**이다.")

    print("\n" + "=" * 96)
    print("㉢ 흔들리지 «않는» 것 — 200판을 다 쓰는 자 (참고)")
    b = [r["equity_pct"] for r in base]
    pr = sorted(((1 + a / 100) / (1 + c / 100) - 1) * 100 for a, c in zip(eqs, b))
    print("   A  스위칭 중앙 %+.2f%% vs 바탕 %+.2f%%" % (st.median(eqs), st.median(b)))
    print("   F  짝 %d판 중앙 %+.2f%% · 이기는 판 %.1f%%"
          % (N, pr[N // 2], 100.0 * sum(1 for x in pr if x > 0) / N))
    print("   → A·C·D·F 는 **200판을 다 쓴다**. B·E 만 한 판에 걸려 있었다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
