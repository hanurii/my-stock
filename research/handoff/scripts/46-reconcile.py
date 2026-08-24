# -*- coding: utf-8 -*-
"""46 — **두 회계를 화해시킨다.** 그리고 「1회차가 무엇을 고쳤나」를 «재고 나서» 답한다.

문제
----
같은 이름(`격차`)의 두 양이 **정반대 이야기**를 한다:
```
41번 회계(명목 20% 고정)   0회차 −33.69%p → 1a **+2.21%p**    (+35.9%p 개선)
새 회계(실제 비중)         0회차 −13.82%p → 1a **−13.07%p**   (+0.75%p 뿐)
```

두 회계가 «무엇을» 재는가
--------------------------
| | 식 | 재는 것 |
|---|---|---|
| **41번** | `체결 × 0.20 × 체결분 거래당` | **「매번 정확히 20%를 넣었다면」의 반사실** |
| **새 판** | `Σ(실제 명목 비중 × 순수익)` | **「실제로 넣은 만큼」의 산술 합** |

**차이 = 「실제 비중이 20%에서 얼마나 벗어났나」.** 그 벗어남을 **값으로** 낸다.

「1회차가 무엇을 고쳤나」 — 후보 셋
-----------------------------------
- **(가) 자본 효율**(분산 손실 감소) — 새 회계에서 +0.75%p 뿐이라 «약하다»
- **(나) 체결되는 거래의 질** — 체결분 거래당 +0.0132 → +0.8166 · 선택 이득 +0.3993%p
- **(다) 둘 다 · 다른 것**
🚨 **기전을 쓰기 전에 «보유일수»를 잰다.** 0회차만 쟀고 1a·2a 는 안 쟀다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/46-reconcile.py
"""
from __future__ import annotations

import collections
import importlib.util as _u
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import slot_sim                                          # noqa: E402
import slot_sim_frac as sf                               # noqa: E402
import slot_sim_size as ss                               # noqa: E402

_s = _u.spec_from_file_location("r41", HERE / "41-round1-exits.py")
r41 = _u.module_from_spec(_s)
_s.loader.exec_module(r41)
OUT = ROOT / ".cache" / "bt5y" / "out"
N = 60


def filled_keys(ev, seed, slots=5):
    """그 seed 에서 칸을 잡은 거래. **`nextday` 규약을 정본과 같게 쓴다.**"""
    byday = collections.defaultdict(list)
    for t in ev:
        byday[t["entry_date"]].append(t)
    for k in byday:
        byday[k].sort(key=lambda x: (x["code"], x["pattern"], x["scan_date"]))
    dates = sorted(set(list(byday) + [t["resolve_date"] for t in ev]))
    held, out = [], []
    for d in dates:
        held = [h for h in held if h[0] >= d]
        free = slots - len(held)
        if d in byday and free > 0:
            for t in sorted(byday[d], key=lambda x: slot_sim.order_key(seed, x))[:free]:
                held.append([t["resolve_date"], t])
                out.append(t)
    return out


def main() -> int:
    by, miss = r41.v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2
    idx = {(q["scan_date"], q["code"], q["pattern"]): q for ps in by.values() for q in ps}

    def hold(e):
        p = idx[(e["scan_date"], e["code"], e["pattern"])]
        return p["d"].index(e["resolve_date"])

    r41.TARGET_FILL, r41.STOP_FILL = "close", "close"
    ev = {}
    ev["0회차"], _ = r41.replay(by, lambda p: r41.resolve_v0(p))
    ev["1a"], _ = r41.replay(by, lambda p: r41.resolve_half_then_trail(p, 8.0, 20.0))
    ev["2a"] = ev["1a"]
    for e in ev["0회차"]:
        e["stop_frac"] = 0.10
    for e in ev["1a"]:
        e["stop_frac"] = 0.08

    # ── ① 두 회계 화해 ────────────────────────────────────────────────────
    print("=" * 96, flush=True)
    print("① 두 회계 — **무엇을 재는가**", flush=True)
    print("=" * 96, flush=True)
    print("  41번: `체결 × 0.20 × 체결분 거래당`  = **「매번 정확히 20%를 넣었다면」의 반사실**", flush=True)
    print("  새 판: `Σ(실제 명목 비중 × 순수익)`   = **「실제로 넣은 만큼」의 산술 합**", flush=True)
    print("  차이 = **실제 비중이 20%에서 벗어난 몫**", flush=True)
    print("", flush=True)
    print("  %-6s %8s %11s %11s %11s %11s %11s %9s"
          % ("판", "체결", "명목비중 평균", "중앙", "P10", "P90", "<20%인 비율", "관측"), flush=True)
    res = {}
    for name in ("0회차", "1a", "2a"):
        fn = ((lambda seed: ss.sim_size(ev["1a"], seed=seed, risk=0.0125, cap=0.25,
                                        partial=False)) if name == "2a"
              else (lambda seed, e=ev[name]: sf.sim_frac(e, seed=seed, sizing="cash")))
        rs = [fn(seed=s) for s in range(N)]
        g = lambda k: st.median([r[k] for r in rs])       # noqa: E731
        a41 = g("n_filled") * 0.20 * g("filled_per_trade")
        res[name] = {"n_filled": g("n_filled"), "filled_pt": g("filled_per_trade"),
                     "arith_new": g("arith_pct"), "arith_41": a41,
                     "equity": g("equity_pct"), "nom_mean": g("nom_w_mean"),
                     "nom_median": g("nom_w_median"), "nom_p10": g("nom_w_p10"),
                     "nom_p90": g("nom_w_p90"), "nom_lt20": g("nom_w_lt20")}
        d = res[name]
        print("  %-6s %8.0f %10.4f %10.4f %10.4f %10.4f %10.1f%% %+8.2f%%"
              % (name, d["n_filled"], d["nom_mean"], d["nom_median"], d["nom_p10"],
                 d["nom_p90"], d["nom_lt20"], d["equity"]), flush=True)
    print("", flush=True)
    print("  %-6s %14s %14s %14s %14s"
          % ("판", "41번 산술", "새 산술", "41번 격차", "새 격차"), flush=True)
    for name in ("0회차", "1a", "2a"):
        d = res[name]
        print("  %-6s %+13.2f%% %+13.2f%% %+13.2f%%p %+13.2f%%p"
              % (name, d["arith_41"], d["arith_new"], d["equity"] - d["arith_41"],
                 d["equity"] - d["arith_new"]), flush=True)
    print("  → 41번 개선(0회차→1a) %+.2f%%p · 새 회계 개선 %+.2f%%p"
          % ((res["1a"]["equity"] - res["1a"]["arith_41"])
             - (res["0회차"]["equity"] - res["0회차"]["arith_41"]),
             (res["1a"]["equity"] - res["1a"]["arith_new"])
             - (res["0회차"]["equity"] - res["0회차"]["arith_new"])), flush=True)

    # ── ② 보유일수 — 체결 집합 vs 방아쇠 전수 ────────────────────────────
    print("", flush=True)
    print("=" * 96, flush=True)
    print("② 보유일수 — **체결 집합이 전수와 다른가** (기전을 쓰기 «전»에 잰다)", flush=True)
    print("=" * 96, flush=True)
    print("  %-6s %26s %30s"
          % ("판", "방아쇠 전수(중앙/평균/P90)", "체결 집합(중앙/평균/P90)"), flush=True)
    hold_res = {}
    for name in ("0회차", "1a"):
        e = ev[name]
        allh = sorted(hold(x) for x in e)
        na = len(allh)
        fm, fmed, fp90 = [], [], []
        for seed in range(20):
            f = sorted(hold(x) for x in filled_keys(e, seed))
            m = len(f)
            fm.append(st.mean(f)); fmed.append(f[m // 2]); fp90.append(f[9 * m // 10])
        hold_res[name] = {"all_median": allh[na // 2], "all_mean": st.mean(allh),
                          "all_p90": allh[9 * na // 10], "fill_median": st.mean(fmed),
                          "fill_mean": st.mean(fm), "fill_p90": st.mean(fp90)}
        h = hold_res[name]
        print("  %-6s %8d / %6.1f / %6d %12.1f / %6.1f / %6.1f"
              % (name, h["all_median"], h["all_mean"], h["all_p90"],
                 h["fill_median"], h["fill_mean"], h["fill_p90"]), flush=True)
        print("        → 체결이 **%s** (중앙 %+.1f일)"
              % ("길다" if h["fill_median"] > h["all_median"] else "짧다",
                 h["fill_median"] - h["all_median"]), flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "46-reconcile.json").write_text(
        json.dumps({"accounting": res, "holding": hold_res}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print("", flush=True)
    print("저장: .cache/bt5y/out/46-reconcile.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
