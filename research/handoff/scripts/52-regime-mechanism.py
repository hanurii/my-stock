# -*- coding: utf-8 -*-
"""52 — **4회차 기전 규명**. 「새 회차」가 아니라 4회차가 «왜» 이기는가.

앞뒤가 안 맞는 자리
-------------------
```
꺼짐 거래가 per-trade 로 «더 좋다»      (+0.54 / +0.94%p · 27~31/40)
그런데 꺼짐을 «버리는» 4a 가 «이긴다»    (자산 3a +2.42% → 4a +16.39%)
설명은 「자리를 비워 켜짐을 두 배 담는다」인데 —
켜짐 per-trade 가 3a −1.6352% → 4a −1.0222% 로 «올랐다».
```
> **더 담으면 평균은 «희석»되는 게 보통이다. 올랐다는 건 «새로 들어온 것이 기존보다 좋다»는 뜻이다.**
> **왜 그것들이 3a 에서는 막혀 있었나?**

가설 둘 (둘 다 **안 쟀다**)
---------------------------
- **(가) 막힌 이유가 「같은 종목을 이미 보유」** → **재진입이 더 좋을 수 있다**(추세 지속)
- **(나) 자리가 비는 «시점»이 다르다** → 필터가 꺼짐 구간을 걷어내면 자본이
  **「국면이 다시 켜지는 초입」에 남아** 그때 진입한다. **전환 «직후»가 좋은 자리일 수 있다.**

재는 것
-------
① **4a 에만 있는 1,166건의 per-trade** (3a 공통분과 비교)
② **진입일이 「국면 켜진 지 며칠째」인지** — 4a 전용 vs 공통
③ **3a 에서 막힌 사유** — `open_until`(같은 종목 보유) 인가 자본인가
④ **왜 꺼짐이 좋은가** — 꺼짐 vs 켜짐 거래의 성질(결과 구성·보유일·수익 분포)

⚠️ **재기 전엔 기전을 안 쓴다.** 오늘 그걸로 세 번 틀렸다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/52-regime-mechanism.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import slot_sim                                          # noqa: E402
import slot_sim_pyr as sp                                # noqa: E402

_s = _u.spec_from_file_location("r48", HERE / "48-round4-regime.py")
r48 = _u.module_from_spec(_s)
_s.loader.exec_module(r48)
r47, r41 = r48.r47, r48.r41
OUT = ROOT / ".cache" / "bt5y" / "out"
ADDS = ((3.0, 0.5),)
N = 40
RISK, CAP, PILOT = 0.0125, 0.25, 0.5


def main() -> int:
    by, miss = r41.v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2
    eqw = json.loads((OUT / "26-eqw-us.json").read_text(encoding="utf-8"))
    flags = r48.ma_flags(eqw["curve_harness_filt"])
    days = [x[0] for x in eqw["curve_harness_filt"]]

    # 「국면 켜진 지 며칠째」 — 그날까지 연속으로 켜진 일수 (꺼진 날은 0)
    streak, run = {}, 0
    for d in days:
        f = flags[d][20]
        run = (run + 1) if f else 0
        streak[d] = run

    def on(p):
        g = flags.get(p["scan_date"])
        return True if (g is None or g[20] is None) else g[20]

    onmap = {(p["scan_date"], p["code"], p["pattern"]): on(p)
             for ps in by.values() for p in ps}

    res = {}
    for fname, ft, fs in (("종가판", "close", "close"), ("실집행 근사판", "limit", "market")):
        e3, _ = r47.replay(by, ft, fs, adds=ADDS)
        by_r = {y: [p for p in ps if on(p)] for y, ps in by.items()}
        e4, _ = r47.replay(by_r, ft, fs, adds=ADDS)
        K3 = {(x["scan_date"], x["code"], x["pattern"]) for x in e3}
        pt = {(x["scan_date"], x["code"], x["pattern"]): x for x in e3}
        for x in e4:
            pt.setdefault((x["scan_date"], x["code"], x["pattern"]), x)
        only4 = [(x["scan_date"], x["code"], x["pattern"]) for x in e4
                 if (x["scan_date"], x["code"], x["pattern"]) not in K3]
        print("", flush=True)
        print("#" * 92, flush=True)
        print("# %s — 3a 진입 %d · 4a 진입 %d · **4a 에만 %d**"
              % (fname, len(e3), len(e4), len(only4)), flush=True)
        print("#" * 92, flush=True)

        def ret(k):
            e = pt[k]
            lots = ([(e["entry_px"], 0.5), (e["add"][1], 0.5)] if e.get("add")
                    else [(e["entry_px"], 1.0)])
            tot = sum(x[1] for x in lots)
            return sum(fr * slot_sim.net(round(px / ep * 100 - 100, 2)) * (w / tot)
                       for _d, fr, px in e["exits"] for ep, w in lots)

        # ── ③ 막힌 사유 ─────────────────────────────────────────────────
        print("", flush=True)
        print("③ **3a 에서 막힌 사유** — 4a 에만 있는 진입은 어디서 막혔나", flush=True)
        print("   4a 에만 있는 %d건은 «정의상» 3a 의 진입 집합에 «없다» = **`open_until` 로 막혔다**"
              % len(only4), flush=True)
        print("   (자본으로 막히는 것은 «진입 집합에는 있고 체결만 안 된» 것이라 다른 무리다)",
              flush=True)
        same_code = Counter()
        for k in only4:
            same_code[k[1]] += 1
        print("   → **같은 종목을 이미 들고 있어서**다. 종목 %d개 · 한 종목당 최대 %d건"
              % (len(same_code), max(same_code.values()) if same_code else 0), flush=True)

        # ── ① per-trade 비교 ────────────────────────────────────────────
        print("", flush=True)
        print("① **per-trade** — 4a 전용 vs 3a 공통(국면 켜진 것만) · **진입 집합**", flush=True)
        common_on = [k for k in K3 if onmap.get(k)]
        a = st.mean(ret(k) for k in only4)
        b = st.mean(ret(k) for k in common_on)
        print("   4a 전용 %5d건 **%+.4f%%**  ·  3a 공통(켜짐) %5d건 %+.4f%%  · 차 **%+.4f%%p**"
              % (len(only4), a, len(common_on), b, a - b), flush=True)

        # ── ② 국면 켜진 지 며칠째 ────────────────────────────────────────
        print("", flush=True)
        print("② **진입일이 「국면 켜진 지 며칠째」인가** (스캔일 기준 · 0 = 꺼진 날)", flush=True)
        s4 = sorted(streak.get(pt[k]["scan_date"], 0) for k in only4)
        sc = sorted(streak.get(pt[k]["scan_date"], 0) for k in common_on)
        for lab, v in (("4a 전용", s4), ("3a 공통(켜짐)", sc)):
            n = len(v)
            print("   %-14s n=%5d · 중앙 %3d일 · 평균 %5.1f · P10 %3d · P90 %4d · "
                  "**5일 이내 %5.1f%%**"
                  % (lab, n, v[n // 2], st.mean(v), v[n // 10], v[9 * n // 10],
                     100 * sum(1 for x in v if x <= 5) / n), flush=True)

        # ── ④ 꺼짐이 왜 좋은가 ──────────────────────────────────────────
        print("", flush=True)
        print("④ **꺼짐 vs 켜짐 거래의 성질** · **진입 집합**", flush=True)
        grp = {"켜짐": [k for k in K3 if onmap.get(k)],
               "꺼짐": [k for k in K3 if not onmap.get(k)]}
        print("   %-6s %8s %12s %10s %26s"
              % ("국면", "n", "per-trade", "보유일 중앙", "결과 구성(win/loss/amb/unres)"), flush=True)
        res4 = {}
        for g, ks in grp.items():
            v = [ret(k) for k in ks]
            hd = sorted(_hold(pt[k], by) for k in ks)
            c = Counter(pt[k]["result"] for k in ks)
            n = len(ks)
            res4[g] = {"n": n, "pt": st.mean(v), "hold": hd[n // 2],
                       "mix": {kk: 100 * c.get(kk, 0) / n for kk in
                               ("win", "loss", "ambiguous", "unresolved")}}
            print("   %-6s %8d %11.4f%% %9d일 %8.1f / %5.1f / %4.1f / %5.1f"
                  % (g, n, st.mean(v), hd[n // 2],
                     res4[g]["mix"]["win"], res4[g]["mix"]["loss"],
                     res4[g]["mix"]["ambiguous"], res4[g]["mix"]["unresolved"]), flush=True)
        res[fname] = {"only4": len(only4), "only4_pt": a, "common_on_pt": b,
                      "streak_only4_med": s4[len(s4) // 2], "streak_common_med": sc[len(sc) // 2],
                      "kinds": res4}

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "52-regime-mechanism.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                                  encoding="utf-8")
    print("", flush=True)
    print("저장: .cache/bt5y/out/52-regime-mechanism.json", flush=True)
    return 0


_DAYIDX = {}


def _hold(e, by):
    k = (e["scan_date"], e["code"], e["pattern"])
    if not _DAYIDX:
        for ps in by.values():
            for p in ps:
                _DAYIDX[(p["scan_date"], p["code"], p["pattern"])] = p["d"]
    d = _DAYIDX.get(k)
    if not d:
        return 0
    try:
        return d.index(e["resolve_date"])
    except ValueError:
        return len(d) - 1


if __name__ == "__main__":
    sys.exit(main())
