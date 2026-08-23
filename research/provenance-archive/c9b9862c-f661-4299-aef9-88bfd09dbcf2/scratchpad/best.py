# -*- coding: utf-8 -*-
import json, sys, random
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MAIN=Path(r"C:\Users\hanul\playground\my-stock"); SCR=Path(sys.argv[0]).parent
rows=json.loads((SCR/"events_feat3.json").read_text(encoding="utf-8"))
rs=json.loads((MAIN/"public/data/market-regime.json").read_text(encoding="utf-8"))["series"]
reg={x["date"]:x["up"] for x in rs}
for r in rows:
    r["up"]=reg.get(r["entry_date"]); r["up_scan"]=reg.get(r["scan_date"])
byday=defaultdict(list)
for r in rows: byday[r["scan_date"]].append(r)
for d,g in byday.items():
    g2=sorted(g,key=lambda x:-x["turnover_eok"])
    for i,x in enumerate(g2): x["tv_pct"]=(i+0.5)/len(g2); x["tv_rank"]=i+1
R=[r for r in rows if r["result"] in ("win","loss")]
def wr(g): return sum(1 for x in g if x["result"]=="win")/len(g)*100 if g else float('nan')
def ev(g):
    v=[x["gain_at_resolve_pct"] for x in g if x.get("gain_at_resolve_pct") is not None]
    return sum(v)/len(v) if v else float('nan')
print("국면 정의 확인:")
for k in ["up","up_scan"]:
    U=[r for r in R if r[k]]; D=[r for r in R if r[k] is False]
    print(f"  {k}: 상승 n={len(U)} {wr(U):.1f}% {ev(U):+.2f}% / 조정 n={len(D)} {wr(D):.1f}% {ev(D):+.2f}%")
print("\n국면지수 추이(월말):")
bym={}
for x in rs: bym[x["date"][:7]]=x
for m in sorted(bym)[-13:]:
    x=bym[m]; print(f"  {m}  지수 {x['index']:>6.1f}  20일선 {x['ma20']:>6.1f}  {'상승' if x['up'] else '조정'}")

print("\n=== 도달 가능한 최고 승률 조합 (사후에 고른 컷임을 명시) ===")
print(f"{'규칙':<46}{'n':>5}{'남는%':>7}{'승률':>7}{'기대값':>8}")
def sh(lbl,g): print(f"{lbl:<46}{len(g):>5}{len(g)/len(R)*100:>6.0f}%{wr(g):>7.1f}{ev(g):>+8.2f}")
sh("무필터(현행)",R)
sh("① 상승국면만",[r for r in R if r["up"]])
sh("② 거래대금 그날 상위절반",[r for r in R if r["tv_pct"]<0.5])
sh("③ 거래대금 그날 상위 1/3",[r for r in R if r["tv_pct"]<1/3])
sh("①+②",[r for r in R if r["up"] and r["tv_pct"]<0.5])
sh("①+③",[r for r in R if r["up"] and r["tv_pct"]<1/3])
sh("①+②+VCP만",[r for r in R if r["up"] and r["tv_pct"]<0.5 and r["pattern"]=="VCP"])
# 탐색적 복합(검증 안 됨): 얕은 베이스 + 피벗 근접
med_bd=sorted(x["base_depth"] for x in R if x.get("base_depth") is not None)[len(R)//2]
med_pp=sorted(x["pct_to_pivot"] for x in R if x.get("pct_to_pivot") is not None)[len(R)//2]
print(f"  (참고: 베이스깊이 중앙 {med_bd:.1f}% · 피벗까지 거리 중앙 {med_pp:.2f}%)")
sh("[탐색] ①+② + 베이스깊이 중앙이하",[r for r in R if r["up"] and r["tv_pct"]<0.5 and (r.get("base_depth") or 99)<=med_bd])
sh("[탐색] ①+② + 피벗거리 중앙이하",[r for r in R if r["up"] and r["tv_pct"]<0.5 and (r.get("pct_to_pivot") or 99)<=med_pp])
sh("[탐색] ①+② + 깊이·거리 둘다 중앙이하",[r for r in R if r["up"] and r["tv_pct"]<0.5 and (r.get("base_depth") or 99)<=med_bd and (r.get("pct_to_pivot") or 99)<=med_pp])
sh("[탐색] ② + 깊이·거리 둘다 중앙이하",[r for r in R if r["tv_pct"]<0.5 and (r.get("base_depth") or 99)<=med_bd and (r.get("pct_to_pivot") or 99)<=med_pp])

print("\n=== 탐색적 복합의 전후반 안정성 ===")
for lbl,f in [("①+②",lambda r: r["up"] and r["tv_pct"]<0.5),
              ("[탐색]②+깊이·거리",lambda r: r["tv_pct"]<0.5 and (r.get("base_depth") or 99)<=med_bd and (r.get("pct_to_pivot") or 99)<=med_pp)]:
    a=[r for r in R if f(r) and r["entry_date"]<"2026-03-25"]; b=[r for r in R if f(r) and r["entry_date"]>="2026-03-25"]
    print(f"  {lbl:<22} 전반 n={len(a):>3} {wr(a):>5.1f}%  후반 n={len(b):>3} {wr(b):>5.1f}%")

print("\n=== 슬롯 5개 현실: 하루 진입 후보가 5개 넘는 날 ===")
cnt=defaultdict(int)
for r in rows: cnt[r["scan_date"]]+=1
over=[d for d,c in cnt.items() if c>5]
print(f"  진입 6건 이상인 날 {len(over)}/{len(cnt)}일 · 그 날들 거래 {sum(cnt[d] for d in over)}/{len(rows)}건")
print("  → 슬롯을 다투는 날이 많다 = '누구를 고를까' 규칙이 실제로 작동할 여지가 있음")
