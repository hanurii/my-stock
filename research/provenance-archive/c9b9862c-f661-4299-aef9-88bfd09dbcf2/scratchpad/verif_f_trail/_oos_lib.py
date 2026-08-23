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
