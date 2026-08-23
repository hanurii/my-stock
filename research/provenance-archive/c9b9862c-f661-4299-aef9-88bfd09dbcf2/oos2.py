import pickle, json
from collections import defaultdict
D=pickle.load(open("oos_raw_full.pkl","rb")); REC=D["rec"]
exec(open("oos_run.py",encoding="utf-8").read().split("rows=[]")[0].split('D=pickle')[0])
def build_series(hist):
    ds=sorted(hist)
    if len(ds)<260: return None
    cl=[];op=[];hi=[];lo=[];tv=[];to=[]
    adj=None
    for d in ds:
        c,m,h,l,q,t,f = hist[d]
        adj = c if adj is None else adj*(1+(f or 0.0)/100.0)
        cl.append(adj); sc=adj/c if c else 1.0
        op.append((m or c)*sc); hi.append((h or c)*sc); lo.append((l or c)*sc)
        tv.append(q or 0); to.append(t or 0.0)
    return dict(dates=ds,c=cl,o=op,h=hi,l=lo,v=tv,t=to)
def sim_one(S,b,mode,target=20.0,stop=10.0,trail=10.0,maxhold=60):
    c,o,h,l,ds=S["c"],S["o"],S["h"],S["l"],S["dates"]; n=len(c)
    E=c[b]; T=E*(1+target/100); St=E*(1-stop/100); lim=min(n-1,b+maxhold); k=None
    for i in range(b+1,lim+1):
        if l[i]<=St: px=min(o[i],St); return (px/E-1)*100,i-b,ds[i],False
        if h[i]>=T: k=i; break
    if k is None: return (c[lim]/E-1)*100,lim-b,ds[lim],False
    if mode=="base": px=max(o[k],T); return (px/E-1)*100,k-b,ds[k],True
    peak=h[k]
    for i in range(k+1,lim+1):
        tr=peak*(1-trail/100)
        if l[i]<=tr: px=min(o[i],tr); return (px/E-1)*100,i-b,ds[i],True
        if h[i]>peak: peak=h[i]
    return (c[lim]/E-1)*100,lim-b,ds[lim],True

def ma(c,i,w): return sum(c[i-w+1:i+1])/w
SER={}
for code,hist in REC.items():
    S=build_series(hist)
    if S: SER[code]=S
print("series", len(SER))
# 날짜별 12M 모멘텀 랭크(RS 대용)
alld=sorted({d for S in SER.values() for d in S["dates"]})
pos={code:{d:i for i,d in enumerate(S["dates"])} for code,S in SER.items()}
rows=[]
mom_cache={}
for code,S in SER.items():
    c=S["c"]
    S["mom"]=[None]*len(c)
    for i in range(250,len(c)):
        S["mom"][i]= c[i]/c[i-250]-1
# 날짜별 랭크
bydate=defaultdict(list)
for code,S in SER.items():
    for i,d in enumerate(S["dates"]):
        if S["mom"][i] is not None: bydate[d].append((S["mom"][i],code))
rank={}
for d,lst in bydate.items():
    lst.sort()
    N=len(lst)
    rank[d]={code:(j+1)/N*100 for j,(m,code) in enumerate(lst)}
print("rank dates", len(rank))
for code,S in SER.items():
    c,v,t,ds,h,l=S["c"],S["v"],S["t"],S["dates"],S["h"],S["l"]; n=len(c)
    lastexit=-1
    for i in range(260,n-3):
        if i<=lastexit: continue
        if c[i] < max(c[i-60:i]): continue
        seg=[x for x in v[i-50:i] if x]
        if len(seg)<30 or v[i] < 1.5*(sum(seg)/len(seg)): continue
        tt=[x for x in t[i-50:i] if x]
        if not tt or sum(tt)/len(tt) < 5.0: continue
        rs = rank.get(ds[i],{}).get(code)
        m50,m150,m200 = ma(c,i,50), ma(c,i,150), ma(c,i,200)
        lead = (rs is not None and rs>=80 and c[i]>m50>m150>m200 and m200>ma(c,i-20,200))
        rb,db,xb,tb=sim_one(S,i,"base"); rt,dt,xt,tc=sim_one(S,i,"trail")
        rows.append(dict(code=code,entry=ds[i],base=rb,tr=rt,touched=tc,lead=lead,rs=rs))
        lastexit=i+max(db,dt)
json.dump(rows,open("oos_rows2.json","w"))
print("entries",len(rows))
def rep(v,lab):
    if not v: print(lab,"n=0"); return
    b=sum(x["base"] for x in v)/len(v); t=sum(x["tr"] for x in v)/len(v)
    print(f"  {lab:<34} n={len(v):6d}  현행 {b:+6.2f}  추적 {t:+6.2f}  차이 {t-b:+6.3f}%p  (20%도달 {sum(1 for x in v if x['touched'])/len(v)*100:.1f}%)")
PIL0,PIL1="2025-11-26","2026-08-21"
print("\n[동일 규격 일반 돌파 유니버스 — 기간 대조]")
for lab,f in [("① OOS 2021-10~2025-11-25", lambda r: r["entry"]<PIL0),
              ("② 파일럿 창 2025-11-26~", lambda r: r["entry"]>=PIL0)]:
    v=[r for r in rows if f(r)]; rep(v,lab+" 전체")
    rep([r for r in v if r["lead"]], lab+" 주도주필터")
print("\n[연도별]")
byy=defaultdict(list)
for r in rows: byy[r["entry"][:4]].append(r)
for y in sorted(byy):
    rep(byy[y], y)
    rep([r for r in byy[y] if r["lead"]], y+" 주도주")
