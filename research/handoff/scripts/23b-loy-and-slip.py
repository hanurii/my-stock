# -*- coding: utf-8 -*-
"""23b · **2단계 leave-one-year(의존율)** + **3단계 슬리피지**.

★ 2021을 뺀 값을 같은 표에 나란히 싣는다(달력 착시가 6번 걸렸고 거의 항상 2021이었다).
★ 슬립은 **체결된 거래마다** 뺀다 — 래칫은 청산이 빨라 체결 수가 늘어 기준선과 다르게 먹힌다.
★ 헤드라인은 칸마다 `min(보수적, 낙관적)`(두뇌 세션 26-08-23 정정).

속도: `order_key(seed, t)` 는 (seed, code, scan_date, pattern) 만의 함수라
      **팔·연도부분집합·슬립과 무관**하다 → seed마다 한 번만 계산해 재사용한다.
      G3 관문으로 최적화판이 23-stage1 의 `sim_slip` 과 같은 값을 내는지 확인한다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/23b-loy-and-slip.py
난수 seed: 슬롯 순서 0~199
"""
from __future__ import annotations

import importlib.util
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import slot_sim  # noqa: E402

spec = importlib.util.spec_from_file_location("g1", HERE / "23-stage1-ratchet.py")
g1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g1)

OUT = ROOT / ".cache" / "bt5y" / "out"
N_SEED = 200
YEARS = [2021, 2022, 2023, 2024, 2025, 2026]
SLIPS = [0.0, 0.25, 0.5]
SLOTS = 5


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def fast_sim(rows, n_pos, slip=0.0, slots=SLOTS):
    """rows: 진입위치 오름차순, 각 원소 (epos, okey, rpos, net, is_win).
    같은 epos 안에서는 okey 오름차순으로 이미 정렬돼 있어야 한다."""
    eq, held = 1.0, []
    n = w = 0
    peak, mdd = 1.0, 0.0
    i, m = 0, len(rows)
    for p in range(n_pos):
        if held:
            keep = []
            for h in held:
                if h[0] < p:
                    eq += h[1] * (h[2] - slip) / 100
                    n += 1
                    w += h[3]
                else:
                    keep.append(h)
            held = keep
        free = slots - len(held)
        while i < m and rows[i][0] < p:
            i += 1
        if free > 0 and i < m and rows[i][0] == p:
            wgt = eq / slots
            j = i
            while j < m and rows[j][0] == p and free > 0:
                held.append([rows[j][2], wgt, rows[j][3], rows[j][4]])
                free -= 1
                j += 1
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    for h in held:
        eq += h[1] * (h[2] - slip) / 100
        n += 1
        w += h[3]
    peak = max(peak, eq)
    mdd = min(mdd, eq / peak - 1)
    return (eq - 1) * 100, n, mdd * 100


def main():
    P = g1.build()
    all_dates = sorted({d for p in P for d in p["dates"]})
    pos_of = {d: i for i, d in enumerate(all_dates)}
    n_pos = len(all_dates)
    arms = []
    for trig in g1.TRIGGERS:
        for lab, f in g1.NEWSTOPS:
            news = f(trig)
            if news < trig:
                arms.append((trig, lab, news))
    tr = {"_base": g1.to_trades(P, None)}
    for trig, lab, news in arms:
        for mode in ("pess", "opt"):
            tr["%g/%s/%s" % (trig, lab, mode)] = g1.to_trades(P, (trig, news, mode))
    keys = list(tr)
    print("팔 %d + 기준선 · 거래일 %d · 거래 %d"
          % (len(tr) - 1, n_pos, len(tr["_base"])), flush=True)

    # ── 정렬키 사전계산 (팔·연도·슬립과 무관) ──
    base = tr["_base"]
    print("정렬키 %d seed × %d거래 사전계산 …" % (N_SEED, len(base)), flush=True)
    okeys = [[slot_sim.order_key(s, t) for t in base] for s in range(N_SEED)]
    print("  완료", flush=True)

    # 팔별 (epos, rpos, net, is_win) — 거래 인덱스는 팔끼리 공통
    meta = {}
    for k in keys:
        meta[k] = [(pos_of[t["entry_date"]], pos_of[t["resolve_date"]],
                    slot_sim.net(t["gain"]), 1 if t["result"] == "win" else 0)
                   for t in tr[k]]
    years = [int(t["entry_date"][:4]) for t in base]

    def rows_for(k, s, keep):
        r = [(meta[k][x][0], okeys[s][x], meta[k][x][1], meta[k][x][2], meta[k][x][3])
             for x in keep]
        r.sort(key=lambda z: (z[0], z[1]))
        return r

    # ── G3 관문 ──
    print("\n★ G3 관문 — 최적화판이 23-stage1 의 sim_slip 과 같은가", flush=True)
    allidx = list(range(len(base)))
    ok = True
    for k in ("_base", "10/본전(0%)/pess", "15/트리거의 절반/opt"):
        for s in (0, 137):
            a = fast_sim(rows_for(k, s, allidx), n_pos)[0]
            b = g1.sim_slip(tr[k], all_dates, pos_of, s)["equity_pct"]
            same = abs(a - b) < 1e-9
            ok = ok and same
            print("   %-22s seed %3d · %+.6f vs %+.6f · %s"
                  % (k, s, a, b, "일치" if same else "**불일치**"), flush=True)
    if not ok:
        print("   ⚠ 불일치 상태로는 값을 신뢰할 수 없다. 여기서 멈춘다.", flush=True)
        return
    print("   → **통과**", flush=True)

    res = {"years": YEARS, "slips": SLIPS}

    def headline(keep, slip=0.0):
        eqs = {}
        for k in keys:
            eqs[k] = [fast_sim(rows_for(k, s, keep), n_pos, slip)[0]
                      for s in range(N_SEED)]
        out = {}
        for trig, lab, _news in arms:
            best = None
            for mode in ("pess", "opt"):
                nm = "%g/%s/%s" % (trig, lab, mode)
                d = [eqs[nm][i] - eqs["_base"][i] for i in range(N_SEED)]
                m_ = st.median(d)
                if best is None or m_ < best[0]:
                    best = (m_, mode, list(ci(d)),
                            sum(1 for x in d if x > 0) / N_SEED * 100)
            out["+%g%%/%s" % (trig, lab)] = {"headline": best[0], "mode": best[1],
                                             "ci": best[2], "win_share": best[3]}
        out["_base_equity"] = st.median(eqs["_base"])
        return out

    # ── 2단계 ──
    print("\n" + "=" * 80, flush=True)
    print("2단계 · **leave-one-year** — 헤드라인 = min(보수적, 낙관적) 짝비교 중앙(%p)",
          flush=True)
    print("=" * 80, flush=True)
    fullh = headline(allidx)
    loy = {}
    for y in YEARS:
        keep = [i for i in allidx if years[i] != y]
        loy[y] = headline(keep)
        print("  %d 뺌 (거래 %d · 기준선 자산 중앙 %+.2f%%)"
              % (y, len(keep), loy[y]["_base_equity"]), flush=True)
    names = [k for k in fullh if k != "_base_equity"]
    print("\n  %-16s %9s %9s %9s %9s %9s %9s %9s"
          % ("칸", "전체", "−2021", "−2022", "−2023", "−2024", "−2025", "−2026"), flush=True)
    rows = []
    for nm in names:
        f = fullh[nm]["headline"]
        vals = [loy[y][nm]["headline"] for y in YEARS]
        print("  %-16s %+8.2f %+8.2f %+8.2f %+8.2f %+8.2f %+8.2f %+8.2f"
              % (nm, f, *vals), flush=True)
        dep = {str(y): ((1 - v / f) * 100 if f != 0 else None)
               for y, v in zip(YEARS, vals)}
        rows.append({"cell": nm, "full": f,
                     "loy": {str(y): v for y, v in zip(YEARS, vals)},
                     "dependence_pct": dep,
                     "sign_flips": sum(1 for v in vals if (v > 0) != (f > 0))})
    res["loy"] = rows
    flips = sum(r["sign_flips"] for r in rows)
    print("\n  **한 해를 빼서 부호가 뒤집힌 (칸, 해) 쌍: %d / %d**"
          % (flips, len(rows) * len(YEARS)), flush=True)
    d21 = [r["dependence_pct"]["2021"] for r in rows]
    print("  **2021을 뺐을 때 효과가 사라진 비율: 중앙 %.1f%% (최소 %.1f · 최대 %.1f)**"
          % (st.median(d21), min(d21), max(d21)), flush=True)
    print("  (양수 = 2021을 빼면 효과가 줄어든다 · 음수 = 오히려 커진다)", flush=True)
    res["dep2021"] = {"median": st.median(d21), "min": min(d21), "max": max(d21)}
    res["sign_flips"] = flips

    # ── 3단계 ──
    print("\n" + "=" * 80, flush=True)
    print("3단계 · **슬리피지** — 체결 거래마다 차감", flush=True)
    print("=" * 80, flush=True)
    slip_out = {}
    for sl in SLIPS:
        h = headline(allidx, sl)
        slip_out[str(sl)] = h
        pos = [nm for nm in names if h[nm]["headline"] > 0]
        cip = [nm for nm in names if h[nm]["ci"][0] > 0]
        best = max(names, key=lambda n: h[n]["headline"])
        print("\n  슬립 %.2f%%p · 기준선 자산 중앙 %+.2f%%" % (sl, h["_base_equity"]),
              flush=True)
        print("    헤드라인 플러스 **%d / 12** · 구간이 0 제외 플러스 **%d / 12**"
              % (len(pos), len(cip)), flush=True)
        print("    최고 칸 %s **%+.2f%%p** (구간 %+.1f ~ %+.1f · 우세율 %.1f%%)"
              % (best, h[best]["headline"], *h[best]["ci"], h[best]["win_share"]),
              flush=True)
    res["slip"] = slip_out

    (OUT / "23b-loy-and-slip.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/23b-loy-and-slip.json", flush=True)


if __name__ == "__main__":
    main()
