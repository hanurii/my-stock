# -*- coding: utf-8 -*-
import json, sys, random
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MAIN=Path(r"C:\Users\hanul\playground\my-stock"); SCR=Path(sys.argv[0]).parent
rows=json.loads((SCR/"events_feat3.json").read_text(encoding="utf-8"))
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
P=lambda x: x["tv_pct"]<1/3
print("=== 상위1/3 규칙: 월 층화 ===")
bym=defaultdict(lambda:[[],[]])
for r in R: bym[r["month"]][0 if P(r) else 1].append(r)
pos=neg=0
for m in sorted(bym):
    h,l=bym[m]
    if not h or not l: continue
    d=wr(h)-wr(l); pos+= d>0; neg+= d<0
    print(f"  {m}  상 {wr(h):>5.1f}%(n={len(h):>3})  나머지 {wr(l):>5.1f}%(n={len(l):>3})  차 {d:>+6.1f}%p")
print(f"  → 월 +{pos} / -{neg}")
print("\n=== 상위1/3 규칙: 전후반 ===")
for lbl,f in [("전반(~03-24)",lambda x:x["entry_date"]<"2026-03-25"),("후반(03-25~)",lambda x:x["entry_date"]>="2026-03-25")]:
    h=[r for r in R if f(r) and P(r)]; l=[r for r in R if f(r) and not P(r)]
    print(f"  {lbl}: 상 {wr(h):>5.1f}%(n={len(h):>3}) 나머지 {wr(l):>5.1f}%(n={len(l):>3}) 차 {wr(h)-wr(l):>+6.1f}%p")
print("\n=== 상위1/3 규칙: 종목 클러스터 부트스트랩(2000회) ===")
bc=defaultdict(list)
for r in R: bc[r["code"]].append(r)
codes=list(bc); rnd=random.Random(9)
obs=wr([r for r in R if P(r)])-wr([r for r in R if not P(r)])
ds=[]
for _ in range(2000):
    h=[];l=[]
    for _ in codes:
        for x in bc[rnd.choice(codes)]:
            (h if P(x) else l).append(x)
    if h and l: ds.append(wr(h)-wr(l))
ds.sort()
print(f"  관측 {obs:+.2f}%p · 95% [{ds[int(.025*len(ds))]:+.2f}, {ds[int(.975*len(ds))]:+.2f}] · P(<=0)={sum(1 for d in ds if d<=0)/len(ds):.3f}")
print("\n=== 상위1/3 안에서 국면 ===")
for lbl,f in [("상승",lambda x: x.get("up_scan")),("조정",lambda x: x.get("up_scan") is False)]:
    pass
rs={x["date"]:x["up"] for x in json.loads((MAIN/"public/data/market-regime.json").read_text(encoding="utf-8"))["series"]}
for r in R: r["u"]=rs.get(r["scan_date"])
for lbl,v in [("상승",True),("조정",False)]:
    h=[r for r in R if P(r) and r["u"]==v]; l=[r for r in R if not P(r) and r["u"]==v]
    print(f"  {lbl}: 상위1/3 {wr(h):>5.1f}%(n={len(h):>3}) 기대 {ev(h):>+6.2f}% | 나머지 {wr(l):>5.1f}%(n={len(l):>3}) 기대 {ev(l):>+6.2f}%")
print("\n=== 최종 후보 규칙표 (국면=scan_date 기준, 프롬프트 수치와 정합) ===")
def sh(lbl,g): print(f"  {lbl:<34} n={len(g):>3} ({len(g)/len(R)*100:>3.0f}%)  승률 {wr(g):>5.1f}%  기대 {ev(g):>+6.2f}%")
sh("무필터",R)
sh("상승국면만",[r for r in R if r["u"]])
sh("거래대금 상위1/3",[r for r in R if P(r)])
sh("상승국면 + 거래대금 상위1/3",[r for r in R if r["u"] and P(r)])
sh("상승국면 + 상위1/3 + VCP",[r for r in R if r["u"] and P(r) and r["pattern"]=="VCP"])
