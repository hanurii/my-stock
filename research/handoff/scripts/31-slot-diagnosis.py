# -*- coding: utf-8 -*-
"""31 · **왜 미국은 거래가 2배인데 체결이 절반인가** — 슬롯 점유 진단.

미국 거래 7,619 (한국의 2.02배) · 슬롯5 체결 **231** (한국 424의 0.54배).
슬롯 다섯 칸에서 체결 수를 지배하는 건 **보유 기간**이다. 그 숫자를 낸다.

🚨 **이건 판정이 아니라 기술이다.** 그리고 20번 C팔의 교훈이 그대로 걸린다 —
   **체결 수 차이를 실력으로 읽지 않도록** 자산곡선 차이를 **「거래당 × 체결 수」로 분해**해
   함께 낸다.

내는 것
-------
1. 보유일수 분포 (평균·P25·중앙·P75·P90) — 양 시장
2. 슬롯 점유율 = Σ보유일 ÷ (5칸 × 거래일)
3. 결착 사유 분포 — `result`(win/loss/ambiguous/unresolved) 로 **양 시장 같은 축**.
   ⚠️ 미국 이벤트에만 `exit_reason` 이 있어 그쪽은 더 잘게도 낸다(원본 하네스에 없던 키).
4. `open_until` 차단 건수 — 「이미 보유 중」으로 막힌 진입
5. 하루 진입 가능 후보 분포 — 슬롯 경쟁 강도
6. **자산 = 거래당 × 체결 수 분해**: 예측 `exp(체결수 × 거래당 ÷ 500) − 1`
   (슬롯 다섯 칸에 `eq/5` 씩 넣으므로 로그자산이 대략 `n × 거래당/5`)

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/31-slot-diagnosis.py
"""
from __future__ import annotations

import json
import math
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_SEED = 200
REGIMES = {"무비용(미국 실제)": (0.0, 0.0),
           "한국-우대(세금만)": (0.0, 0.0020),
           "한국-미래에셋": (0.0014, 0.0034)}


class Cost:
    def __init__(self, b, s):
        self.b, self.s = b, s

    def __enter__(self):
        self.ob, self.os_ = slot_sim.FEE_BUY, slot_sim.FEE_SELL
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.b, self.s

    def __exit__(self, *a):
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.ob, self.os_


def load(mkt):
    ev, per, skip = [], [], Counter()
    if mkt == "KR":
        for y in range(2021, 2027):
            f = BT / ("bt_%d.json" % y)
            if not f.exists():
                continue
            d = json.loads(f.read_text(encoding="utf-8"))
            ev += d["events"]
            per += d.get("per_date") or []
            for k, v in ((d.get("params") or {}).get("skipped") or {}).items():
                skip[k] += v
    else:
        # 🚨 미국도 **연도별 여섯 실행**이다(워밍업 430 · `open_until` 연도 초기화)
        #    → 한국 `bt_YYYY.json` 과 **구조까지 같다**. 옛 연속 실행판은
        #    `us_full_DEADZONE.json` 으로 보존돼 있고 **인용 금지**다.
        for f in sorted((BT / "sub").glob("us_20*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            ev += d["events"]
            per += d.get("per_date") or []
            for k, v in ((d.get("params") or {}).get("skipped") or {}).items():
                skip[k] += v
    seen, out = set(), []
    last = max((e.get("resolve_date") or e["entry_date"]) for e in ev)
    for e in sorted(ev, key=lambda x: (x["entry_date"], x["code"], x.get("pattern", ""))):
        k = (e["scan_date"], e["code"], e.get("pattern", ""))
        if k in seen or e.get("gain_at_resolve_pct") is None:
            continue
        seen.add(k)
        e = dict(e)
        e["resolve_date"] = e.get("resolve_date") or last
        out.append(e)
    return out, per, skip


def to_trades(ev):
    return [{"code": e["code"], "scan_date": e["scan_date"],
             "pattern": e.get("pattern", ""), "entry_date": e["entry_date"],
             "resolve_date": e["resolve_date"], "gain": e["gain_at_resolve_pct"],
             "result": e["result"]} for e in ev]


def filled_and_occupancy(trades, dates, seed=0, slots=5):
    """🚨 **슬롯 점유율을 근사로 재면 안 된다.**

    처음엔 `평균보유일 × 체결수 ÷ (5 × 거래일)` 로 쟀는데 미국에서 **106.6%** 가 나왔다.
    다섯 칸에서 106%는 **불가능**하다 — 원인은 「평균 보유일」을 **전체 거래**로 냈기 때문이다.
    실측하니 **체결분이 오히려 «더 짧다»**(한국 14.13 vs 전체 15.62 · 미국 21.00 vs 27.86).
    그래서 `전체평균 × 체결수` 는 참값보다 **크게** 나오고, 미국에서 100%를 넘겼다.
    (내 처음 추측 「체결분이 더 길 것」은 **실측에 반증됐다.**)

    그래서 `slot_sim.sim` 의 선택 논리를 그대로 되짚어 **체결된 거래를 직접 모으고**
    **칸-일을 세어** 점유율을 낸다. 아래 관문으로 `slot_sim.sim` 과 같은 값인지 확인한다.
    """
    pos = {d: i for i, d in enumerate(dates)}
    byday = slot_sim._byday(trades, "canonical")
    all_d = sorted(set(list(byday) + [t["resolve_date"] for t in trades]))
    eq, held = 1.0, []
    filled, slot_days = [], 0
    for d in all_d:
        done = [h for h in held if h[0] < d]
        held = [h for h in held if h[0] >= d]
        for rd, t, wg in sorted(done, key=lambda h: (h[0], h[1]["code"])):
            eq += wg * slot_sim.net(t["gain"]) / 100
        free = slots - len(held)
        if d in byday and free > 0:
            c = sorted(byday[d], key=lambda t: slot_sim.order_key(seed, t))
            for t in c[:free]:
                held.append([t["resolve_date"], t, eq / slots])
                filled.append(t)
                i, j = pos.get(t["entry_date"]), pos.get(t["resolve_date"])
                slot_days += max(1, (j - i)) if (i is not None and j is not None) else 1
        if d in pos:
            pass
    for rd, t, wg in held:
        eq += wg * slot_sim.net(t["gain"]) / 100
    return filled, slot_days, (eq - 1) * 100


def q(xs, p):
    s = sorted(xs)
    return s[min(len(s) - 1, int(len(s) * p))]


def main():
    res = {}
    for mkt in ("KR", "US"):
        ev, per, skip = load(mkt)
        tr = to_trades(ev)
        dates = sorted({p["scan_date"] for p in per})
        pos = {d: i for i, d in enumerate(dates)}
        # 보유일수 — 하네스의 days_held 가 있으면 그것, 없으면 거래일 간격
        hold = []
        for e in ev:
            h = e.get("days_held")
            if h is None:
                i, j = pos.get(e["entry_date"]), pos.get(e["resolve_date"])
                h = (j - i) if (i is not None and j is not None) else None
            if h is not None:
                hold.append(h)
        # 🚨 분해는 **무비용 팔**로 통일한다(두뇌 세션 결정 1) — 비용을 빼면
        #    순수하게 「슬롯 선택 + 분산 손실」만 남는다. 비용 판은 **항등식으로 되돌릴 수 있다.**
        with Cost(*REGIMES["무비용(미국 실제)"]):
            band = slot_sim.band(tr, n_runs=N_SEED)
            pt = st.mean(slot_sim.net(t["gain"]) for t in tr)
        # 근사 대신 **직접 세기**. 그리고 정본 시뮬과 같은 값인지 관문으로 확인한다.
        with Cost(*REGIMES["무비용(미국 실제)"]):
            fl, sdays, eqx = filled_and_occupancy(tr, dates, seed=0)
            ref = slot_sim.sim(tr, seed=0)
        gate_ok = (len(fl) == ref["n_filled"] and abs(eqx - ref["equity_pct"]) < 1e-9)
        print("  [관문] 점유율 계산기가 `slot_sim.sim` 과 같은가 — 체결 %d vs %d · "
              "자산 %+.6f vs %+.6f → **%s**"
              % (len(fl), ref["n_filled"], eqx, ref["equity_pct"],
                 "일치" if gate_ok else "🚨불일치 — 점유율을 신뢰하지 않는다"), flush=True)
        occ = (sdays / (5 * len(dates))) if (gate_ok and dates) else None
        hold_filled = []
        for t in fl:
            i, j = pos.get(t["entry_date"]), pos.get(t["resolve_date"])
            if i is not None and j is not None:
                hold_filled.append(j - i)
        pred = (math.exp(band["n_filled"] * pt / 500.0) - 1) * 100
        cand = [p.get("n_candidates") or 0 for p in per]
        entered = [p.get("n_entered") or 0 for p in per]
        rc = Counter(e["result"] for e in ev)
        xr = Counter(e.get("exit_reason") for e in ev if e.get("exit_reason"))
        r = {
            "n_trades": len(tr), "n_days": len(dates),
            "hold_mean": st.mean(hold), "hold_p25": q(hold, .25),
            "hold_med": st.median(hold), "hold_p75": q(hold, .75),
            "hold_p90": q(hold, .90), "hold_max": max(hold),
            "n_filled": band["n_filled"], "equity_median": band["median"],
            "per_trade": pt, "equity_pred_from_fills": pred,
            "slot_occupancy_pct": occ * 100 if occ else None,
            "occupancy_gate_ok": gate_ok,
            "hold_med_filled": st.median(hold_filled) if hold_filled else None,
            "hold_mean_filled": st.mean(hold_filled) if hold_filled else None,
            "result_dist": dict(rc), "exit_reason_dist": dict(xr),
            "blocked_open_until": skip.get("overlap"),
            "skipped": dict(skip),
            "cand_per_day_mean": st.mean(cand), "cand_per_day_med": st.median(cand),
            "entered_per_day_mean": st.mean(entered),
            "days_with_ge5_entries": sum(1 for x in entered if x >= 5),
        }
        res[mkt] = r
        print("", flush=True)
        print("=" * 78, flush=True)
        print("%s — 거래 %d · 거래일 %d" % (mkt, r["n_trades"], r["n_days"]), flush=True)
        print("=" * 78, flush=True)
        print("  보유일수  평균 **%.2f** · P25 %d · 중앙 **%d** · P75 %d · P90 %d · 최대 %d"
              % (r["hold_mean"], r["hold_p25"], r["hold_med"], r["hold_p75"],
                 r["hold_p90"], r["hold_max"]), flush=True)
        print("  ⚠️ 점유율은 **seed 0 한 판**의 직접 셈이고 체결 수는 **200 seed 중앙**이다 — "
              "둘의 분모가 다르다(seed 0 체결 %d)." % len(fl), flush=True)
        print("  슬롯5 체결 **%.0f** · **슬롯 점유율 %s** (체결분 칸-일 ÷ 5칸×거래일 · 직접 셈)"
              % (r["n_filled"],
                 ("%.1f%%" % r["slot_occupancy_pct"]) if r["slot_occupancy_pct"] else "계산 불가"),
              flush=True)
        print("  ⚠️ **체결분만의 보유일수**: 평균 %.2f · 중앙 %.0f "
              "(전체 거래 평균 %.2f · 중앙 %.0f) — 체결분이 더 길면 근사식이 위로 샌다"
              % (r["hold_mean_filled"] or 0, r["hold_med_filled"] or 0,
                 r["hold_mean"], r["hold_med"]), flush=True)
        print("  결착 사유(result): %s" % r["result_dist"], flush=True)
        if xr:
            print("  결착 사유(exit_reason · 미국만 있는 키): %s" % r["exit_reason_dist"],
                  flush=True)
        print("  `open_until` 차단 **%s건** · 전체 스킵 %s"
              % (r["blocked_open_until"], r["skipped"]), flush=True)
        print("  하루 후보 평균 %.1f · 중앙 %.0f · 하루 진입 평균 %.2f · "
              "**진입 5건 이상인 날 %d일 (%.1f%%)**"
              % (r["cand_per_day_mean"], r["cand_per_day_med"],
                 r["entered_per_day_mean"], r["days_with_ge5_entries"],
                 r["days_with_ge5_entries"] / r["n_days"] * 100), flush=True)
        print("  **분해**: 거래당 %+.4f%% × 체결 %.0f → 예측 자산 %+.2f%% · "
              "관측 %+.2f%% · **격차 %+.2f%%p**"
              % (pt, r["n_filled"], pred, r["equity_median"],
                 r["equity_median"] - pred), flush=True)

    print("", flush=True)
    print("=" * 78, flush=True)
    print("두 시장 나란히 (**무비용 팔로 통일** — 비용 판은 항등식으로 되돌린다)", flush=True)
    print("=" * 78, flush=True)
    k, u = res["KR"], res["US"]
    for lab, key, f in (("거래 수", "n_trades", "%.0f"),
                        ("**슬롯5 체결**", "n_filled", "%.0f"),
                        ("보유일수 중앙", "hold_med", "%.0f"),
                        ("보유일수 평균", "hold_mean", "%.2f"),
                        ("슬롯 점유율(%)", "slot_occupancy_pct", "%.1f"),
                        ("하루 후보 평균", "cand_per_day_mean", "%.1f"),
                        ("`open_until` 차단", "blocked_open_until", "%.0f"),
                        ("거래당(%)", "per_trade", "%+.4f"),
                        ("자산 관측(%)", "equity_median", "%+.2f"),
                        ("자산 예측(%)", "equity_pred_from_fills", "%+.2f")):
        a, b = k.get(key), u.get(key)
        rat = (b / a) if (a not in (None, 0) and b is not None) else None
        print("   %-18s 한국 %10s · 미국 %10s · %s"
              % (lab, (f % a) if a is not None else "-",
                 (f % b) if b is not None else "-",
                 ("미국/한국 %.3f배" % rat) if rat else ""), flush=True)
    print("  ⚠️ **판정이 아니라 기술이다.** 체결 수 차이를 실력으로 읽지 않는다 —"
          " 자산 차이는 위 분해대로 **거래당과 체결 수 둘의 곱**이다.", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "31-slot-diagnosis.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/31-slot-diagnosis.json", flush=True)


if __name__ == "__main__":
    main()
