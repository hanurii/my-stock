# -*- coding: utf-8 -*-
"""53 — **「전환 직후」인가 「재진입」인가**. 2×2 로 가른다.

왜
--
4a 에만 있는 진입 1,166건은 **동시에 둘 다**다:
- **재진입** — 정의상 100%(`open_until` 로 막혔던 것이므로 같은 종목을 이미 보유했었다)
- **전환 직후** — 「국면 켜진 지」 중앙 **2일** · 5일 이내 **77.9%**
**이 자료로는 못 가린다.** 그래서 3a 의 «전체» 진입을 넷으로 쪼갠다.

🚨 사전등록 — **결과 보기 «전»에 못 박는다**
```
              전환 직후(≤5일)   전환 한참 뒤(>5일)
재진입              A                 B
신규                C                 D
```
| 관측 | 결론 |
|---|---|
| **A>B 그리고 C>D** | **「전환 타이밍」이 주효** — 재진입 여부와 무관 |
| **A>C 그리고 B>D** | **「재진입」이 주효** — 타이밍과 무관 |
| **한쪽에서만** | **교호작용 — 못 가림** |
| 넷이 다 비슷 | **둘 다 아님** — 4a 전용의 우위가 «다른 데서» 온다 |

⚠️ **칸별 n 과 MDE 를 «먼저» 낸다.** 칸이 작으면 애초에 못 가린다.
⚠️ **셋 이상의 칸에서 「못 가림」이면 표를 «해석하지 않는다».**

정의
----
- **재진입** = 같은 해 안에서 그 종목의 **두 번째 이후** 진입(`open_until` 규약과 같은 해 단위)
- **전환 직후** = 스캔일이 「등가중 ≥ 20MA 연속 5일 이내」 (꺼진 날은 0 → 「한참 뒤」에 안 넣고 «제외»)
  🚨 **꺼진 날 진입은 이 표에서 뺀다** — 「전환 뒤 며칠째」가 정의되지 않는다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/53-timing-vs-reentry.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import slot_sim                                          # noqa: E402

_s = _u.spec_from_file_location("r48", HERE / "48-round4-regime.py")
r48 = _u.module_from_spec(_s)
_s.loader.exec_module(r48)
r47, r41 = r48.r47, r48.r41
OUT = ROOT / ".cache" / "bt5y" / "out"
ADDS = ((3.0, 0.5),)
NEAR = 5
N_BOOT = 1000
BOOT_SEED = 530825
BLOCK = (20, 40)


def boot_mde(rows):
    """진입일 블록 재표집 → MDE = 2.80 × SD. (자료 축)"""
    byd = defaultdict(list)
    for d, v in rows:
        byd[d].append(v)
    dates = sorted(byd)
    n = len(dates)
    if n < 5:
        return None, None, None
    rnd = random.Random(BOOT_SEED)
    means = []
    for _ in range(N_BOOT):
        acc = cnt = tot = 0
        while tot < n:
            L = rnd.randint(*BLOCK)
            a = rnd.randint(0, max(0, n - L))
            for j in range(min(L, n - tot)):
                v = byd[dates[a + j]]
                acc += sum(v)
                cnt += len(v)
            tot += L
        means.append(acc / cnt if cnt else 0.0)
    means.sort()
    return (means[int(N_BOOT * .025)], means[int(N_BOOT * .975)],
            2.80 * st.pstdev(means))


def main() -> int:
    by, miss = r41.v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2
    eqw = json.loads((OUT / "26-eqw-us.json").read_text(encoding="utf-8"))
    flags = r48.ma_flags(eqw["curve_harness_filt"])
    streak, run = {}, 0
    for d, _v in eqw["curve_harness_filt"]:
        run = (run + 1) if flags[d][20] else 0
        streak[d] = run

    res = {}
    for fname, ft, fs in (("종가판", "close", "close"), ("실집행 근사판", "limit", "market")):
        ev, _ = r47.replay(by, ft, fs, adds=ADDS)
        # 재진입 표시 — 같은 해 안에서 그 종목의 두 번째 이후
        seen = defaultdict(set)
        for e in sorted(ev, key=lambda x: (x["entry_date"][:4], x["code"], x["entry_date"])):
            y = e["entry_date"][:4]
            e["_re"] = e["code"] in seen[y]
            seen[y].add(e["code"])

        def ret(e):
            lots = ([(e["entry_px"], 0.5), (e["add"][1], 0.5)] if e.get("add")
                    else [(e["entry_px"], 1.0)])
            tot = sum(x[1] for x in lots)
            return sum(fr * slot_sim.net(round(px / ep * 100 - 100, 2)) * (w / tot)
                       for _d, fr, px in e["exits"] for ep, w in lots)

        cells = {("재진입", "직후"): [], ("재진입", "뒤"): [],
                 ("신규", "직후"): [], ("신규", "뒤"): []}
        n_off = 0
        for e in ev:
            s = streak.get(e["scan_date"], 0)
            if s == 0:
                n_off += 1                      # 꺼진 날 — 표에서 제외
                continue
            k = ("재진입" if e["_re"] else "신규", "직후" if s <= NEAR else "뒤")
            cells[k].append((e["entry_date"], ret(e)))

        print("", flush=True)
        print("#" * 92, flush=True)
        print("# %s — 진입 %d · **꺼진 날 진입 %d건은 제외**(전환 뒤 며칠째가 정의 안 됨)"
              % (fname, len(ev), n_off), flush=True)
        print("#" * 92, flush=True)
        print("", flush=True)
        print("  🚨 **칸별 n 과 MDE 를 먼저** — 칸이 작으면 애초에 못 가린다", flush=True)
        print("    %-14s %8s %12s %12s %24s"
              % ("칸", "n", "per-trade", "**MDE**", "95% 구간"), flush=True)
        st_ = {}
        for k, rows in cells.items():
            lo, hi, mde = boot_mde(rows)
            m = st.mean(v for _d, v in rows) if rows else 0.0
            st_[k] = {"n": len(rows), "mean": m, "mde": mde, "lo": lo, "hi": hi}
            print("    %-14s %8d %11.4f%% %11s %24s"
                  % ("%s × %s" % k, len(rows), m,
                     ("%.4f" % mde) if mde else "—",
                     ("%+.4f ~ %+.4f" % (lo, hi)) if lo is not None else "—"), flush=True)
        print("", flush=True)
        print("  2×2 (per-trade %)", flush=True)
        print("    %-8s %14s %14s %12s" % ("", "전환 직후(≤5일)", "전환 뒤(>5일)", "차 (직후−뒤)"),
              flush=True)
        for r in ("재진입", "신규"):
            a, b = st_[(r, "직후")]["mean"], st_[(r, "뒤")]["mean"]
            print("    %-8s %13.4f%% %13.4f%% %11.4f%%p" % (r, a, b, a - b), flush=True)
        print("    %-8s %13.4f%% %13.4f%%"
              % ("차(재−신)", st_[("재진입", "직후")]["mean"] - st_[("신규", "직후")]["mean"],
                 st_[("재진입", "뒤")]["mean"] - st_[("신규", "뒤")]["mean"]), flush=True)
        # 사전등록 규칙 적용
        A = st_[("재진입", "직후")]["mean"]; B = st_[("재진입", "뒤")]["mean"]
        C = st_[("신규", "직후")]["mean"]; D = st_[("신규", "뒤")]["mean"]
        mmax = max(v["mde"] or 0 for v in st_.values())
        timing = (A > B) and (C > D)
        reentry = (A > C) and (B > D)
        small = sum(1 for v in st_.values() if (v["mde"] or 9) > abs(A - D) if True)
        print("", flush=True)
        print("  🚨 사전등록 판정 — 최대 MDE **%.4f%%p** vs 칸 사이 최대 차 **%.4f%%p**"
              % (mmax, max(abs(x - y) for x in (A, B, C, D) for y in (A, B, C, D))), flush=True)
        v = ("**「전환 타이밍」이 주효**" if (timing and not reentry) else
             ("**「재진입」이 주효**" if (reentry and not timing) else
              ("**둘 다 방향은 같음 — 못 가림(교호)**" if (timing and reentry) else
               "**한쪽에서만 — 교호작용 · 못 가림**")))
        print("     A>B %s · C>D %s · A>C %s · B>D %s  →  %s"
              % (A > B, C > D, A > C, B > D, v), flush=True)
        if mmax > max(abs(x - y) for x in (A, B, C, D) for y in (A, B, C, D)):
            print("     ⚠️ **최대 MDE 가 칸 사이 최대 차보다 크다 — 표를 «해석하지 않는다».**",
                  flush=True)
        res[fname] = {"cells": {"%s|%s" % k: v for k, v in st_.items()},
                      "n_off_excluded": n_off, "verdict": v}

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "53-timing-vs-reentry.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                                   encoding="utf-8")
    print("", flush=True)
    print("저장: .cache/bt5y/out/53-timing-vs-reentry.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
