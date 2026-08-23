import json, os
from collections import Counter, defaultdict
SCRATCH=os.environ["SCRATCH"]
P=json.load(open(os.path.join(SCRATCH,"panel.json"),encoding="utf-8"))
RULES=P["rules"]; EV=P["events"]
print("events", len(EV), "K=0", sum(1 for e in EV if e["K"]==0))
print("result", Counter(e["result"] for e in EV))
print("agree w/ json result", sum(1 for e in EV if e["result"]==e["json_result"]), "/", len(EV))
import statistics
print("mean K", round(statistics.mean(e["K"] for e in EV),2), "median", statistics.median(e["K"] for e in EV))
print()
for ridx,r in enumerate(RULES):
    ever=0; before=0; onlast=0; ff=[]
    for e in EV:
        f=None
        for dd in e["days"]:
            if dd["st"][ridx]=="violation":
                f=dd["k"]; break
        if f is not None:
            ever+=1
            if f < e["K"]: before+=1; ff.append(f)
            else: onlast+=1
    print(f"{r:26s} ever={ever:4d} ({ever/len(EV)*100:5.1f}%)  fires_before_resolve={before:4d} ({before/len(EV)*100:5.1f}%)  only_on_resolve_day={onlast:3d}  median_first_day={statistics.median(ff) if ff else '-'}")
print()
# any-of-5
ever=0
for e in EV:
    if any(dd["st"][ri]=="violation" for dd in e["days"] for ri in range(5)): ever+=1
print("any of 5 ever fires:", ever, round(ever/len(EV)*100,1),"%")
# status distribution per rule across all day-evals
tot=sum(len(e["days"]) for e in EV)
for ridx,r in enumerate(RULES):
    c=Counter(dd["st"][ridx] for e in EV for dd in e["days"])
    print(f"{r:26s}", dict(c), "viol share", round(c['violation']/tot*100,1))
