import json, random, statistics
from collections import defaultdict, Counter
exec(open("t3.py",encoding="utf-8").read().split("def run(")[0])
allm=Counter(r["entry"][:7] for r in rows)
tk=defaultdict(Counter)
for s in range(30):
    pb,tb = slot_sim(rows,"base",slots=5,seed=s)
    for r,_,_ in tb: tk[r["entry"][:7]][r["base_kind"]]+=1
print("월  전체건수  채택(30회평균)  채택률  채택승률")
for m in sorted(allm):
    c=tk[m]; tot=sum(c.values())/30
    wr = c["target"]/max(1,sum(c.values()))*100
    print(f"  {m}  {allm[m]:4d}   {tot:6.1f}   {tot/allm[m]*100:5.1f}%   {wr:5.1f}%")
