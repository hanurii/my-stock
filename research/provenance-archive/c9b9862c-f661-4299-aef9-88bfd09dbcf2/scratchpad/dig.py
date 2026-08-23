# -*- coding: utf-8 -*-
import json, sys, random, math
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCR = Path(sys.argv[0]).parent
MAIN = Path(r"C:\Users\hanul\playground\my-stock")
rows = json.loads((SCR/"events_feat.json").read_text(encoding="utf-8"))
reg = {x["date"]: x["up"] for x in json.loads((MAIN/"public/data/market-regime.json").read_text(encoding="utf-8"))["series"]}
print("regime 범위", min(reg), "~", max(reg))
for r in rows:
    r["up"] = reg.get(r["entry_date"])
R = [r for r in rows if r["result"] in ("win","loss")]
print("결착", len(R), "· 국면 결측", sum(1 for r in R if r["up"] is None))

def wr(g): return sum(1 for x in g if x["result"]=="win")/len(g)*100 if g else float('nan')
def ev(g):
    v=[x["gain_at_resolve_pct"] for x in g if x.get("gain_at_resolve_pct") is not None]
    return sum(v)/len(v) if v else float('nan')

print("\n=== 거래대금(50일 평균, 억원) 10분위 — 전체(국면 오염 있음) ===")
S=sorted(R,key=lambda x:x["turnover_eok"])
n=len(S)
for i in range(10):
    g=S[i*n//10:(i+1)*n//10]
    print(f" {i+1:>2}분위 {g[0]['turnover_eok']:>8.0f}~{g[-1]['turnover_eok']:>8.0f}억  n={len(g):>3}  승률 {wr(g):>5.1f}%  기대값 {ev(g):>+6.2f}%")

print("\n=== 후보 컷별 (전체 / 상승국면만) ===")
print(f"{'컷':>10}{'n':>6}{'승률':>8}{'기대값':>9}{'남는비율':>9}   | {'상승n':>6}{'상승승률':>9}{'상승기대':>9}")
UP=[r for r in R if r["up"]]
for c in [0,10,20,30,50,80,100,150,200,300,500,1000]:
    g=[x for x in R if x["turnover_eok"]>=c]
    gu=[x for x in UP if x["turnover_eok"]>=c]
    print(f"{c:>10}{len(g):>6}{wr(g):>8.1f}{ev(g):>9.2f}{len(g)/len(R)*100:>8.0f}%   |{len(gu):>6}{wr(gu):>9.1f}{ev(gu):>9.2f}")
print(f"\n상승국면 전체: n={len(UP)} 승률 {wr(UP):.1f}% 기대값 {ev(UP):+.2f}%")

# 시총과의 혼동 분리
print("\n=== 거래대금 vs 시총 (2x2, 각각 중앙값 기준) ===")
tmed=sorted(x["turnover_eok"] for x in R)[len(R)//2]
cmed=sorted(x["cap_eok"] for x in R)[len(R)//2]
print(f"거래대금 중앙 {tmed:.0f}억 · 시총 중앙 {cmed:.0f}억")
for tl,tp in [("거래대금↑",lambda x:x["turnover_eok"]>=tmed),("거래대금↓",lambda x:x["turnover_eok"]<tmed)]:
    for cl,cp in [("시총↑",lambda x:x["cap_eok"]>=cmed),("시총↓",lambda x:x["cap_eok"]<cmed)]:
        g=[x for x in R if tp(x) and cp(x)]
        print(f"  {tl} {cl}: n={len(g):>3} 승률 {wr(g):>5.1f}% 기대 {ev(g):>+6.2f}%")

# 회전율(거래대금/시총)
for r in R:
    r["turnover_ratio"] = r["turnover_eok"]/r["cap_eok"]*100 if r.get("cap_eok") else None
print("\n=== 회전율(거래대금/시총 %) 5분위 ===")
S=sorted([x for x in R if x["turnover_ratio"] is not None],key=lambda x:x["turnover_ratio"])
n=len(S)
for i in range(5):
    g=S[i*n//5:(i+1)*n//5]
    print(f" {i+1}분위 {g[0]['turnover_ratio']:>6.2f}~{g[-1]['turnover_ratio']:>6.2f}%  n={len(g):>3} 승률 {wr(g):>5.1f}% 기대 {ev(g):>+6.2f}%")
json.dump([{k:v for k,v in r.items()} for r in rows], open(SCR/"events_feat2.json","w",encoding="utf-8"), ensure_ascii=False)
