import json, random, statistics
from collections import defaultdict
rows = json.load(open("rows.json"))
for r in rows: r["d"]=r["tr_ret"]-r["base_ret"]; r["m"]=r["entry"][:7]
n=len(rows); obs=sum(r["d"] for r in rows)/n
random.seed(7)
def boot(blocks, B=4000):
    keys=list(blocks); out=[]
    for _ in range(B):
        s=0.0; c=0
        for _ in range(len(keys)):
            k=random.choice(keys); v=blocks[k]
            s+=sum(x["d"] for x in v); c+=len(v)
        out.append(s/c)
    out.sort()
    return out
def rep(name, out):
    lo,hi=out[int(.025*len(out))], out[int(.975*len(out))]
    p=sum(1 for x in out if x<=0)/len(out)
    print(f"  {name:<22} 평균 {statistics.mean(out):+.3f}  95%CI [{lo:+.3f}, {hi:+.3f}]  P(≤0)={p:.4f}")

byc=defaultdict(list)
for r in rows: byc[r["code"]].append(r)
byw=defaultdict(list)
for r in rows:
    import datetime as dt
    y,m,dd=map(int,r["entry"].split("-")); iso=dt.date(y,m,dd).isocalendar()
    byw[(iso[0],iso[1])].append(r)
bym=defaultdict(list)
for r in rows: bym[r["m"]].append(r)
byd=defaultdict(list)
for r in rows: byd[r["entry"]].append(r)

print(f"관측 차이/건 = {obs:+.3f}%p   (종목 {len(byc)}, 진입일 {len(byd)}, 주 {len(byw)}, 월 {len(bym)})")
print("\n[블록 부트스트랩 4000회]")
rep("종목 블록", boot(byc))
rep("진입일 블록", boot(byd))
rep("진입주(ISO) 블록", boot(byw))
rep("진입월 블록", boot(bym))
