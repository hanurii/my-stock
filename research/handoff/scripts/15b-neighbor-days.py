# -*- coding: utf-8 -*-
"""15b — 이웃 일차(3·4·5·6·7) 부트스트랩만 따로.

지시서: research/handoff/tasks/15-variant2-followup.md "함께 낼 것" 마지막 항목.
**판정은 5일차로만 한다.** 이 파일은 "5일차만 튀면 우연, 이웃도 같으면 구조"를 보기 위한 것이다.

15-variant2-followup.py 와 같은 부트스트랩 장치(블록 20~40거래일 · 1,000회 · seed 고정 0)를 쓴다.
본체와 분리한 이유는 메모리다 — 한 번에 다 돌리다 다른 세션과 겹쳐 프로세스가 죽었다.

실행: PYTHONIOENCODING=utf-8 python research/handoff/scripts/15b-neighbor-days.py
난수 seed: 부트스트랩 블록 추출 20000 · 슬롯 순서 seed 0
"""
from __future__ import annotations

import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import slot_sim  # noqa: E402

import importlib.util  # noqa: E402


def _load(name, fname):
    sp = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parent / fname)
    mod = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod)
    return mod


e6 = _load("e6", "06-early-exit-10.py")
v15 = _load("v15", "15-variant2-followup.py")

OUT = ROOT / ".cache" / "bt5y" / "out"
DAYS = [3, 4, 5, 6, 7]


def simulate_dayN(p, dday):
    e = p["entry_price"]
    T, S = e * 1.2, e * 0.9
    n = p["n"]
    o, h, l, c = p["o"], p["h"], p["l"], p["c"]
    pend = False
    for i in range(n):
        if pend:
            return {"gain": (o[i] / e - 1) * 100, "days": i,
                    "resolve_date": p["dates"][i], "reason": "dayN"}
        hit_t, hit_s = h[i] >= T, l[i] <= S
        if hit_t and hit_s:
            return {"gain": (c[i] / e - 1) * 100, "days": i,
                    "resolve_date": p["dates"][i], "reason": "both_same_day"}
        if hit_t:
            return {"gain": (c[i] / e - 1) * 100, "days": i,
                    "resolve_date": p["dates"][i], "reason": "target"}
        if hit_s:
            return {"gain": (c[i] / e - 1) * 100, "days": i,
                    "resolve_date": p["dates"][i], "reason": "stop"}
        if i == dday and (c[i] / e - 1) * 100 <= -5.0:
            pend = True
    i = n - 1
    return {"gain": (c[i] / e - 1) * 100, "days": i,
            "resolve_date": p["dates"][i], "reason": "last_close"}


def build_dayN(P, dday):
    out = []
    for k, p in P.items():
        r = simulate_dayN(p, dday)
        out.append({"code": k[1], "pattern": k[2], "scan_date": k[0],
                    "entry_date": p["entry_date"], "resolve_date": r["resolve_date"],
                    "gain": r["gain"], "days": r["days"], "reason": r["reason"],
                    "result": e6.label(r["reason"], r["gain"])})
    return out


def main():
    P = e6.load_paths()
    all_dates = sorted({d for p in P.values() for d in p["dates"]})
    pos_of = {d: i for i, d in enumerate(all_dates)}
    n_pos = len(all_dates)
    base, _ = e6.build(P, None, None)
    bm = {(t["scan_date"], t["code"], t["pattern"]): t for t in base}

    out = {}
    for dd in DAYS:
        tr = build_dayN(P, dd)
        fired = [t for t in tr if t["reason"] == "dayN"]
        orig = Counter(bm[(t["scan_date"], t["code"], t["pattern"])]["reason"]
                       for t in fired)
        r = v15.bootstrap({"base": base, "v": tr}, pos_of, n_pos, seeds=(0,))
        d = [r["v"][i] - r["base"][i] for i in range(len(r["base"]))]
        lo, hi = v15.ci(d)
        out["%d일차" % dd] = {
            "n_fired": len(fired), "abandoned_winners": orig.get("target", 0),
            "diff_median": st.median(d), "ci_lo": lo, "ci_hi": hi,
            "excludes_zero": bool(lo > 0 or hi < 0),
            "pct_positive": sum(1 for x in d if x > 0) / len(d) * 100}
        print("%d일차 발동 %4d건(버린 승자 %2d) · 차이 중앙 %+7.2f%%p "
              "(95%% %+7.2f ~ %+7.2f) 0제외 %s · 양수 %.1f%%"
              % (dd, len(fired), orig.get("target", 0), st.median(d), lo, hi,
                 "예" if out["%d일차" % dd]["excludes_zero"] else "아니오",
                 out["%d일차" % dd]["pct_positive"]), flush=True)
        (OUT / "15b-neighbor-days.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n저장: .cache/bt5y/out/15b-neighbor-days.json")


if __name__ == "__main__":
    main()
