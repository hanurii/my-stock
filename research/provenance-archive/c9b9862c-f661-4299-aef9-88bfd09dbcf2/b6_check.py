import sys, random, statistics as s
sys.path.insert(0,"C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/taskB_stack")
from blib import *
random.seed(1)
d, ev = bload()
R=resolved(ev)
multi=[e for e in R if e.get("to_pct") is not None]

print("[1] 그날 후보 수별로 효과가 유지되나 (소수 후보일의 착시 배제)")
for lo,hi,lab in [(2,3,"2~3건인 날"),(4,6,"4~6건"),(7,100,"7건 이상")]:
    sub=[e for e in multi if lo<=e["day_n"]<=hi]
    a=[e for e in sub if e["to_pct"]>=0.75]; b=[e for e in sub if e["to_pct"]<0.75]
    if not a or not b: continue
    print(f"   {lab:10s} 상위25% {wr(a)[0]:5.1f}%(n{wr(a)[1]:3d}) vs 나머지 {wr(b)[0]:5.1f}%(n{wr(b)[1]:3d})  차 {wr(a)[0]-wr(b)[0]:+5.1f}%p")

print("\n[2] 절대 거래대금 층 안에서 '상대 순위'가 여전히 갈리나 (진짜 상대신호인지)")
for lo,hi,lab in [(5,50,"5~50억"),(50,200,"50~200억"),(200,800,"200~800억"),(800,1e9,"800억+")]:
    sub=[e for e in multi if lo<=e["turnover_eok"]<hi]
    a=[e for e in sub if e["to_pct"]>=0.5]; b=[e for e in sub if e["to_pct"]<0.5]
    if len(a)<10 or len(b)<10:
        print(f"   {lab:10s} 표본부족 (상위{len(a)}/하위{len(b)})"); continue
    print(f"   {lab:10s} 그날상위절반 {wr(a)[0]:5.1f}%(n{wr(a)[1]:3d}) vs 하위절반 {wr(b)[0]:5.1f}%(n{wr(b)[1]:3d})  차 {wr(a)[0]-wr(b)[0]:+5.1f}%p")

print("\n[3] 그날 75백분위 거래대금 임계값의 분포 (절대규칙으로 대체 가능한가)")
byday=defaultdict(list)
for e in ev: byday[e["scan_date"]].append(e["turnover_eok"])
th=[]
for dte,l in byday.items():
    if len(l)<4: continue
    l=sorted(l); th.append(l[int(0.75*(len(l)-1))])
th.sort()
print(f"   n={len(th)}일  중앙 {s.median(th):.0f}억  10%분위 {th[int(.1*len(th))]:.0f}억  90%분위 {th[int(.9*len(th))]:.0f}억  최소 {th[0]:.0f} 최대 {th[-1]:.0f}")

print("\n[4] 상위25% 종목 쏠림 확인 (몇 종목이 결과를 끌고 가나)")
top=[e for e in multi if e["to_pct"]>=0.75]
c=defaultdict(lambda:[0,0])
for e in top:
    c[e["name"]][0]+= e["result"]=="win"; c[e["name"]][1]+=1
srt=sorted(c.items(), key=lambda kv:-kv[1][1])[:12]
print("   최다 등장 종목:", ", ".join(f"{k}({v[0]}/{v[1]})" for k,v in srt))
print(f"   고유 종목 수 {len(c)} / 거래 {len(top)}")
# 종목 1개씩 빼며 최악 케이스
base=wr(top)[0]
worst=None
for name in c:
    sub=[e for e in top if e["name"]!=name]
    w=wr(sub)[0]
    if worst is None or w<worst[1]: worst=(name,w)
print(f"   상위25% 전체 승률 {base:.1f}% / 가장 크게 기여한 종목 1개 제거시 {worst[1]:.1f}% ({worst[0]})")

print("\n[5] 상승국면 안에서만 같은날 순열검정 (국면 제거 후에도 남나)")
up=[e for e in multi if e["regime_up"]]
g=defaultdict(list)
for e in up: g[e["scan_date"]].append(e)
groups=[v for v in g.values() if len(v)>=2]
flat=[e for v in groups for e in v]
ws=[e["to_pct"] for e in flat if e["result"]=="win"]
obs=sum(ws)/len(ws); cnt=0;N=5000
for _ in range(N):
    tot=0.0;k=0
    for lst in groups:
        rr=[e["result"] for e in lst]; random.shuffle(rr)
        for e,r_ in zip(lst,rr):
            if r_=="win": tot+=e["to_pct"]; k+=1
    if tot/k>=obs: cnt+=1
print(f"   상승국면 결착 {len(flat)}건, 관측 {obs:.3f} vs 0.5, 단측 p={(cnt+1)/(N+1):.4f}")

print("\n[6] 다중검정 보정 참고")
print("   1차 관문에서 실제로 훑은 컷: 패턴2·시장1·RS5·거래대금6·가격대6·피벗초과5·갭업3·ATR4 = 32개 절대컷 + 순위검정 15개 = 47개")
print("   거래대금 계열 최선 p=0.0042(날짜셔플). Bonferroni 47개 → 0.20 (유의 아님)")
print("   요인가족 8개 기준 보정 → 0.034 (경계적 유의)")
