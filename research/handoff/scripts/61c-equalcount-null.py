# -*- coding: utf-8 -*-
"""61c — **진입 수를 맞춘** 「효과 없다고 쳤을 때」 검정.

61b 가 스스로 알렸다: 가짜 판이 진입을 훨씬 적게 남긴다(S3 3,731 vs 730).
그러면 «고르는 방식»이 아니라 «몇 건 사느냐»를 견주게 된다.

여기서는 **달마다 실제 필터가 남긴 «것과 같은 수»를 무작위로 남긴다.**
- 보존: 월별 진입 건수 · 시간 구조 · 총 진입 수
- 파괴: **어느 종목을 고르느냐**  ← 우리가 재려는 것 «딱 그것»

**이게 「주도 그룹의 주도주」에 대한 가장 곧은 검정이다.**
"""
from __future__ import annotations
import importlib.util as _u, json, random, statistics as st, sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]; HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim_frac as sf
_s = _u.spec_from_file_location("r41", HERE / "41-round1-exits.py")
r41 = _u.module_from_spec(_s); _s.loader.exec_module(r41)
_s2 = _u.spec_from_file_location("r61b", HERE / "61b-matched-null.py")
r61b = _u.module_from_spec(_s2); _s2.loader.exec_module(r61b)
r61 = r61b.r61
OUT = ROOT / ".cache" / "bt5y" / "out"
N_NULL = 200; N_SEED_NULL = 12; N_SEED = 200

def main() -> int:
    if r41.YEARS[0] != 2017:
        print("BT_Y0=2017 필요"); return 2
    by, _m = r41.v39.load_paths()
    r41.TARGET_FILL, r41.STOP_FILL = "close", "close"
    for vname, fn, _l, _h in r41.VARIANTS:
        if vname == "1a": ev0, _b = r41.replay(by, fn)
    pack = json.loads((OUT / "61-monthly-us.json").read_text(encoding="utf-8"))
    monthly, sector = pack["monthly"], pack["sector"]
    months = sorted({ym for d in monthly.values() for ym in d if ym >= "2016-12"})
    mret = r61b.month_returns(monthly, sector, months)
    top, pct = r61b.make_flags(mret, sector)
    reg = (0.0, 0.0)
    def eq_of(ev, n):
        with r41.Cost(*reg):
            return st.median(sf.sim_frac(ev, slots=5, seed=i, sizing="cash")["equity_pct"]
                             for i in range(n))
    base = eq_of(ev0, N_SEED)
    print("=" * 78); print("61c — **진입 수를 맞춘** 검정"); print("=" * 78)
    print("R0 자산 중앙 %+.2f%%" % base, flush=True)
    bymon = defaultdict(list)
    for e in ev0: bymon[e["entry_date"][:7]].append(e)
    RES = {}
    for kind in ("S1", "S2", "S3"):
        real = r61b.keep(ev0, sector, top, pct, kind)
        obs = eq_of(real, N_SEED) - base
        cnt = defaultdict(int)
        for e in real: cnt[e["entry_date"][:7]] += 1
        rnd = random.Random(610827)
        null, fills = [], []
        for _i in range(N_NULL):
            sel = []
            for ym, lst in bymon.items():
                k = cnt.get(ym, 0)
                if k: sel.extend(rnd.sample(lst, min(k, len(lst))))
            null.append(eq_of(sel, N_SEED_NULL) - base)
            fills.append(len(sel))
        null.sort(); p95 = null[int(N_NULL * .95)]
        ok = obs > p95
        print("\n%s — 관측 진입 %d · **%+.2f%%p**" % (kind, len(real), obs), flush=True)
        print("  같은 수를 «무작위로» 골랐을 때 (진입 중앙 %d — 관측과 %s)"
              % (st.median(fills), "일치" if abs(st.median(fills)-len(real)) <= 2 else "🚨 불일치"), flush=True)
        print("    보통 %+.2f%%p · **95%% %+.2f%%p** · 최대 %+.2f%%p  →  **%s**"
              % (null[N_NULL//2], p95, null[-1],
                 "넘음 — 「어느 종목을 고르느냐」가 값을 만든다" if ok
                 else "범위 안 — 「고른 것」과 구분 안 됨"), flush=True)
        RES[kind] = {"obs": obs, "n": len(real), "null_median": null[N_NULL//2],
                     "null_p95": p95, "null_max": null[-1], "pass": ok}
    (OUT / "61c-equalcount-null.json").write_text(json.dumps(RES, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: 61c-equalcount-null.json")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
