# -*- coding: utf-8 -*-
"""16(a) — **편향 없는 방아쇠 비교**: 감시목록에서 피벗 vs 전일 고가.

앞선 "우리 종목 × 전일 고가"는 **룩어헤드**였다 — 표본이 "피벗이 뚫린 거래"로 정의돼 있어
**피벗이 뚫릴 것을 알고 전날 고가에 샀다고 계산한 값**이었다. 폐기했다.

여기서는 **같은 감시목록(entry_ready 검출 전수 23,465건)에서 두 방아쇠를 나란히** 돌린다.
- **현행** : 익일 고가 ≥ **피벗** 이면 `max(피벗, 익일시가)` 진입, 아니면 **진입 없음**
- **대안** : 익일 고가 ≥ **전일 고가** 이면 `max(전일고가, 익일시가)` 진입, 아니면 **진입 없음**

**두 팔 모두 "못 뚫으면 안 산다"가 같고, 대안이 뚫었지만 피벗까지 못 간 건의 손실이 전부 들어온다.**
겹침 차단(`open_until`)도 하네스와 같게 **해마다 초기화**한다.

★ 기존 기록과의 연결: 메모리 `watch-grade-entry-experiment`에
  "피벗 도달 + 거래량 확인 매수, 선진입·갭업 추격 불리"가 규율로 남아 있다
  (9개월 0승6패, 판정보류). **이번이 그 규율의 5.6년 검정이다.**

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/16c-trigger-compare.py
난수: 슬롯 순서 0~399 (추첨 없음 — 두 팔 다 결정적)
"""
from __future__ import annotations

import importlib.util
import json
import statistics as st
import sys
from bisect import bisect_left
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts"))
import slot_sim  # noqa: E402
from canslim_lib.pdata_series import build_series  # noqa: E402

spec = importlib.util.spec_from_file_location("g16", HERE / "16-selection-edge.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
WATCH = BT / "watch"
N_PAIR, N_LEVEL = 400, 200
YEARS = [2021, 2022, 2023, 2024, 2025, 2026]
YS = ("2021", "2022", "2023", "2024", "2025", "2026")
MDE_K, EQUIV = 2.80, 0.5
net = slot_sim.net


def band(xs, lo=5, hi=95):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def main():
    rows = []          # 감시목록 한 건마다 두 팔의 결과(없으면 None)
    diag = defaultdict(int)
    for y in YEARS:
        d = json.loads((WATCH / ("bt_%d_w.json" % y)).read_text(encoding="utf-8"))
        prm = d["params"]
        w = (datetime.strptime(prm["start"], "%Y-%m-%d")
             - timedelta(days=g.WARM_DAYS)).strftime("%Y-%m-%d")
        le = (datetime.strptime(prm["end"], "%Y-%m-%d")
              + timedelta(days=g.TAIL_DAYS)).strftime("%Y-%m-%d")
        wl = d["watchlist"]
        need = {x["code"] for x in wl}
        print("[%d] 감시목록 %d건 · 종목 %d · 시계열 %s ~ %s …"
              % (y, len(wl), len(need), w, le), flush=True)
        full = build_series((dt, {c: r for c, r in recs.items() if c in need})
                            for dt, recs in g.iter_pdata(w, le))
        for x in wl:
            s = full.get(x["code"])
            if not s:
                diag["series_missing"] += 1
                continue
            ds = s["dates"]
            i = bisect_left(ds, x["scan_date"])
            di = i if (i < len(ds) and ds[i] == x["scan_date"]) else None
            if di is None or di + 1 >= len(ds):
                diag["no_next_day"] += 1
                continue
            ni = di + 1
            o, h = s["opens"], s["highs"]
            E = ds[ni]
            rec = {"code": x["code"], "pattern": x["pattern"], "src_year": y,
                   "scan_date": x["scan_date"], "entry_date": E, "year": E[:4],
                   "pivot": x["pivot"], "prev_high": h[di]}
            for nm, thr in (("cur", x["pivot"]), ("alt", h[di])):
                if h[ni] is None or h[ni] < thr:
                    rec[nm] = None
                    continue
                epx = max(thr, o[ni] or thr)
                gain, why, days = g.resolve(s, ni, epx)
                rec[nm] = {"entry_price": epx, "gain": gain, "reason": why,
                           "resolve_date": ds[min(ni + days, len(ds) - 1)],
                           "result": ("win" if why == "target" else
                                      "loss" if why in ("stop", "both_same_day")
                                      else ("win" if gain > 0 else "loss"))}
            rows.append(rec)
        del full
        print("[%d]   누적 %d" % (y, len(rows)), flush=True)

    n = len(rows)
    both = sum(1 for r in rows if r["cur"] and r["alt"])
    only_cur = sum(1 for r in rows if r["cur"] and not r["alt"])
    only_alt = sum(1 for r in rows if r["alt"] and not r["cur"])
    neither = sum(1 for r in rows if not r["cur"] and not r["alt"])
    same_px = sum(1 for r in rows if r["cur"] and r["alt"]
                  and abs(r["cur"]["entry_price"] - r["alt"]["entry_price"]) < 1e-9)
    print("\n감시목록 %d건 (결측 %d · 익일 없음 %d)"
          % (n, diag["series_missing"], diag["no_next_day"]), flush=True)
    print("  현행만 발동 %d · 대안만 발동 %d · 둘 다 %d · 둘 다 아님 %d"
          % (only_cur, only_alt, both, neither), flush=True)
    print("  ★ 구조적 영 — 두 팔의 **진입가가 같은** 건 %d / 둘 다 발동 %d = **%.1f%%**"
          % (same_px, both, same_px / both * 100 if both else 0), flush=True)
    print("  현행 진입 %d건 · 대안 진입 %d건 (**%.2f배**)"
          % (only_cur + both, only_alt + both,
             (only_alt + both) / (only_cur + both)), flush=True)

    # 진입가 차이 분포 (검증 요청 ①)
    dpx = [(r["cur"]["entry_price"] / r["alt"]["entry_price"] - 1) * 100
           for r in rows if r["cur"] and r["alt"]]
    dpx.sort()
    print("  진입가 차이(현행 ÷ 대안 − 1): 중앙 %+.3f%% · P10 %+.3f · P90 %+.3f · "
          "대안이 더 싼 건 %.1f%%"
          % (st.median(dpx), dpx[int(len(dpx) * .1)], dpx[int(len(dpx) * .9)],
             sum(1 for x in dpx if x > 0) / len(dpx) * 100), flush=True)

    def build(nm):
        """겹침 차단은 하네스와 같게 **해마다 초기화**."""
        open_until, cur_y, out = {}, None, []
        for r in rows:
            if r["src_year"] != cur_y:
                cur_y, open_until = r["src_year"], {}
            v = r[nm]
            if v is None:
                continue
            c, E = r["code"], r["entry_date"]
            if c in open_until and E <= open_until[c]:
                continue
            open_until[c] = v["resolve_date"] or E
            out.append({"code": c, "pattern": r["pattern"], "scan_date": r["scan_date"],
                        "entry_date": E, "resolve_date": v["resolve_date"],
                        "gain": v["gain"], "result": v["result"], "year": r["year"]})
        return out

    cur, alt = build("cur"), build("alt")
    print("\n겹침 차단 후 실제 진입: 현행 **%d건** · 대안 **%d건** (%.2f배)"
          % (len(cur), len(alt), len(alt) / len(cur)), flush=True)

    def stats(tr, nm):
        nets = [net(t["gain"]) for t in tr]
        eqs = [slot_sim.sim(tr, seed=s)["equity_pct"] for s in range(N_PAIR)]
        lo, hi = band(eqs[:N_LEVEL])
        fills = st.median(slot_sim.sim(tr, seed=s)["n_filled"] for s in range(20))
        wr = sum(1 for t in tr if t["result"] == "win") / len(tr) * 100
        print("  %-10s n %5d · 승률 %5.2f%% · 거래당 %+7.4f%%p · 중앙 %+8.4f · "
              "슬롯5 중앙 %+7.1f%% · 폭 %6.1f · 체결 %4.0f"
              % (nm, len(tr), wr, st.mean(nets), st.median(nets),
                 st.median(eqs[:N_LEVEL]), hi - lo, fills), flush=True)
        return {"n": len(tr), "win_rate": wr, "per_trade": st.mean(nets),
                "median": st.median(nets), "eqs": eqs,
                "slot5_median": st.median(eqs[:N_LEVEL]), "band": [lo, hi],
                "band_width": hi - lo, "n_filled": fills,
                "by_year": {y: st.mean([net(t["gain"]) for t in tr if t["year"] == y])
                            for y in YS if any(t["year"] == y for t in tr)}}

    print("\n[두 팔]", flush=True)
    a = stats(cur, "현행 피벗")
    b = stats(alt, "대안 전일고가")

    # 거래당 — 같은 날 짝비교 (하루 한 표)
    by_a, by_b = defaultdict(list), defaultdict(list)
    for t in cur:
        by_a[t["entry_date"]].append(net(t["gain"]))
    for t in alt:
        by_b[t["entry_date"]].append(net(t["gain"]))
    days = sorted(set(by_a) & set(by_b))
    pairs = {d: st.mean(by_a[d]) - st.mean(by_b[d]) for d in days}
    r = g.day_stat(pairs, sorted(set(by_a) | set(by_b)), "거래당 현행−대안", 162000)

    # 슬롯5 짝비교
    diff = [b["eqs"][i] - a["eqs"][i] for i in range(N_PAIR)]
    dlo, dhi = ci(diff)
    print("\n  ★ 슬롯5 차이(대안 − 현행) 중앙 **%+.1f%%p** · 95%% %+.1f ~ %+.1f · "
          "우세율(참고) %.1f%%"
          % (st.median(diff), dlo, dhi, sum(1 for x in diff if x > 0) / N_PAIR * 100),
          flush=True)
    key = lambda t: abs(net(t["gain"]))
    d5 = [x - y for x, y in zip(
        [slot_sim.sim(sorted(alt, key=key)[:-5], seed=s)["equity_pct"] for s in range(N_LEVEL)],
        [slot_sim.sim(sorted(cur, key=key)[:-5], seed=s)["equity_pct"] for s in range(N_LEVEL)])]
    print("  |기여| 상위 5건 제거 후 %+.1f%%p (부호 %s)"
          % (st.median(d5), "유지" if (st.median(d5) > 0) == (st.median(diff) > 0)
             else "반전"), flush=True)
    dy = {}
    for y in YS:
        dd = [x - z for x, z in zip(
            [slot_sim.sim([t for t in alt if t["year"] != y], seed=s)["equity_pct"]
             for s in range(N_LEVEL)],
            [slot_sim.sim([t for t in cur if t["year"] != y], seed=s)["equity_pct"]
             for s in range(N_LEVEL)])]
        dy[y] = st.median(dd)
    flips = [y for y in YS if (dy[y] > 0) != (st.median(diff) > 0)]
    print("  [연도별] " + " · ".join("%s제거 %+.1f" % (y, dy[y]) for y in YS), flush=True)
    print("   → 부호 반전: %s" % (", ".join(flips) if flips else "없음 (6/6 유지)"),
          flush=True)

    res = {"n_watchlist": n, "trigger_counts": {"only_cur": only_cur, "only_alt": only_alt,
                                                "both": both, "neither": neither,
                                                "same_price": same_px},
           "entry_price_diff_pct": {"median": st.median(dpx),
                                    "p10": dpx[int(len(dpx) * .1)],
                                    "p90": dpx[int(len(dpx) * .9)]},
           "cur": {k: v for k, v in a.items() if k != "eqs"},
           "alt": {k: v for k, v in b.items() if k != "eqs"},
           "per_trade_daypair": r,
           "slot5_diff_median": st.median(diff), "slot5_diff_ci": [dlo, dhi],
           "slot5_win_pct": sum(1 for x in diff if x > 0) / N_PAIR * 100,
           "slot5_drop_top5": st.median(d5), "slot5_drop_year": dy, "flip_years": flips,
           "diag": dict(diag)}
    (OUT / "16c-trigger-compare.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/16c-trigger-compare.json")


if __name__ == "__main__":
    main()
