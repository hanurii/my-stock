import json, random, statistics
from collections import defaultdict
# t13 이 rows 를 저장 안 했으므로 재사용 위해 다시 계산하지 않고, t12 의 oos_piv.json + tight 없는 버전 사용
rows=json.load(open("oos_piv.json"))
byy=defaultdict(list)
for r in rows: byy[r["entry"][:4]].append(r["tr"]-r["base"])
random.seed(3)
d=[r["tr"]-r["base"] for r in rows]; n=len(d)
byc=defaultdict(list)
for r in rows: byc[r["code"]].append(r["tr"]-r["base"])
bym=defaultdict(list)
for r in rows: bym[r["entry"][:7]].append(r["tr"]-r["base"])
def boot(blocks,B=4000):
    ks=list(blocks); out=[]
    for _ in range(B):
        s=0;c=0
        for _ in range(len(ks)):
            v=blocks[random.choice(ks)]; s+=sum(v); c+=len(v)
        out.append(s/c)
    out.sort(); return out
for lab,bl in [("종목블록",byc),("월블록",bym)]:
    o=boot(bl)
    print("OOS(피벗진입 6,518건) {}: 평균 {:+.3f} 95%CI [{:+.3f},{:+.3f}] P(<=0)={:.3f}".format(
        lab, statistics.mean(o), o[100], o[3899], sum(1 for x in o if x<=0)/len(o)))
pos=sum(1 for m,v in bym.items() if sum(v)/len(v)>0)
print("월 {}개 중 양(+) {}개 = {:.0f}%".format(len(bym), pos, pos/len(bym)*100))
