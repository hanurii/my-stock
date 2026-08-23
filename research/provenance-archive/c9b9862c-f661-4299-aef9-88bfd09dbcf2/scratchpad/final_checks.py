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
    for i,x in enumerate(g2): x["tv_rank"]=i+1; x["tv_pct"]=(i+0.5)/len(g2); x["n_day"]=len(g2)
R=[r for r in rows if r["result"] in ("win","loss")]
def wr(g): return sum(1 for x in g if x["result"]=="win")/len(g)*100 if g else float('nan')
def ev(g):
    v=[x["gain_at_resolve_pct"] for x in g if x.get("gain_at_resolve_pct") is not None]
    return sum(v)/len(v) if v else float('nan')

print("=== 같은날 거래대금 3분위(그날 후보 안에서) ===")
for lbl,f in [("상위1/3",lambda x:x["tv_pct"]<1/3),("중간1/3",lambda x:1/3<=x["tv_pct"]<2/3),("하위1/3",lambda x:x["tv_pct"]>=2/3)]:
    g=[r for r in R if f(r) and r["n_day"]>=3]
    print(f"  {lbl}: n={len(g):>3} 승률 {wr(g):>5.1f}% 기대 {ev(g):>+6.2f}%")

print("\n=== 거래대금 효과가 ATR·시총 착시인가 (층 안에서 같은날 분할) ===")
def daysplit(rows_,key):
    bd=defaultdict(list)
    for r in rows_:
        if r.get(key) is not None: bd[r["scan_date"]].append(r)
    H=[];L=[];nd=0
    for d,g in bd.items():
        if len(g)<2: continue
        v=sorted(x[key] for x in g)
        med=v[len(v)//2] if len(v)%2 else (v[len(v)//2-1]+v[len(v)//2])/2
        hi=[x for x in g if x[key]>med]; lo=[x for x in g if x[key]<=med]
        if not hi or not lo:
            hi=[x for x in g if x[key]>=med]; lo=[x for x in g if x[key]<med]
        if hi and lo: H+=hi; L+=lo; nd+=1
    return H,L,nd
for band in ["①조용 <2.5%","②보통 2.5~4%","③큼 4~6%","④매우큼 6%+"]:
    sub=[r for r in R if r["atr_band"]==band]
    H,L,nd=daysplit(sub,"turnover_eok")
    if H and L: print(f"  ATR {band:<12} 상 {wr(H):>5.1f}%(n={len(H):>3}) 하 {wr(L):>5.1f}%(n={len(L):>3}) 차 {wr(H)-wr(L):>+6.1f}%p (날 {nd})")
cmed=sorted(x["cap_eok"] for x in R)[len(R)//2]
for lbl,f in [("시총 상위",lambda x:x["cap_eok"]>=cmed),("시총 하위",lambda x:x["cap_eok"]<cmed)]:
    sub=[r for r in R if f(r)]
    H,L,nd=daysplit(sub,"turnover_eok")
    print(f"  {lbl:<14} 상 {wr(H):>5.1f}%(n={len(H):>3}) 하 {wr(L):>5.1f}%(n={len(L):>3}) 차 {wr(H)-wr(L):>+6.1f}%p (날 {nd})")
# 반대로 시총 효과를 거래대금 층 안에서
tmed=sorted(x["turnover_eok"] for x in R)[len(R)//2]
for lbl,f in [("거래대금 상위",lambda x:x["turnover_eok"]>=tmed),("거래대금 하위",lambda x:x["turnover_eok"]<tmed)]:
    sub=[r for r in R if f(r)]
    H,L,nd=daysplit(sub,"cap_eok")
    print(f"  [역방향] 시총분할 in {lbl:<8} 상 {wr(H):>5.1f}%(n={len(H):>3}) 하 {wr(L):>5.1f}%(n={len(L):>3}) 차 {wr(H)-wr(L):>+6.1f}%p")

print("\n=== 날짜 단위 요인(같은날 비교 불가 — 국면과 뒤엉킴) ===")
def daylevel(key,label):
    bd={}
    for r in R: bd.setdefault(r["scan_date"],[]).append(r)
    dv=[(d,g[0][key],g) for d,g in bd.items() if g[0].get(key) is not None]
    dv.sort(key=lambda x:x[1])
    n=len(dv)
    print(f"  [{label}] 스캔일 {n}일")
    for i in range(4):
        seg=dv[i*n//4:(i+1)*n//4]
        g=[x for _,_,gg in seg for x in gg]
        up=sum(1 for _,_,gg in seg for x in gg if x["up"])/max(1,len(g))*100
        print(f"    {i+1}분위 {seg[0][1]:>5}~{seg[-1][1]:>5}  거래 {len(g):>3}  승률 {wr(g):>5.1f}%  기대 {ev(g):>+6.2f}%  (상승국면비중 {up:>4.0f}%)")
daylevel("n_eval_day","그날 평가 종목 수")
daylevel("n_cand_day","그날 진입후보 수(관문+패턴+임박)")
daylevel("n_entered_day","그날 실제 진입 수")

print("\n=== 국면 고정 후 '그날 후보 수' 잔여효과 (상승국면만) ===")
UP=[r for r in R if r["up"]]
bd={}
for r in UP: bd.setdefault(r["scan_date"],[]).append(r)
dv=sorted([(d,g[0]["n_cand_day"],g) for d,g in bd.items()],key=lambda x:x[1])
n=len(dv)
for i in range(3):
    seg=dv[i*n//3:(i+1)*n//3]; g=[x for _,_,gg in seg for x in gg]
    print(f"    {i+1}/3 후보수 {seg[0][1]}~{seg[-1][1]}  거래 {len(g):>3}  승률 {wr(g):>5.1f}%  기대 {ev(g):>+6.2f}%")

print("\n=== 다중검정 요약 ===")
print("  검정한 요인 수: 42 (1차 배치 28 + 2차 배치 14)")
print(f"  p<0.05 인 요인 수(순열): 1 (turnover_eok)  ← 우연 기대치 ≈ {42*0.05:.1f}개")
print(f"  Bonferroni 문턱 0.05/42 = {0.05/42:.4f}")
