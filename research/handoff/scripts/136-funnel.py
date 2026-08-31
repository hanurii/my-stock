# -*- coding: utf-8 -*-
"""136 — **「몇 개가 추천되고, 몇 개를 살 수 있나」 연도별 깔때기** (묘사 · 판정 아님)

사용자(2026-08-31): 「**작년 기준으로 몇 개의 종목이 매수 추천 종목으로 나타났으며,
그중 우리는 몇 개의 종목만 살 수 있었습니까? 또, 평균적으로 몇 개의 종목이 추천되며
우리는 몇 개의 종목을 1년에 거래합니까?**」

# 깔때기의 «층»을 먼저 정한다 — 안 그러면 숫자가 층마다 다르다
```
① **감시 목록**   등급 필터까지 통과한 후보          (by2)
② **매수 추천**   + 성장 둔화 필터 통과              (by_f)   ← 「사도 되는 종목」
③ **돌파 발생**   피벗을 실제로 돌파해 «주문이 나간» 것 (replay 의 ev)
                 🚨 같은 종목이 «아직 보유 중»이면 여기서 걸러진다
④ **실제 매수**   그때 «슬롯이 비어 있어» 산 것       (fill_log 의 pilot)
```
**사용자님이 물으신 「추천」은 ③(주문이 나간 것)에 가깝고, 「살 수 있었던 것」은 ④다.**

# 재는 것
```
목표 +20/−10 (현행) 과 +30/−10 (검토 중) 둘 다 · 연도별 · 운의 번호 20판 중앙
🚨 **판정이 아니라 «묘사»다.** 문턱을 걸지 않는다
🚨 **2026 은 8월 21일까지라 «반쪽 해»다** — 평균에서 뺀다
```
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _load(mod, fn):
    s = _u.spec_from_file_location(mod, HERE / fn)
    m = _u.module_from_spec(s)
    s.loader.exec_module(m)
    return m


r91 = _load("r91", "91-us-out-of-sample.py")
r102 = _load("r102", "102-implement-principles.py")
r103 = _load("r103", "103-code33-strength.py")
f92a = r102.f92a

YEARS = tuple(range(1999, 2027))
CFG = ((20.0, "현행 +20/−10"), (30.0, "검토 +30/−10"))
LAST = "2025"


def main() -> int:
    n_seed = 6 if "--quick" in sys.argv else 20
    print("=" * 100, flush=True)
    print("136 — **몇 개가 추천되고 몇 개를 살 수 있나** · 연도별 깔때기 (묘사)", flush=True)
    print("=" * 100, flush=True)

    (_a, _b, by2), missing, _ = r91.load_ladder(
        YEARS, "1999-04-01", "2026-08-21", "91-monthly-us-full.json", use_ext=False)
    if missing:
        print("🚨 경로 없음", flush=True)
        return 2
    fund, ixf = f92a.load()
    ix = {f: i for i, f in enumerate(ixf)}
    by_f = {}
    for y in sorted(by2):
        k = []
        for p in by2[y]:
            arq = (fund.get(p["code"]) or {}).get("ARQ") or []
            a = f92a.asof(arq, p["entry_date"]) if arq else None
            v = (None if (a is None or r102._ord(p["entry_date"]) - r102._ord(a[0])
                          > r102.STALE_MAX)
                 else r103.judge(arq, arq.index(a), ix, 1, 2))
            if v is not False:
                k.append(p)
        by_f[y] = k

    # ①② 층 — 후보를 «진입일 기준 연도»로 센다 (스캔 연도와 다를 수 있다)
    w1, w2 = Counter(), Counter()
    for y in sorted(by2):
        for p in by2[y]:
            w1[p["entry_date"][:4]] += 1
        for p in by_f[y]:
            w2[p["entry_date"][:4]] += 1

    r91.STOP = 10.0
    r91.HALF = 0.5
    out = {}
    for tg, nm in CFG:
        r91.TARGET = tg
        ev, _b1, _b2 = r91.replay(by_f)
        w3 = Counter(t["entry_date"][:4] for t in ev)
        rs = r91.sim(ev, n_seed)
        per = []
        for x in rs:
            per.append(Counter(f[3][:4] for f in x["fill_log"] if f[1] == "pilot"))
        yrs = sorted(w3)
        w4 = {y: st.median(c.get(y, 0) for c in per) for y in yrs}
        out[nm] = {"w3": dict(w3), "w4": w4}

        print("\n### %s — 연도별 깔때기" % nm, flush=True)
        print("  %-6s %10s %10s %11s %11s %9s"
              % ("연도", "① 감시", "② 추천", "③ 돌파주문", "④ 실제매수", "④/③"), flush=True)
        print("  " + "-" * 62, flush=True)
        full = [y for y in yrs if y not in ("1999", "2026")]
        for y in yrs:
            mk = "  ← 작년" if y == LAST else ("  (반쪽 해)" if y in ("1999", "2026") else "")
            print("  %-6s %9d %9d %10d %10.0f %8.1f%%%s"
                  % (y, w1.get(y, 0), w2.get(y, 0), w3.get(y, 0), w4.get(y, 0),
                     100.0 * w4.get(y, 0) / max(1, w3.get(y, 0)), mk), flush=True)
        a1 = st.mean(w1.get(y, 0) for y in full)
        a2 = st.mean(w2.get(y, 0) for y in full)
        a3 = st.mean(w3.get(y, 0) for y in full)
        a4 = st.mean(w4.get(y, 0) for y in full)
        print("  " + "-" * 62, flush=True)
        print("  %-6s %9.0f %9.0f %10.0f %10.1f %8.1f%%   ← **평균(온전한 %d해)**"
              % ("평균", a1, a2, a3, a4, 100.0 * a4 / max(1, a3), len(full)), flush=True)
        r1 = [y for y in full if y >= "2016"]
        print("  %-6s %9.0f %9.0f %10.0f %10.1f %8.1f%%   ← 최근 %d해"
              % ("최근", st.mean(w1.get(y, 0) for y in r1), st.mean(w2.get(y, 0) for y in r1),
                 st.mean(w3.get(y, 0) for y in r1), st.mean(w4.get(y, 0) for y in r1),
                 100.0 * st.mean(w4.get(y, 0) for y in r1)
                 / max(1, st.mean(w3.get(y, 0) for y in r1)), len(r1)), flush=True)
        out[nm]["avg"] = {"w1": a1, "w2": a2, "w3": a3, "w4": a4}

    print("\n" + "=" * 100, flush=True)
    print("### ★ 작년(%s) 한 해 — 두 설정 나란히" % LAST, flush=True)
    print("  %-14s %10s %10s %11s %11s %9s"
          % ("", "① 감시", "② 추천", "③ 돌파주문", "④ 실제매수", "④/③"), flush=True)
    for tg, nm in CFG:
        d = out[nm]
        print("  %-14s %9d %9d %10d %10.0f %8.1f%%"
              % (nm, w1.get(LAST, 0), w2.get(LAST, 0), d["w3"].get(LAST, 0),
                 d["w4"].get(LAST, 0),
                 100.0 * d["w4"].get(LAST, 0) / max(1, d["w3"].get(LAST, 0))), flush=True)

    (r91.OUT / "136-funnel.json").write_text(
        json.dumps({"w1": dict(w1), "w2": dict(w2),
                    "cfg": {k: {"w3": v["w3"], "w4": v["w4"], "avg": v["avg"]}
                            for k, v in out.items()}},
                   ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("\n저장: 136-funnel.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
