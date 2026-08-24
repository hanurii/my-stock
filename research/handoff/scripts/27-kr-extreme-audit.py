# -*- coding: utf-8 -*-
"""27 · **한국 하네스 시계열의 「하루 |수익률| > 100%」 전수 감사** (두뇌 세션 결정 3).

왜
--
제일바이오 2026-02-09 는 `fltRt = +29,948.08` 인데 **비수정 종가비도 같은 값**이라
하네스의 대체 규약(`pdata_series.py:94`)이 그대로 통과시킨다.
→ **한국 6년 결과(3,776진입) 안에 가짜 움직임이 들어갔는지**를 직접 본다.

무엇을 재는가
-------------
1. **하네스가 실제로 쓰는 하루 비율**로 전수를 센다.
   `ratio = 1 + fltRt/100`  단, `fltRt` 없거나 `|fltRt| > 100` 이면 `close_i / close_{i-1}`,
   그 결과가 `<= 0` 이면 `1.0`. (`pdata_series.py:92~101` 그대로)
2. 그중 `|ratio - 1| > 1.0` (=±100%p) 인 **종목-일 전수**.
3. 그 종목-일이 **3,776 진입의 보유 구간**에 걸리는가 (걸리면 가짜 익절·손절).
4. 그 종목-일이 진입 **직전 253거래일**에 있는가 (걸리면 52주 신고가·200일선·RS 오염).

⚠️ **관문 통과 후보 172,764 대조는 이 스크립트로 못 한다** — `bt_*.json` 은 후보의
   «수»만 남기고 종목 코드를 안 남긴다(`per_date.n_candidates`). **확인 불가**로 보고한다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/27-kr-extreme-audit.py
"""
from __future__ import annotations

import json
import re
import sys
from bisect import bisect_left, bisect_right
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PD = ROOT / ".cache" / "pdata"
BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
# 하네스가 실제로 본 구간: 관문이 253거래일을 요구하므로 warm 430일이 앞에 붙는다.
LO, HI = "20191201", "20260821"
# 문턱은 인자로 받는다: `python 27-... [하한] [상한]` (배율 아닌 «비율 차」, 1.0 = 100%p)
#   기본 (1.0, inf) = ±100%p 초과.  결정 C 는 (0.5, 1.0) = 50~100%p 구간.
# 🚨 이건 **찾을 곳을 넓히는 것**이지 결과에 맞춰 문턱을 옮기는 게 아니다.
THRESH = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
THRESH_HI = float(sys.argv[2]) if len(sys.argv) > 2 else float("inf")
LOOKBACK = 253

EXCLUDE = re.compile(
    "스팩|SPAC|리츠|REIT|ETF|ETN|인프라|우B$|우C$|[0-9]우$|우$|우\\(전환\\)|우B\\(전환\\)")
FOREIGN = re.compile("^9[0-9]{5}$")


def num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def main():
    files = sorted(x for x in PD.glob("price_*.json") if LO <= x.stem[6:] <= HI)
    print("pdata %d일 (%s ~ %s)" % (len(files), files[0].stem[6:], files[-1].stem[6:]),
          flush=True)
    prev = {}
    hits = []                     # (date, code, name, ratio, 출처)
    cal = []
    for p in files:
        d = p.stem[6:]
        date = "%s-%s-%s" % (d[:4], d[4:6], d[6:])
        try:
            recs = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        cal.append(date)
        cur = {}
        for code, r in recs.items():
            if r.get("mrktCtg") not in ("KOSPI", "KOSDAQ") or FOREIGN.match(code):
                continue
            nm = r.get("itmsNm") or ""
            if EXCLUDE.search(nm):
                continue
            c = num(r.get("clpr"))
            if not c or c <= 0:
                continue
            pc = prev.get(code)
            cur[code] = c
            if pc is None:
                continue                      # 상장 첫날·창 첫날은 비율 미정의
            f = num(r.get("fltRt"))
            if f is None or abs(f) > 100.0:    # 하네스: 대체 (제외 아님)
                ratio = c / pc if pc else 1.0
                src = "종가비(대체)"
            else:
                ratio = 1.0 + f / 100.0
                src = "fltRt"
            if ratio <= 0:
                ratio = 1.0
            if THRESH < abs(ratio - 1.0) <= THRESH_HI:
                hits.append((date, code, nm, ratio, src))
        prev = cur
    print("거래일 %d · **하루 |수익률| %d~%s%%p 인 종목-일 %d건 · %d종목**"
          % (len(cal), int(THRESH * 100),
             ("%d" % (THRESH_HI * 100)) if THRESH_HI != float("inf") else "무한",
             len(hits), len({h[1] for h in hits})), flush=True)
    hits.sort(key=lambda h: -abs(h[3] - 1))
    print("", flush=True)
    print("상위 20", flush=True)
    for date, code, nm, ratio, src in hits[:20]:
        print("   %s  %-8s %-16s **%+12.1f%%**  (%s)"
              % (date, code, nm[:16], (ratio - 1) * 100, src), flush=True)
    up = sum(1 for h in hits if h[3] > 1)
    print("", flush=True)
    print("방향: 위로 %d · 아래로 %d" % (up, len(hits) - up), flush=True)

    by_code = defaultdict(list)
    for date, code, nm, ratio, src in hits:
        by_code[code].append((date, ratio, nm, src))
    pos = {d: i for i, d in enumerate(cal)}

    # ── 3,776 진입과 대조 ────────────────────────────────────────────────────
    ev = []
    for y in range(2021, 2027):
        f = BT / ("bt_%d.json" % y)
        if f.exists():
            ev += json.loads(f.read_text(encoding="utf-8"))["events"]
    print("", flush=True)
    print("=" * 74, flush=True)
    print("한국 진입 %d건과 대조" % len(ev), flush=True)
    print("=" * 74, flush=True)
    in_hold, in_look = [], []
    for e in ev:
        hl = by_code.get(e["code"])
        if not hl:
            continue
        ed, rd = e["entry_date"], e.get("resolve_date") or e["entry_date"]
        for date, ratio, nm, src in hl:
            if ed <= date <= rd:
                in_hold.append((e, date, ratio))
            else:
                i, j = pos.get(ed), pos.get(date)
                if i is not None and j is not None and 0 < i - j <= LOOKBACK:
                    in_look.append((e, date, ratio))
    print("**보유 구간에 걸린 진입: %d건**" % len(in_hold), flush=True)
    for e, date, ratio in in_hold[:20]:
        print("   %-8s %-14s 진입 %s → 결착 %s | 사건 %s **%+.1f%%** | %s · 실현 %+.2f%%"
              % (e["code"], (e.get("name") or "")[:14], e["entry_date"],
                 e.get("resolve_date"), date, (ratio - 1) * 100,
                 e.get("exit_reason") or e["result"],
                 e.get("gain_at_resolve_pct") or 0), flush=True)
    print("", flush=True)
    print("**진입 직전 %d거래일 안에 사건이 있던 진입: %d건 (%d종목)**"
          % (LOOKBACK, len(in_look), len({x[0]["code"] for x in in_look})), flush=True)
    for e, date, ratio in in_look[:20]:
        print("   %-8s %-14s 진입 %s | 사건 %s **%+.1f%%** | %s · 실현 %+.2f%%"
              % (e["code"], (e.get("name") or "")[:14], e["entry_date"], date,
                 (ratio - 1) * 100, e.get("exit_reason") or e["result"],
                 e.get("gain_at_resolve_pct") or 0), flush=True)
    print("", flush=True)
    print("⚠️ **관문 통과 후보(172,764)와의 대조는 확인 불가** — `bt_*.json` 의 "
          "`per_date` 는 후보 «수»만 남기고 종목 코드를 남기지 않는다.", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / ("27-kr-extreme-audit-%d-%s.json" % (int(THRESH*100), ("%d" % (THRESH_HI*100)) if THRESH_HI != float("inf") else "inf"))).write_text(json.dumps({
        "threshold_lo_pct": THRESH * 100, "threshold_hi_pct": THRESH_HI * 100, "n_days": len(cal),
        "n_hits": len(hits), "n_codes": len({h[1] for h in hits}),
        "hits": [{"date": d, "code": c, "name": n, "ret_pct": (r - 1) * 100,
                  "source": s} for d, c, n, r, s in hits],
        "n_entries": len(ev),
        "in_holding": [{"code": e["code"], "name": e.get("name"),
                        "entry": e["entry_date"], "resolve": e.get("resolve_date"),
                        "event_date": d, "event_ret_pct": (r - 1) * 100,
                        "exit_reason": e.get("exit_reason"), "result": e["result"],
                        "gain_pct": e.get("gain_at_resolve_pct")}
                       for e, d, r in in_hold],
        "in_lookback": [{"code": e["code"], "entry": e["entry_date"],
                         "event_date": d, "event_ret_pct": (r - 1) * 100,
                         "result": e["result"],
                         "gain_pct": e.get("gain_at_resolve_pct")}
                        for e, d, r in in_look],
        "gate_candidates_check": "확인 불가 — bt_*.json 이 후보 코드를 남기지 않음",
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("저장 완료", flush=True)


if __name__ == "__main__":
    main()
