# -*- coding: utf-8 -*-
"""23 · **0단계-C(슬롯5 MDE)** + **1단계 격자 12칸 × 2모드**.

지시서 + 두뇌 세션 26-08-23 지시(헤드라인 = 칸마다 `min(보수적, 낙관적)`).

★ 판정 축은 **슬롯5 자산곡선**(절대 규칙 4). 거래당도 함께 내되 판정은 슬롯5로.
★ 헤드라인은 **`min(보수적, 낙관적)`** — 구성상 규칙에 불리한 쪽이라 부풀릴 수 없다.
  **두 값은 병기한다.**
★ 모든 점추정에 구간(M35-9). 우세율·최대낙폭 포함.
★ 슬립은 **체결된 거래마다** 뺀다 — 래칫은 청산이 빨라 슬롯이 일찍 비고 **체결 수가 늘기** 때문에
  기준선과 팔에 다르게 먹힌다(같은 값을 양쪽에서 빼는 게 아니다).

관문 둘:
  G1 경로 재생 = 하네스 (23-gate-path-identity.py, 3,776/3,776 통과 확인 완료)
  G2 이 파일의 `sim_slip(slip=0)` == `slot_sim.sim` (정본) — 아래에서 건다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/23-stage1-ratchet.py
난수 seed: 슬롯 순서 0~199 · 블록 부트스트랩 230100
"""
from __future__ import annotations

import importlib.util
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

spec = importlib.util.spec_from_file_location("g0", HERE / "23-stage0-ratchet.py")
g0 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g0)

BT = ROOT / ".cache" / "bt5y"
OUT = BT / "out"
N_SEED = 200
N_BOOT = 1000
BOOT_SEED = 230100
BLOCK_MIN, BLOCK_MAX = 20, 40
MDE_K = 2.80
SLOTS = 5
TRIGGERS = g0.TRIGGERS
NEWSTOPS = g0.NEWSTOPS
YEARS = [2021, 2022, 2023, 2024, 2025, 2026]


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def sim_slip(trades, dates, pos_of, seed, slip=0.0, slots=SLOTS):
    """정본 ④(결착분은 다음 거래일부터) + 체결 거래마다 slip %p 차감.
    slip=0 이면 slot_sim.sim 과 같아야 한다(G2 관문)."""
    by_pos = defaultdict(list)
    for t in trades:
        by_pos[pos_of[t["entry_date"]]].append(t)
    for k in by_pos:
        by_pos[k].sort(key=lambda t: (t["code"], t.get("pattern", ""),
                                      t.get("scan_date", "")))
        if len(by_pos[k]) > 1:
            by_pos[k].sort(key=lambda t: slot_sim.order_key(seed, t))
    eq, held = 1.0, []
    n = w = 0
    peak, mdd = 1.0, 0.0
    for p in range(len(dates)):
        if held:
            for h in held:
                if not h[3] and h[0] < p:
                    eq += h[2] * (slot_sim.net(h[1]["gain"]) - slip) / 100
                    h[3] = True
                    n += 1
                    w += h[1]["result"] == "win"
            held = [h for h in held if h[0] >= p]
        free = slots - len(held)
        if free > 0 and p in by_pos:
            wgt = eq / slots
            for t in by_pos[p][:free]:
                held.append([pos_of[t["resolve_date"]], t, wgt, False])
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    for h in held:
        if not h[3]:
            eq += h[2] * (slot_sim.net(h[1]["gain"]) - slip) / 100
            n += 1
            w += h[1]["result"] == "win"
    peak = max(peak, eq)
    mdd = min(mdd, eq / peak - 1)
    return {"equity_pct": (eq - 1) * 100, "n_filled": n,
            "win_rate": w / n * 100 if n else 0.0, "mdd_pct": mdd * 100}


def boot_sim(by_pos, n_pos, seed, slip=0.0, slots=SLOTS):
    """새 시간축(정수 위치) 위의 슬롯5 — 12b 선례와 같은 형태."""
    eq, held = 1.0, []
    for p in range(n_pos):
        if held:
            for h in held:
                if not h[3] and h[0] < p:
                    eq += h[2] * (slot_sim.net(h[1]["gain"]) - slip) / 100
                    h[3] = True
            held = [h for h in held if h[0] >= p]
        free = slots - len(held)
        if free > 0:
            c = by_pos.get(p)
            if c:
                if len(c) > 1:
                    c = sorted(c, key=lambda t: slot_sim.order_key(seed, t))
                wgt = eq / slots
                for t in c[:free]:
                    held.append([p + t["days_held"], t, wgt, False])
    for h in held:
        if not h[3]:
            eq += h[2] * (slot_sim.net(h[1]["gain"]) - slip) / 100
    return (eq - 1) * 100


def build():
    paths = {}
    for y in range(2021, 2027):
        d = json.loads((OUT / ("paths_%d.json" % y)).read_text(encoding="utf-8"))
        for p in d["paths"]:
            paths[(p["scan_date"], p["code"], p["pattern"])] = p
    ev, seen = [], set()
    for y in range(2021, 2027):
        d = json.loads((BT / ("bt_%d.json" % y)).read_text(encoding="utf-8"))
        for e in d["events"]:
            k = (e["scan_date"], e["code"], e["pattern"])
            if k in seen:
                continue
            seen.add(k)
            ev.append(e)
    P = [paths[(e["scan_date"], e["code"], e["pattern"])] for e in ev]
    return P


def to_trades(P, arm):
    """arm=None 이면 기준선, 아니면 (trig, news, mode)."""
    out = []
    for p in P:
        if arm is None:
            r, i, g = g0.base_replay(p)
        else:
            trig, news, mode = arm
            r, i, g, _a, _amb = g0.ratchet(p, trig, news, mode)
        out.append({"code": p["code"], "pattern": p["pattern"],
                    "scan_date": p["scan_date"], "entry_date": p["entry_date"],
                    "resolve_date": p["dates"][i], "days_held": i,
                    "gain": g, "result": r, "year": int(p["entry_date"][:4])})
    return out


def main():
    P = build()
    base_tr = to_trades(P, None)
    all_dates = sorted({d for p in P for d in p["dates"]})
    pos_of = {d: i for i, d in enumerate(all_dates)}
    print("거래 %d건 · 거래일 %d" % (len(base_tr), len(all_dates)), flush=True)

    # ── G2 관문 ──
    print("\n★ G2 관문 — sim_slip(slip=0) 이 정본 slot_sim.sim 과 같은가", flush=True)
    ok = True
    for s in (0, 7, 42, 199):
        a = sim_slip(base_tr, all_dates, pos_of, s)["equity_pct"]
        b = slot_sim.sim(base_tr, seed=s)["equity_pct"]
        same = abs(a - b) < 1e-9
        ok = ok and same
        print("   seed %3d · 내 %+.6f%% · 정본 %+.6f%% · %s"
              % (s, a, b, "일치" if same else "**불일치**"), flush=True)
    if not ok:
        print("   ⚠ 불일치 상태로는 1단계 값을 신뢰할 수 없다. 여기서 멈춘다.", flush=True)
        return
    print("   → **통과**", flush=True)

    arms = []
    for trig in TRIGGERS:
        for lab, f in NEWSTOPS:
            news = f(trig)
            if news >= trig:
                continue
            for mode in ("pess", "opt"):
                arms.append(((trig, news, mode), "%g/%s/%s" % (trig, lab, mode)))
    print("\n팔 %d개 (12칸 × 2모드) + 기준선" % len(arms), flush=True)

    tr = {"_base": base_tr}
    for arm, name in arms:
        tr[name] = to_trades(P, arm)

    # ── 200 seed 짝비교 ──
    print("\n%s\n0단계-C + 1단계 · 슬롯5 200 seed 짝비교\n%s" % ("=" * 74, "=" * 74),
          flush=True)
    full = {}
    for key, t in tr.items():
        rs = [sim_slip(t, all_dates, pos_of, s) for s in range(N_SEED)]
        full[key] = {"eq": [r["equity_pct"] for r in rs],
                     "mdd": [r["mdd_pct"] for r in rs],
                     "n_filled": [r["n_filled"] for r in rs],
                     "win": [r["win_rate"] for r in rs]}
        print("  %-24s 자산 중앙 %+8.2f%% · 체결 중앙 %5.0f · MDD 중앙 %+7.2f%%"
              % (key, st.median(full[key]["eq"]), st.median(full[key]["n_filled"]),
                 st.median(full[key]["mdd"])), flush=True)

    obs = {}
    for _arm, name in arms:
        d = [full[name]["eq"][i] - full["_base"]["eq"][i] for i in range(N_SEED)]
        obs[name] = {"diff_median": st.median(d), "diff_seed_ci": list(ci(d)),
                     "diff_seed_sd": st.pstdev(d),
                     "MDE_seed": MDE_K * st.pstdev(d),
                     "win_share": sum(1 for x in d if x > 0) / N_SEED * 100,
                     "mdd_median": st.median(full[name]["mdd"]),
                     "n_filled_median": st.median(full[name]["n_filled"])}

    mdes = [obs[n]["MDE_seed"] for _a, n in arms]
    print("\n0단계-C · **슬롯5 짝비교 MDE(seed 축)** — 최소 %.2f · 중앙 %.2f · 최대 %.2f %%p"
          % (min(mdes), st.median(mdes), max(mdes)), flush=True)
    print("  ⚠️ 이것은 **seed 변동만** 잰 값이다. **자료 불확실성은 안 들어 있다.**"
          "\n     아래 블록 부트스트랩이 자료 축이고, 그쪽이 넓다.", flush=True)

    res = {"n": len(base_tr), "n_dates": len(all_dates),
           "base_slot5_median": st.median(full["_base"]["eq"]),
           "base_slot5_seed_ci": list(ci(full["_base"]["eq"])),
           "base_n_filled": st.median(full["_base"]["n_filled"]),
           "base_mdd": st.median(full["_base"]["mdd"]),
           "MDE_seed": {"min": min(mdes), "median": st.median(mdes), "max": max(mdes)},
           "obs": obs}
    print("\n기준선 슬롯5 중앙 **%+.2f%%** (seed 95%% %+.2f ~ %+.2f) · 체결 %.0f · MDD %+.2f%%"
          % (res["base_slot5_median"], *res["base_slot5_seed_ci"],
             res["base_n_filled"], res["base_mdd"]), flush=True)

    # ── 헤드라인 = min(보수적, 낙관적) ──
    print("\n%s\n1단계 · 12칸 — 헤드라인 = **min(보수적, 낙관적)**\n%s"
          % ("=" * 74, "=" * 74), flush=True)
    cells = []
    print("  %-8s %-13s %11s %11s %11s %9s %9s"
          % ("트리거", "새손절", "보수적", "낙관적", "**헤드라인**", "우세율", "체결"), flush=True)
    for trig in TRIGGERS:
        for lab, f in NEWSTOPS:
            news = f(trig)
            if news >= trig:
                continue
            pn = "%g/%s/pess" % (trig, lab)
            on = "%g/%s/opt" % (trig, lab)
            hp, ho = obs[pn]["diff_median"], obs[on]["diff_median"]
            head = min(hp, ho)
            hn = pn if hp <= ho else on
            cells.append({"trigger": trig, "stop_label": lab, "stop_pct": news,
                          "pess": obs[pn], "opt": obs[on],
                          "headline": head, "headline_mode": hn.split("/")[-1],
                          "headline_ci": obs[hn]["diff_seed_ci"]})
            print("  %-8s %-13s %+10.2f%% %+10.2f%% %+10.2f%%  %8.1f%% %9.0f"
                  % ("+%g%%" % trig, lab, hp, ho, head,
                     obs[hn]["win_share"], obs[hn]["n_filled_median"]), flush=True)
    res["cells"] = cells

    (OUT / "23-stage1-ratchet.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/23-stage1-ratchet.json", flush=True)


if __name__ == "__main__":
    main()
