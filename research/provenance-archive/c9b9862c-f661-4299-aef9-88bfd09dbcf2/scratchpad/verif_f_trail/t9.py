import pickle, json
from collections import defaultdict
D=pickle.load(open("oos_raw_full.pkl","rb")); REC=D["rec"]
from _oos_lib import build_series, sim_one

SER={}
for code,hist in REC.items():
    S=build_series(hist)
    if S: SER[code]=S
def ma(c,i,w): return sum(c[i-w+1:i+1])/w
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
TRAILS=[5,7.5,10,12.5,15,20,30]
TARGETS=[25,30,40,50]
rows=[]
for code,S in SER.items():
    c,v,t,ds=S["c"],S["v"],S["t"],S["dates"]; n=len(c); lastexit=-1
    for i in range(260,n-3):
        if i<=lastexit: continue
        if c[i]<max(c[i-60:i]): continue
        seg=[x for x in v[i-50:i] if x]
        if len(seg)<30 or v[i]<1.5*(sum(seg)/len(seg)): continue
        tt=[x for x in t[i-50:i] if x]
        if not tt or sum(tt)/len(tt)<5.0: continue
        rs=rank.get(ds[i],{}).get(code)
        if not(rs is not None and rs>=80 and c[i]>ma(c,i,50)>ma(c,i,150)>ma(c,i,200) and ma(c,i,200)>ma(c,i-20,200)): continue
        rb,db,_,_=sim_one(S,i,"base")
        rec=dict(code=code,entry=ds[i],base=rb,bd=db)
        mx=db
        for tr in TRAILS:
            r,d2,_,_=sim_one(S,i,"trail",trail=tr); rec[f"t{tr}"]=r; rec[f"d{tr}"]=d2; mx=max(mx,d2)
        for tg in TARGETS:
            r,d2,_,_=sim_one(S,i,"base",target=tg); rec[f"g{tg}"]=r; mx=max(mx,d2)
        rows.append(rec); lastexit=i+mx
json.dump(rows,open("oos_lead.json","w"))
print("주도주 돌파 n=",len(rows))
def yr(r): return r["entry"][:4]
byy=defaultdict(list)
for r in rows: byy[yr(r)].append(r)
cols=[("현행 +20/-10","base")]+[(f"-{x}% 추적",f"t{x}") for x in TRAILS]+[(f"고정+{x}",f"g{x}") for x in TARGETS]
print(f"{'구간':<10}{'n':>6}"+"".join(f"{c[0]:>12}" for c in cols))
for y in sorted(byy)+["ALL"]:
    v=rows if y=="ALL" else byy[y]
    print(f"{y:<10}{len(v):>6}"+"".join(f"{sum(x[c[1]] for x in v)/len(v):>+12.2f}" for c in cols))
print("\n차이(추적-현행)")
print(f"{'구간':<10}{'n':>6}"+"".join(f"{c[0]:>12}" for c in cols[1:]))
for y in sorted(byy)+["ALL"]:
    v=rows if y=="ALL" else byy[y]
    b=sum(x["base"] for x in v)/len(v)
    print(f"{y:<10}{len(v):>6}"+"".join(f"{sum(x[c[1]] for x in v)/len(v)-b:>+12.2f}" for c in cols[1:]))
