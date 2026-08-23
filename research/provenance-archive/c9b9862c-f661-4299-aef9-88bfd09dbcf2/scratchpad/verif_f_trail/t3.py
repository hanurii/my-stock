import json, random, statistics
rows = json.load(open("rows.json"))
DATES = sorted({r["entry"] for r in rows})
COST = 0.34  # %p 왕복(수수료0.14+세금0.2)

def slot_sim(rows, mode, slots=5, seed=0, pos=1000.0, compound=False, cost=COST):
    """pos: 만원. compound=True 면 자본/slots."""
    rnd = random.Random(seed)
    kind = "tr" if mode=="trail" else "base"
    byd = {}
    for r in rows: byd.setdefault(r["entry"], []).append(r)
    equity = pos*slots
    busy = []   # (exit_date, )
    taken = []
    for D in DATES:
        busy = [b for b in busy if b < D]     # 청산일 < 오늘이면 슬롯 반환
        cand = byd.get(D, [])[:]
        rnd.shuffle(cand)
        for r in cand:
            if len(busy) >= slots: break
            ed = r[kind+"_date"]; ret = r[kind+"_ret"] - cost
            size = (equity/slots) if compound else pos
            pnl = size*ret/100
            equity += pnl
            busy.append(ed)
            taken.append((r, ret, pnl))
    return equity - pos*slots, taken

def run(seedlist, compound=False, slots=5):
    res=[]
    for s in seedlist:
        pb,tb = slot_sim(rows,"base",slots=slots,seed=s,compound=compound)
        pt,tt = slot_sim(rows,"trail",slots=slots,seed=s,compound=compound)
        res.append((pb,pt,len(tb),len(tt)))
    b=[x[0] for x in res]; t=[x[1] for x in res]
    d=[x[1]-x[0] for x in res]
    print(f"  슬롯{slots} {'복리' if compound else '정액1,000만'}  현행 중앙 {statistics.median(b):,.0f}만  추적 중앙 {statistics.median(t):,.0f}만")
    print(f"     차이 중앙 {statistics.median(d):+,.0f}만  평균 {statistics.mean(d):+,.0f}만  추적이 이긴 비율 {sum(1 for x in d if x>0)/len(d)*100:.0f}%  차이 5%분위 {sorted(d)[int(.05*len(d))]:+,.0f}만  95%분위 {sorted(d)[int(.95*len(d))]:+,.0f}만")
    print(f"     매매수 현행 중앙 {statistics.median([x[2] for x in res]):.0f} / 추적 {statistics.median([x[3] for x in res]):.0f}")
    return res

seeds=list(range(500))
print("[슬롯 제약 포트폴리오, 비용 0.34%p 반영]")
run(seeds, compound=False, slots=5)
run(seeds, compound=True, slots=5)
run(seeds, compound=False, slots=3)
run(seeds, compound=False, slots=10)
