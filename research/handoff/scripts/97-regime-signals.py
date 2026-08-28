# -*- coding: utf-8 -*-
r"""97 — **「더 빠른 국면 신호」면 82 의 결론이 바뀌는가.** 사용자 물음(2026-08-28).

> 「그들이 쓰는 방식의 국면 판단으로 진행하면 뭔가 달라질까요? 여러 케이스를 두고 검증해보면 좋겠습니다.」

82 가 이미 찾아 둔 것 — **이게 이 판의 출발점이다:**
```
손해는 「파는 것」이 아니라 «안 사는 것»에서 온다
   ㉡ 팔기만 하고 «계속 산다»  +298.83%  ≈ 바탕
   ㉠ «안 산다»                +79.63%   ← 여기서 다 깎인다
그리고 **「200일선이 늦다」**
```
→ **그렇다면 «더 빠른» 신호는 덜 늦을 것이다.** 그걸 시험한다.

## 1단계 — **서술. 문턱 없음. 판정 아님.**
여섯 신호가 «며칠 쉬는지»와 세 구간에서 어떻게 되는지를 «찍기만» 한다.
**여기서 뭐라도 있으면** 2단계(가짜약 + 짝비교 판정)로 간다.
🚨 **1단계 값으로 규칙을 고치지 않는다.**

## 🚨🚨 원전 대조 결과 (검증 세션 `9b5fddc6`) — **여섯 중 원전은 «① 하나»다**
```
① SPY > 200일선        **원전**. 미너비니가 실제로 말하는 것
                       🚨 **82 ㉠ 과 «같은 실험»이다**(−218.81%p · 막힌 365건이 평균 +2.819%
                          = 남은 것의 4.5배, 폭락 «직후 반등»에 몰림).
                          → 이 판은 **「82 ㉠ 의 28년 재검정」**이다. 새 발견이 «아니다».
②③④⑤                  **내가 만든 것.** 원전에 없다.
⑥ 시장 폭 (그날 돌파 후보 수 > 60일 중앙값)
                       ⛔ **「오닐의 개념」이라 쓴 귀속을 «철회»한다.**
                          **저장소에 오닐의 「시장 폭」 «정의» 기록이 없다.** 원문 대조를 안 했다.
                          → **「우리가 만든 지표 · 원전 대조 안 함」**으로 적는다.
                          (정본의 «오귀속 금지 목록»이 정확히 이런 자리를 위해 있다)
```
🚨 **그리고 «빠진» 것 둘이 더 중요하다** — **분산일(distribution days)**·**후속 매수일(follow-through day)**.
   **그 둘은 원전의 «시장 방향» 도구로 기록돼 있고 ⑥ 은 아니다.**

## ★★ 가장 큰 어긋남 — **이진 대 점진**
```
원전  0 현금 → 1 파일럿 → 2 견인력 확인 → 3 증액 → 4 풀   (줄일 때 역순)
97    「위험」이면 신규 매수만 안 함                       (이진 on/off)
```
**원전에는 «끄는 스위치»가 없다. 다이얼이 다섯 칸이고 97 은 0 과 4 사이만 왕복한다.**
🚨 **그런데 77 이 그 다이얼을 이미 재 봤고 3a(점진적 노출)가 +2.42% 로 «가장 나빴다».**
   게다가 동시보유가 중앙 12 로 깨졌다(원전 4~8 밖).
   → **「점진적 노출을 넣으면 원전에 가까워진다」가 실측에서 반대로 나온 적이 있다.**

**적용 방식**: 신호가 「위험」이면 그날 **신규 매수만** 안 한다(보유는 유지) — 82 ㉠ 과 같은 형태.
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

import slot_sim_lots as sl                                     # noqa: E402
import _lean_load as LL                                        # noqa: E402

r91 = LL.r91
r41 = r91.r41

D0, D1 = "1999-04-01", "2026-08-21"
YEARS = tuple(range(1999, 2027))
N_SEED = 200
BLOCKS = (("닷컴 1999~2001", "1999-04-01", "2001-12-31"),
          ("2002~2017", "2002-01-01", "2017-08-31"),
          ("2018~2026", "2017-09-01", "2026-08-21"))


def ma_ok(ser, n):
    """날짜 → (그날 종가가 n일 이동평균 «위»인가). 🚨 그날 종가까지만 쓴다."""
    ds = sorted(ser)
    v = [ser[d][0] for d in ds]
    out, run = {}, []
    for i, d in enumerate(ds):
        run.append(v[i])
        if len(run) > n:
            run.pop(0)
        out[d] = (len(run) == n and v[i] > sum(run) / n)
    return out, ds


def ma_cross(ser, a, b):
    """a일 평균 > b일 평균."""
    ds = sorted(ser)
    v = [ser[d][0] for d in ds]
    out = {}
    for i, d in enumerate(ds):
        if i + 1 < b:
            out[d] = False
            continue
        out[d] = (sum(v[i - a + 1:i + 1]) / a) > (sum(v[i - b + 1:i + 1]) / b)
    return out


def breadth_ok(cnt, win=60):
    """그날 «돌파 후보 수»가 최근 `win`일 중앙값 위인가.

    ⛔ **「오닐의 시장 폭」이라 부르지 않는다** — 저장소에 오닐의 «정의» 기록이 없고
       원문 대조를 안 했다. **우리가 만든 지표다.**
    🚨 «그날까지»의 중앙값만 쓴다(그날 포함). 미래를 안 본다.
    """
    ds = sorted(cnt)
    out, run = {}, []
    for d in ds:
        run.append(cnt[d])
        if len(run) > win:
            run.pop(0)
        out[d] = (len(run) >= win // 2 and cnt[d] > st.median(run))
    return out


def sim(ev, n_seed):
    with r41.Cost(*r91.COST):
        return [sl.sim_lots(ev, seed=k, slots=r91.SLOTS, risk=r91.RISK, cap=r91.CAP,
                            reserve=False, fill_rule="truncate", cash_rule="per_slot")
                for k in range(n_seed)]


def main() -> int:
    quick = "--quick" in sys.argv
    n_seed = 12 if quick else N_SEED
    print("=" * 106, flush=True)
    print("97 1단계 — 「더 빠른 국면 신호」면 82 의 결론이 바뀌는가 (**서술 · 문턱 없음**)",
          flush=True)
    print("=" * 106, flush=True)
    print("82 가 찾은 기전: 손해는 «안 사는 데»서 온다 · 200일선이 «늦다»", flush=True)
    print("→ 더 빠른 신호는 덜 늦을 것이다. 그걸 잰다.\n", flush=True)

    # 🚨 메모리 — 조합만 남기고 «전체 후보 수»는 날짜별 «수»로만 받는다(시장 폭에 그것만 필요).
    #    28년치를 통째로 올리면 MemoryError (실측 ≈5.8GB).
    by2, cand, n_all = LL.load_combo(YEARS, D0, D1)
    ev_all, _b, _t = r91.replay(by2)
    print("전체 후보 %s → 조합 거래 %s\n"
          % ("{:,}".format(n_all), "{:,}".format(len(ev_all))), flush=True)

    bm = json.loads((r91.OUT / "91-benchmarks.json").read_text(encoding="utf-8"))
    spy, qqq = bm["SPY"]["series"], bm["QQQ"]["series"]
    s200, _ = ma_ok(spy, 200)
    s50, _ = ma_ok(spy, 50)
    q200, _ = ma_ok(qqq, 200)
    q50, _ = ma_ok(qqq, 50)
    scross = ma_cross(spy, 50, 200)
    brd = breadth_ok(cand)

    SIG = (("① SPY>200일선", s200), ("② SPY>50일선", s50),
           ("③ SPY 50>200", scross), ("④ QQQ>200일선", q200),
           ("⑤ QQQ>50일선", q50), ("⑥ 시장폭(우리것·원전아님)", brd))

    print("  %-16s %9s  %s" % ("신호", "쉬는 날", "«안 사는 날» 비율 — 구간별"), flush=True)
    print("  " + "-" * 92, flush=True)
    dates = sorted({t["entry_date"] for t in ev_all})
    for nm, ok in SIG:
        tot = sum(1 for d in dates if not ok.get(d, True))
        per = []
        for blab, a, b in BLOCKS:
            dd = [d for d in dates if a <= d <= b]
            n = sum(1 for d in dd if not ok.get(d, True))
            per.append("%s %.0f%%" % (blab.split()[0], 100.0 * n / max(1, len(dd))))
        print("  %-16s %8.1f%%  %s" % (nm, 100.0 * tot / len(dates), " · ".join(per)), flush=True)

    print("\n" + "=" * 106, flush=True)
    print("  구간별 자산 중앙 (seed %d) — «신호를 쓸 때» vs «안 쓸 때(바탕)»" % n_seed, flush=True)
    print("  %-16s %-14s %-14s %-14s %10s"
          % ("신호", BLOCKS[0][0], BLOCKS[1][0], BLOCKS[2][0], "세 구간 승"), flush=True)
    print("  " + "-" * 92, flush=True)

    base = {}
    for blab, a, b in BLOCKS:
        e = [t for t in ev_all if a <= t["entry_date"] <= b]
        base[blab] = [x["equity_pct"] for x in sim(e, n_seed)]
        print("  %-16s %-14s" % ("(바탕 · 신호 없음)" if blab == BLOCKS[0][0] else "",
                                 "%+.2f%%" % st.median(base[blab])), end="", flush=True)
    print("", flush=True)
    print("  " + "-" * 92, flush=True)

    out = {}
    for nm, ok in SIG:
        cells, wins = [], 0
        for blab, a, b in BLOCKS:
            e = [t for t in ev_all if a <= t["entry_date"] <= b and ok.get(t["entry_date"], True)]
            eq = [x["equity_pct"] for x in sim(e, n_seed)]
            dif = [x - y for x, y in zip(eq, base[blab])]
            w = 100.0 * sum(1 for x in dif if x > 0) / n_seed
            wins += (st.median(dif) > 0)
            cells.append((st.median(eq), st.median(dif), w))
        out[nm] = cells
        print("  %-16s %s %9s"
              % (nm,
                 " ".join("%+8.2f%%(%+6.2f)" % (c[0], c[1]) for c in cells),
                 "%d/3" % wins), flush=True)

    print("\n  괄호 안 = 바탕 대비 «짝차 중앙». 세 구간 «모두» 플러스인 신호가 있는가?", flush=True)
    good = [nm for nm, cs in out.items() if all(c[1] > 0 for c in cs)]
    print("  → **세 구간 모두 플러스: %s**" % (", ".join(good) if good else "**없음**"), flush=True)
    print("\n🚨 **1단계는 여기까지다.** 문턱을 안 걸었고 가짜약도 안 돌렸다.", flush=True)
    print("   무엇이든 플러스가 나오면 «쉬는 날 비율을 맞춘 무작위 대조»가 필요하다.", flush=True)
    (r91.OUT / "97-regime-signals.json").write_text(
        json.dumps({"signals": {k: v for k, v in out.items()},
                    "base": {k: st.median(v) for k, v in base.items()},
                    "n_seed": n_seed}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    print("\n저장: 97-regime-signals.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
