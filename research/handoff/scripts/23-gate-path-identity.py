# -*- coding: utf-8 -*-
"""23 · **경로 재생 관문** — paths_*.json으로 기준선(+20/−10)을 재생해
하네스 `bt_*.json`의 `result`·`gain_at_resolve_pct`·`days_held`와 **한 건씩** 맞춘다.

★ 이 관문을 통과하지 못하면 23번은 착수하지 않는다(근사 금지).
★ 하네스 관례(코드에서 확인):
  - 청산가 = **그날 종가**(`closes[i]/pivot`), 목표가·손절가가 아니다.
  - 같은 날 고가≥T 이고 저가≤S → `ambiguous`
  - 돌파일에 저가≤S만 → `ambiguous`("stop_on_breakout_day")
  - 끝까지 미도달 → `unresolved`
  - 분모는 **pivot**이다(entry_price가 아니다).

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/23-gate-path-identity.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
TARGET, STOP = 20.0, 10.0


def replay(p, target=TARGET, stop=STOP):
    """paths 레코드 하나를 기준선 규칙으로 재생. h_pct/l_pct/c_pct는 어떤 기준인가를
    호출부에서 정하고, 여기서는 '퍼센트 시계열'만 받는다."""
    h, l, c = p["h_pct"], p["l_pct"], p["c_pct"]
    n = len(h)
    for i in range(n):
        hit_t = h[i] is not None and h[i] >= target
        hit_s = l[i] is not None and l[i] <= -stop
        if hit_t and hit_s:
            return ("ambiguous", i, c[i])
        if hit_t:
            return ("win", i, c[i])
        if hit_s:
            if i == 0:
                return ("ambiguous", i, c[i])
            return ("loss", i, c[i])
    return ("unresolved", n - 1, c[n - 1])


def main():
    # ── 경로 적재 ──
    paths, dup = {}, 0
    for y in range(2021, 2027):
        d = json.loads((OUT / ("paths_%d.json" % y)).read_text(encoding="utf-8"))
        for p in d["paths"]:
            k = (p["scan_date"], p["code"], p["pattern"])
            if k in paths:
                dup += 1
                continue
            paths[k] = p
    print("경로 %d건 (중복 %d 건너뜀)" % (len(paths), dup), flush=True)

    # ── 이벤트 적재(중복제거 첫 건) ──
    ev, seen = [], set()
    for y in range(2021, 2027):
        d = json.loads((BT / ("bt_%d.json" % y)).read_text(encoding="utf-8"))
        for e in d["events"]:
            k = (e["scan_date"], e["code"], e["pattern"])
            if k in seen:
                continue
            seen.add(k)
            ev.append(e)
    print("이벤트 %d건" % len(ev), flush=True)

    missing = [e for e in ev if (e["scan_date"], e["code"], e["pattern"]) not in paths]
    print("경로 없는 이벤트 **%d건**" % len(missing), flush=True)

    # ── 퍼센트 기준 확인: pivot 기준인가 entry_price 기준인가 ──
    gap = [p for p in paths.values() if p.get("gap_up_pct", 0) > 0]
    print("\n갭업 경로 %d건 — 기준 확인용 첫 3건:" % len(gap), flush=True)
    for p in gap[:3]:
        print("  %s %s  pivot %.2f · entry %.2f · gap %+.2f%% · h_pct[0] %+.4f"
              % (p["code"], p["entry_date"], p["pivot"], p["entry_price"],
                 p["gap_up_pct"], p["h_pct"][0]), flush=True)

    # ── 한 건씩 대조 ──
    res_mis, gain_mis, day_mis, ok = [], [], [], 0
    reason = Counter()
    for e in ev:
        k = (e["scan_date"], e["code"], e["pattern"])
        p = paths.get(k)
        if p is None:
            continue
        r, i, g = replay(p)
        good = True
        if r != e["result"]:
            res_mis.append((k, r, e["result"]))
            reason["result"] += 1
            good = False
        if abs(round(g, 2) - e["gain_at_resolve_pct"]) > 0.011:
            gain_mis.append((k, round(g, 2), e["gain_at_resolve_pct"]))
            reason["gain"] += 1
            good = False
        if i != e["days_held"]:
            day_mis.append((k, i, e["days_held"]))
            reason["days"] += 1
            good = False
        if good:
            ok += 1
    n = len(ev) - len(missing)
    print("\n" + "=" * 58, flush=True)
    print("대조 대상 %d건 · **전부 일치 %d건 (%.2f%%)**" % (n, ok, ok / n * 100), flush=True)
    print("  어긋남: result %d · gain %d · days %d"
          % (reason["result"], reason["gain"], reason["days"]), flush=True)
    for lab, arr in (("result", res_mis), ("gain", gain_mis), ("days", day_mis)):
        if arr:
            print("\n  [%s] 첫 5건:" % lab, flush=True)
            for x in arr[:5]:
                print("    %s  경로=%s  하네스=%s" % x, flush=True)
    print("=" * 58, flush=True)
    print("판정: **%s**" % ("통과" if ok == n and not missing else "미통과"), flush=True)

    (OUT / "23-gate-path-identity.json").write_text(json.dumps(
        {"n_paths": len(paths), "n_events": len(ev), "n_missing": len(missing),
         "n_compared": n, "n_exact": ok,
         "mismatch": {"result": reason["result"], "gain": reason["gain"],
                      "days": reason["days"]},
         "pass": bool(ok == n and not missing)},
        ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
