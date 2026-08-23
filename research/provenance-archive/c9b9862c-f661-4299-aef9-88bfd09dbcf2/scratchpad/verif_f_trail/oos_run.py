import pickle, statistics, json
from collections import defaultdict
D=pickle.load(open("oos_raw.pkl","rb")); DATES=D["dates"]; REC=D["rec"]
IDX={d:i for i,d in enumerate(DATES)}

def build_series(hist):
    ds=sorted(hist)
    if len(ds)<120: return None
    cl=[];op=[];hi=[];lo=[];tv=[];to=[]
    adj=1.0; prev=None
    for d in ds:
        c,m,h,l,q,t,f = hist[d]
        if prev is None: adj=c
        else:
            r = (f or 0.0)/100.0
            adj = adj*(1+r)
            # fltRt 이상치 방어: 실제 종가비와 크게 어긋나면 종가비 사용
            if prev[0] and abs((c/prev[0]-1)-r) > 0.03 and abs(r)<0.001:
                pass
        cl.append(adj)
        sc = adj/c if c else 1.0
        op.append((m or c)*sc); hi.append((h or c)*sc); lo.append((l or c)*sc)
        tv.append(q or 0); to.append(t or 0.0)
        prev=(c,)
    return dict(dates=ds, c=cl, o=op, h=hi, l=lo, v=tv, t=to)

def sim_one(S, b, mode, target=20.0, stop=10.0, trail=10.0, maxhold=60):
    c,o,h,l,ds = S["c"],S["o"],S["h"],S["l"],S["dates"]; n=len(c)
    E=c[b]  # 돌파일 종가 매수
    T=E*(1+target/100); St=E*(1-stop/100)
    lim=min(n-1, b+maxhold)
    k=None
    for i in range(b+1, lim+1):
        if l[i]<=St:
            px=min(o[i],St); return (px/E-1)*100, i-b, ds[i], False
        if h[i]>=T: k=i; break
    if k is None: return (c[lim]/E-1)*100, lim-b, ds[lim], False
    if mode=="base":
        px=max(o[k],T); return (px/E-1)*100, k-b, ds[k], True
    peak=h[k]
    for i in range(k+1, lim+1):
        tr=peak*(1-trail/100)
        if l[i]<=tr:
            px=min(o[i],tr); return (px/E-1)*100, i-b, ds[i], True
        if h[i]>peak: peak=h[i]
    return (c[lim]/E-1)*100, lim-b, ds[lim], True

rows=[]
for code,hist in REC.items():
    S=build_series(hist)
    if not S: continue
    c,v,t,ds = S["c"],S["v"],S["t"],S["dates"]; n=len(c)
    lastexit=-1
    for i in range(60, n-5):
        if i<=lastexit: continue
        if c[i] < max(c[i-60:i]): continue          # 60일 신고가 종가 돌파
        seg=[x for x in v[i-50:i] if x]
        if len(seg)<30: continue
        if v[i] < 1.5*(sum(seg)/len(seg)): continue  # 거래량 1.5배+
        tt=[x for x in t[i-50:i] if x]
        if not tt or sum(tt)/len(tt) < 5.0: continue # 거래대금 5억+
        rb,db,xb,tb = sim_one(S,i,"base")
        rt,dt,xt,tc = sim_one(S,i,"trail")
        rows.append(dict(code=code, entry=ds[i], base=rb, bd=db, tr=rt, td=dt, touched=tc))
        lastexit = i+max(db,dt)
print("OOS 진입", len(rows))
json.dump(rows, open("oos_rows.json","w"))
byy=defaultdict(list)
for r in rows: byy[r["entry"][:4]].append(r)
print("연도    n     현행     추적    차이/건   승률(20%도달)")
for y in sorted(byy):
    v=byy[y]; b=sum(x["base"] for x in v)/len(v); t=sum(x["tr"] for x in v)/len(v)
    print(f"  {y} {len(v):6d}  {b:+7.2f}  {t:+7.2f}  {t-b:+7.2f}   {sum(1 for x in v if x['touched'])/len(v)*100:5.1f}%")
n=len(rows); d=[r["tr"]-r["base"] for r in rows]
print(f"전체 n={n} 현행 {sum(r['base'] for r in rows)/n:+.2f} 추적 {sum(r['tr'] for r in rows)/n:+.2f} 차이 {sum(d)/n:+.3f}")
sd=sorted(d,reverse=True); tot=sum(d)
for k in (10,20,50,100):
    print(f"  상위{k} 제거 차이/건 {(tot-sum(sd[:k]))/n:+.3f}  (상위{k}={sum(sd[:k])/tot*100:.0f}%)")
