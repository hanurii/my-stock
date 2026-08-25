# -*- coding: utf-8 -*-
"""61b — **짝이 맞는 「효과 없다고 쳤을 때」 검정**.

🚨 61번의 검정은 **섹터 라벨만** 섞었다. 그건 **S1 용**이다.
   S3 = S1 ∧ S2 인데 S2 부분(그룹 내 상위 20%)은 가짜 판에 «없었다» →
   **가진 필터가 다른 둘을 견줬다.** 사전등록 §3 에 ⚠️ 로 적어 놓고 «구현을 빠뜨렸다».

여기서는 **월별 수익률 «값»을 종목들 사이에서 섞는다.**
- 보존: 섹터 구성 · 섹터 크기 · 수익률 분포 · **필터의 선택 강도**
- 파괴: 「어느 종목이 올랐나」 — **즉 우리가 재려는 신호 그 자체**

이러면 S1·S2·S3 «각각»에 짝이 맞는 판이 나온다.
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import slot_sim_frac as sf                                    # noqa: E402

_s = _u.spec_from_file_location("r41", HERE / "41-round1-exits.py")
r41 = _u.module_from_spec(_s)
_s.loader.exec_module(r41)

_s2 = _u.spec_from_file_location("r61", HERE / "61-selection-leaders.py")
r61 = _u.module_from_spec(_s2)
_s2.loader.exec_module(r61)

OUT = ROOT / ".cache" / "bt5y" / "out"
N_NULL = 200
N_SEED_NULL = 12
N_SEED = 200


def month_returns(monthly, sector, months, lookback=6):
    """월 -> [(티커, 6개월 수익률)] · 섹터는 따로."""
    out = {}
    for ym in months:
        base = r61.prev_ym(ym, lookback)
        v = []
        for t, d in monthly.items():
            a, b = d.get(base), d.get(ym)
            if a and b and a > 0 and sector.get(t):
                v.append((t, b / a - 1))
        if v:
            out[ym] = v
    return out


def make_flags(mret, sector, shuffle_rnd=None):
    """월별 (상위 섹터 집합, 종목 -> 자기 섹터 내 백분위)."""
    sec_top, in_pct = {}, {}
    for ym, v in mret.items():
        if shuffle_rnd is not None:
            vals = [r for _t, r in v]
            shuffle_rnd.shuffle(vals)          # 🚨 값만 섞는다 — 구성은 그대로
            v = [(t, vals[i]) for i, (t, _r) in enumerate(v)]
        bysec = defaultdict(list)
        for t, r in v:
            bysec[sector[t]].append((r, t))
        smean = {s: st.mean(x for x, _ in lst) for s, lst in bysec.items()
                 if len(lst) >= 5}
        sec_top[ym] = set(sorted(smean, key=lambda s: -smean[s])[:r61.TOP_SECTORS])
        pct = {}
        for s, lst in bysec.items():
            lst.sort(key=lambda x: -x[0])
            n = len(lst)
            for i, (_r, t) in enumerate(lst):
                pct[t] = i / n
        in_pct[ym] = pct
    return sec_top, in_pct


def keep(ev0, sector, sec_top, in_pct, kind):
    out = []
    for e in ev0:
        s = sector.get(e["code"])
        if not s:
            out.append(e)
            continue
        ym = r61.prev_ym(e["scan_date"][:7], 1)
        top = sec_top.get(ym)
        if top is None:
            out.append(e)
            continue
        a = s in top
        b = in_pct.get(ym, {}).get(e["code"], 1.0) <= r61.TOP_PCT
        if (a if kind == "S1" else (b if kind == "S2" else (a and b))):
            out.append(e)
    return out


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 `BT_Y0=2017` 을 주지 않았다 — 멈춘다.", flush=True)
        return 2
    by, _m = r41.v39.load_paths()
    r41.TARGET_FILL, r41.STOP_FILL = "close", "close"
    ev0 = None
    for vname, fn, _l, _h in r41.VARIANTS:
        if vname == "1a":
            ev0, _b = r41.replay(by, fn)
    pack = json.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({ym for d in monthly.values() for ym in d if ym >= "2016-12"})
    mret = month_returns(monthly, sector, months)
    print("=" * 80, flush=True)
    print("61b — **짝이 맞는 「효과 없다고 쳤을 때」 검정**", flush=True)
    print("=" * 80, flush=True)
    print("월 %d개 · 수익률 있는 종목 중앙 %d개/월"
          % (len(mret), st.median(len(v) for v in mret.values())), flush=True)

    reg = (0.0, 0.0)

    def eq_of(ev, n):
        with r41.Cost(*reg):
            rs = [sf.sim_frac(ev, slots=5, seed=i, sizing="cash")["equity_pct"]
                  for i in range(n)]
        return st.median(rs)

    base = eq_of(ev0, N_SEED)
    print("R0 자산 중앙 %+.2f%%" % base, flush=True)

    real_top, real_pct = make_flags(mret, sector)
    obs, ncount = {}, {}
    for kind in ("S1", "S2", "S3"):
        ev = keep(ev0, sector, real_top, real_pct, kind)
        ncount[kind] = len(ev)
        obs[kind] = eq_of(ev, N_SEED) - base
        print("관측 %s — 진입 %5d · R0 대비 **%+.2f%%p**" % (kind, len(ev), obs[kind]),
              flush=True)

    rnd = random.Random(610826)
    null = {k: [] for k in ("S1", "S2", "S3")}
    nsel = {k: [] for k in ("S1", "S2", "S3")}
    for i in range(N_NULL):
        st_, ip_ = make_flags(mret, sector, shuffle_rnd=rnd)
        for kind in ("S1", "S2", "S3"):
            ev = keep(ev0, sector, st_, ip_, kind)
            nsel[kind].append(len(ev))
            null[kind].append(eq_of(ev, N_SEED_NULL) - base)
        if (i + 1) % 50 == 0:
            print("  ... %d/%d" % (i + 1, N_NULL), flush=True)

    print("\n%-6s %10s %10s %12s %12s %12s   %s"
          % ("칸", "관측", "진입", "가짜 보통", "**가짜 95%**", "가짜 최대", "판정"),
          flush=True)
    RES = {}
    for kind in ("S1", "S2", "S3"):
        v = sorted(null[kind])
        p95 = v[int(N_NULL * .95)]
        ok = obs[kind] > p95
        print("%-6s %+9.2f%%p %10d %+11.2f%%p %+11.2f%%p %+11.2f%%p   **%s**"
              % (kind, obs[kind], ncount[kind], v[N_NULL // 2], p95, v[-1],
                 "넘음" if ok else "범위 안 — 「고른 것」과 구분 안 됨"), flush=True)
        print("       (가짜 판 진입 수 중앙 %d — 관측 %d 와 %s)"
              % (st.median(nsel[kind]), ncount[kind],
                 "비슷" if abs(st.median(nsel[kind]) - ncount[kind])
                 < 0.25 * ncount[kind] else "🚨 다르다 — 짝이 안 맞는다"), flush=True)
        RES[kind] = {"obs": obs[kind], "n_entry": ncount[kind],
                     "null_median": v[N_NULL // 2], "null_p95": p95,
                     "null_max": v[-1], "null_n_median": st.median(nsel[kind]),
                     "pass": ok}
    (OUT / "61b-matched-null.json").write_text(
        json.dumps(RES, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 61b-matched-null.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
