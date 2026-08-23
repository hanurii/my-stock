# -*- coding: utf-8 -*-
"""16b — "우리 종목 × 전일 고가"를 **슬롯5에서도** 재본다.

16번에서 거래당 **−0.9432%p**(우리 피벗 − 우리종목β1, 렌즈 4/4, 95% −1.221 ~ −0.674)로
**이번 검증 전체에서 구간이 0을 확실히 제외한 유일한 결과**가 나왔다.
그런데 **거래당은 슬롯 회전 비용을 못 잰다**(05번에서 이미 나온 한계).
전일 고가는 피벗보다 자주 닿으므로 **실제로는 슬롯 점유가 달라진다.**

★ 이 판의 범위 (반드시 함께 읽을 것)
  **같은 거래 집합(우리 3,776건)에 방아쇠만 바꾼 것**이다.
  검출기의 감시목록(entry_ready 이지만 아직 안 뚫린 종목)은 기록이 없어
  **"전일 고가 방아쇠로 새로 생겼을 진입"은 재지 못한다.**
  즉 이것은 **"우리가 실제로 산 거래에서 방아쇠만 낮췄을 때"**의 값이다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/16b-beta1-slot5.py
난수 seed: 슬롯 순서 0~399
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
GATE = BT / "gate"
N_PAIR, N_LEVEL = 400, 200
YEARS = [2021, 2022, 2023, 2024, 2025, 2026]
YS = ("2021", "2022", "2023", "2024", "2025", "2026")
net = slot_sim.net


def band(xs, lo=5, hi=95):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def ci(xs, lo=2.5, hi=97.5):
    s = sorted(xs)
    return s[int(len(s) * lo / 100)], s[int(len(s) * hi / 100) - 1]


def main():
    ours, beta = [], []
    n_nobreak = 0
    for y in YEARS:
        d = json.loads((GATE / ("bt_%d_gate.json" % y)).read_text(encoding="utf-8"))
        prm = d["params"]
        w = (datetime.strptime(prm["start"], "%Y-%m-%d")
             - timedelta(days=g.WARM_DAYS)).strftime("%Y-%m-%d")
        le = (datetime.strptime(prm["end"], "%Y-%m-%d")
              + timedelta(days=g.TAIL_DAYS)).strftime("%Y-%m-%d")
        need = {e["code"] for e in d["events"]}
        print("[%d] 시계열 %s ~ %s · 종목 %d …" % (y, w, le, len(need)), flush=True)
        full = build_series((dt, {c: r for c, r in recs.items() if c in need})
                            for dt, recs in g.iter_pdata(w, le))
        for e in d["events"]:
            base = {"code": e["code"], "pattern": e["pattern"],
                    "scan_date": e["scan_date"], "entry_date": e["entry_date"],
                    "year": e["entry_date"][:4]}
            ours.append(dict(base, resolve_date=e["resolve_date"] or e["entry_date"],
                             gain=e["gain_at_resolve_pct"], result=e["result"]))
            s = full.get(e["code"])
            if not s:
                n_nobreak += 1
                continue
            ds = s["dates"]
            i = bisect_left(ds, e["scan_date"])
            di = i if (i < len(ds) and ds[i] == e["scan_date"]) else None
            r = g.outcome(s, di, ("beta", 1)) if di is not None else None
            if r is None:
                n_nobreak += 1
                continue
            beta.append(dict(base, resolve_date=ds[min(di + 1 + r["days"], len(ds) - 1)],
                             gain=r["gain"],
                             result=("win" if r["reason"] == "target" else "loss")))
        del full
        print("[%d]   우리 %d · β1 %d" % (y, len(ours), len(beta)), flush=True)

    print("\n우리 %d건 · 전일고가 방아쇠 %d건 (못 넘어 진입 없음 %d건 = %.1f%%)"
          % (len(ours), len(beta), n_nobreak, n_nobreak / len(ours) * 100), flush=True)

    def stats(tr, nm):
        nets = [net(t["gain"]) for t in tr]
        eqs = [slot_sim.sim(tr, seed=s)["equity_pct"] for s in range(N_PAIR)]
        lo, hi = band(eqs[:N_LEVEL])
        fills = st.median(slot_sim.sim(tr, seed=s)["n_filled"] for s in range(20))
        by_year = {y: st.mean([net(t["gain"]) for t in tr if t["year"] == y])
                   for y in YS if any(t["year"] == y for t in tr)}
        print("  %-16s n %4d · 거래당 %+7.4f%%p · 슬롯5 중앙 %+7.1f%% · 폭 %6.1f%%p · 체결 %4.0f"
              % (nm, len(tr), st.mean(nets), st.median(eqs[:N_LEVEL]), hi - lo, fills),
              flush=True)
        return {"n": len(tr), "per_trade": st.mean(nets), "eqs": eqs,
                "median": st.median(eqs[:N_LEVEL]), "band": [lo, hi],
                "band_width": hi - lo, "n_filled": fills, "by_year": by_year}

    print("\n[슬롯5] 정본 slot_sim · 400 seed · 밴드는 앞 200 seed 5~95%", flush=True)
    a = stats(ours, "우리(피벗)")
    b = stats(beta, "우리종목×전일고가")
    diff = [b["eqs"][i] - a["eqs"][i] for i in range(N_PAIR)]
    dlo, dhi = ci(diff)
    print("\n  ★ 차이(전일고가 − 피벗) 중앙 **%+.1f%%p** · 95%% %+.1f ~ %+.1f · "
          "우세율(참고) %.1f%%"
          % (st.median(diff), dlo, dhi,
             sum(1 for x in diff if x > 0) / N_PAIR * 100), flush=True)

    # 상위 5건 제거 (M30 — |기여| 양쪽 꼬리)
    key = lambda t: abs(net(t["gain"]))
    b5 = sorted(beta, key=key)[:-5]
    a5 = sorted(ours, key=key)[:-5]
    e5b = [slot_sim.sim(b5, seed=s)["equity_pct"] for s in range(N_LEVEL)]
    e5a = [slot_sim.sim(a5, seed=s)["equity_pct"] for s in range(N_LEVEL)]
    d5 = [e5b[i] - e5a[i] for i in range(N_LEVEL)]
    print("  |기여| 상위 5건 제거 후 차이 중앙 %+.1f%%p (부호 %s)"
          % (st.median(d5), "유지" if (st.median(d5) > 0) == (st.median(diff) > 0)
             else "반전"), flush=True)

    # 연도별 (슬롯5 축, 짝비교)
    print("\n  [연도별 · 슬롯5 축] 한 해를 빼고 다시 비교", flush=True)
    dy = {}
    for y in YS:
        bb = [t for t in beta if t["year"] != y]
        aa = [t for t in ours if t["year"] != y]
        dd = [slot_sim.sim(bb, seed=s)["equity_pct"]
              - slot_sim.sim(aa, seed=s)["equity_pct"] for s in range(N_LEVEL)]
        dy[y] = st.median(dd)
    flips = [y for y in YS if (dy[y] > 0) != (st.median(diff) > 0)]
    print("   " + " · ".join("%s제거 %+.1f" % (y, dy[y]) for y in YS), flush=True)
    print("   → 부호 반전: %s" % (", ".join(flips) if flips else "없음 (6/6 유지)"),
          flush=True)

    res = {"n_ours": len(ours), "n_beta": len(beta), "n_no_breakout": n_nobreak,
           "ours": {k: v for k, v in a.items() if k != "eqs"},
           "beta": {k: v for k, v in b.items() if k != "eqs"},
           "diff_median": st.median(diff), "diff_ci": [dlo, dhi],
           "win_pct": sum(1 for x in diff if x > 0) / N_PAIR * 100,
           "diff_drop_top5": st.median(d5), "drop_year": dy, "flip_years": flips,
           "scope": "같은 거래 집합에 방아쇠만 바꾼 판. 감시목록 기록이 없어 "
                    "'전일 고가 방아쇠로 새로 생겼을 진입'은 재지 못한다."}
    (OUT / "16b-beta1-slot5.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/16b-beta1-slot5.json")


if __name__ == "__main__":
    main()
