# -*- coding: utf-8 -*-
"""과제A 엔진: 같은날 상위K 선택 규칙 대결."""
import json, random, math, sys
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCR = Path(__file__).resolve().parent
ROWS = json.loads((SCR/"panelA.json").read_text(encoding="utf-8"))

AMB = -10.0   # ambiguous 처리(보수적). 민감도에서 +20 도 확인
def ret_of(r, amb=AMB):
    x = r["result"]
    if x == "win":  return 20.0
    if x == "loss": return -10.0
    if x == "ambiguous": return amb
    return r["gain"]          # unresolved = 종료시점 평가손익
def win_of(r):
    x = r["result"]
    if x == "win": return 1
    if x in ("loss","ambiguous"): return 0
    return None               # unresolved 는 승률 분모 제외

for r in ROWS:
    r["ret"] = ret_of(r); r["win"] = win_of(r)

BYDAY = defaultdict(list)
for r in ROWS: BYDAY[r["entry_date"]].append(r)
DAYS = sorted(BYDAY)

# ── 순서 규칙: (이름, key함수, 내림차순?) ─────────────────────
RULES = [
 ("(b) 돌파순서 대리(시가/피벗 높은 순)", lambda r: r["open_ratio"], True),
 ("(c) 거래대금 큰 순",                   lambda r: r["turnover"],  True),
 ("(d) 거래대금 작은 순",                 lambda r: r["turnover"],  False),
 ("(e) RS 높은 순",                       lambda r: r["rs"],        True),
 ("(f) 초수익점수 높은 순",               lambda r: r["sp"],        True),
 ("(g) 피벗에 가까운 순",                 lambda r: r["pct_to_pivot"], False),
 ("(h) ATR 낮은 순",                      lambda r: r["atr"],       False),
 ("(i) 52주고가에 가까운 순",             lambda r: r["dist52"],    True),
 ("(j) 시가총액 큰 순",                   lambda r: r["cap"],       True),
]

def pick(day_rows, keyf, desc, K, rng):
    """상위 K 선택 — 동점은 무작위 파단."""
    dec = sorted(day_rows, key=lambda r: (keyf(r), rng.random()), reverse=desc)
    return dec[:K]

def pick_random(day_rows, K, rng):
    return rng.sample(day_rows, min(K, len(day_rows)))

def agg(sel):
    """선택된 거래 묶음 → 승률·기대값"""
    rets=[r["ret"] for r in sel]
    wins=[r["win"] for r in sel if r["win"] is not None]
    return (sum(rets)/len(rets) if rets else 0.0,
            100*sum(wins)/len(wins) if wins else float("nan"),
            len(rets), len(wins))
