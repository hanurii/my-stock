# -*- coding: utf-8 -*-
"""(거래 x 보유일차) 관측표 생성 — 보유 중인 날만, 규칙상태 + 전방성과."""
import os, pickle, sys
sys.stdout.reconfigure(encoding='utf-8')
OUT = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad"
PANEL = pickle.load(open(os.path.join(OUT, "panel.pkl"), "rb"))
RIDS = ["heavy_volume_pullback", "consecutive_lower_lows", "close_below_ma",
        "weak_days_dominant", "breakout_failure"]
H = 60
KMAX = 20


def baseline_exit(e, H):
    """현행 +20/-10. (exit_k, exit_price) — 진입일 포함, 같은날 둘다면 손절."""
    E = e["entry_price"]; T = E * 1.20; S = E * 0.90
    O = [e["entry_o"]] + [d["o"] for d in e["days"][:H]]
    Hi = [e["entry_h"]] + [d["h"] for d in e["days"][:H]]
    Lo = [e["entry_l"]] + [d["l"] for d in e["days"][:H]]
    C = [e["entry_c"]] + [d["c"] for d in e["days"][:H]]
    for k in range(len(C)):
        if Lo[k] <= S:
            return k, min(O[k], S)
        if Hi[k] >= T:
            return k, max(O[k], T)
    return len(C) - 1, C[-1]


rows = []
for e in PANEL:
    if e["avail"] < 20:
        continue
    ek, epx = baseline_exit(e, H)
    C = [e["entry_c"]] + [d["c"] for d in e["days"][:H]]
    for d in e["days"]:
        k = d["k"]
        if k > KMAX or k > ek:      # 이미 청산된 뒤는 관측 아님
            continue
        c = d["c"]
        st = d["st"]
        viol = {r: (st[r] == "violation") for r in RIDS}
        cnt = sum(viol.values())
        fwd = {}
        for m in (5, 10, 20):
            if k + m < len(C):
                fwd[m] = (C[k + m] / c - 1) * 100
            else:
                fwd[m] = None
        rows.append({
            "code": e["code"], "entry_date": e["entry_date"], "date": d["date"],
            "k": k, "cnt": cnt, **{("v_" + r): viol[r] for r in RIDS},
            "rem": (epx / c - 1) * 100,          # 지금 팔지 않고 현행대로 갔을 때 남은 수익
            "fwd5": fwd[5], "fwd10": fwd[10], "fwd20": fwd[20],
            "pnl_now": (c / e["entry_price"] - 1) * 100,
            "exit_k": ek,
        })
print("관측 수", len(rows), "거래 수", len(set((r['code'], r['entry_date']) for r in rows)))
pickle.dump(rows, open(os.path.join(OUT, "obs.pkl"), "wb"))
from collections import Counter
print("위반개수 분포", Counter(r["cnt"] for r in rows))
for r in RIDS:
    n = sum(1 for x in rows if x["v_" + r])
    print(f"  {r:<24} 점등 {n}/{len(rows)} = {n/len(rows)*100:.1f}%")
print("k별 평균 위반개수:")
for kb in range(1, 21):
    sub = [r for r in rows if r["k"] == kb]
    if sub:
        print(f"  k={kb:2d} n={len(sub):5d} 평균위반 {sum(r['cnt'] for r in sub)/len(sub):.2f}  위반0비율 {sum(1 for r in sub if r['cnt']==0)/len(sub)*100:.1f}%")
