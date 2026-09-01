# -*- coding: utf-8 -*-
r"""143a — **돌리기 «전»에 「답이 나올 수는 있는가」를 먼저 센다.** (142 §12 규약)

왜 이걸 «먼저» 하나
-------------------
142 에서 **「옳은 자」가 「못 재는 자」**였다 — 자를 바로잡자 분모가 95일로 쪼그라들었다.
그래서 143 은 **자·분모·MDE 를 «성적을 보기 전»에** 계산한다. **답이 안 나올 크기면 시작하지 않는다.**

재는 것 — 🚨 **전부 «라벨»만 쓴다. 체는 없다**
```
자      「체가 1등으로 고른 종목의 실현 r_  −  그날 후보 «전체»의 평균 r_」   (같은 날 짝비교)
분모    후보가 **2개 이상**인 날 전부
귀무    그날 후보 중 «무작위로» 하나 고르기
        → E[차이] = 0 · Var = 그날 r_ 의 «모집단 분산»   ← **체 없이 계산된다**
MDE     SE = √(ΣVar_d) / n  ·  단측 95% 로 잡을 수 있는 가장 작은 차이 = 1.645 × SE
        8할 검정력 크기 = 2.486 × SE
```
🚨 **목표 +20 과 +30 «둘 다»** 낸다(사용자 미결). 손절 −10 고정.
🚨 쪼개기는 «날짜»가 아니라 **«후보 수»**로 — 유형 33(작은 쪽이 관문을 독차지한다).

실행: PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python research/handoff/scripts/143a-power.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import math
import sys
from collections import defaultdict
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

NEW = Path("D:/stock-data/uspath-warm/full")
OUT = ROOT / "research" / "handoff" / "data" / "143-power.json"
CACHE = ROOT / ".cache" / "bt5y" / "out"
# 🚨 뒤 구간 차단 — 140 `_guard` 와 같은 규약
YEARS = tuple(range(1999, 2012))
FRONT_D0, FRONT_D1 = "1999-04-01", "2011-12-31"
TARGETS = (20.0, 30.0)
STOP, HALF = 10.0, 0.5


def _guard():
    bad = [y for y in YEARS if y >= 2012]
    if bad:
        raise RuntimeError("🚨 뒤 구간 차단 — %r" % (bad,))


def label(t):
    m = t["masks"][next(iter(t["masks"]))]
    return sum(sh * (px / t["entry_px"] * 100.0 - 100.0) for _d, sh, px in m["exits"])


def collect(target):
    cf = CACHE / ("_143_lab_t%d.json" % int(target))
    if cf.exists():
        return json.loads(cf.read_text(encoding="utf-8"))
    r91.TARGET, r91.STOP, r91.HALF = target, STOP, HALF
    import _lean_load as ll
    ll.r91.SUB = NEW                       # 🚨 «이쪽»을 바꿔야 한다 (142 사고)
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

    rows = []
    for y in YEARS:
        by1, _c, _n = ll.load_combo((y,), FRONT_D0, FRONT_D1)
        byf = {y: [p for p in by1.get(y, []) if keep_f(p)]}
        for t in r91.replay(byf)[0]:
            rows.append({"d": t["entry_date"], "r": label(t)})
        del by1, byf
        print("   목표 +%.0f · %d년 — 누적 %d" % (target, y, len(rows)), flush=True)
    del fund
    cf.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")),
                  encoding="utf-8")
    return rows


def split_point(rows):
    """🚨 «날짜»가 아니라 «후보 수»로 반 가른다 (유형 33)."""
    byday = defaultdict(list)
    for r in rows:
        byday[r["d"]].append(r["r"])
    days = sorted(byday)
    tot = len(rows)
    run = 0
    for d in days:
        run += len(byday[d])
        if run >= tot / 2:
            return d, byday
    return days[-1], byday


def power(byday, days):
    """귀무(무작위 1개 고르기)에서의 SE 와 MDE. **체 없이** 계산된다."""
    n, var = 0, 0.0
    for d in days:
        v = byday[d]
        if len(v) < 2:
            continue
        n += 1
        m = sum(v) / len(v)
        var += sum((x - m) ** 2 for x in v) / len(v)    # 모집단 분산
    if n == 0:
        return 0, None, None, None
    se = math.sqrt(var) / n
    return n, se, 1.645 * se, 2.486 * se


def main() -> int:
    _guard()
    res = {}
    for target in TARGETS:
        print("", flush=True)
        print("=" * 92, flush=True)
        print("목표 **+%.0f%%** / 손절 −%.0f%%" % (target, STOP), flush=True)
        print("=" * 92, flush=True)
        rows = collect(target)
        cut, byday = split_point(rows)
        days = sorted(byday)
        lo = [d for d in days if d < cut]
        hi = [d for d in days if d >= cut]
        n_lo = sum(len(byday[d]) for d in lo)
        n_hi = sum(len(byday[d]) for d in hi)
        gap = abs(n_lo - n_hi) / max(1, (n_lo + n_hi) / 2) * 100

        print("   후보 **%s건** · 날 %d일" % ("{:,}".format(len(rows)), len(days)), flush=True)
        print("   쪼갠 지점 **%s** (후보 수 기준)" % cut, flush=True)
        print("   학습 후보 **%d** (날 %d) · 시험 후보 **%d** (날 %d) · 어긋남 **%.1f%%** %s"
              % (n_lo, len(lo), n_hi, len(hi), gap,
                 "→ 관문 A★ **통과**" if gap <= 5.0 else "→ 🚨 **A★ 미통과**"), flush=True)

        row = {"target": target, "n_cand": len(rows), "cut": cut,
               "train_cand": n_lo, "test_cand": n_hi, "gap_pct": gap}
        for name, ds in (("학습", lo), ("시험", hi)):
            n, se, mde, p80 = power(byday, ds)
            print("   [%s] 후보 2+ 인 날 **%d일** · SE **%.4f%%p** · "
                  "**MDE(단측95) %.3f%%p** · 8할 크기 %.3f%%p"
                  % (name, n, se or 0, mde or 0, p80 or 0), flush=True)
            row[name] = {"n_days": n, "se": se, "mde95": mde, "p80": p80}
        # 참고 — 그날 «최고»를 늘 집으면 얼마인가 (천장)
        ceil = []
        for d in hi:
            v = byday[d]
            if len(v) >= 2:
                ceil.append(max(v) - sum(v) / len(v))
        row["ceiling"] = (sum(ceil) / len(ceil)) if ceil else None
        print("   🚨 **천장** — 시험 구간에서 «늘 그날 최고»를 집으면 평균 **+%.3f%%p / 날**"
              % (row["ceiling"] or 0), flush=True)
        if row["ceiling"] and row["시험"]["mde95"]:
            print("      → 천장이 MDE 의 **%.1f배**  %s"
                  % (row["ceiling"] / row["시험"]["mde95"],
                     "✅ 잴 수 있는 크기다" if row["ceiling"] > row["시험"]["mde95"]
                     else "🚨 **천장조차 MDE 아래 — 시작하면 안 된다**"), flush=True)
        res["t%d" % int(target)] = row

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("", flush=True)
    print("저장: %s" % OUT.name, flush=True)
    print("🚨 **여기까지는 «성적»이 아니다** — 라벨과 개수만 썼다. 체는 아직 없다.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
