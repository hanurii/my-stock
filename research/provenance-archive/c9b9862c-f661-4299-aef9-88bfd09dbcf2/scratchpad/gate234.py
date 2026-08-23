# -*- coding: utf-8 -*-
"""2·3·4차 관문: 월 층화 · 종목 블록(클러스터 부트스트랩) · 전후반 분할."""
import json, sys, random
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCR=Path(sys.argv[0]).parent
rows=json.loads((SCR/"events_feat3.json").read_text(encoding="utf-8"))
R=[r for r in rows if r["result"] in ("win","loss")]
def wr(g): return sum(1 for x in g if x["result"]=="win")/len(g)*100 if g else float('nan')
def ev(g):
    v=[x["gain_at_resolve_pct"] for x in g if x.get("gain_at_resolve_pct") is not None]
    return sum(v)/len(v) if v else float('nan')

def daysplit(rows_,key):
    byday=defaultdict(list)
    for r in rows_:
        if r.get(key) is not None: byday[r["scan_date"]].append(r)
    days=[]
    for d,g in byday.items():
        if len(g)<2: continue
        v=sorted(x[key] for x in g)
        med=v[len(v)//2] if len(v)%2 else (v[len(v)//2-1]+v[len(v)//2])/2
        hi=[x for x in g if x[key]>med]; lo=[x for x in g if x[key]<=med]
        if not hi or not lo:
            hi=[x for x in g if x[key]>=med]; lo=[x for x in g if x[key]<med]
        if hi and lo: days.append((d,hi,lo))
    return days

KEY="turnover_eok"
days=daysplit(R,KEY)
H=[x for _,h,_ in days for x in h]; L=[x for _,_,l in days for x in l]
print(f"[1차 재확인] 같은날 거래대금 상/하: {wr(H):.1f}% (n={len(H)}) vs {wr(L):.1f}% (n={len(L)})  차 {wr(H)-wr(L):+.2f}%p")
print(f"           기대값 {ev(H):+.2f}% vs {ev(L):+.2f}%")

print("\n=== 2차: 월 층화 (같은날 분할을 월별로 집계) ===")
bym=defaultdict(lambda:[[],[]])
for _,h,l in days:
    for x in h: bym[x["month"]][0].append(x)
    for x in l: bym[x["month"]][1].append(x)
pos=neg=0
for m in sorted(bym):
    h,l=bym[m]
    if not h or not l: continue
    d=wr(h)-wr(l)
    pos+= d>0; neg+= d<0
    print(f"  {m}  상 {wr(h):>5.1f}%(n={len(h):>3})  하 {wr(l):>5.1f}%(n={len(l):>3})  차 {d:>+6.1f}%p")
print(f"  → 월 {pos}개 양(+) / {neg}개 음(-)")

print("\n=== 4차: 전후반 (2026-03-25 기준) ===")
for lbl,f in [("전반(~2026-03-24)",lambda x:x["entry_date"]<"2026-03-25"),
              ("후반(2026-03-25~)",lambda x:x["entry_date"]>="2026-03-25")]:
    sub=[r for r in R if f(r)]
    dd=daysplit(sub,KEY)
    h=[x for _,a,_ in dd for x in a]; l=[x for _,_,b in dd for x in b]
    print(f"  {lbl}: 상 {wr(h):>5.1f}%(n={len(h):>3}) 하 {wr(l):>5.1f}%(n={len(l):>3}) 차 {wr(h)-wr(l):>+6.1f}%p  | 날수 {len(dd)}")

print("\n=== 3차: 종목 블록 클러스터 부트스트랩 (2000회, 종목 단위 재표집) ===")
bycode=defaultdict(list)
for _,h,l in days:
    for x in h: bycode[x["code"]].append(("H",x))
    for x in l: bycode[x["code"]].append(("L",x))
codes=list(bycode); rnd=random.Random(3)
obs=wr(H)-wr(L); diffs=[]
for _ in range(2000):
    hh=[];ll=[]
    for _ in codes:
        c=rnd.choice(codes)
        for side,x in bycode[c]:
            (hh if side=="H" else ll).append(x)
    if hh and ll: diffs.append(wr(hh)-wr(ll))
diffs.sort()
lo95=diffs[int(0.025*len(diffs))]; hi95=diffs[int(0.975*len(diffs))]
frac_le0=sum(1 for d in diffs if d<=0)/len(diffs)
print(f"  관측 {obs:+.2f}%p · 95% 구간 [{lo95:+.2f}, {hi95:+.2f}] · P(차<=0)={frac_le0:.3f} (양측≈{min(1,2*frac_le0):.3f})")

print("\n=== 3차-b: 종목 블록 순열검정 (종목 통째로 승패 라벨 섞기, 3000회) ===")
# 종목별 결과 벡터를 통째로 다른 종목 자리에 배치 → 종목 내 상관 보존
allev=[x for _,h,l in days for x in h]+[x for _,_,l in days for x in l]
lab={id(x):("H" if any(x is y for _,h,_ in days for y in h) else "L") for x in allev}
codelist=sorted({x["code"] for x in allev})
res_by_code={c:[x["result"] for x in allev if x["code"]==c] for c in codelist}
side_by_code={c:[lab[id(x)] for x in allev if x["code"]==c] for c in codelist}
rnd2=random.Random(5); cnt=0
for _ in range(3000):
    donors=codelist[:]; rnd2.shuffle(donors)
    hw=hn=lw=ln=0
    for c,d in zip(codelist,donors):
        sides=side_by_code[c]; results=res_by_code[d]
        for i,s in enumerate(sides):
            rr=results[i%len(results)]
            if s=="H": hn+=1; hw+= rr=="win"
            else: ln+=1; lw+= rr=="win"
    st=(hw/hn-lw/ln)*100 if hn and ln else 0
    if abs(st)>=abs(obs)-1e-9: cnt+=1
print(f"  p = {(cnt+1)/3001:.4f}")
