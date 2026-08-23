# -*- coding: utf-8 -*-
import json, sys, os, pickle, random
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from canslim_lib import ohlcv_matrix, sell_rules, pivot_backtest
OUT = r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad"
panel = pickle.load(open(os.path.join(OUT, "panel.pkl"), "rb"))

RULES = [
    ("heavy_volume_pullback", lambda s, bi, pv: sell_rules.rule_heavy_volume_pullback(s, bi)),
    ("consecutive_lower_lows", lambda s, bi, pv: sell_rules.rule_consecutive_lower_lows(s, bi)),
    ("close_below_ma", lambda s, bi, pv: sell_rules.rule_close_below_ma(s, bi)),
    ("weak_days_dominant", lambda s, bi, pv: sell_rules.rule_weak_days_dominant(s, bi)),
    ("breakout_failure", lambda s, bi, pv: sell_rules.rule_breakout_failure(s, bi, pv, breakout_confirmed=True, start=bi)),
]

# 1) 로컬 슬라이스 == 전체 시계열 (사전 이력 절단 무해) 검증
random.seed(0)
bad = 0; checked = 0
for p in random.sample(panel, 40):
    s = ohlcv_matrix.get_series(p["code"])
    bi_full = s["dates"].index(p["entry_date"])
    for d in p["days"][:: max(1, len(p["days"]) // 6) ] if p["days"] else []:
        t = pivot_backtest.truncate_series(s, d["date"])
        for rid, fn in RULES:
            got = fn(t, bi_full, p["pivot"])["status"]
            checked += 1
            if got != d["st"][rid]:
                bad += 1
                if bad < 6:
                    print("MISMATCH", p["code"], d["date"], rid, got, d["st"][rid])
print("slice-check: checked", checked, "mismatch", bad)

# 2) 단조성(한번 violation 이면 계속 violation?) 검증
nonmono = {rid: 0 for rid, _ in RULES}
for p in panel:
    seen = {}
    for d in p["days"]:
        for rid, _ in RULES:
            v = d["st"][rid] == "violation"
            if seen.get(rid) and not v:
                nonmono[rid] += 1
            seen[rid] = seen.get(rid) or v
print("non-monotone days:", nonmono)

# 3) 기준선 +20/-10 (피벗 기준) 재현 → 배포된 result 와 일치?
agree = dis = 0
from collections import Counter
cc = Counter()
for p in panel:
    pv = p["pivot"]; T = pv * 1.20; S = pv * 0.90
    res = None
    # 진입일(돌파일) 특례: simulate_pivot_trade 와 동일
    if p["entry_h"] >= T and p["entry_l"] <= S: res = "ambiguous"
    elif p["entry_h"] >= T: res = "win"
    elif p["entry_l"] <= S: res = "ambiguous"
    else:
        for d in p["days"]:
            ht = d["h"] >= T; hs = d["l"] <= S
            if ht and hs: res = "ambiguous"; break
            if ht: res = "win"; break
            if hs: res = "loss"; break
    if res is None: res = "unresolved" if p["avail"] <= 90 else "beyond90"
    cc[(p["result"], res)] += 1
    if res == p["result"]: agree += 1
    else: dis += 1
print("baseline reproduce agree", agree, "disagree", dis)
for k, v in sorted(cc.items(), key=lambda x: -x[1])[:12]:
    print("  ", k, v)
