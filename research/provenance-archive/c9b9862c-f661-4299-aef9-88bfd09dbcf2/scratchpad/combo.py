# -*- coding: utf-8 -*-
"""거래대금 순위 규칙의 실사용 형태 + 국면·패턴 조합 + 손익비 레버."""
import json, sys, random
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MAIN=Path(r"C:\Users\hanul\playground\my-stock"); SCR=Path(sys.argv[0]).parent
sys.path.insert(0,str(MAIN/"scripts"))
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR=MAIN/".cache"/"ohlcv"/"series"; ohlcv_matrix.FOREIGN_PATH=MAIN/".cache"/"ohlcv"/"foreign.json"
from canslim_lib.pivot_backtest import simulate_pivot_trade, tally

rows=json.loads((SCR/"events_feat3.json").read_text(encoding="utf-8"))
reg={x["date"]:x["up"] for x in json.loads((MAIN/"public/data/market-regime.json").read_text(encoding="utf-8"))["series"]}
for r in rows: r["up"]=reg.get(r["entry_date"])
# 그날 후보 중 거래대금 순위(1=최상위) / 상위비율
byday=defaultdict(list)
for r in rows: byday[r["scan_date"]].append(r)
for d,g in byday.items():
    g2=sorted(g,key=lambda x:-x["turnover_eok"])
    for i,x in enumerate(g2):
        x["tv_rank"]=i+1; x["tv_pct"]=(i+0.5)/len(g2); x["n_day"]=len(g2)
R=[r for r in rows if r["result"] in ("win","loss")]
def wr(g): return sum(1 for x in g if x["result"]=="win")/len(g)*100 if g else float('nan')
def ev(g):
    v=[x["gain_at_resolve_pct"] for x in g if x.get("gain_at_resolve_pct") is not None]
    return sum(v)/len(v) if v else float('nan')
def line(lbl,g,base=len(R)):
    print(f"  {lbl:<38} n={len(g):>3} ({len(g)/base*100:>4.0f}%)  승률 {wr(g):>5.1f}%  기대값 {ev(g):>+6.2f}%")

print("=== 그날 후보 거래대금 순위별(전체 결착 580) ===")
for lbl,f in [("1위만",lambda x:x["tv_rank"]==1),("상위2",lambda x:x["tv_rank"]<=2),
              ("상위3",lambda x:x["tv_rank"]<=3),("상위절반",lambda x:x["tv_pct"]<0.5),
              ("하위절반",lambda x:x["tv_pct"]>=0.5),("최하위",lambda x:x["tv_rank"]==x["n_day"])]:
    line(lbl,[r for r in R if f(r)])

print("\n=== 국면 × 거래대금순위 ===")
for rl,rf in [("상승",lambda x:x["up"]),("조정",lambda x:not x["up"])]:
    for tl,tf in [("상위절반",lambda x:x["tv_pct"]<0.5),("하위절반",lambda x:x["tv_pct"]>=0.5)]:
        line(f"{rl} × 거래대금{tl}",[r for r in R if rf(r) and tf(r)])

print("\n=== 국면 × 거래대금순위 × 패턴 ===")
for rl,rf in [("상승",lambda x:x["up"])]:
    for tl,tf in [("상위절반",lambda x:x["tv_pct"]<0.5)]:
        for pl,pf in [("VCP",lambda x:x["pattern"]=="VCP"),("전패턴",lambda x:True)]:
            line(f"{rl} × {tl} × {pl}",[r for r in R if rf(r) and tf(r) and pf(r)])
        for pl,pf in [("VCP+상위3",lambda x:x["pattern"]=="VCP" and x["tv_rank"]<=3)]:
            line(f"{rl} × {pl}",[r for r in R if rf(r) and pf(r)])

print("\n=== 손익비 레버: 같은 614 진입을 목표/손절만 바꿔 재시뮬 ===")
ser={c:ohlcv_matrix.get_series(c) for c in sorted({r['code'] for r in rows})}
sims={}
for tgt,stp in [(20,10),(15,10),(10,10),(10,7.5),(10,5),(8,8),(25,10),(20,8),(30,10),(15,7.5),(12,6)]:
    evs=[]
    for r in rows:
        s=ser.get(r["code"])
        if not s or r["entry_date"] not in s["dates"]: continue
        i=s["dates"].index(r["entry_date"])
        sm=simulate_pivot_trade(s,i,r["entry_price"],tgt,stp)
        evs.append({**r,"result":sm["result"],"gain_at_resolve_pct":sm.get("gain_at_resolve_pct")})
    t=tally(evs); res=[e for e in evs if e["result"] in ("win","loss")]
    sims[(tgt,stp)]=evs
    print(f"  +{tgt}/-{stp}: 결착 {len(res):>3}  승률 {wr(res):>5.1f}%  기대값 {ev(res):>+6.2f}%  (손익분기승률 {stp/(tgt+stp)*100:>4.1f}%)")

print("\n=== 손익비 × 거래대금 상위절반 × 상승국면 (승률 50% 달성 조합 탐색) ===")
for (tgt,stp),evs in sims.items():
    g=[e for e in evs if e["result"] in ("win","loss") and e["up"] and e["tv_pct"]<0.5]
    if g: print(f"  +{tgt}/-{stp}: n={len(g):>3} 승률 {wr(g):>5.1f}% 기대값 {ev(g):>+6.2f}%")
