# -*- coding: utf-8 -*-
"""33 · **미결착 처리(결정 2)** + **등가중 극단값 육안 확인(결정 3)**.

결정 2 — 미결착
---------------
미국 미결착 410건(5.4%) vs 한국 21건(0.6%) = **9배**. 그냥 못 넘긴다.
- `pivot_backtest._daily_first_touch` 는 끝까지 못 닿으면
  `_result("unresolved", series, b, n-1, pivot, "open")` → **시계열 마지막 종가로 평가한 미실현**이다.
- 🚨 **상폐인지 창 끝인지 가른다.** 상폐는 「결착」이고 창 끝은 「미결착」이다.
  (**상폐 ≠ 손실** — M&A 프리미엄이 섞인다. 24d)
- **양 시장 모두** 미결착을 뺀 판을 함께 낸다(유형 18 짝 규칙).
- 미실현 손익의 **부호**도 낸다. 한쪽으로 쏠려 있으면 방향이 있는 편향이다.

결정 3 — 등가중 극단값
----------------------
미국 등가중 필터 판이 `none +52.76%` → `cap31 −48.69%` 로 100%p 넘게 움직인다.
**최대 기여 5건의 전후 원시 시세를 눈으로 본다.**
- 자료 사고면 → `cap100`·`cap31` 이 옳고 **「청소해야 한다」가 결론**
- 실제 사건이면 → `none` 이 옳고 **「미국 등가중은 꼬리가 지배한다」가 결론**

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/33-unresolved-and-extremes.py
"""
from __future__ import annotations

import csv
import io
import json
import statistics as st
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "scripts"))
import slot_sim  # noqa: E402

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_SEED = 200
REGIMES = {"무비용": (0.0, 0.0), "한국-미래에셋": (0.0014, 0.0034)}
WATCH = ["INTEQ", "TPST", "INHD", "ORBS", "CERO"]


class Cost:
    def __init__(self, b, s):
        self.b, self.s = b, s

    def __enter__(self):
        self.o = (slot_sim.FEE_BUY, slot_sim.FEE_SELL)
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.b, self.s

    def __exit__(self, *a):
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.o


def load(mkt):
    ev = []
    if mkt == "KR":
        for y in range(2021, 2027):
            f = BT / ("bt_%d.json" % y)
            if f.exists():
                ev += json.loads(f.read_text(encoding="utf-8"))["events"]
    else:
        ev = json.loads((BT / "sub" / "us_full.json").read_text(encoding="utf-8"))["events"]
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
    return out, last


def to_trades(ev):
    return [{"code": e["code"], "scan_date": e["scan_date"],
             "pattern": e.get("pattern", ""), "entry_date": e["entry_date"],
             "resolve_date": e["resolve_date"], "gain": e["gain_at_resolve_pct"],
             "result": e["result"]} for e in ev]


def part1():
    print("=" * 86, flush=True)
    print("결정 2 — 미결착 처리", flush=True)
    print("=" * 86, flush=True)
    print("  `gain_at_resolve_pct` 는 미결착일 때 **시계열 마지막 종가로 평가한 «미실현»**이다"
          " (`_daily_first_touch` → `_result('unresolved', …, n-1, …, 'open')`).", flush=True)
    res = {}
    for mkt in ("KR", "US"):
        ev, last = load(mkt)
        unr = [e for e in ev if e["result"] == "unresolved"]
        # 상폐(시계열이 창 끝보다 먼저 끝남) vs 창 끝
        deli = [e for e in unr if e["resolve_date"] < last]
        endw = [e for e in unr if e["resolve_date"] >= last]
        g = [e["gain_at_resolve_pct"] for e in unr]
        print("", flush=True)
        print("  [%s] 미결착 **%d / %d = %.2f%%** · 창 끝 %s"
              % (mkt, len(unr), len(ev), len(unr) / len(ev) * 100, last), flush=True)
        if unr:
            pos = sum(1 for x in g if x > 0)
            print("     미실현 평균 **%+.2f%%** · 중앙 %+.2f%% · P10 %+.2f%% · P90 %+.2f%% "
                  "· **플러스 %d / %d = %.1f%%**"
                  % (st.mean(g), st.median(g), sorted(g)[int(len(g) * .1)],
                     sorted(g)[int(len(g) * .9)], pos, len(g), pos / len(g) * 100),
                  flush=True)
            print("     **상폐성(시계열이 먼저 끝남) %d건** vs **창 끝 %d건**"
                  % (len(deli), len(endw)), flush=True)
            for lab, xs in (("상폐성", deli), ("창끝", endw)):
                if xs:
                    v = [e["gain_at_resolve_pct"] for e in xs]
                    print("       %-5s 평균 %+.2f%% · 중앙 %+.2f%% · 플러스 %.1f%%"
                          % (lab, st.mean(v), st.median(v),
                             sum(1 for x in v if x > 0) / len(v) * 100), flush=True)
        tr = to_trades(ev)
        keep = to_trades([e for e in ev if e["result"] != "unresolved"])
        # 🚨 **상폐성은 사실상 「결착」이다** — 마지막 종가에 청산된 것이고,
        #    상폐 ≠ 손실(M&A 프리미엄, 24d). 진짜 미결착은 **창 끝**뿐이다.
        #    그래서 「창끝만 제외」 판을 함께 낸다 — 이쪽이 더 방어 가능한 절단이다.
        keep2 = to_trades([e for e in ev if not (e["result"] == "unresolved"
                                                 and e["resolve_date"] >= last)])
        row = {"n": len(ev), "n_unresolved": len(unr),
               "n_delisted_like": len(deli), "n_window_end": len(endw),
               "unreal_mean": st.mean(g) if g else None,
               "unreal_median": st.median(g) if g else None,
               "unreal_pos_pct": (sum(1 for x in g if x > 0) / len(g) * 100) if g else None}
        for rg, (b, sl) in REGIMES.items():
            with Cost(b, sl):
                a = slot_sim.band(tr, n_runs=N_SEED)
                c = slot_sim.band(keep, n_runs=N_SEED)
                c2 = slot_sim.band(keep2, n_runs=N_SEED)
                pa = st.mean(slot_sim.net(t["gain"]) for t in tr)
                pc = st.mean(slot_sim.net(t["gain"]) for t in keep)
                pc2 = st.mean(slot_sim.net(t["gain"]) for t in keep2)
            row[rg] = {"equity_all": a["median"], "equity_ex_all_unres": c["median"],
                       "equity_ex_window_end": c2["median"],
                       "filled_all": a["n_filled"], "filled_ex": c["n_filled"],
                       "filled_ex2": c2["n_filled"],
                       "per_trade_all": pa, "per_trade_ex": pc, "per_trade_ex2": pc2}
            print("     %-8s 원판          자산 %+8.2f%% · 체결 %3.0f · 거래당 %+.4f%%"
                  % (rg, a["median"], a["n_filled"], pa), flush=True)
            print("     %-8s 미결착 전부 제외 자산 %+8.2f%% · 체결 %3.0f · 거래당 %+.4f%% "
                  "· 차이 %+.2f%%p"
                  % ("", c["median"], c["n_filled"], pc, c["median"] - a["median"]),
                  flush=True)
            print("     %-8s **창끝만 제외**  자산 %+8.2f%% · 체결 %3.0f · 거래당 %+.4f%% "
                  "· 차이 %+.2f%%p  ← 상폐성은 「결착」으로 본 판"
                  % ("", c2["median"], c2["n_filled"], pc2, c2["median"] - a["median"]),
                  flush=True)
        res[mkt] = row
    return res


def part2():
    print("", flush=True)
    print("=" * 86, flush=True)
    print("결정 3 — 미국 등가중 최대 기여 5건 **원시 시세 육안 확인**", flush=True)
    print("=" * 86, flush=True)
    import us_loader as U
    keep = set(WATCH)
    rows = {c: [] for c in keep}
    with zipfile.ZipFile(U.STOCKS_ZIP) as z:
        rd = csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8"))
        next(rd)
        for r in rd:
            if r[0] in keep:
                rows[r[0]].append(r)
    focus = {"INTEQ": "2021-09-30", "TPST": "2023-10-11", "INHD": "2026-06-08",
             "ORBS": "2025-09-08", "CERO": "2025-06-09"}
    out = {}
    for c in WATCH:
        v = sorted(rows[c], key=lambda r: r[1])
        d0 = focus[c]
        idx = next((i for i, r in enumerate(v) if r[1] == d0), None)
        print("", flush=True)
        print("  ── %s · 사건일 %s (전체 %d행 · %s ~ %s)"
              % (c, d0, len(v), v[0][1] if v else "-", v[-1][1] if v else "-"), flush=True)
        if idx is None:
            print("     그 날짜가 시계열에 없다.", flush=True)
            continue
        seg = v[max(0, idx - 4):idx + 4]
        print("     %-11s %11s %11s %11s %11s %14s %11s"
              % ("날짜", "시가", "고가", "저가", "종가", "거래량", "비수정종가"), flush=True)
        for r in seg:
            print("     %-11s %11.4f %11.4f %11.4f %11.4f %14.0f %11.4f"
                  % (r[1], float(r[2]), float(r[3]), float(r[4]), float(r[5]),
                     float(r[6]), float(r[8])), flush=True)
        # 사건일 전후 거래일 간격 — 시계열이 끊겼는지
        gaps = []
        for i in range(max(1, idx - 3), min(len(v), idx + 3)):
            gaps.append((v[i - 1][1], v[i][1]))
        print("     인접 거래일: %s" % " → ".join("%s/%s" % g for g in gaps[-4:]), flush=True)
        out[c] = [{"date": r[1], "open": float(r[2]), "high": float(r[3]),
                   "low": float(r[4]), "close": float(r[5]), "volume": float(r[6]),
                   "closeunadj": float(r[8])} for r in seg]
    return out


def main():
    a = part1()
    b = part2()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "33-unresolved-and-extremes.json").write_text(
        json.dumps({"unresolved": a, "extremes_raw": b}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print("\n저장: .cache/bt5y/out/33-unresolved-and-extremes.json", flush=True)


if __name__ == "__main__":
    main()
