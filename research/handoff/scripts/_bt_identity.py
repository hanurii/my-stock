# -*- coding: utf-8 -*-
"""두 백테스트 산출물의 **동일성 관문** (두뇌·검증 세션 확정 정의).

1. events 는 **전 필드 완전 일치**
2. `skipped` 세 항목(overlap·halted·low_turnover)은 **합계만 일치**
   — 필터 순서를 바꾸면 배분이 달라지는 것은 **예상된 것**이다
3. `n_scan_dates` · `n_trades` 일치

사용: python research/handoff/scripts/_bt_identity.py <기준.json> <비교.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

FIELDS = ["code", "name", "market", "pattern", "gate_near", "scan_date", "entry_date",
          "resolve_date", "pivot", "entry_price", "gap_up_pct", "rs", "atr_pct",
          "turnover_eok", "result", "days_held", "max_gain_pct", "max_dd_pct",
          "gain_at_resolve_pct"]
KEY = ("scan_date", "code", "pattern")


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main():
    a, b = load(sys.argv[1]), load(sys.argv[2])
    ea = {tuple(e[k] for k in KEY): e for e in a["events"]}
    eb = {tuple(e[k] for k in KEY): e for e in b["events"]}
    print("기준 %s  events %d" % (sys.argv[1], len(ea)), flush=True)
    print("비교 %s  events %d" % (sys.argv[2], len(eb)), flush=True)

    only_a, only_b = sorted(set(ea) - set(eb)), sorted(set(eb) - set(ea))
    diff = []
    for k in sorted(set(ea) & set(eb)):
        for f in FIELDS:
            if ea[k].get(f) != eb[k].get(f):
                diff.append((k, f, ea[k].get(f), eb[k].get(f)))

    ok1 = not only_a and not only_b and not diff
    print("\n[관문 1] events 전 필드 완전 일치 — %s" % ("**통과**" if ok1 else "**실패**"))
    if only_a:
        print("  기준에만 있는 키 %d개: %s" % (len(only_a), only_a[:5]))
    if only_b:
        print("  비교에만 있는 키 %d개: %s" % (len(only_b), only_b[:5]))
    if diff:
        print("  필드 불일치 %d건 (앞 10건):" % len(diff))
        for k, f, x, y in diff[:10]:
            print("    %s  %s: %r → %r" % ("|".join(k), f, x, y))
        from collections import Counter
        print("  필드별 건수:", dict(Counter(f for _, f, _, _ in diff)))

    sa, sb = a["params"].get("skipped", {}), b["params"].get("skipped", {})
    ta, tb = sum(sa.values()), sum(sb.values())
    ok2 = ta == tb
    print("\n[관문 2] skipped 합계 일치 — %s" % ("**통과**" if ok2 else "**실패**"))
    print("  기준 %s 합계 %d" % (sa, ta))
    print("  비교 %s 합계 %d" % (sb, tb))
    if sa != sb and ok2:
        print("  ※ 배분은 다르지만 합계가 같다 — 필터 순서 교체의 **예상된 결과**")

    ok3 = (a["params"].get("n_scan_dates") == b["params"].get("n_scan_dates")
           and a["params"].get("n_trades") == b["params"].get("n_trades"))
    print("\n[관문 3] n_scan_dates · n_trades 일치 — %s" % ("**통과**" if ok3 else "**실패**"))
    print("  기준 %s / %s · 비교 %s / %s"
          % (a["params"].get("n_scan_dates"), a["params"].get("n_trades"),
             b["params"].get("n_scan_dates"), b["params"].get("n_trades")))

    print("\n===== 종합: %s =====" % ("**전 관문 통과**" if (ok1 and ok2 and ok3)
                                    else "**실패 — 다음 단계로 가지 않는다**"))
    sys.exit(0 if (ok1 and ok2 and ok3) else 1)


if __name__ == "__main__":
    main()
