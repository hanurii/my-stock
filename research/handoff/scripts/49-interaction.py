# -*- coding: utf-8 -*-
"""49 — **회차 간 상호작용**. 「순서가 결과를 바꾸는가」를 «실패할 수 있는» 방식으로 잰다.

🚨 왜 「로그 축 누적 ≈ 증분 합」으로는 못 재는가
------------------------------------------------
```
log(4a) − log(0회차) = [log(1a)−log(0회차)] + [log(2a)−log(1a)] + [log(3a)−log(2a)] + [log(4a)−log(3a)]
```
**좌변과 우변이 «같은 항들의 망원경 합»이다. 대수적으로 «항상» 성립한다.**
어떤 상호작용이 있어도 0.00e+00 이 나온다. **실패할 수 없는 검정이다.**
(실제로 2·3회차에서 0.00e+00 이 나왔는데, 그건 「상호작용 없음」의 증거가 아니라
 **그 검산이 아무것도 안 잰다는 증거**였다.)

무엇을 대신 재는가 — **같은 규칙을 «다른 바탕» 위에 얹는다**
------------------------------------------------------------
상호작용이 없다면 **한 회차의 증분은 어느 바탕 위에서든 같아야 한다.**
```
국면 필터(4회차)의 증분을   0회차 위 / 1a 위 / 3a 위   에서 각각 잰다
위험 기반 크기(2회차)의 증분을  0회차 위 / 1a 위        에서 각각 잰다
```
**증분이 바탕마다 크게 다르면 → 상호작용이 있고 «순서가 결과를 바꾼다».**
**비슷하면 → 회차가 독립적이고 「2·3이 나빴다」가 그대로 결론이다.**

⚠️ **이건 순서를 바꾸려고 하는 게 아니다.** 결과를 보고 순서를 바꾸면 그건 「고른 것」이다.
**「가법성이 깨졌다」는 «측정»이 있어야만 순서를 진단 대상으로 올릴 수 있다.**

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/49-interaction.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import math
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import slot_sim                                          # noqa: E402
import slot_sim_frac as sf                               # noqa: E402
import slot_sim_pyr as sp                                # noqa: E402
import slot_sim_size as ss                               # noqa: E402

_s = _u.spec_from_file_location("r48", HERE / "48-round4-regime.py")
r48 = _u.module_from_spec(_s)
_s.loader.exec_module(r48)
r47, r41 = r48.r47, r48.r41
OUT = ROOT / ".cache" / "bt5y" / "out"

N = 60
RISK, CAP, PILOT = 0.0125, 0.25, 0.5
REGIMES = (("무비용", 0.0, 0.0), ("한국-미래에셋", 0.0014, 0.0034))


class Cost:
    def __init__(self, b, s):
        self.b, self.s = b, s

    def __enter__(self):
        self.o = (slot_sim.FEE_BUY, slot_sim.FEE_SELL)
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.b, self.s

    def __exit__(self, *a):
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.o


def med(fn):
    return st.median([fn(seed=s)["equity_pct"] for s in range(N)])


def dl(a, b):
    """Δlog — 곱셈 효과를 더하기로 바꾼다."""
    return math.log(1 + a / 100) - math.log(1 + b / 100)


def main() -> int:
    by, miss = r41.v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2
    eqw = json.loads((OUT / "26-eqw-us.json").read_text(encoding="utf-8"))
    flags = r48.ma_flags(eqw["curve_harness_filt"])

    def on(p):
        g = flags.get(p["scan_date"])
        return True if (g is None or g[20] is None) else g[20]

    by_r = {y: [p for p in ps if on(p)] for y, ps in by.items()}
    print("방아쇠 %d → 국면 켜진 것 %d (%.1f%%)"
          % (sum(len(v) for v in by.values()), sum(len(v) for v in by_r.values()),
             100 * sum(len(v) for v in by_r.values()) / sum(len(v) for v in by.values())),
          flush=True)

    r41.TARGET_FILL, r41.STOP_FILL = "close", "close"
    E = {}
    for tag, src in (("", by), ("_R", by_r)):
        e0, _ = r41.replay(src, lambda p: r41.resolve_v0(p))
        e1, _ = r41.replay(src, lambda p: r41.resolve_half_then_trail(p, 8.0, 20.0))
        for x in e0:
            x["stop_frac"] = 0.10
        for x in e1:
            x["stop_frac"] = 0.08
        e3, _ = r47.replay(src, "close", "close", adds=((3.0, 0.5),))
        E["0" + tag], E["1" + tag], E["3" + tag] = e0, e1, e3

    res = {}
    for rname, fb, fs_ in REGIMES:
        print("", flush=True)
        print("=" * 96, flush=True)
        print("[%s]" % rname, flush=True)
        print("=" * 96, flush=True)
        with Cost(fb, fs_):
            v = {
                "0회차": med(lambda seed: sf.sim_frac(E["0"], seed=seed, sizing="cash")),
                "1a": med(lambda seed: sf.sim_frac(E["1"], seed=seed, sizing="cash")),
                "2a": med(lambda seed: ss.sim_size(E["1"], seed=seed, risk=RISK, cap=CAP,
                                                   partial=False)),
                "3a": med(lambda seed: sp.sim_pyr(E["3"], seed=seed, risk=RISK, cap=CAP,
                                                  pilot=PILOT)),
                # 국면 필터를 «세 바탕» 위에
                "0+R": med(lambda seed: sf.sim_frac(E["0_R"], seed=seed, sizing="cash")),
                "1+R": med(lambda seed: sf.sim_frac(E["1_R"], seed=seed, sizing="cash")),
                "3+R": med(lambda seed: sp.sim_pyr(E["3_R"], seed=seed, risk=RISK, cap=CAP,
                                                   pilot=PILOT)),
                # 위험 기반 크기를 «두 바탕» 위에
                "0+S": med(lambda seed: ss.sim_size(E["0"], seed=seed, risk=RISK, cap=CAP,
                                                    partial=False)),
            }
        print("  자산 중앙: " + " · ".join("%s %+.2f%%" % (k, v[k]) for k in
                                          ("0회차", "1a", "2a", "3a")), flush=True)
        print("", flush=True)
        print("  🚨 **국면 필터(4회차)의 증분을 «세 바탕» 위에서**", flush=True)
        print("    %-10s %14s %14s %12s" % ("바탕", "바탕 자산", "필터 얹은 뒤", "Δlog"), flush=True)
        rows = [("0회차", v["0회차"], v["0+R"]), ("1a", v["1a"], v["1+R"]),
                ("3a", v["3a"], v["3+R"])]
        for nm, a, b in rows:
            print("    %-10s %+13.2f%% %+13.2f%% %+11.4f" % (nm, a, b, dl(b, a)), flush=True)
        d = [dl(b, a) for _n, a, b in rows]
        print("    → Δlog 폭 **%.4f** (최소 %+.4f · 최대 %+.4f)"
              % (max(d) - min(d), min(d), max(d)), flush=True)
        print("", flush=True)
        print("  🚨 **위험 기반 크기(2회차)의 증분을 «두 바탕» 위에서**", flush=True)
        print("    %-10s %14s %14s %12s" % ("바탕", "바탕 자산", "크기 얹은 뒤", "Δlog"), flush=True)
        rows2 = [("0회차", v["0회차"], v["0+S"]), ("1a", v["1a"], v["2a"])]
        for nm, a, b in rows2:
            print("    %-10s %+13.2f%% %+13.2f%% %+11.4f" % (nm, a, b, dl(b, a)), flush=True)
        d2 = [dl(b, a) for _n, a, b in rows2]
        print("    → Δlog 폭 **%.4f**" % (max(d2) - min(d2)), flush=True)
        res[rname] = {"equity": v, "regime_dlog": d, "size_dlog": d2}

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "49-interaction.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    print("", flush=True)
    print("저장: .cache/bt5y/out/49-interaction.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
