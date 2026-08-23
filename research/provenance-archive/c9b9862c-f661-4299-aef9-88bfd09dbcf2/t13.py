import pickle, json
from collections import defaultdict
from _oos_lib import build_series
exec(open("t12.py",encoding="utf-8").read().split("SER={}")[0].split("D=pickle")[1].split("\n",1)[1])
D=pickle.load(open("oos_raw_full.pkl","rb")); REC=D["rec"]
SER={}
for code,hist in REC.items():
    S=build_series(hist)
    if S: SER[code]=S
for code,S in SER.items():
    c=S["c"]; S["mom"]=[None]*len(c)
    for i in range(250,len(c)): S["mom"][i]=c[i]/c[i-250]-1
bydate=defaultdict(list)
for code,S in SER.items():
    for i,d in enumerate(S["dates"]):
        if S["mom"][i] is not None: bydate[d].append((S["mom"][i],code))
rank={}
for d,lst in bydate.items():
    lst.sort(); N=len(lst); rank[d]={cd:(j+1)/N*100 for j,(m,cd) in enumerate(lst)}
rows=[]
for code,S in SER.items():
    c,v,t,ds,h,o=S["c"],S["v"],S["t"],S["dates"],S["h"],S["o"]; n=len(c); lastexit=-1
    for i in range(260,n-3):
        if i<=lastexit: continue
        piv=max(h[i-60:i])
        if h[i]<piv: continue
        seg=[x for x in v[i-50:i] if x]
        if len(seg)<30 or v[i]<1.5*(sum(seg)/len(seg)): continue
        tt=[x for x in t[i-50:i] if x]
        if not tt or sum(tt)/len(tt)<5.0: continue
        rs=rank.get(ds[i],{}).get(code)
        if not(rs is not None and rs>=80 and c[i]>ma(c,i,50)>ma(c,i,150)>ma(c,i,200) and ma(c,i,200)>ma(c,i-20,200)): continue
        # 베이스 타이트: 최근 25일 (고-저)/저 <= 25%  (VCP 대용)
        tight=(max(h[i-25:i])/min(S["l"][i-25:i])-1)*100
        E=max(piv,o[i])
        rb,db,_=sim_piv(S,i,E,"base"); rt,dt,_=sim_piv(S,i,E,"trail")
        rows.append(dict(code=code,entry=ds[i],base=rb,tr=rt,rs=rs,tight=tight)); lastexit=i+max(db,dt)
def rep(v,lab):
    if len(v)<50: print("  {:<28} n={:5d}  (표본부족)".format(lab,len(v))); return
    b=sum(x["base"] for x in v)/len(v); t=sum(x["tr"] for x in v)/len(v)
    print("  {:<28} n={:5d}  base {:+6.2f} trail {:+6.2f} delta {:+6.3f}".format(lab,len(v),b,t,t-b))
print("[RS 대역별 — 전체기간]")
for lo,hi in [(80,90),(90,95),(95,101)]: rep([r for r in rows if lo<=r["rs"]<hi], f"RS {lo}~{hi}")
print("[베이스 타이트(25일폭)]")
for lo,hi in [(0,15),(15,25),(25,40),(40,999)]: rep([r for r in rows if lo<=r["tight"]<hi], f"25일폭 {lo}~{hi}%")
print("[파일럿 창 2025-11-26~ 만]")
pw=[r for r in rows if r["entry"]>="2025-11-26"]
rep(pw,"전체")
for lo,hi in [(80,90),(90,101)]: rep([r for r in pw if lo<=r["rs"]<hi], f"RS {lo}~{hi}")
rep([r for r in pw if r["tight"]<25], "25일폭<25%")
rep([r for r in pw if r["rs"]>=90 and r["tight"]<25], "RS90+ & 타이트")
