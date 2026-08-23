import pickle, json
from collections import defaultdict
from _oos_lib import build_series
D=pickle.load(open("oos_raw_full.pkl","rb")); REC=D["rec"]
def ma(c,i,w): return sum(c[i-w+1:i+1])/w
def sim_piv(S,b,E,mode,target=20.0,stop=10.0,trail=10.0,maxhold=60):
    """파일럿과 동일: 돌파 당일(b) 포함, 진입가 E 기준 +20/-10 선착."""
    c,o,h,l,ds=S["c"],S["o"],S["h"],S["l"],S["dates"]; n=len(c)
    T=E*(1+target/100); St=E*(1-stop/100); lim=min(n-1,b+maxhold); k=None
    for i in range(b,lim+1):
        if l[i]<=St and not (h[i]>=T): 
            px=min(o[i],St) if i>b else St; return (px/E-1)*100,i-b,False
        if h[i]>=T: k=i; break
        if l[i]<=St: px=St; return (px/E-1)*100,i-b,False
    if k is None: return (c[lim]/E-1)*100,lim-b,False
    if mode=="base": px=max(o[k],T) if k>b else T; return (px/E-1)*100,k-b,True
    peak=h[k]
    for i in range(k+1,lim+1):
        tr=peak*(1-trail/100)
        if l[i]<=tr: px=min(o[i],tr); return (px/E-1)*100,i-b,True
        if h[i]>peak: peak=h[i]
    return (c[lim]/E-1)*100,lim-b,True
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
        if h[i]<piv: continue                       # 장중 60일 신고가 돌파
        seg=[x for x in v[i-50:i] if x]
        if len(seg)<30 or v[i]<1.5*(sum(seg)/len(seg)): continue
        tt=[x for x in t[i-50:i] if x]
        if not tt or sum(tt)/len(tt)<5.0: continue
        rs=rank.get(ds[i],{}).get(code)
        if not(rs is not None and rs>=80 and c[i]>ma(c,i,50)>ma(c,i,150)>ma(c,i,200) and ma(c,i,200)>ma(c,i-20,200)): continue
        E=max(piv,o[i])
        rb,db,_=sim_piv(S,i,E,"base"); rt,dt,_=sim_piv(S,i,E,"trail")
        rows.append(dict(code=code,entry=ds[i],base=rb,tr=rt,bd=db,td=dt)); lastexit=i+max(db,dt)
json.dump(rows,open("oos_piv.json","w"))
byy=defaultdict(list)
for r in rows: byy[r["entry"][:4]].append(r)
print("pivot-entry mimic n=",len(rows))
for y in sorted(byy)+["ALL"]:
    v=rows if y=="ALL" else byy[y]
    b=sum(x["base"] for x in v)/len(v); t=sum(x["tr"] for x in v)/len(v)
    print("  {:<5} n={:5d}  base {:+6.2f}  trail {:+6.2f}  delta {:+6.3f}".format(y,len(v),b,t,t-b))
d=[r["tr"]-r["base"] for r in rows]; n=len(d); tot=sum(d); sd=sorted(d,reverse=True)
for k in (5,10,20,50):
    print("  drop top{}: {:+.3f}pp ({:.0f}% of gain)".format(k,(tot-sum(sd[:k]))/n, sum(sd[:k])/tot*100))
# pilot window only
pw=[r for r in rows if r["entry"]>="2025-11-26"]
print("  pilot window n={} delta {:+.3f}".format(len(pw), sum(r["tr"]-r["base"] for r in pw)/len(pw)))
