# -*- coding: utf-8 -*-
"""61 — **선별 축: 주도 그룹의 주도주**. 사전등록: `tasks/61-selection-leaders.md`

🚨 룩어헤드 차단 — 6개월 수익률은 **스캔일 «이전» 월말**까지만 쓴다(그 달은 안 쓴다).
🚨 「아무런 효과 없는 가정으로 돌려 보기」를 **설계에 넣었다**(60번에서 배운 것).

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python 61-selection-leaders.py
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

import dataaxis as da                                         # noqa: E402
import slot_sim_frac as sf                                    # noqa: E402

_s = _u.spec_from_file_location("r41", HERE / "41-round1-exits.py")
r41 = _u.module_from_spec(_s)
_s.loader.exec_module(r41)

OUT = ROOT / ".cache" / "bt5y" / "out"
N_SEED = 200
N_NULL = 200
LOOKBACK = 6              # 개월
TOP_SECTORS = 3
TOP_PCT = 0.20            # 그룹 내 상위 20%
HLD0, HLD1 = "2017-01-01", "2021-01-31"


def prev_ym(ym, k):
    y, m = int(ym[:4]), int(ym[5:])
    m -= k
    while m <= 0:
        m += 12
        y -= 1
    return "%04d-%02d" % (y, m)


def build_ranks(monthly, sector, months):
    """월별로 ① 섹터 순위 ② 종목의 «자기 섹터 내» 백분위 를 만든다.

    🚨 기준월 `ym` 의 값은 **`ym` 월말까지의 자료**로만 만든다.
       스캔일이 속한 달에는 **`ym = 직전 달»`** 을 쓴다(아래 `flag`).
    """
    sec_rank, in_rank = {}, {}
    for ym in months:
        base = prev_ym(ym, LOOKBACK)
        rets, bysec = {}, defaultdict(list)
        for t, d in monthly.items():
            a, b = d.get(base), d.get(ym)
            if not a or not b or a <= 0:
                continue
            s = sector.get(t)
            if not s:
                continue
            r = b / a - 1
            rets[t] = r
            bysec[s].append((r, t))
        if not bysec:
            continue
        # ① 섹터 등가중 수익률 순위
        smean = {s: st.mean(x for x, _t in v) for s, v in bysec.items() if len(v) >= 5}
        top = set(sorted(smean, key=lambda s: -smean[s])[:TOP_SECTORS])
        sec_rank[ym] = top
        # ② 섹터 «내» 백분위
        pct = {}
        for s, v in bysec.items():
            v.sort(key=lambda x: -x[0])
            n = len(v)
            for i, (_r, t) in enumerate(v):
                pct[t] = i / n          # 0 이 최상위
        in_rank[ym] = pct
    return sec_rank, in_rank


def main() -> int:
    if r41.YEARS[0] != 2017:
        print("🚨 `BT_Y0=2017` 을 주지 않았다 — 멈춘다.", flush=True)
        return 2
    by, miss = r41.v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2
    pack = json.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]

    r41.TARGET_FILL, r41.STOP_FILL = "close", "close"
    ev0 = None
    for vname, fn, _l, _h in r41.VARIANTS:
        if vname == "1a":
            ev0, _b = r41.replay(by, fn)

    print("=" * 80, flush=True)
    print("61번 — **선별 축: 주도 그룹의 주도주** (사전등록 tasks/61)", flush=True)
    print("=" * 80, flush=True)

    # ── 관문 1·2: 섹터 매칭률 ────────────────────────────────────────────
    codes = {e["code"] for e in ev0}
    hit = {c for c in codes if sector.get(c)}
    print("관문1 섹터 매칭 — 방아쇠 티커 %d 중 **%d (%.1f%%)**"
          % (len(codes), len(hit), 100.0 * len(hit) / len(codes)), flush=True)
    if len(hit) / len(codes) < 0.80:
        print("🚨 80%% 미만 — 멈춘다.", flush=True)
        return 3
    n_nosec = sum(1 for e in ev0 if not sector.get(e["code"]))
    print("  🚨 섹터 없는 진입 %d건 (%.1f%%) — **탈락 아니라 «제3군»으로 «통과» 처리**"
          % (n_nosec, 100.0 * n_nosec / len(ev0)), flush=True)

    months = sorted({ym for d in monthly.values() for ym in d})
    months = [m for m in months if m >= "2016-12"]
    sec_rank, in_rank = build_ranks(monthly, sector, months)
    print("월별 순위 %d개월 (%s ~ %s)" % (len(sec_rank), min(sec_rank), max(sec_rank)),
          flush=True)

    def base_ym(scan):
        """🚨 스캔일이 속한 달은 «안 쓴다» — 직전 달 말까지만."""
        return prev_ym(scan[:7], 1)

    def mk(kind, sr=None, ir=None):
        sr = sec_rank if sr is None else sr
        ir = in_rank if ir is None else ir

        def f(e):
            s = sector.get(e["code"])
            if not s:
                return True                       # 제3군 = 통과
            ym = base_ym(e["scan_date"])
            top = sr.get(ym)
            pct = ir.get(ym, {})
            if top is None:
                return True
            a = (s in top)
            b = (pct.get(e["code"], 1.0) <= TOP_PCT)
            return a if kind == "S1" else (b if kind == "S2" else (a and b))
        return f

    CELLS = [("R0 없음", None), ("S1 주도그룹", mk("S1")),
             ("S2 그룹내주도주", mk("S2")), ("S3 주도그룹의주도주", mk("S3"))]

    def band(ev, reg, n=N_SEED):
        with r41.Cost(*reg):
            rs = [sf.sim_frac(ev, slots=5, seed=i, sizing="cash") for i in range(n)]
        eq = sorted(r["equity_pct"] for r in rs)
        return {"eq": st.median(eq), "p5": eq[int(n * .05)],
                "mdd": st.median(r["mdd_pct"] for r in rs),
                "n_filled": st.median(r["n_filled"] for r in rs),
                "fpt": st.median(r["filled_per_trade"] for r in rs),
                "curves": [r["curve"] for r in rs[:da.N_STREAM]]}

    RES = {}
    for reg, rn in (((0.0, 0.0), "무비용"), ((0.0014, 0.0034), "미래에셋")):
        print("\n" + "─" * 80, flush=True)
        print("[1a · %s] 9년 · seed %d" % (rn, N_SEED), flush=True)
        print("  %-20s %7s %6s %11s %11s %8s" %
              ("칸", "진입", "체결", "자산중앙", "5%하단", "MDD"), flush=True)
        got = {}
        for cname, ff in CELLS:
            ev = ev0 if ff is None else [e for e in ev0 if ff(e)]
            if cname == "S1 주도그룹":
                p = 100.0 * len(ev) / len(ev0)
                if not (5 < p < 95):
                    print("🚨 관문4 미통과 — S1 통과율 %.1f%%. 멈춘다." % p, flush=True)
                    return 3
            r = band(ev, reg)
            got[cname] = r
            print("  %-20s %7d %6d %+10.2f%% %+10.2f%% %7.1f%%"
                  % (cname, len(ev), r["n_filled"], r["eq"], r["p5"], r["mdd"]),
                  flush=True)
            RES["%s|%s" % (rn, cname)] = {k: v for k, v in r.items() if k != "curves"}
            RES["%s|%s" % (rn, cname)]["n_entry"] = len(ev)
        print("  ── A. 자료 축 짝비교 (vs R0) ──", flush=True)
        for cname, _ff in CELLS[1:]:
            sw = da.sweep(got[cname]["curves"], got["R0 없음"]["curves"])
            w = sw["_widest"]
            rr = sw[w]
            print("    %-20s 블록%-3d 중앙 %+8.2f%%  95%% %+8.2f ~ %+8.2f → **%s**"
                  % (cname, w, rr["median"], rr["lo"], rr["hi"],
                     "0 배제" if rr["excl0"] else "0 포함"), flush=True)
            RES["%s|%s" % (rn, cname)]["paired"] = {
                "median": rr["median"], "lo": rr["lo"], "hi": rr["hi"],
                "excl0": rr["excl0"]}

        # ── B. 「아무런 효과 없는 가정」으로 돌려 보기 ────────────────────
        if rn == "무비용":
            print("  ── ★ B. **아무런 효과 없는 가정으로 돌려 보기** — 섹터 라벨을 "
                  "섞어 가짜 필터 %d회 ──" % N_NULL, flush=True)
            rnd = random.Random(610825)
            base = got["R0 없음"]["eq"]
            secs = sorted({v for v in sector.values()})
            null = []
            for _i in range(N_NULL):
                keys = sorted(sector)
                vals = [sector[k] for k in keys]
                rnd.shuffle(vals)
                fake = dict(zip(keys, vals))
                fsr, _fir = build_ranks({t: monthly[t] for t in monthly}, fake,
                                        months[::6])   # 6개월마다 (비용 절약)
                # 가장 가까운 «이전» 기준월을 찾아 쓴다
                ks = sorted(fsr)

                def top_of(ym, _ks=ks, _fsr=fsr):
                    c = [k for k in _ks if k <= ym]
                    return _fsr[c[-1]] if c else None

                ev = [e for e in ev0
                      if (not fake.get(e["code"]))
                      or (top_of(base_ym(e["scan_date"])) is None)
                      or (fake[e["code"]] in top_of(base_ym(e["scan_date"])))]
                with r41.Cost(*reg):
                    rs = [sf.sim_frac(ev, slots=5, seed=s, sizing="cash")["equity_pct"]
                          for s in range(12)]
                null.append(st.median(rs) - base)
            null.sort()
            p95 = null[int(N_NULL * .95)]
            obs = {c: got[c]["eq"] - base for c, _f in CELLS[1:]}
            best = max(obs, key=lambda k: obs[k])
            print("    효과 없다고 쳤을 때 — 보통 %+.2f%%p · **95%% %+.2f%%p** · 최대 %+.2f%%p"
                  % (null[N_NULL // 2], p95, null[-1]), flush=True)
            for c in obs:
                print("    관측 %-20s %+8.2f%%p → %s"
                      % (c, obs[c], "**넘음**" if obs[c] > p95 else "범위 안"),
                      flush=True)
            print("    ★ 관측 최선 = %s (%+.2f%%p) vs 95%% %+.2f%%p → **%s**"
                  % (best, obs[best], p95,
                     "통과" if obs[best] > p95
                     else "**미통과 — 「고른 것」과 구분 안 됨**"), flush=True)
            RES["null"] = {"median": null[N_NULL // 2], "p95": p95, "max": null[-1],
                           "obs": obs, "best": best, "pass": obs[best] > p95}
            _ = secs
    (OUT / "61-selection-leaders.json").write_text(
        json.dumps(RES, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 61-selection-leaders.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
