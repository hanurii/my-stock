# -*- coding: utf-8 -*-
r"""143b — **「그날 «실제로 살 수 있었던» 자리 수 s」의 분포.** 자를 정하기 «전»에.

왜
--
검증 세션 개정 ③: 주판정을 **「상위 s개 평균 − 무작위 s개 평균」**으로 한다.
그런데 **s 는 「몇 자리가 비어 있었나」**이고, 그건 **시뮬을 돌려야 안다.**

## 🚨 그리고 «순환»이 있다 — 미리 못박는다
```
s 는 «그날까지 무엇을 샀나»에 달렸고, 그건 «순서»에 달렸다  →  순서를 바꾸면 s 도 바뀐다
```
> ### **해법: s 를 «무작위 순서 기준판»(씨앗 고정)에서 뽑아 «양쪽에 같은 s»를 쓴다.**
> ### 그러면 짝비교가 공정하고 순환이 없다. **이건 «선택»이므로 사전등록에 적는다.**

재는 것 — 🚨 **개수뿐이다. 성적이 아니다**
```
· 시험 구간에서 하루 체결 수 s 의 «분포»
· s = 1 인 날의 비율   ← 이게 높으면 「1등 자」와 「상위 s 자」가 거의 같다 = 어긋남이 «작다»
· 후보 k 와 s 의 관계 (s = min(k, 빈자리))
```
실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/143b-slots.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

_s = _u.spec_from_file_location("r102", HERE / "102-implement-principles.py")
r102 = _u.module_from_spec(_s)
_s.loader.exec_module(r102)
r91, f92a = r102.r91, r102.f92a
_s3 = _u.spec_from_file_location("r103", HERE / "103-code33-strength.py")
r103 = _u.module_from_spec(_s3)
_s3.loader.exec_module(r103)

import slot_sim_lots as sl                                      # noqa: E402

NEW = Path("D:/stock-data/uspath-warm/full")
OUT = ROOT / "research" / "handoff" / "data" / "143-slots.json"
YEARS = tuple(range(1999, 2012))                # 🚨 뒤 구간 닫힘
FRONT_D0, FRONT_D1 = "1999-04-01", "2011-12-31"
CUT = {20.0: "2003-11-19", 30.0: "2003-11-26"}  # 143a 가 «후보 수»로 낸 지점
N_SEED = 20


def main() -> int:
    bad = [y for y in YEARS if y >= 2012]
    if bad:
        raise RuntimeError("🚨 뒤 구간 차단 — %r" % (bad,))

    res = {}
    for target, cut in CUT.items():
        r91.TARGET, r91.STOP, r91.HALF = target, 10.0, 0.5
        import _lean_load as ll
        ll.r91.SUB = NEW
        assert ll.r91.SUB == NEW
        fund, ixf = f92a.load()
        ix = {f: i for i, f in enumerate(ixf)}

        def keep_f(p):
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0])
                          > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            return v is not False

        ev = []
        for y in YEARS:
            by1, _c, _n = ll.load_combo((y,), FRONT_D0, FRONT_D1)
            byf = {y: [p for p in by1.get(y, []) if keep_f(p)]}
            ev.extend(r91.replay(byf)[0])
            del by1, byf
        del fund
        print("", flush=True)
        print("=" * 92, flush=True)
        print("목표 **+%.0f%%** · 후보 %s건 · 시험 구간 = %s 부터"
              % (target, "{:,}".format(len(ev)), cut), flush=True)
        print("=" * 92, flush=True)

        # 후보 수 k (그날 «주문이 나간» 수)
        k_by_day = Counter(t["entry_date"] for t in ev)

        # s = 그날 «실제 체결» 수 — 무작위 순서 기준판 여러 판
        per_seed = []
        with r91.r41.Cost(*r91.COST):
            for sd in range(N_SEED):
                r = sl.sim_lots(ev, seed=sd, slots=r91.SLOTS, risk=r91.RISK,
                                cap=r91.CAP, reserve=False, fill_rule="truncate",
                                cash_rule="per_slot")
                c = Counter(x[3] for x in r["fill_log"])   # x[3] = 체결일
                per_seed.append(c)

        test_days = [d for d in k_by_day if d >= cut and k_by_day[d] >= 2]
        s_all = Counter()
        s_med = {}
        for d in test_days:
            v = [c.get(d, 0) for c in per_seed]
            s_med[d] = st.median(v)
            for x in v:
                s_all[x] += 1
        n_pos = [d for d in test_days if s_med[d] >= 1]
        n_one = [d for d in test_days if s_med[d] == 1]
        n_two = [d for d in test_days if s_med[d] >= 2]

        print("   시험 구간 «후보 2+» 인 날 **%d일**" % len(test_days), flush=True)
        print("   그중 «체결이 1건 이상» 인 날(중앙 기준) **%d일 (%.1f%%)**"
              % (len(n_pos), 100 * len(n_pos) / max(1, len(test_days))), flush=True)
        print("      s = 1 인 날 **%d일 (%.1f%%)**  ·  s ≥ 2 인 날 **%d일 (%.1f%%)**"
              % (len(n_one), 100 * len(n_one) / max(1, len(n_pos)),
                 len(n_two), 100 * len(n_two) / max(1, len(n_pos))), flush=True)
        tot = sum(s_all.values())
        print("   s 분포(20판 전부): %s"
              % {k: "%.1f%%" % (100 * v / tot) for k, v in sorted(s_all.items())[:6]},
              flush=True)
        kk = [k_by_day[d] for d in test_days]
        print("   (참고) 그날 후보 수 k — 중앙 %d · 평균 %.2f · 최대 %d"
              % (st.median(kk), sum(kk) / len(kk), max(kk)), flush=True)
        print("", flush=True)
        print("   🚨 **s = 1 인 날이 %.1f%%** → 「1등 자」와 「상위 s 자」의 어긋남이 %s"
              % (100 * len(n_one) / max(1, len(n_pos)),
                 "**작다**" if len(n_one) / max(1, len(n_pos)) > 0.7 else "**작지 않다**"),
              flush=True)
        res["t%d" % int(target)] = {
            "cut": cut, "test_days": len(test_days), "days_filled": len(n_pos),
            "s1_days": len(n_one), "s2plus_days": len(n_two),
            "s_dist": {str(k): v for k, v in s_all.items()},
            "k_median": st.median(kk), "k_mean": sum(kk) / len(kk)}
        del ev

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("", flush=True)
    print("저장: %s" % OUT.name, flush=True)
    print("🚨 **개수뿐이다. 성적이 아니다.**", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
