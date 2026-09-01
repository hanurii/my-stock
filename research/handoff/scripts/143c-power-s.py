# -*- coding: utf-8 -*-
r"""143c — 🚨 **「상위 s개」 자로 바꾸면 검정력이 어떻게 되나.** 자를 «정하기 전»에.

왜 급한가
---------
143b 가 낸 것:
```
시험 «후보 2+» 인 날      **348일**
그중 체결이 «1건 이상»    **51일 (14.7%)**   ← 나머지 297일은 자리가 «꽉 차 있었다»
```
> ### **「상위 s개」 자는 s=0 인 날에 «값이 없다».** → 분모가 **348 → 51일**
> ### 🚨 **이건 142 가 죽은 방식과 «똑같다»** — 「옳은 자」가 「못 재는 자」.

그래서 **둘의 MDE 를 나란히 재고, 결정을 «수»로 넘긴다.** (성적 아님 — 라벨과 개수만)
```
자 A  「1등 − 그날 평균」          분모 348일   (원안)
자 B  「상위 s개 평균 − 무작위 s개 평균」  분모 s≥1 인 날만  (개정 ③)
      귀무 Var = (σ²_pop / s) · (k−s)/(k−1)      ← 비복원 표집
```
실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/143c-power-s.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import math
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

import slot_sim_lots as sl                                       # noqa: E402

NEW = Path("D:/stock-data/uspath-warm/full")
CACHE = ROOT / ".cache" / "bt5y" / "out"
OUT = ROOT / "research" / "handoff" / "data" / "143-power-s.json"
YEARS = tuple(range(1999, 2012))
FRONT_D0, FRONT_D1 = "1999-04-01", "2011-12-31"
CUT = {20.0: "2003-11-19", 30.0: "2003-11-26"}
REF_SEED = 143                       # 🚨 s 를 정하는 «기준판». 고정이고 사전등록에 적는다


def _ev(target):
    """후보 목록. 143a 캐시를 «그대로» 쓴다(라벨) + 체결 재현용 replay."""
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
    return ev


def label(t):
    m = t["masks"][next(iter(t["masks"]))]
    return sum(sh * (px / t["entry_px"] * 100.0 - 100.0) for _d, sh, px in m["exits"])


def main() -> int:
    bad = [y for y in YEARS if y >= 2012]
    if bad:
        raise RuntimeError("🚨 뒤 구간 차단 — %r" % (bad,))

    res = {}
    for target, cut in CUT.items():
        ev = _ev(target)
        byday = defaultdict(list)
        for t in ev:
            byday[t["entry_date"]].append(label(t))
        with r91.r41.Cost(*r91.COST):
            r = sl.sim_lots(ev, seed=REF_SEED, slots=r91.SLOTS, risk=r91.RISK,
                            cap=r91.CAP, reserve=False, fill_rule="truncate",
                            cash_rule="per_slot")
        sday = Counter(x[3] for x in r["fill_log"])
        days = [d for d in sorted(byday) if d >= cut and len(byday[d]) >= 2]

        print("", flush=True)
        print("=" * 96, flush=True)
        print("목표 **+%.0f%%** · 시험 «후보 2+» 인 날 **%d일** · 기준판 씨앗 %d"
              % (target, len(days), REF_SEED), flush=True)
        print("=" * 96, flush=True)

        # ── 자 A : 1등 − 그날 평균 ────────────────────────────────
        nA, varA, ceilA = 0, 0.0, []
        for d in days:
            v = byday[d]
            nA += 1
            m = sum(v) / len(v)
            varA += sum((x - m) ** 2 for x in v) / len(v)
            ceilA.append(max(v) - m)
        seA = math.sqrt(varA) / nA
        mdeA, cA = 1.645 * seA, sum(ceilA) / len(ceilA)

        # ── 자 B : 상위 s개 평균 − 무작위 s개 평균 ────────────────
        nB, varB, ceilB, ss = 0, 0.0, [], []
        for d in days:
            v = byday[d]
            k = len(v)
            s = min(sday.get(d, 0), k)
            if s < 1:
                continue
            if s >= k:                     # 다 사면 «고를 게» 없다 → 차이가 정의상 0
                continue
            nB += 1
            ss.append(s)
            m = sum(v) / len(v)
            pv = sum((x - m) ** 2 for x in v) / k
            varB += (pv / s) * ((k - s) / (k - 1))       # 비복원 표집
            top = sorted(v, reverse=True)[:s]
            ceilB.append(sum(top) / s - m)
        seB = math.sqrt(varB) / nB if nB else float("nan")
        mdeB = 1.645 * seB if nB else float("nan")
        cB = (sum(ceilB) / len(ceilB)) if ceilB else float("nan")

        print("   자 A  「1등 − 그날 평균」", flush=True)
        print("      분모 **%d일** · SE %.4f%%p · **MDE %.3f%%p** · 천장 **+%.3f%%p** → 천장/MDE **%.1f배**"
              % (nA, seA, mdeA, cA, cA / mdeA), flush=True)
        print("   자 B  「상위 s개 − 무작위 s개」  (s = 기준판 체결 수)", flush=True)
        # 🚨 분모를 «글자»로 박았다가 +30 줄에 348(실제 343)을 찍었다 — nA 를 쓴다
        print("      분모 **%d일** (%d일의 %.1f%%) · SE %.4f%%p · **MDE %.3f%%p** · "
              "천장 **+%.3f%%p** → 천장/MDE **%.1f배**"
              % (nB, nA, 100.0 * nB / max(1, nA), seB, mdeB, cB,
                 (cB / mdeB) if mdeB == mdeB else float("nan")), flush=True)
        if ss:
            print("      s — 중앙 %d · 평균 %.2f · 최대 %d  (s≥k 라 «고를 게 없는» 날은 뺐다)"
                  % (st.median(ss), sum(ss) / len(ss), max(ss)), flush=True)
        print("", flush=True)
        print("   🚨 **분모 %d → %d일 (%.0f%% 잃음) · MDE %.3f → %.3f%%p (%.1f배)**"
              % (nA, nB, 100.0 * (1 - nB / max(1, nA)), mdeA, mdeB, mdeB / mdeA), flush=True)
        print("   → 자 B 는 %s"
              % ("✅ **그래도 천장이 MDE 위**" if cB > mdeB
                 else "🚨 **천장조차 MDE 아래 — 142 와 같은 죽음**"), flush=True)
        res["t%d" % int(target)] = {
            "A": {"n": nA, "se": seA, "mde": mdeA, "ceiling": cA},
            "B": {"n": nB, "se": seB, "mde": mdeB, "ceiling": cB,
                  "s_median": st.median(ss) if ss else None},
            "ref_seed": REF_SEED}
        del ev, byday

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("", flush=True)
    print("저장: %s" % OUT.name, flush=True)
    print("🚨 **성적이 아니다** — 라벨과 개수만 썼다. 체는 아직 없다.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
