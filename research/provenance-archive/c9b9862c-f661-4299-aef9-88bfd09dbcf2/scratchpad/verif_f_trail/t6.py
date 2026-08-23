import json, random, statistics
from collections import defaultdict, Counter
COST=0.34
def slot_sim(rows, mode, slots=5, seed=0, pos=1000.0, compound=False, cost=COST):
    rnd=random.Random(seed); kind="tr" if mode=="trail" else "base"
    DATES=sorted({r["entry"] for r in rows})
    byd=defaultdict(list)
    for r in rows: byd[r["entry"]].append(r)
    equity=pos*slots; busy=[]; taken=[]
    for D in DATES:
        busy=[b for b in busy if b>=D]
        cand=byd[D][:]; rnd.shuffle(cand)
        for r in cand:
            if len(busy)>=slots: break
            size=(equity/slots) if compound else pos
            ret=r[kind+"_ret"]-cost
            equity+=size*ret/100
            busy.append(r[kind+"_date"]); taken.append(r)
    return equity-pos*slots, taken

for mh in (40,60):
    rows=json.load(open(f"rows_mh{mh}.json"))
    print(f"\n=== maxhold {mh}일 ===")
    for compound in (False,True):
        db=[];dt_=[];nb=[];nt=[]
        for s in range(300):
            pb,tb=slot_sim(rows,"base",seed=s,compound=compound)
            pt,tt=slot_sim(rows,"trail",seed=s,compound=compound)
            db.append(pb);dt_.append(pt);nb.append(len(tb));nt.append(len(tt))
        d=[y-x for x,y in zip(db,dt_)]
        lab="복리" if compound else "정액1,000만"
        print(f"  슬롯5 {lab}: 현행중앙 {statistics.median(db):+,.0f}만 / 추적중앙 {statistics.median(dt_):+,.0f}만 / 차이중앙 {statistics.median(d):+,.0f}만 / 추적승 {sum(1 for x in d if x>0)/3:.0f}%")
        print(f"      매매수 {statistics.median(nb):.0f}→{statistics.median(nt):.0f}, 현행흑자비율 {sum(1 for x in db if x>0)/3:.0f}% 추적흑자비율 {sum(1 for x in dt_ if x>0)/3:.0f}%")
    # 채택률 월별
    tk=Counter()
    for s in range(20):
        _,tb=slot_sim(rows,"base",seed=s)
        for r in tb: tk[r["entry"][:7]]+=1
    allm=Counter(r["entry"][:7] for r in rows)
    print("  월별 채택률:", " ".join(f"{m}:{tk[m]/20/allm[m]*100:.0f}%" for m in sorted(allm)))
