# -*- coding: utf-8 -*-
"""38-0 · **0회차 기준선** — 현행 규칙 그대로, 창만 잘라 본다.

새 실행 없다. 오늘 낸 `us_2021~2026.json` 을 그대로 슬라이스한다.
🚨 **개발 구간(2021-02-01 ~ 2026-08-21)만 쓴다.**
   확인 구간(2017-09-01 ~ 2021-01-31)은 **열지 않는다.**

내는 것
-------
- 창 셋: **1년(2025) · 3년(2023~2025) · 5.6년(전체)**
- 비용 **두 팔**: 미국 실제(무비용) · 한국 미래에셋(0.14/0.14+0.2)
- 자산 중앙(200 seed 밴드) · 최대낙폭 · 체결 수 · 거래당(자료 축 구간) · 승률
🚨 **주지표는 자산**(사용자 물음이 「돈을 불리는가」) · **부지표는 거래당**(거래 수 효과 분리).

⚠️ 창을 자르면 **슬롯 시뮬의 시작 자본이 1.0으로 되돌아간다.** 1년 판은
   「그 해에 새로 시작했으면」이고 5.6년 판의 부분구간이 아니다. **다른 물음이다.**

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/38-round0.py
난수 seed: 슬롯 0~199 · 부트스트랩 380824
"""
from __future__ import annotations

import json
import random
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_SEED = 200
N_BOOT = 1000
BOOT_SEED = 380824
BLOCK = (20, 40)
DEV_LO, DEV_HI = "2021-02-01", "2026-08-21"
WINDOWS = (("1년(2025)", "2025-01-01", "2025-12-31"),
           ("3년(2023~2025)", "2023-01-01", "2025-12-31"),
           ("5.6년(전체)", DEV_LO, DEV_HI))
REGIMES = (("미국 실제(무비용)", 0.0, 0.0),
           ("한국-미래에셋", 0.0014, 0.0034))


class Cost:
    def __init__(self, b, s):
        self.b, self.s = b, s

    def __enter__(self):
        self.o = (slot_sim.FEE_BUY, slot_sim.FEE_SELL)
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.b, self.s

    def __exit__(self, *a):
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.o


def load_us():
    fs = sorted((BT / "sub").glob("us_20*.json"))
    assert fs, "us_YYYY.json 이 없다"
    assert not any("DEADZONE" in f.name for f in fs), "🚨 사각지대 판이 섞였다"
    print("출처: %s" % ", ".join(f.stem for f in fs), flush=True)
    ev = []
    for f in fs:
        ev += json.loads(f.read_text(encoding="utf-8"))["events"]
    seen, out = set(), []
    last = max((e.get("resolve_date") or e["entry_date"]) for e in ev)
    for e in sorted(ev, key=lambda x: (x["entry_date"], x["code"], x.get("pattern", ""))):
        k = (e["scan_date"], e["code"], e.get("pattern", ""))
        if k in seen or e.get("gain_at_resolve_pct") is None:
            continue
        seen.add(k)
        out.append({"code": e["code"], "scan_date": e["scan_date"],
                    "pattern": e.get("pattern", ""), "entry_date": e["entry_date"],
                    "resolve_date": e.get("resolve_date") or last,
                    "gain": e["gain_at_resolve_pct"], "result": e["result"]})
    return out


def boot_per_trade(trades):
    byd = defaultdict(list)
    for t in trades:
        byd[t["entry_date"]].append(slot_sim.net(t["gain"]))
    dates = sorted(byd)
    n = len(dates)
    rnd = random.Random(BOOT_SEED)
    means = []
    for _ in range(N_BOOT):
        acc, cnt, tot = 0.0, 0, 0
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
    return (st.mean(slot_sim.net(t["gain"]) for t in trades),
            means[int(N_BOOT * .025)], means[int(N_BOOT * .975)],
            2.80 * st.pstdev(means))


def main():
    tr = load_us()
    print("미국 거래 %d (개발 구간 %s ~ %s)" % (len(tr), DEV_LO, DEV_HI), flush=True)
    print("🚨 확인 구간(2017-09-01 ~ 2021-01-31)은 **열지 않았다.**", flush=True)
    res = {}
    print("", flush=True)
    print("=" * 96, flush=True)
    print("0회차 기준선 — 현행 규칙(+20% 전량 / −10% 전량 · 슬롯5 균등)", flush=True)
    print("=" * 96, flush=True)
    print("  %-16s %-16s %7s %7s %11s %9s %11s"
          % ("창", "비용", "거래", "체결", "자산 중앙", "MDD", "거래당"), flush=True)
    for wname, lo, hi in WINDOWS:
        sub = [t for t in tr if lo <= t["entry_date"] <= hi]
        for rname, fb, fs_ in REGIMES:
            with Cost(fb, fs_):
                b = slot_sim.band(sub, n_runs=N_SEED)
                pt, plo, phi, mde = boot_per_trade(sub)
            k = "%s / %s" % (wname, rname)
            res[k] = {"window": [lo, hi], "n_trades": len(sub),
                      "n_filled": b["n_filled"], "equity_median": b["median"],
                      "equity_p5": b["p5"], "equity_p95": b["p95"], "mdd": b["mdd"],
                      "per_trade": pt, "per_trade_lo": plo, "per_trade_hi": phi,
                      "per_trade_mde": mde, "win_rate": b["win_rate"]}
            print("  %-16s %-16s %7d %7.0f %10.2f%% %8.2f%% %10.4f%%"
                  % (wname, rname, len(sub), b["n_filled"], b["median"],
                     b["mdd"], pt), flush=True)
        r0 = res["%s / %s" % (wname, REGIMES[0][0])]
        r1 = res["%s / %s" % (wname, REGIMES[1][0])]
        print("      %-16s 자산 5~95%% %+.1f ~ %+.1f (무비용) · %+.1f ~ %+.1f (한국비용)"
              % ("", r0["equity_p5"], r0["equity_p95"], r1["equity_p5"], r1["equity_p95"]),
              flush=True)
        print("      %-16s 거래당 95%% %+.4f ~ %+.4f (무비용 · MDE %.4f) · 승률 %.1f%%"
              % ("", r0["per_trade_lo"], r0["per_trade_hi"], r0["per_trade_mde"],
                 r0["win_rate"]), flush=True)
    print("", flush=True)
    print("  ⚠️ **창을 자르면 슬롯 시뮬의 시작 자본이 1.0으로 되돌아간다.**", flush=True)
    print("     1년 판은 「그 해에 새로 시작했으면」이고 **5.6년 판의 부분구간이 아니다.**",
          flush=True)
    print("  🚨 **판정 문턱(사전등록)**: 실효성 있음 = 자산 95%% 하단 > 0 **AND** 거래당 하단 > 0",
          flush=True)
    for wname, _lo, _hi in WINDOWS:
        for rname, _a, _b in REGIMES:
            r = res["%s / %s" % (wname, rname)]
            ok = r["equity_p5"] > 0 and r["per_trade_lo"] > 0
            no = r["equity_p95"] < 0 and r["per_trade_hi"] < 0
            print("     %-16s %-16s → **%s**"
                  % (wname, rname,
                     "실효성 있음" if ok else ("실효성 없음" if no else "못 가림")),
                  flush=True)
    # ── 🚨 분해: 산술 예측 vs 관측 ──────────────────────────────────────────
    #   슬롯5에 포지션 20%씩이므로 «산술» 예측은 체결 수 × 0.20 × 거래당.
    #   관측과의 격차가 **분산 손실**(손실이 곱으로 겹치는 효과 + 슬롯 선택)이다.
    #   🚨 **판정이 아니라 기술이다.**
    print("", flush=True)
    print("=" * 96, flush=True)
    print("분해 — 산술 예측 vs 관측 (무비용 팔)", flush=True)
    print("=" * 96, flush=True)
    print("  %-16s %8s %10s %12s %12s %12s"
          % ("창", "체결", "거래당", "산술 예측", "관측", "**격차**"), flush=True)
    for wname, _lo, _hi in WINDOWS:
        r = res["%s / %s" % (wname, REGIMES[0][0])]
        pred = r["n_filled"] * 0.20 * r["per_trade"]
        res["%s / %s" % (wname, REGIMES[0][0])]["arith_pred"] = pred
        print("  %-16s %8.0f %9.4f%% %11.2f%% %11.2f%% %11.2f%%p"
              % (wname, r["n_filled"], r["per_trade"], pred, r["equity_median"],
                 r["equity_median"] - pred), flush=True)
    print("  ⚠️ 격차 = **분산 손실**(손실이 곱으로 겹치는 효과 + 슬롯 선택). "
          "**「거래당을 올리는 것」만으로는 못 메운다.**", flush=True)

    # ── 벤치마크 지수 (FDR · 한국 KS11 과 «같은 도구») ─────────────────────
    f = OUT / "38-indices.json"
    if f.exists():
        idx = json.loads(f.read_text(encoding="utf-8"))
        print("", flush=True)
        print("=" * 96, flush=True)
        print("벤치마크 지수 — **FDR**(한국 `KS11` 과 같은 경로 · 짝 규칙)", flush=True)
        print("=" * 96, flush=True)
        print("  %-16s %14s %14s" % ("창", "S&P500(US500)", "나스닥(IXIC)"), flush=True)
        for wname, lo, hi in WINDOWS:
            row = {}
            for sym in ("US500", "IXIC"):
                ks = sorted(k for k in idx[sym] if lo <= k <= hi)
                row[sym] = ((idx[sym][ks[-1]] / idx[sym][ks[0]] - 1) * 100) if len(ks) > 1 else None
            res.setdefault("_benchmark", {})[wname] = row
            print("  %-16s %13.2f%% %13.2f%%" % (wname, row["US500"], row["IXIC"]),
                  flush=True)
        print("  ⚠️ **어느 것도 나중에 고르지 않는다.** 둘 다 싣는다.", flush=True)
        print("  ⚠️ 지수는 **시총가중**이고 슬롯5는 **다섯 칸**이다 — "
              "**지수 셋 중 어느 것도 슬롯5의 반사실이 아니다**(26번 §4).", flush=True)
    else:
        print("", flush=True)
        print("  🚨 벤치마크 지수 파일이 없다 — **확인 불가**", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "38-round0.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    print("\n저장: .cache/bt5y/out/38-round0.json", flush=True)


if __name__ == "__main__":
    main()
