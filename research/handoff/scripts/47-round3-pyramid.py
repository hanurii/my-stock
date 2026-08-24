# -*- coding: utf-8 -*-
"""47 — **3회차 · 점진적 노출**. 헤드라인 `3a` 는 결과를 보기 «전»에 고정됐다. **2a 위에 누적.**

| 변형 | |
|---|---|
| **3a ★** | 목표 크기의 **1/2 로 시작** → **+3% 이상 오르면 나머지 1/2 추가** |
| 3b | **1/3 → 1/3 → 1/3** (+3%, +6%) |
| 3c | 3a + **최근 청산 5건 중 3건 이상 손실이면 목표 크기 절반** |
| 3d | (대조) 3회차 없음 = **2a** |

규약 — 지시서 그대로
--------------------
- 🚨 **추가 매수분의 손절선은 «평균단가» 기준.** 원전이 위험을 계좌 기준으로 관리한다.
  목표(+20%)·본전선·추격 바닥도 **평균단가** 기준으로 옮긴다(하나의 포지션이 되므로).
- 🚨 **파일럿은 «반만» 잡는다.** 목표 크기로 자리를 예약하지 않는다
  (2회차 「쪼갬 금지」와 일관되게, **증액분은 그때 현금이 있어야 들어간다**).
- 청산 규칙은 **1a 그대로**(−8% / +20% 절반 / 본전→25일 추격), 기준만 평균단가.
- 체결가 규약은 회차 공통: **종가판** / **실집행 근사판**(`max(방아쇠,시가)` · `min(선,시가)`).
  **증액은 «위로 사는 것»이라 목표와 같은 편**(갭업이면 시가에 산다).

🚨 **양방향 관문**: `pilot=1.0` 이고 **증액을 끄면** `slot_sim_size`(2a)와 같아야 한다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/47-round3-pyramid.py
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

import dataaxis as da                                    # noqa: E402
import slot_sim                                          # noqa: E402
import slot_sim_pyr as sp                                # noqa: E402
import slot_sim_size as ss                               # noqa: E402

_s = _u.spec_from_file_location("r41", HERE / "41-round1-exits.py")
r41 = _u.module_from_spec(_s)
_s.loader.exec_module(r41)
OUT = ROOT / ".cache" / "bt5y" / "out"

N_SEED = 200
RISK, CAP = 0.0125, 0.25
TRAIL = 25
REGIMES = (("무비용", 0.0, 0.0), ("한국-미래에셋", 0.0014, 0.0034))
FILLS = (("종가판", "close", "close"), ("실집행 근사판", "limit", "market"))


class Cost:
    def __init__(self, b, s):
        self.b, self.s = b, s

    def __enter__(self):
        self.o = (slot_sim.FEE_BUY, slot_sim.FEE_SELL)
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.b, self.s

    def __exit__(self, *a):
        slot_sim.FEE_BUY, slot_sim.FEE_SELL = self.o


def _buy_px(p, i, lvl_px, fill):
    """위로 사는 체결가 — 갭업이면 시가."""
    if fill != "limit":
        return p["c"][i]
    o = (p.get("o") or [None] * len(p["c"]))[i]
    return lvl_px if o is None else max(lvl_px, o)


def _sell_up_px(p, i, lvl_px, fill):
    """목표(위로 파는 것) — 갭업이면 시가."""
    if fill != "limit":
        return p["c"][i]
    o = (p.get("o") or [None] * len(p["c"]))[i]
    return lvl_px if o is None else max(lvl_px, o)


def _sell_dn_px(p, i, lvl_px, fill):
    """손절·추격(아래로 파는 것) — 갭다운이면 시가."""
    if fill != "market":
        return p["c"][i]
    o = (p.get("o") or [None] * len(p["c"]))[i]
    return lvl_px if o is None else min(lvl_px, o)


def resolve_pyr(p, ft, fs, stop=8.0, target=20.0, half=0.5,
                adds=((3.0, 0.5),)):
    """3회차 해결자. `adds` = [(발동 상승률%, 그때 넣는 «목표 대비» 몫), ...]

    반환: dict(entry_px · add · exits[(날짜,몫,가격)] · resolve_date · result · at_end)
    **몫은 «포지션 전체» 기준.** 트랜치별 취득가는 시뮬이 따로 들고 있다.
    """
    h, l, c, d = p["h"], p["l"], p["c"], p["d"]
    n = len(c)
    epx = p["entry_price"]
    lots = [(epx, 1.0 - sum(a[1] for a in adds))]      # (취득가, 목표대비 몫)
    pend = list(adds)
    add_rec = None

    def avg():
        s = sum(x[1] for x in lots)
        return sum(px * fr for px, fr in lots) / s if s else epx

    for i in range(n):
        # ① 증액 (위로 사는 것) — 여러 단계 가능
        while pend and h[i] is not None and h[i] >= epx * (1 + pend[0][0] / 100):
            lvl = epx * (1 + pend[0][0] / 100)
            px = _buy_px(p, i, lvl, ft)
            lots.append((px, pend[0][1]))
            if add_rec is None:
                add_rec = (d[i], px)
            pend.pop(0)
        a = avg()
        S, T = a * (1 - stop / 100), a * (1 + target / 100)
        hit_t = h[i] is not None and h[i] >= T
        hit_s = l[i] is not None and l[i] <= S
        if i == 0:
            if hit_s:
                return _mk(p, d[0], "ambiguous", [(d[0], 1.0, c[0])], False, add_rec, epx)
            if hit_t:
                return _phase2(p, i, half, a, ft, fs, add_rec, epx,
                               _sell_up_px(p, i, T, ft))
            continue
        if hit_t and hit_s:
            return _mk(p, d[i], "ambiguous", [(d[i], 1.0, c[i])], False, add_rec, epx)
        if hit_t:
            return _phase2(p, i, half, a, ft, fs, add_rec, epx, _sell_up_px(p, i, T, ft))
        if hit_s:
            return _mk(p, d[i], "loss", [(d[i], 1.0, _sell_dn_px(p, i, S, fs))],
                       False, add_rec, epx)
    return _mk(p, d[n - 1], "unresolved", [(d[n - 1], 1.0, c[n - 1])], True, add_rec, epx)


def _phase2(p, i, half, a, ft, fs, add_rec, epx, tpx):
    """절반 판 뒤 — 본전(평균단가) + 25일 저가 추격."""
    l, c, d = p["l"], p["c"], p["d"]
    n = len(c)
    ex = [(d[i], half, tpx)]
    for j in range(i + 1, n):
        seg = [x for x in l[max(0, j - TRAIL):j] if x is not None]
        s2 = max(a, min(seg)) if seg else a
        if l[j] is not None and l[j] <= s2:
            ex.append((d[j], 1.0 - half, _sell_dn_px(p, j, s2, fs)))
            return _mk(p, d[j], "win", ex, False, add_rec, epx)
    ex.append((d[n - 1], 1.0 - half, c[n - 1]))
    return _mk(p, d[n - 1], "win", ex, True, add_rec, epx)


def _mk(p, rd, res, ex, at_end, add_rec, epx):
    return {"code": p["code"], "scan_date": p["scan_date"], "pattern": p["pattern"],
            "entry_date": p["entry_date"], "entry_px": epx, "add": add_rec,
            "exits": ex, "resolve_date": rd, "result": res, "at_end": at_end,
            "stop_frac": 0.08}


def replay(by, ft, fs, **kw):
    ev, blocked = [], 0
    for y in sorted(by):
        open_until = {}
        for p in by[y]:
            c = p["code"]
            if c in open_until and p["entry_date"] <= open_until[c]:
                blocked += 1
                continue
            e = resolve_pyr(p, ft, fs, **kw)
            open_until[c] = e["resolve_date"] or p["entry_date"]
            ev.append(e)
    return ev, blocked


def half_scale(recent):
    """3c — 최근 청산 5건 중 3건 이상 손실이면 목표 크기 절반."""
    return 0.5 if len(recent) >= 5 and sum(1 for x in recent if not x) >= 3 else 1.0


VARIANTS = (
    ("3a", dict(adds=((3.0, 0.5),)), 0.5, None, "1/2 → +3%에 나머지 1/2"),
    ("3b", dict(adds=((3.0, 1 / 3), (6.0, 1 / 3))), 1 / 3, None, "1/3 → +3% → +6%"),
    ("3c", dict(adds=((3.0, 0.5),)), 0.5, half_scale, "3a + 연속손실이면 목표 절반"),
)


def main() -> int:
    by, miss = r41.v39.load_paths()
    if miss:
        print("🚨 uspath_%d.json 이 없다" % miss)
        return 2
    res = {}
    for fname, ft, fs in FILLS:
        print("", flush=True)
        print("#" * 92, flush=True)
        print("# 3회차 · %s" % fname, flush=True)
        print("#" * 92, flush=True)
        # 2a (대조 = 3d) — 1a 청산 + 위험 기반 크기
        r41.TARGET_FILL, r41.STOP_FILL = ft, fs
        ev2, _ = r41.replay(by, lambda p: r41.resolve_half_then_trail(p, 8.0, 20.0))
        for e in ev2:
            e["stop_frac"] = 0.08

        # 🚨 양방향 관문 — 증액 없이 pilot=1.0 이면 2a 와 같아야 한다
        if ft == "close":
            ev_g, _ = replay(by, ft, fs, adds=())
            bad, worst = [], 0.0
            for s in range(10):
                a = sp.sim_pyr(ev_g, risk=RISK, cap=CAP, seed=s, pilot=1.0)
                b = ss.sim_size(ev2, risk=RISK, cap=CAP, seed=s, partial=False)
                for k in ("equity_pct", "n_filled", "mdd_pct"):
                    rel = abs(a[k] - b[k]) / max(1e-12, abs(b[k]))
                    worst = max(worst, rel)
                    if rel > 1e-9:
                        bad.append((s, k, a[k], b[k]))
            print("  🚨 **양방향 관문**(증액 없음 · pilot=1.0 → 2a): %s · 최대 상대 편차 %.3e"
                  % ("**통과**" if not bad else "**미통과 %d곳** %s" % (len(bad), bad[:2]), worst),
                  flush=True)
            if bad:
                print("  → 점진 노출 시뮬을 쓸 수 없다. 중단한다.", flush=True)
                return 1

        for rname, fb, fs_ in REGIMES:
            print("", flush=True)
            print("  [%s]" % rname, flush=True)
            print("    %-4s %8s %13s %12s %12s %12s %10s %9s"
                  % ("판", "체결", "체결분거래당", "산술", "관측", "격차", "증액", "증액막힘"),
                  flush=True)
            row, curves = {}, {}
            with Cost(fb, fs_):
                b2 = ss.band(ev2, n_runs=N_SEED, risk=RISK, cap=CAP, partial=False)
                c2 = [ss.sim_size(ev2, seed=s, risk=RISK, cap=CAP, partial=False)["curve"]
                      for s in range(10)]
                row["2a(=3d)"] = {"n_filled": b2["n_filled"], "equity": b2["median"],
                                  "p5": b2["p5"], "p95": b2["p95"], "mdd": b2["mdd"],
                                  "arith": b2["arith"], "fpt": b2["filled_per_trade"],
                                  "added": 0, "add_blocked": 0,
                                  "conc_median": b2["conc_median"], "conc_p10": b2["conc_p10"],
                                  "conc_p90": b2["conc_p90"], "conc_max": b2["conc_max"],
                                  "overrun": b2["risk_overrun_mean"],
                                  "cash_floor": b2["cash_floor"]}
                curves["2a(=3d)"] = c2
                for name, kw, pilot, scale, _lab in VARIANTS:
                    evx, _ = replay(by, ft, fs, **kw)
                    bx = sp.band(evx, n_runs=N_SEED, risk=RISK, cap=CAP, pilot=pilot,
                                 size_scale=scale)
                    cx = [sp.sim_pyr(evx, seed=s, risk=RISK, cap=CAP, pilot=pilot,
                                     size_scale=scale)["curve"] for s in range(10)]
                    row[name] = {"n_filled": bx["n_filled"], "equity": bx["median"],
                                 "p5": bx["p5"], "p95": bx["p95"], "mdd": bx["mdd"],
                                 "arith": bx["arith"], "fpt": bx["filled_per_trade"],
                                 "added": bx["n_added"], "add_blocked": bx["n_add_blocked"],
                                 "conc_median": bx["conc_median"], "conc_p10": bx["conc_p10"],
                                 "conc_p90": bx["conc_p90"], "conc_max": bx["conc_max"],
                                 "overrun": bx["risk_overrun_mean"],
                                 "cash_floor": bx["cash_floor"]}
                    curves[name] = cx
            for k in ("2a(=3d)", "3a", "3b", "3c"):
                v = row[k]
                print("    %-4s %8.0f %12.4f%% %11.2f%% %11.2f%% %11.2f%%p %9.0f %8.0f"
                      % (k, v["n_filled"], v["fpt"], v["arith"], v["equity"],
                         v["equity"] - v["arith"], v["added"], v["add_blocked"]), flush=True)
            print("    동시 보유 — %s"
                  % " · ".join("%s 중앙%.0f(P10 %.0f~P90 %.0f·최대%d)"
                               % (k, row[k]["conc_median"], row[k]["conc_p10"],
                                  row[k]["conc_p90"], row[k]["conc_max"])
                               for k in ("2a(=3d)", "3a")), flush=True)
            print("    위험초과 — %s · 자유현금 최솟값 %s"
                  % (" · ".join("%s %+.4f%%p" % (k, row[k]["overrun"])
                                for k in ("2a(=3d)", "3a")),
                     " · ".join("%s %+.6f" % (k, row[k]["cash_floor"])
                                for k in ("2a(=3d)", "3a"))), flush=True)
            print("    🚨 주판정 — 짝비교(자료 축 · 3a − 2a)", flush=True)
            print(da.fmt(da.sweep(curves["3a"], curves["2a(=3d)"])), flush=True)
            L = {k: math.log(1 + row[k]["equity"] / 100) for k in row}
            print("    항등 분해(3a): 산술 증분 %+.2f%%p · 격차 증분 %+.2f%%p = 관측 증분 %+.2f%%p"
                  % (row["3a"]["arith"] - row["2a(=3d)"]["arith"],
                     (row["3a"]["equity"] - row["3a"]["arith"])
                     - (row["2a(=3d)"]["equity"] - row["2a(=3d)"]["arith"]),
                     row["3a"]["equity"] - row["2a(=3d)"]["equity"]), flush=True)
            res["%s|%s" % (fname, rname)] = row
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "47-round3.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    print("", flush=True)
    print("저장: .cache/bt5y/out/47-round3.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
