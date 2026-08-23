import json, os, statistics, sys
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from canslim_lib import ohlcv_matrix
SCRATCH=os.environ["SCRATCH"]
P=json.load(open(os.path.join(SCRATCH,"panel.json"),encoding="utf-8"))
EV=P["events"]
for e in EV:
    s=ohlcv_matrix.get_series(e["code"]); e["_s"]=s; e["_b"]=s["dates"].index(e["entry_date"])
MAXH=120
def sim(e,target,stop,trail=None):
    s=e["_s"]; b=e["_b"]; pv=e["pivot"]; ep=e["entry_price"]
    n=len(s["closes"]); T=pv*(1+target/100); S=pv*(1-stop/100); peak=None
    for i in range(b,min(n,b+MAXH+1)):
        k=i-b; hi,lo,cl=s["highs"][i],s["lows"][i],s["closes"][i]
        if hi is not None and hi>=T and lo is not None and lo<=S: return (S/ep-1)*100,"amb",k
        if hi is not None and hi>=T: return (T/ep-1)*100,"win",k
        if lo is not None and lo<=S: return (S/ep-1)*100,"loss",k
        if trail:
            peak=cl if peak is None else max(peak,cl); S=max(S,peak*(1-trail/100))
    i=min(n,b+MAXH+1)-1
    return (s["closes"][i]/ep-1)*100,"open",i-b
H1=[e for e in EV if e["entry_date"]<"2026-03-25"]; H2=[e for e in EV if e["entry_date"]>="2026-03-25"]
def mm(S,**kw): 
    rs=[sim(e,**kw) for e in S]; return statistics.mean(r[0] for r in rs), rs
print("트레일 폭 촘촘 스윕 (초기 -10% 손절 병행, 익절 없음)")
print(f"{'트레일':>6s} {'전체':>8s} {'전반':>8s} {'후반':>8s} {'평균보유':>8s} {'미결(120일)':>10s} {'중앙수익':>8s}")
for tr in range(6,31):
    m,rs=mm(EV,target=10000,stop=10,trail=tr); m1,_=mm(H1,target=10000,stop=10,trail=tr); m2,_=mm(H2,target=10000,stop=10,trail=tr)
    op=sum(1 for r in rs if r[1]=="open"); dh=statistics.mean(r[2] for r in rs); med=statistics.median(r[0] for r in rs)
    print(f"  -{tr:2d}% {m:+8.2f}% {m1:+8.2f}% {m2:+8.2f}% {dh:8.1f} {op:10d} {med:+8.2f}%")
print()
print("현행(+20/-10) 참고:", f"{mm(EV,target=20,stop=10)[0]:+.2f}% / 전반 {mm(H1,target=20,stop=10)[0]:+.2f}% / 후반 {mm(H2,target=20,stop=10)[0]:+.2f}%")
print()
print("트레일 + 상한익절 병행 (트레일 -12%):")
for tg in (20,30,40,60,80,10000):
    m,rs=mm(EV,target=tg,stop=10,trail=12); m1,_=mm(H1,target=tg,stop=10,trail=12); m2,_=mm(H2,target=tg,stop=10,trail=12)
    print(f"  익절 상한 +{tg if tg<10000 else 999}% : {m:+.2f}% (전반 {m1:+.2f} / 후반 {m2:+.2f})")
