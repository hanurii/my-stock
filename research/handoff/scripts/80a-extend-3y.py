# -*- coding: utf-8 -*-
"""80a — **경로를 1년 → 3년으로 다시 자른다**. 사전등록 `tasks/80-longer-paths.md`

40번(`40-extend-cap-paths.py`)의 구조를 그대로 쓰되 셋을 바꾼다:
```
① 대상   `resolve_base` 로 고른 것 → **`len(c) >= 250` 인 «모든» 경로**
         (청산 규칙에 따라 어느 게 걸릴지 다르므로 규칙과 무관한 상위집합)
② 끝     그 해 12-31 + 300일 → **진입일 + 3년**(자료가 끝나면 거기까지)
         🚨 40번의 «해마다 경계»는 하네스 «재현»을 위한 제약이지 룩어헤드 방지가 아니다.
            80번은 재현이 목적이 아니다. **관문 ①은 «원본 경로»로만 돌린다.**
③ 출력   `uspath_ext3y2017.json`  (원본·기존 연장본을 «덮지 않는다»)
```
🚨 **입력은 «날것»이어야 한다** — 40번이 이미 연장된 것을 다시 연장 대상으로 잡아
   「하나도 안 늘어남」이 나온 적이 있다(2026-08-24). 원본 연도 파일만 읽는다.

실행: BT_Y0=2017 PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \
        python research/handoff/scripts/80a-extend-3y.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SUB = ROOT / ".cache" / "bt5y" / "sub"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts"))

import us_loader                                              # noqa: E402

WARM_DAYS = 430
CAP_DAYS = 250
EXTEND_YEARS = 3
Y0 = int(os.environ.get("BT_Y0", "2017"))
YEARS = tuple(range(Y0, 2027))
OUT_NAME = "uspath_ext3y%d.json" % Y0


def main() -> int:
    paths = {}
    for y in YEARS:
        f = SUB / ("uspath_%d.json" % y)
        if not f.exists():
            print("🚨 uspath_%d.json 이 없다" % y)
            return 2
        paths[y] = json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
    n_in = sum(len(v) for v in paths.values())
    n_ext_in = sum(1 for ps in paths.values() for q in ps if "_ext_from" in q)
    print("원본 경로 %d개 · 이미 연장된 것 %d개 (0 이어야 한다)" % (n_in, n_ext_in), flush=True)
    assert n_ext_in == 0, "🚨 원본에 연장본이 섞였다"

    # 🚨 **첫 선택이 틀렸다** (2026-08-26 자기 정정) — `len(c) >= 250` 은
    #    「상한에 걸렸다」가 아니라 «자료가 250일 있었다»다. 67%(30,231개)가 걸리고
    #    3,236 종목 × 12년을 한꺼번에 올리다 **MemoryError** 로 죽었다.
    #    바른 선택 = **우리가 실제로 잴 청산들 중 «하나라도» 열린 채 끝나는 경로**.
    #    (규칙 하나에 묶이지 않도록 «합집합»으로 잡는다.)
    import pyr_trigger as _pt
    EXITS = (dict(exit_mode="half_trail"),
             dict(exit_mode="runner", run_trail=25.0),
             dict(exit_mode="runner", run_trail=15.0))
    hit = []
    for y, ps in paths.items():
        for p in ps:
            if len(p["c"]) < CAP_DAYS:
                continue
            for ek in EXITS:
                r = _pt.resolve_one(p, (), ft="limit", fs="market", stop=8.0,
                                    target=20.0, shares=(1.0,), add_stop="avg",
                                    px_round=2, **ek)
                if r["at_end"]:
                    hit.append((y, p))
                    break
    print("상한(%d봉)에 닿은 경로 **%d개** (%.1f%%)"
          % (CAP_DAYS, len(hit), 100.0 * len(hit) / n_in), flush=True)
    byy = defaultdict(int)
    for y, _p in hit:
        byy[y] += 1
    print("   연도별 %s" % dict(sorted(byy.items())), flush=True)
    if not hit:
        print("   연장할 것이 없다")
        return 0

    codes = sorted({p["code"] for _y, p in hit})
    lo = (dt.date(min(YEARS), 1, 1) - dt.timedelta(days=WARM_DAYS)).strftime("%Y-%m-%d")
    hi = "2027-12-31"          # 자료가 끝나는 곳까지 (로더가 있는 만큼만 준다)
    print("   종목 %d개 · 적재 창 %s ~ %s (한 번만 훑는다)" % (len(codes), lo, hi), flush=True)

    # 🚨 종목을 «묶음»으로 훑는다 — 한꺼번에 올리면 MemoryError 로 죽는다.
    BATCH = 400
    ser = {c: {"dates": [], "opens": [], "highs": [], "lows": [], "closes": []}
           for c in codes}
    n_row = n_bad = 0
    _rows = []
    for _i in range(0, len(codes), BATCH):
        _rows.extend(us_loader._iter_prices(set(codes[_i:_i + BATCH]), lo, hi))
    for t, d, o_, h, l, c, _v, _cu in _rows:
        cf = float(c)
        if cf <= 0:
            n_bad += 1
            continue
        s = ser[t]
        s["dates"].append(d)
        s["opens"].append(float(o_))
        s["highs"].append(float(h))
        s["lows"].append(float(l))
        s["closes"].append(cf)
        n_row += 1
    for c, s in ser.items():
        if not s["dates"]:
            continue
        o = sorted(range(len(s["dates"])), key=lambda i: s["dates"][i])
        for k in ("dates", "opens", "highs", "lows", "closes"):
            s[k] = [s[k][i] for i in o]
    last = max((s["dates"][-1] for s in ser.values() if s["dates"]), default="?")
    print("   %d행 적재 (종가<=0 배제 %d) · 자료 마지막 날 **%s**" % (n_row, n_bad, last),
          flush=True)

    out, skip = [], []
    for y, p in hit:
        s = ser.get(p["code"])
        if not s or not s["dates"]:
            skip.append((p["code"], "시계열 없음"))
            continue
        try:
            i0 = s["dates"].index(p["entry_date"])
        except ValueError:
            skip.append((p["code"], "진입일 %s 없음" % p["entry_date"]))
            continue
        ed = dt.date(*map(int, p["entry_date"].split("-")))
        end = (ed + dt.timedelta(days=365 * EXTEND_YEARS)).strftime("%Y-%m-%d")
        i1 = i0
        while i1 < len(s["dates"]) and s["dates"][i1] <= end:
            i1 += 1
        q = dict(p)
        q["d"] = s["dates"][i0:i1]
        q["o"] = [round(x, 4) for x in s["opens"][i0:i1]]
        q["h"] = [round(x, 4) for x in s["highs"][i0:i1]]
        q["l"] = [round(x, 4) for x in s["lows"][i0:i1]]
        q["c"] = [round(x, 4) for x in s["closes"][i0:i1]]
        q["_ext_from"] = len(p["c"])
        q["_ext_to"] = len(q["c"])
        q["_year"] = y
        out.append(q)

    print("\n연장 %d개 · 건너뜀 %d개" % (len(out), len(skip)), flush=True)
    for c, r in skip[:10]:
        print("   🚨 %s — %s" % (c, r), flush=True)
    if out:
        g = sorted(q["_ext_to"] - q["_ext_from"] for q in out)
        z = [q for q in out if q["_ext_to"] <= q["_ext_from"]]
        print("   늘어난 거래일: 중앙 **%d** · P10 %d · P90 %d · 최소 %d · 최대 %d"
              % (g[len(g) // 2], g[len(g) // 10], g[9 * len(g) // 10], g[0], g[-1]),
              flush=True)
        print("   ⚠️ 하나도 안 늘어난 것 **%d개** (%.1f%%) — 자료 끝에 걸린 것들"
              % (len(z), 100.0 * len(z) / len(out)), flush=True)
        zy = defaultdict(int)
        for q in z:
            zy[q["_year"]] += 1
        print("      연도별 %s  ← 최근일수록 많아야 정상" % dict(sorted(zy.items())),
              flush=True)
    SUB.mkdir(parents=True, exist_ok=True)
    (SUB / OUT_NAME).write_text(json.dumps(
        {"trigger_paths": out, "n_skip": len(skip), "cap_days": CAP_DAYS,
         "extend_years": EXTEND_YEARS}, ensure_ascii=False), encoding="utf-8")
    print("\n저장: .cache/bt5y/sub/%s" % OUT_NAME, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
