# -*- coding: utf-8 -*-
import json, os
from pathlib import Path
SCR = Path(os.environ["SCR"])
P = json.load(open(SCR/"paths.json", encoding="utf-8"))

def base_sim(p, T=20.0, S=-10.0):
    """원본 simulate_pivot_trade 재현: 진입일 특례 포함."""
    pa = p["path"]
    for k, b in enumerate(pa):
        ht = b["h"] >= T; hs = b["l"] <= S
        if k == 0:
            if ht and hs: return ("ambiguous", 0, b["d"])
            if ht: return ("win", 0, b["d"])
            if hs: return ("ambiguous", 0, b["d"])
            continue
        if ht and hs: return ("ambiguous", k, b["d"])
        if ht: return ("win", k, b["d"])
        if hs: return ("loss", k, b["d"])
    return ("unresolved", len(pa)-1, pa[-1]["d"])

ok = dh = 0
bad = []
for p in P:
    r, k, rd = base_sim(p)
    if r == p["result"] and rd == p["resolve_date"]:
        ok += 1
    else:
        bad.append((p["code"], p["entry_date"], r, k, rd, p["result"], p["days_held"], p["resolve_date"]))
    if k == p["days_held"]: dh += 1
print("result+date 일치", ok, "/", len(P), " days_held 일치", dh)
for b in bad[:15]: print(b)
