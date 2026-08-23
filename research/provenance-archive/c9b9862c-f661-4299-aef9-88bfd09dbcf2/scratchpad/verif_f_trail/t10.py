import json, random, statistics
from collections import defaultdict
rows=json.load(open("oos_lead.json"))
for r in rows: r["d"]=r["t10"]-r["base"]
# 월별 부호
bym=defaultdict(list)
for r in rows: bym[r["entry"][:7]].append(r)
ms=sorted(bym)
pos=sum(1 for m in ms if sum(x["d"] for x in bym[m])/len(bym[m])>0)
print(f"주도주 OOS 4,473건: 월 {len(ms)}개 중 차이 양(+) {pos}개 = {pos/len(ms)*100:.0f}%")
# 분기별
byq=defaultdict(list)
for r in rows:
    y,m=r["entry"][:4],int(r["entry"][5:7]); byq[f"{y}Q{(m-1)//3+1}"].append(r)
print("분기별 차이/건:")
line=[]
for q in sorted(byq):
    v=byq[q]; line.append(f"{q} {sum(x['d'] for x in v)/len(v):+.2f}({len(v)})")
print("  "+"  ".join(line))
# 꼬리
d=[r["d"] for r in rows]; n=len(d); tot=sum(d); sd=sorted(d,reverse=True)
print(f"\n전체 차이/건 {tot/n:+.3f}%p; 영향 {sum(1 for x in d if abs(x)>1e-9)}건 중 이득 {sum(1 for x in d if x>0)} 손해 {sum(1 for x in d if x<0)}")
for k in (5,10,20,50):
    print(f"  상위{k} 제거 차이/건 {(tot-sum(sd[:k]))/n:+.3f}%p (상위{k}={sum(sd[:k])/tot*100:.0f}%)")
# 슬롯 시뮬
COST=0.34
DATES=sorted({r["entry"] for r in rows})
byd=defaultdict(list)
for r in rows: byd[r["entry"]].append(r)
def slot(mode, seed, slots=5, pos=1000.0, sub=None):
    rnd=random.Random(seed); rk="base" if mode=="base" else "t10"; dk="bd" if mode=="base" else "d10"
    eq=0.0; busy=[]; cnt=0
    for D in DATES:
        if sub and not sub(D): continue
        busy=[b for b in busy if b>D]
        cand=byd[D][:]; rnd.shuffle(cand)
        for r in cand:
            if len(busy)>=slots: break
            eq += pos*(r[rk]-COST)/100; cnt+=1
            # 청산일 근사: 진입일 인덱스 + days
            busy.append(D+"#"+str(r[dk]))
    return eq,cnt
# 정확한 청산일 필요 → 진입일 인덱스 기반으로 재구성
ALLD=sorted({r["entry"] for r in rows})
IDX={d:i for i,d in enumerate(ALLD)}
def slot2(mode, seed, slots=5, pos=1000.0, y=None):
    rnd=random.Random(seed); rk="base" if mode=="base" else "t10"; dk="bd" if mode=="base" else "d10"
    eq=0.0; busy=[]; cnt=0
    for di,D in enumerate(ALLD):
        if y and D[:4]!=y: continue
        busy=[b for b in busy if b>di]
        cand=byd[D][:]; rnd.shuffle(cand)
        for r in cand:
            if len(busy)>=slots: break
            eq+=pos*(r[rk]-COST)/100; cnt+=1
            busy.append(di+max(1,r[dk]))
    return eq,cnt
print("\n[슬롯5 정액 1,000만 · 비용 0.34%p · 200회 무작위 순서]  (단위 만원)")
print(f"{'연도':<8}{'현행중앙':>10}{'추적중앙':>10}{'차이중앙':>10}{'추적승률':>10}{'매매수':>8}")
for y in ["2022","2023","2024","2025","2026",None]:
    b=[];t=[];nb=[]
    for s in range(200):
        pb,cb=slot2("base",s,y=y); pt,ct=slot2("trail",s,y=y)
        b.append(pb);t.append(pt);nb.append(cb)
    d=[y2-x for x,y2 in zip(b,t)]
    lab=y or "전체"
    print(f"{lab:<8}{statistics.median(b):>+10,.0f}{statistics.median(t):>+10,.0f}{statistics.median(d):>+10,.0f}{sum(1 for x in d if x>0)/2:>9.0f}%{statistics.median(nb):>8.0f}")
