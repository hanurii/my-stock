# -*- coding: utf-8 -*-
"""40 — **250일 상한에 닿은 방아쇠만** 경로를 «자료 끝까지» 다시 뽑는다. (두뇌 세션 결정 (b))

왜
--
0회차 재현 관문이 **미통과**였고 원인 셋 중 하나가 **250일 상한**이다.
경로가 250거래일까지만 담겨 오프라인은 `unresolved` 로 끝나는데
하네스는 그 뒤에 결착한다(35건). **그 35건이 관문을 깬다.**

🚨 **이 35건은 무작위가 아니다 — 「오래 걸린 거래」다.**
   상한 시점 미실현 **평균 +6.95% · 86.1%가 플러스**. **방향이 정해진 편향**이고
   **1회차가 검정하려는 대상 그 자체**다.

무엇을 «그대로» 지키는가
------------------------
🚨 **하네스는 해마다 «다른 곳»에서 시계열이 끝난다.**
   `series_load_end(end) = 그 해 12-31 + RESOLVE_TAIL_DAYS(300일)`
   → 2023년 실행은 **2024-10-26** 까지만 본다.
   **연장할 때 이 경계를 넘으면 하네스가 «보지 못한» 자료로 결착시키게 된다.**
   그래서 **방아쇠마다 «그 방아쇠가 속한 해»의 경계에서 자른다.**

그리고 시계열은 하네스와 **같은 로더·같은 규약**(M38 수정주가 그대로)으로 만든다.
`us_loader._iter_prices` 를 **한 번만** 훑는다(36종목뿐이라 싸다).

내는 것: `.cache/bt5y/sub/uspath_ext.json`
실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/40-extend-cap-paths.py
"""
from __future__ import annotations

import datetime as dt
import importlib.util as _u
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SUB = ROOT / ".cache" / "bt5y" / "sub"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts"))

_s = _u.spec_from_file_location("v39", HERE / "39-exit-variants.py")
v39 = _u.module_from_spec(_s)
_s.loader.exec_module(v39)

import us_loader  # noqa: E402

WARM_DAYS = 430          # 하네스와 같다 (미국은 430)
RESOLVE_TAIL_DAYS = 300  # 하네스와 같다
CAP_DAYS = 250
YEARS = tuple(range(2021, 2027))


def series_end(year: int) -> str:
    d = dt.date(year, 12, 31) + dt.timedelta(days=RESOLVE_TAIL_DAYS)
    return d.strftime("%Y-%m-%d")


def main() -> int:
    # 🚨 **원본 연도 파일을 «직접» 읽는다. `v39.load_paths()` 를 쓰면 안 된다.**
    #    그 함수는 `uspath_ext.json` 을 «덮어씌워» 준다. 그러면 이 스크립트가
    #    **이미 연장된 경로를 다시 연장 대상으로 잡아** 「하나도 안 늘어남」이 나온다
    #    (2026-08-24 실제로 101 → 43 · 증가 0 으로 잘못 돌았다).
    #    **연장의 입력은 «날것»이어야 한다.**
    paths = {}
    for y in YEARS:
        f = SUB / ("uspath_%d.json" % y)
        if not f.exists():
            print("🚨 uspath_%d.json 이 없다" % y)
            return 2
        paths[y] = json.loads(f.read_text(encoding="utf-8"))["trigger_paths"]
    n_ext_in = sum(1 for ps in paths.values() for q in ps if "_ext_from" in q)
    print("원본 경로 %d개 적재 (이미 연장된 것 %d개 — 0 이어야 한다)"
          % (sum(len(v) for v in paths.values()), n_ext_in), flush=True)
    assert n_ext_in == 0, "🚨 원본에 연장본이 섞였다"

    # ── 상한에 닿은 방아쇠 고르기 ─────────────────────────────────────────
    #    `unresolved` 이면서 경로 길이가 상한과 같다 = **잘렸다**
    hit = []
    for y, ps in paths.items():
        for p in ps:
            if len(p["c"]) < CAP_DAYS:
                continue
            _d, res, _g = v39.resolve_base(p)
            if res == "unresolved":
                hit.append((y, p))
    print("상한에 닿은 방아쇠 **%d개**" % len(hit), flush=True)
    byy = defaultdict(int)
    for y, _p in hit:
        byy[y] += 1
    print("   연도별 %s" % dict(sorted(byy.items())), flush=True)
    if not hit:
        print("   연장할 것이 없다")
        return 0

    codes = sorted({p["code"] for _y, p in hit})
    lo = (dt.date(min(YEARS), 1, 1) - dt.timedelta(days=WARM_DAYS)).strftime("%Y-%m-%d")
    hi = series_end(max(YEARS))
    print("   종목 %d개 · 적재 창 %s ~ %s (한 번만 훑는다)" % (len(codes), lo, hi), flush=True)

    # ── 시계열 만들기 — 하네스 `build_all` 의 시계열 부분과 «같은» 규약 ──
    ser = {c: {"dates": [], "opens": [], "highs": [], "lows": [], "closes": []} for c in codes}
    n_row = n_bad = 0
    for t, d, o_, h, l, c, _v, _cu in us_loader._iter_prices(set(codes), lo, hi):
        cf = float(c)
        if cf <= 0:                 # 하네스와 같은 배제
            n_bad += 1
            continue
        s = ser[t]
        s["dates"].append(d)
        s["opens"].append(float(o_))
        s["highs"].append(float(h))
        s["lows"].append(float(l))
        s["closes"].append(cf)
        n_row += 1
    for c, s in ser.items():        # CSV 가 날짜순이 아니다
        if not s["dates"]:
            continue
        o = sorted(range(len(s["dates"])), key=lambda i: s["dates"][i])
        for k in ("dates", "opens", "highs", "lows", "closes"):
            s[k] = [s[k][i] for i in o]
    print("   %d행 적재 (종가<=0 배제 %d)" % (n_row, n_bad), flush=True)

    # ── 방아쇠마다 진입일 ~ «그 해» 경계까지 다시 자른다 ──────────────────
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
        end = series_end(y)                     # 🚨 그 해 하네스가 본 마지막 날
        i1 = i0
        while i1 < len(s["dates"]) and s["dates"][i1] <= end:
            i1 += 1
        q = dict(p)
        q["d"] = s["dates"][i0:i1]
        # 🚨 시가도 실어야 «실집행 근사판»(max(목표,시가) / min(선,시가))이 돈다
        q["o"] = [round(x, 4) for x in s["opens"][i0:i1]]
        q["h"] = [round(x, 4) for x in s["highs"][i0:i1]]
        q["l"] = [round(x, 4) for x in s["lows"][i0:i1]]
        q["c"] = [round(x, 4) for x in s["closes"][i0:i1]]
        q["_ext_from"] = len(p["c"])
        q["_ext_to"] = len(q["c"])
        q["_year"] = y
        out.append(q)

    print("\n연장 %d개 · 건너뜀 %d개" % (len(out), len(skip)), flush=True)
    if skip:
        for c, r in skip:
            print("   🚨 %s — %s" % (c, r), flush=True)
    if out:
        g = [q["_ext_to"] - q["_ext_from"] for q in out]
        g.sort()
        print("   늘어난 거래일: 중앙 %d · 최소 %d · 최대 %d" % (g[len(g)//2], g[0], g[-1]),
              flush=True)
        z = [q for q in out if q["_ext_to"] == q["_ext_from"]]
        if z:
            print("   ⚠️ 하나도 안 늘어난 것 %d개 — **그 해 경계가 이미 상한이었다**"
                  % len(z), flush=True)
    SUB.mkdir(parents=True, exist_ok=True)
    (SUB / "uspath_ext.json").write_text(
        json.dumps({"trigger_paths": out, "n_skip": len(skip),
                    "cap_days": CAP_DAYS, "resolve_tail_days": RESOLVE_TAIL_DAYS},
                   ensure_ascii=False), encoding="utf-8")
    print("\n저장: .cache/bt5y/sub/uspath_ext.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
