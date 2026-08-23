import json, os, statistics, random, sys
from collections import defaultdict
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from canslim_lib import ohlcv_matrix
SCRATCH=os.environ["SCRATCH"]
P=json.load(open(os.path.join(SCRATCH,"panel.json"),encoding="utf-8"))
RULES=P["rules"]; EV=P["events"]
for e in EV:
    s=ohlcv_matrix.get_series(e["code"]); e["_s"]=s; e["_b"]=s["dates"].index(e["entry_date"])
    e["_fire"]={}
    for ri,r in enumerate(RULES):
        f=None
        for dd in e["days"]:
            if dd["st"][ri]=="violation": f=dd["k"]; break
        e["_fire"][r]=f
    f=None
    for dd in e["days"]:
        if any(st=="violation" for st in dd["st"]): f=dd["k"]; break
    e["_fire"]["ANY5"]=f
MAXH=120
def sim(e, target=20.0, stop=10.0, sell_rule=None, tighten=None, trail=None):
    s=e["_s"]; b=e["_b"]; pv=e["pivot"]; ep=e["entry_price"]
    n=len(s["closes"]); T=pv*(1+target/100); S=pv*(1-stop/100)
    fire=e["_fire"].get(sell_rule) if sell_rule else None
    fire_t=e["_fire"].get(tighten[0]) if tighten else None
    peak=None
    for i in range(b, min(n, b+MAXH+1)):
        k=i-b; hi,lo,cl=s["highs"][i],s["lows"][i],s["closes"][i]
        if hi is not None and hi>=T and lo is not None and lo<=S: return (S/ep-1)*100,"amb",k
        if hi is not None and hi>=T: return (T/ep-1)*100,"win",k
        if lo is not None and lo<=S: return (S/ep-1)*100,"loss",k
        if fire is not None and k>=fire and k>=1: return (cl/ep-1)*100,"rulesell",k
        if fire_t is not None and k>=fire_t: S=max(S, pv*(1-tighten[1]/100))
        if trail:
            peak = cl if peak is None else max(peak,cl)
            S=max(S, peak*(1-trail/100))
    i=min(n,b+MAXH+1)-1
    return (s["closes"][i]/ep-1)*100,"open",i-b
def agg(S,**kw):
    rs=[sim(e,**kw) for e in S]
    m=statistics.mean(r[0] for r in rs)
    g=[r[0] for r in rs if r[0]>0]; l=[r[0] for r in rs if r[0]<=0]
    return m, (statistics.mean(g)/abs(statistics.mean(l)) if g and l else None), statistics.mean(r[2] for r in rs), len(g)/len(rs)*100, rs
H1=[e for e in EV if e["entry_date"]<"2026-03-25"]; H2=[e for e in EV if e["entry_date"]>="2026-03-25"]
print("="*100); print("[J] 규칙으로 '팔지 말고 손절만 -5%로 당기기' (버그 수정판)"); print("="*100)
b0=agg(EV)[0]
for r_ in RULES+["ANY5"]:
    m,ratio,dh,wr,_=agg(EV,target=20,stop=10,tighten=(r_,5))
    print(f"  {r_:24s}: {m:+.2f}%/건 (기준 {b0:+.2f} 대비 {m-b0:+.2f}%p) | 평균보유 {dh:.1f}일")
print()
print("="*100); print("[K] 유력 후보 전후반 분할 (2026-03-25)"); print("="*100)
cand=[("+20/-10 (현행)",dict()),("+25/-12.5",dict(target=25,stop=12.5)),("+30/-10",dict(target=30,stop=10)),
      ("+40/-12.5",dict(target=40,stop=12.5)),("+60/-10",dict(target=60,stop=10)),
      ("트레일-10%",dict(target=1000,stop=10,trail=10)),("트레일-12%",dict(target=1000,stop=10,trail=12)),
      ("트레일-15%",dict(target=1000,stop=10,trail=15)),
      ("ANY5 규칙매도",dict(sell_rule="ANY5")),("close_below_ma 매도",dict(sell_rule="close_below_ma"))]
print(f"{'전략':22s} {'전체':>9s} {'전반':>9s} {'후반':>9s} {'승률':>7s} {'손익비':>7s} {'보유일':>7s}")
rsbase=None
for lab,kw in cand:
    m,ratio,dh,wr,rs=agg(EV,**kw); m1=agg(H1,**kw)[0]; m2=agg(H2,**kw)[0]
    if lab.startswith("+20/-10"): rsbase=rs
    print(f"{lab:22s} {m:+8.2f}% {m1:+8.2f}% {m2:+8.2f}% {wr:6.1f}% {ratio:7.2f} {dh:7.1f}")
print()
print("="*100); print("[L] 최상위 후보 vs 현행 — 종목 블록 부트스트랩 2000회 (건당 평균 차이 95%CI)"); print("="*100)
random.seed(5)
codes=sorted(set(e["code"] for e in EV)); bycode=defaultdict(list)
for i,e in enumerate(EV): bycode[e["code"]].append(i)
for lab,kw in cand[1:]:
    rs=[sim(e,**kw) for e in EV]
    d=[rs[i][0]-rsbase[i][0] for i in range(len(EV))]
    out=[]
    for _ in range(2000):
        v=[]
        for _ in range(len(codes)):
            for i in bycode[random.choice(codes)]: v.append(d[i])
        out.append(sum(v)/len(v))
    out.sort(); lo,hi=out[50],out[1949]
    ps=sum(1 for x in out if x>0)/len(out); p=2*min(ps,1-ps)
    print(f"  {lab:22s} 차 {statistics.mean(d):+.2f}%p  95%CI [{lo:+.2f},{hi:+.2f}]  p={p:.3f}")
