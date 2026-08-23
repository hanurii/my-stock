import json, os, statistics, random, sys
from collections import defaultdict
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
from canslim_lib import ohlcv_matrix
SCRATCH=os.environ["SCRATCH"]
P=json.load(open(os.path.join(SCRATCH,"panel.json"),encoding="utf-8"))
RULES=P["rules"]; EV=P["events"]
for e in EV:
    s=ohlcv_matrix.get_series(e["code"]); e["_s"]=s; e["_b"]=s["dates"].index(e["entry_date"])
    e["_fire"]={}   # rule -> first fire k (any k, up to end of data window we computed = K)
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
def sim(e, target=20.0, stop=10.0, sell_rule=None, tighten=None, trail=None, time_stop=None):
    s=e["_s"]; b=e["_b"]; pv=e["pivot"]; ep=e["entry_price"]
    n=len(s["closes"]); T=pv*(1+target/100); S0=pv*(1-stop/100)
    fire=e["_fire"].get(sell_rule) if sell_rule else None
    fire_t=e["_fire"].get(tighten) if tighten else None
    S=S0; peak=None
    for i in range(b, min(n, b+MAXH+1)):
        k=i-b
        hi,lo,cl=s["highs"][i],s["lows"][i],s["closes"][i]
        if hi is not None and hi>=T and lo is not None and lo<=S: return (S/ep-1)*100, "amb", k
        if hi is not None and hi>=T: return (T/ep-1)*100, "win", k
        if lo is not None and lo<=S: return (S/ep-1)*100, "loss", k
        # 종가 시점 판단(다음날부터 반영)
        if fire is not None and k>=fire and k>=1: return (cl/ep-1)*100, "rulesell", k
        if time_stop and k>=time_stop[0] and (cl/ep-1)*100 < time_stop[1]: return (cl/ep-1)*100,"timestop",k
        if fire_t is not None and k>=fire_t: S=max(S, pv*(1-tighten[1]/100))
        if trail:
            peak = cl if peak is None else max(peak, cl)
            S=max(S, peak*(1-trail/100))
    i=min(n,b+MAXH+1)-1
    return (s["closes"][i]/ep-1)*100, "open", i-b

def run(**kw):
    rs=[sim(e,**kw) for e in EV]
    m=statistics.mean(r[0] for r in rs)
    w=sum(1 for r in rs if r[1]=="win")/len(rs)*100
    dh=statistics.mean(r[2] for r in rs)
    gains=[r[0] for r in rs if r[0]>0]; losses=[r[0] for r in rs if r[0]<=0]
    pf = (sum(gains)/abs(sum(losses))) if losses and sum(losses)!=0 else None
    ratio = (statistics.mean(gains)/abs(statistics.mean(losses))) if gains and losses else None
    return m,w,dh,pf,ratio,rs

random.seed(3)
codes=sorted(set(e["code"] for e in EV)); bycode=defaultdict(list)
for e in EV: bycode[e["code"]].append(e)
def boot_ci(rs_a, rs_b, reps=2000):
    """두 전략의 건당 평균 차이에 대한 종목 블록 부트 CI"""
    da={id(e): rs_a[i][0]-rs_b[i][0] for i,e in enumerate(EV)}
    out=[]
    for _ in range(reps):
        v=[]
        for _ in range(len(codes)):
            for e in bycode[random.choice(codes)]: v.append(da[id(e)])
        out.append(statistics.mean(v))
    out.sort(); return out[int(.025*len(out))], out[int(.975*len(out))]

print("="*100); print("[I] 청산 규칙 후보 비교 (614건, 최대 120거래일 보유)"); print("="*100)
base=run(); print(f"기준  +20%/-10%                      : {base[0]:+.2f}%/건 | +20%도달 {base[1]:.1f}% | 평균보유 {base[2]:.1f}일 | 손익비 {base[4]:.2f} | PF {base[3]:.2f}")
cands=[]
for tg in (15,20,25,30,40,60):
    for st in (7.5,10,12.5,15):
        r=run(target=tg,stop=st); cands.append((f"+{tg}%/-{st}%", r))
for lab,r in cands:
    print(f"  익절/손절 {lab:12s}: {r[0]:+.2f}%/건 | 목표도달 {r[1]:5.1f}% | 보유 {r[2]:5.1f}일 | 손익비 {r[4]:.2f} | PF {r[3]:.2f}")
print()
print("트레일링(종가 고점 대비, 초기 -10% 손절 병행):")
for tr in (8,10,12,15,20,25):
    r=run(target=1000,stop=10,trail=tr)
    print(f"  트레일 -{tr}%            : {r[0]:+.2f}%/건 | 보유 {r[2]:5.1f}일 | 손익비 {r[4]:.2f} | PF {r[3]:.2f}")
print()
print("규칙으로 손절만 조인다(팔지 않고 스톱을 -5%로 당김):")
for r_ in RULES+["ANY5"]:
    r=run(target=20,stop=10,tighten=(r_,5))
    print(f"  {r_:24s}: {r[0]:+.2f}%/건 (기준대비 {r[0]-base[0]:+.2f}%p) | +20%도달 {r[1]:.1f}%")
print()
print("시간 손절(N일까지 +X% 못 넘으면 종가 청산):")
for N,X in ((5,0),(10,0),(10,3),(15,0),(20,0),(20,5)):
    r=run(target=20,stop=10,time_stop=(N,X))
    print(f"  D+{N}에 {X:+d}% 미만이면 청산 : {r[0]:+.2f}%/건 (기준대비 {r[0]-base[0]:+.2f}%p) | +20%도달 {r[1]:.1f}% | 보유 {r[2]:.1f}일")
