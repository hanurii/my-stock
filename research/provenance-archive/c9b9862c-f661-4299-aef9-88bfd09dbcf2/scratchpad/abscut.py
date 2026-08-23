# -*- coding: utf-8 -*-
import json, sys, math, random
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MAIN=Path(r"C:\Users\hanul\playground\my-stock"); SCR=Path(sys.argv[0]).parent
rows=json.loads((SCR/"events_feat3.json").read_text(encoding="utf-8"))
reg={x["date"]:x["up"] for x in json.loads((MAIN/"public/data/market-regime.json").read_text(encoding="utf-8"))["series"]}
for r in rows: r["up"]=reg.get(r["entry_date"])
byday=defaultdict(list)
for r in rows: byday[r["scan_date"]].append(r)
for d,g in byday.items():
    g2=sorted(g,key=lambda x:-x["turnover_eok"])
    for i,x in enumerate(g2): x["tv_pct"]=(i+0.5)/len(g2)
R=[r for r in rows if r["result"] in ("win","loss")]
def wr(g): return sum(1 for x in g if x["result"]=="win")/len(g)*100 if g else float('nan')
def ev(g):
    v=[x["gain_at_resolve_pct"] for x in g if x.get("gain_at_resolve_pct") is not None]
    return sum(v)/len(v) if v else float('nan')
def binom(k,n):
    if n==0: return 1.0
    pmf=lambda i: math.comb(n,i)*0.5**n
    o=pmf(k); return min(1.0,sum(pmf(i) for i in range(n+1) if pmf(i)<=o*(1+1e-9)))
def sameday_cut(cut):
    bd=defaultdict(list)
    for r in R: bd[r["scan_date"]].append(r)
    H=[];L=[];pos=neg=0;nd=0
    for d,g in bd.items():
        h=[x for x in g if x["turnover_eok"]>=cut]; l=[x for x in g if x["turnover_eok"]<cut]
        if not h or not l: continue
        nd+=1; H+=h; L+=l
        df=wr(h)-wr(l)
        pos+= df>0; neg+= df<0
    return H,L,pos,neg,nd
print("=== 절대 컷(50일 평균 거래대금, 억원) — 같은날 비교 ===")
print(f"{'컷':>6}{'날수':>6}{'+':>4}{'-':>4}{'부호p':>8}{'통과n':>7}{'통과WR':>8}{'탈락WR':>8}{'차':>7}{'통과기대':>9}{'남는%':>7}")
for c in [20,50,100,150,200,300,500,800]:
    H,L,pos,neg,nd=sameday_cut(c)
    g=[x for x in R if x["turnover_eok"]>=c]
    print(f"{c:>6}{nd:>6}{pos:>4}{neg:>4}{binom(pos,pos+neg):>8.4f}{len(H):>7}{wr(H):>8.1f}{wr(L):>8.1f}{wr(H)-wr(L):>+7.1f}{ev(g):>+9.2f}{len(g)/len(R)*100:>6.0f}%")

print("\n=== 월별 성적 (전체 vs 거래대금 상위절반) ===")
print(f"{'월':<9}{'전체n':>6}{'전체WR':>8}{'상위n':>6}{'상위WR':>8}{'상위기대':>9}")
bym=defaultdict(list)
for r in R: bym[r["month"]].append(r)
for m in sorted(bym):
    g=bym[m]; h=[x for x in g if x["tv_pct"]<0.5]
    print(f"{m:<9}{len(g):>6}{wr(g):>8.1f}{len(h):>6}{wr(h) if h else float('nan'):>8.1f}{ev(h) if h else float('nan'):>+9.2f}")

print("\n=== 최근 3개월(2026-06~08) 상세 ===")
rec=[r for r in R if r["month"]>="2026-06"]
print(f"  결착 {len(rec)}건 · 승률 {wr(rec):.1f}% · 기대 {ev(rec):+.2f}%")
unres=[r for r in rows if r["result"] in ("unresolved","ambiguous") and r["month"]>="2026-06"]
print(f"  미결·예외 {len(unres)}건 (최근 진입은 아직 결착 전 → 최근 승률은 표본이 얇음)")
allrec=[r for r in rows if r["month"]>="2026-06"]
print(f"  6~8월 전체 진입 {len(allrec)}건 (11~5월 {len(rows)-len(allrec)}건) — 최근에 신호 자체가 급감")
