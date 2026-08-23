import json, os, statistics
from collections import defaultdict
SCRATCH=os.environ["SCRATCH"]
P=json.load(open(os.path.join(SCRATCH,"panel.json"),encoding="utf-8"))
RULES=P["rules"]; EV=P["events"]
for e in EV:
    e["ff"]={}; e["retk"]={dd["k"]: dd["ret_close"] for dd in e["days"]}
    for ri,r in enumerate(RULES):
        f=None
        for dd in e["days"]:
            if dd["st"][ri]=="violation": f=dd["k"]; break
        e["ff"][r]=f
    f=None
    for dd in e["days"]:
        if any(st=="violation" for st in dd["st"]): f=dd["k"]; break
    e["ff"]["ANY5"]=f
ALL=RULES+["ANY5"]
print("[M] 보유기간이 길어지면 결국 다 뜨나? (K=결착까지 거래일)")
buckets=[(1,2),(3,5),(6,10),(11,20),(21,999)]
print(f"{'규칙':24s}"+"".join(f"{f'K{a}-{b}':>10s}" for a,b in buckets))
for r in ALL:
    row=""
    for a,b in buckets:
        S=[e for e in EV if a<=e["K"]<=b]
        f=sum(1 for e in S if e["ff"][r] is not None)
        row+=f"{f/len(S)*100:9.0f}%" if S else "        -"
    print(f"{r:24s}{row}")
print()
print("[N] 규칙별 핵심 수치 요약")
for r in ALL:
    A=[e for e in EV if e["ff"][r] is not None and e["ff"][r]<e["K"]]
    B=[e for e in EV if not(e["ff"][r] is not None and e["ff"][r]<e["K"])]
    if not A: continue
    wa=sum(1 for e in A if e["result"]=="win")/len(A)*100
    la=sum(1 for e in A if e["result"] in ("loss","ambiguous"))/len(A)*100
    wb=sum(1 for e in B if e["result"]=="win")/len(B)*100
    lb=sum(1 for e in B if e["result"] in ("loss","ambiguous"))/len(B)*100
    sold=statistics.mean(e["retk"][e["ff"][r]] for e in A)
    print(f"■ {r}")
    print(f"   점등 {len(A)}건({len(A)/614*100:.1f}%) · 첫점등 중앙 D+{int(statistics.median(e['ff'][r] for e in A))}일")
    print(f"   점등 후: +20%도달 {wa:.1f}% / -10%도달 {la:.1f}% / 그날 청산 수익률 {sold:+.2f}%")
    print(f"   미점등 : +20%도달 {wb:.1f}% / -10%도달 {lb:.1f}%")
