import sys, random, statistics as s
sys.path.insert(0, "C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/taskB_stack")
from blib import *
random.seed(20260822)
d, ev = bload()
R = resolved(ev)
multi=[e for e in R if e.get("to_pct") is not None]
print("결착 %d건 / 같은날 2건이상 %d건" % (len(R), len(multi)))

print("\n[A] 같은날 거래대금 순위 백분위별 (국면 오염 제거)")
for lo,hi,lab in [(0,0.25,"하위25%"),(0.25,0.5,"25~50%"),(0.5,0.75,"50~75%"),(0.75,1.01,"상위25%")]:
    sub=[e for e in multi if lo<=e["to_pct"]<hi]
    w,n=wr(sub); r,_=realized(sub)
    print(f"   {lab:8s} n={n:3d}  승률 {w:5.1f}%  실현평균 {r:+.2f}%")

print("\n[B] 날짜내 결과 셔플 순열검정 5000회 (승자의 평균 거래대금순위, 귀무=0.5)")
g=defaultdict(list)
for e in multi: g[e["scan_date"]].append(e)
groups=list(g.values())
ws=[e["to_pct"] for e in multi if e["result"]=="win"]
obs=sum(ws)/len(ws)
cnt=0; N=5000
for _ in range(N):
    tot=0.0;k=0
    for lst in groups:
        res=[e["result"] for e in lst]; random.shuffle(res)
        for e,rr in zip(lst,res):
            if rr=="win": tot+=e["to_pct"]; k+=1
    if tot/k>=obs: cnt+=1
print(f"   관측 {obs:.3f}  단측 p={(cnt+1)/(N+1):.4f}")

print("\n[C] 전후반 분할 (2026-03-25)")
for lab,sel in [("전반",lambda e:e["scan_date"]<"2026-03-25"),("후반",lambda e:e["scan_date"]>="2026-03-25")]:
    sub=[e for e in multi if sel(e)]
    hi=[e for e in sub if e["to_pct"]>=0.5]; lo=[e for e in sub if e["to_pct"]<0.5]
    print(f"   {lab} 같은날상위절반 {wr(hi)[0]:.1f}%(n{wr(hi)[1]}) vs 하위절반 {wr(lo)[0]:.1f}%(n{wr(lo)[1]})  차 {wr(hi)[0]-wr(lo)[0]:+.1f}%p")
    sub2=[e for e in R if sel(e)]
    a=[e for e in sub2 if e["turnover_eok"]>=30]; b=[e for e in sub2 if e["turnover_eok"]<30]
    print(f"        절대컷 >=30억 {wr(a)[0]:.1f}%(n{wr(a)[1]}) vs <30억 {wr(b)[0]:.1f}%(n{wr(b)[1]})")

print("\n[D] 월 층화 (상위절반 - 하위절반)")
bym=defaultdict(list)
for e in multi: bym[e["month"]].append(e)
diffs=[]
for m in sorted(bym):
    sub=bym[m]; hi=[e for e in sub if e["to_pct"]>=0.5]; lo=[e for e in sub if e["to_pct"]<0.5]
    if len(hi)<5 or len(lo)<5:
        print(f"   {m}: 표본부족 hi{len(hi)}/lo{len(lo)}"); continue
    dw=wr(hi)[0]-wr(lo)[0]; diffs.append(dw)
    print(f"   {m}: {wr(hi)[0]:5.1f}%(n{len(hi)}) - {wr(lo)[0]:5.1f}%(n{len(lo)}) = {dw:+6.1f}%p")
print(f"   월 부호 양 {sum(1 for x in diffs if x>0)} / 음 {sum(1 for x in diffs if x<0)}  중앙 {s.median(diffs):+.1f}%p  p(sign)={binom_p_two(sum(1 for x in diffs if x>0), sum(1 for x in diffs if x!=0)):.3f}")

print("\n[E] 종목 블록 순열검정 3000회 (상위절반-하위절반 승률차)")
hi=[e for e in multi if e["to_pct"]>=0.5]; lo=[e for e in multi if e["to_pct"]<0.5]
obs_d=wr(hi)[0]-wr(lo)[0]
bycode=defaultdict(list)
for e in multi: bycode[e["code"]].append(e)
codes=list(bycode)
cnt=0;N=3000
for _ in range(N):
    blocks=[[x["result"] for x in bycode[c]] for c in codes]
    random.shuffle(blocks)
    hw=hl=lw=ll=0
    for c,blk in zip(codes,blocks):
        for i,e in enumerate(bycode[c]):
            rr=blk[i%len(blk)]
            if e["to_pct"]>=0.5: hw+= rr=="win"; hl+= rr=="loss"
            else: lw+= rr=="win"; ll+= rr=="loss"
        
    cnt += (100*hw/(hw+hl)-100*lw/(lw+ll)) >= obs_d
print(f"   관측 {obs_d:+.1f}%p  단측 p={(cnt+1)/(N+1):.4f}")

print("\n[F] 절대 거래대금 구간표 (참고, 국면오염 가능)")
for lo_,hi_,lab in [(5,20,"5~20억"),(20,50,"20~50억"),(50,150,"50~150억"),(150,500,"150~500억"),(500,1e9,"500억+")]:
    sub=[e for e in R if lo_<=e["turnover_eok"]<hi_]
    if not sub: continue
    w,n=wr(sub); r,_=realized(sub)
    print(f"   {lab:10s} n={n:3d} 승률 {w:5.1f}% 실현 {r:+.2f}%")
