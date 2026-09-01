# -*- coding: utf-8 -*-
r"""143d — **«묘사»** — 「후보가 몰린 날일수록 자리가 «차» 있는가」. 🚨 판정에 «안» 쓴다.

두뇌 세션 기전(추측): 138 실측 투입률은 72% 라 평균 «28% 비어» 있는데,
«후보가 몰린 날»만 보면 85% 차 있다 → **같은 국면이 둘 다 만든다**.
**반대 방향이면(k 클수록 s 도 큼) 그 기전이 틀린 것이고, 그것도 값있다.**

재는 것: 날마다 (k = 후보 수, s = 기준판 체결 수, free = 그날 시작 빈 자리)
🚨 **성적 아님. 라벨 안 씀.**
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
r102 = _u.module_from_spec(_s); _s.loader.exec_module(r102)
r91, f92a = r102.r91, r102.f92a
_s3 = _u.spec_from_file_location("r103", HERE / "103-code33-strength.py")
r103 = _u.module_from_spec(_s3); _s3.loader.exec_module(r103)
import slot_sim_lots as sl                                       # noqa: E402

NEW = Path("D:/stock-data/uspath-warm/full")
OUT = ROOT / "research" / "handoff" / "data" / "143-crowding.json"
YEARS = tuple(range(1999, 2012))
FRONT_D0, FRONT_D1 = "1999-04-01", "2011-12-31"
CUT, REF_SEED = "2003-11-19", 143


def main() -> int:
    if [y for y in YEARS if y >= 2012]:
        raise RuntimeError("🚨 뒤 구간 차단")
    r91.TARGET, r91.STOP, r91.HALF = 20.0, 10.0, 0.5
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
        ev.extend(r91.replay({y: [p for p in by1.get(y, []) if keep_f(p)]})[0])
        del by1
    del fund

    k_by = Counter(t["entry_date"] for t in ev)
    with r91.r41.Cost(*r91.COST):
        r = sl.sim_lots(ev, seed=REF_SEED, slots=r91.SLOTS, risk=r91.RISK,
                        cap=r91.CAP, reserve=False, fill_rule="truncate",
                        cash_rule="per_slot")
    s_by = Counter(x[3] for x in r["fill_log"])
    days = sorted(d for d in k_by if d >= CUT)

    print("", flush=True)
    print("=" * 92, flush=True)
    print("**묘사** — 후보 수 k 와 그날 체결 수 s  (시험 구간 %d일 · 씨앗 %d)"
          % (len(days), REF_SEED), flush=True)
    print("=" * 92, flush=True)
    print("%-12s %8s %10s %12s" % ("후보 수 k", "날", "채운 날", "채운 날 비율"), flush=True)
    grp = defaultdict(list)
    for d in days:
        k = k_by[d]
        grp[1 if k == 1 else 2 if k == 2 else 3 if k <= 4 else 4].append(
            1 if s_by.get(d, 0) >= 1 else 0)
    NAME = {1: "k = 1", 2: "k = 2", 3: "k = 3~4", 4: "k ≥ 5"}
    out = {}
    for g in sorted(grp):
        v = grp[g]
        print("%-12s %8d %10d %11.1f%%"
              % (NAME[g], len(v), sum(v), 100.0 * sum(v) / len(v)), flush=True)
        out[NAME[g]] = {"days": len(v), "filled": sum(v),
                        "rate": 100.0 * sum(v) / len(v)}
    lo = [x for g in (1, 2) for x in grp.get(g, [])]
    hi = [x for g in (3, 4) for x in grp.get(g, [])]
    rl = 100.0 * sum(lo) / max(1, len(lo))
    rh = 100.0 * sum(hi) / max(1, len(hi))
    print("", flush=True)
    print("   k 작음(1~2) 채운 날 **%.1f%%**  vs  k 큼(3+) **%.1f%%**  →  차이 **%+.1f%%p**"
          % (rl, rh, rh - rl), flush=True)
    print("   🚨 두뇌 세션 기전(「몰린 날일수록 꽉 차 있다」)은 %s"
          % ("**맞는 방향**" if rh < rl else "**틀린 방향 — k 클수록 «더» 채운다**"), flush=True)
    print("   ⚠️ **이건 묘사다. 판정에 안 쓴다.** 그리고 k 와 s 는 «같은 시장»이 만들어 인과가 아니다",
          flush=True)
    out["_summary"] = {"k_small_rate": rl, "k_big_rate": rh, "diff_pp": rh - rl}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("저장: %s" % OUT.name, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
