# -*- coding: utf-8 -*-
"""42 — 1회차에 붙은 확인 셋. **판정 아님. 숫자만.**

① 🚨 **노출 지표** — 41번이 「노출 최대 130.3%」를 찍었다. **0회차도 130.3%다.**
   내가 쓴 지표는 `sum(진입 시점 비중) / 현재 자산` 이었다. 자산은 **청산 때만**
   갱신되므로, 다른 칸이 손실을 확정해 자산이 줄면 **이미 잡아 둔 비중은 그대로**라
   비율이 1을 넘는다. **레버리지가 아니라 «지표 정의»의 문제일 수 있다.**
   → **제대로 된 물음은 「현금이 모자란 적이 있나」다.**
     `자유 현금 = 자산 − 열려 있는 비중의 합` 의 **최솟값**을 잰다. **음수면 실제 초과다.**
   ⚠️ **이건 분할판만의 문제가 아니라 정본 `slot_sim` 에도 똑같이 걸린다** —
      그래서 **정본으로도 같이 잰다.**

② **추격 창이 앞머리에서 짧다** — 경로가 진입일부터라 진입 «전» 저가가 없다.
   변형마다 «얼마나» 다르게 걸리는지 잰다(절반 청산 시점이 다르므로 시작점이 다르다).

③ **시장 통과 문턱을 S&P500 으로** 다시 계산한다(등가중 넷은 130배 벌어져 문턱이 못 된다).

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/42-checks.py
"""
from __future__ import annotations

import importlib.util as _u
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import slot_sim                                       # noqa: E402

_s = _u.spec_from_file_location("r41", HERE / "41-round1-exits.py")
r41 = _u.module_from_spec(_s)
_s.loader.exec_module(r41)

OUT = ROOT / ".cache" / "bt5y" / "out"
SLOTS = 5


def cash_floor_frac(trades, seed=0):
    """분할판 — `자유 현금 = 자산 − 열린 비중 합` 의 최솟값. **음수면 실제 초과다.**

    흐름은 `slot_sim_frac.sim_frac` 과 **한 줄씩 같게** 둔다(다르면 재는 대상이 달라진다).
    """
    from collections import defaultdict
    byday = defaultdict(list)
    for t in trades:
        byday[t["entry_date"]].append(t)
    for k in byday:
        byday[k].sort(key=lambda x: (x["code"], x.get("pattern", ""), x.get("scan_date", "")))
    dates = sorted(set(list(byday) + [t["resolve_date"] for t in trades]
                       + [d for t in trades for d, _f, _g in t["legs"]]))
    eq, held = 1.0, []
    floor, ratio_max, slots_max = 1e9, 0.0, 0
    for d in dates:
        due = []
        for h in held:
            rest = []
            for leg in h[3]:
                if leg[0] < d:
                    due.append((leg[0], h[1]["code"], h[2], leg[1], leg[2]))
                else:
                    rest.append(leg)
            h[3] = rest
        for _dd, _cc, wg, fr, gn in sorted(due, key=lambda x: (x[0], x[1])):
            eq += wg * fr * slot_sim.net(gn) / 100
        held = [h for h in held if h[0] >= d]
        free = SLOTS - len(held)
        if d in byday and free > 0:
            for t in sorted(byday[d], key=lambda x: slot_sim.order_key(seed, x))[:free]:
                held.append([t["resolve_date"], t, eq / SLOTS, list(t["legs"])])
        # 🚨 «아직 안 판 몫»만 열린 비중이다 — 이미 판 다리는 현금으로 돌아왔다
        open_w = sum(h[2] * sum(fr for _dd, fr, _gn in h[3]) for h in held)
        floor = min(floor, eq - open_w)
        ratio_max = max(ratio_max, open_w / eq if eq > 0 else 0)
        slots_max = max(slots_max, len(held))
    return {"cash_floor": floor, "ratio_max": ratio_max * 100, "slots_max": slots_max}


def cash_floor_canon(trades, seed=0):
    """정본 `slot_sim.sim` 과 «같은 흐름»으로 자유 현금 최솟값을 잰다."""
    byday = slot_sim._byday(trades)
    dates = sorted(set(list(byday) + [t["resolve_date"] for t in trades]))
    eq, held = 1.0, []
    floor, ratio_max, slots_max = 1e9, 0.0, 0
    for d in dates:
        done = [h for h in held if h[0] < d]
        held = [h for h in held if h[0] >= d]
        for rd, t, wg, _c in sorted(done, key=lambda h: (h[0], h[1]["code"])):
            eq += wg * slot_sim.net(t["gain"]) / 100
        free = SLOTS - len(held)
        if d in byday and free > 0:
            for t in sorted(byday[d], key=lambda t: slot_sim.order_key(seed, t))[:free]:
                held.append([t["resolve_date"], t, eq / SLOTS, False])
        open_w = sum(h[2] for h in held)
        floor = min(floor, eq - open_w)
        ratio_max = max(ratio_max, open_w / eq if eq > 0 else 0)
        slots_max = max(slots_max, len(held))
    return {"cash_floor": floor, "ratio_max": ratio_max * 100, "slots_max": slots_max}


def main() -> int:
    by, miss = r41.v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2

    print("\n" + "=" * 92, flush=True)
    print("① 노출 — **「현금이 모자란 적이 있나」**", flush=True)
    print("=" * 92, flush=True)
    print("  %-8s %-8s %14s %12s %10s" % ("변형", "경로", "자유현금 최솟값", "옛 지표(비율)", "최대 슬롯"),
          flush=True)
    res1 = {}
    for name, fn, _l, _h in r41.VARIANTS:
        ev, _b = r41.replay(by, fn)
        rows = []
        for s in (0, 1, 2, 7, 13):
            a = cash_floor_frac(ev, seed=s)
            rows.append(a)
            if name == "0회차":
                c = cash_floor_canon([{**t, "gain": t["legs"][0][2]} for t in ev], seed=s)
                rows.append({**c, "_canon": True})
        fr = [r for r in rows if not r.get("_canon")]
        cn = [r for r in rows if r.get("_canon")]
        res1[name] = {"frac_cash_floor": min(r["cash_floor"] for r in fr),
                      "frac_ratio_max": max(r["ratio_max"] for r in fr),
                      "slots_max": max(r["slots_max"] for r in fr),
                      "canon_cash_floor": (min(r["cash_floor"] for r in cn) if cn else None),
                      "canon_ratio_max": (max(r["ratio_max"] for r in cn) if cn else None)}
        r = res1[name]
        print("  %-8s %-8s %+13.6f %11.1f%% %10d"
              % (name, "분할판", r["frac_cash_floor"], r["frac_ratio_max"], r["slots_max"]),
              flush=True)
        if cn:
            print("  %-8s %-8s %+13.6f %11.1f%%   ← **정본에도 같이 걸린다**"
                  % ("", "정본", r["canon_cash_floor"], r["canon_ratio_max"]), flush=True)
    print("  → **자유 현금 최솟값이 0 이상이면 실제 초과가 아니다**"
          "(비율이 100%%를 넘는 건 «청산 때만 자산을 갱신»하는 규약의 결과).", flush=True)

    print("\n" + "=" * 92, flush=True)
    print("② 추격 창이 앞머리에서 짧다 — 변형마다 얼마나 다른가", flush=True)
    print("=" * 92, flush=True)
    print("  %-6s %10s %12s %12s %12s"
          % ("변형", "추격 사용", "창<25 인 것", "비율", "창 길이 중앙"), flush=True)
    res2 = {}
    for name, fn, _l, has_t in r41.VARIANTS:
        if name == "0회차":
            print("  %-6s %10s   (추격 없음)" % (name, "—"), flush=True)
            continue
        used, short, lens = 0, 0, []
        for ps in by.values():
            for p in ps:
                _d, _r, legs, _e = fn(p)
                # 추격으로 나간 다리는 «마지막» 다리이고 진입 후 j 번째 날이다
                j = p["d"].index(legs[-1][0]) if legs[-1][0] in p["d"] else None
                if j is None or j == 0:
                    continue
                used += 1
                w = min(j, r41.TRAIL_WINDOW)
                lens.append(w)
                short += w < r41.TRAIL_WINDOW
        res2[name] = {"used": used, "short": short,
                      "short_pct": short / used * 100 if used else 0.0,
                      "len_median": st.median(lens) if lens else None}
        r = res2[name]
        print("  %-6s %10d %12d %11.1f%% %12s"
              % (name, used, short, r["short_pct"],
                 ("%.0f일" % r["len_median"]) if r["len_median"] else "—"), flush=True)
    print("  ⚠️ 창이 25일보다 짧으면 추격선이 **느슨하다**(저가 최솟값을 덜 본다)."
          " **변형마다 비율이 다르면 그만큼 다르게 걸린다.**", flush=True)

    # ── ③ 문턱을 S&P500 으로 ─────────────────────────────────────────────
    print("\n" + "=" * 92, flush=True)
    print("③ 시장 통과 문턱 = **S&P500** (등가중 넷은 130배 벌어져 문턱이 못 된다)", flush=True)
    print("=" * 92, flush=True)
    r1 = json.loads((OUT / "41-round1.json").read_text(encoding="utf-8"))
    bm = r1["benchmark"]
    print("  S&P500 %+.2f%% · 나스닥 %+.2f%%" % (bm["US500"], bm["IXIC"]), flush=True)
    print("  등가중 4판 — %s" % " · ".join(
        "%s %+.2f%%" % (k.split(":")[1], v) for k, v in bm.items()
        if k.startswith("등가중:") and v is not None), flush=True)
    print("  ⚠️ **S&P500 은 시총가중 대형주이고 우리는 중소형 다섯 칸이다.**", flush=True)
    print("     이건 «귀속»이 아니라 **「이 돈으로 이게 최선이었나」의 잣대**다.", flush=True)
    res3 = {}
    for rname in r1["variants"]["0회차"]["arms"]:
        print("  [%s]" % rname, flush=True)
        for name in ("0회차", "1a", "1b", "1c", "1d"):
            a = r1["variants"][name]["arms"][rname]
            row = {"equity": a["equity_median"], "p5": a["p5"],
                   "breakeven": a["p5"] > 0, "market": a["p5"] > bm["US500"],
                   "median_beats_spx": a["equity_median"] > bm["US500"]}
            res3["%s|%s" % (rname, name)] = row
            print("    %-6s 자산 %+8.2f%% (하단 %+8.2f%%) → 본전 %s · **시장(S&P500) %s**"
                  "   [중앙만 보면 %s]"
                  % (name, row["equity"], row["p5"],
                     "**통과**" if row["breakeven"] else "미통과",
                     "**통과**" if row["market"] else "미통과",
                     "위" if row["median_beats_spx"] else "아래"), flush=True)

    (OUT / "42-checks.json").write_text(
        json.dumps({"exposure": res1, "trail_window": res2, "thresholds": res3,
                    "benchmark": bm}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/42-checks.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
