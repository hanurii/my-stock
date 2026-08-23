import json,glob,sys,os
import numpy as np
sys.path.insert(0,'scripts')
ROOT='C:/Users/hanul/playground/my-stock'
fs=glob.glob(ROOT+'/.cache/ohlcv/series/*.json')
# master date axis: use 005930
ref=json.load(open(ROOT+'/.cache/ohlcv/series/005930.json',encoding='utf-8'))
dates=ref['dates']; N=len(dates); di={d:i for i,d in enumerate(dates)}
# exclusion list
excl=set()
try:
    e=json.load(open(ROOT+'/public/data/excluded-codes.json',encoding='utf-8'))
    excl=set(e if isinstance(e,list) else e.get('codes',[]))
except Exception as ex: print('no excl',ex)
C=[];V=[];codes=[]
for f in fs:
    code=os.path.basename(f)[:-5]
    if code in excl: continue
    d=json.load(open(f,encoding='utf-8'))
    if not d.get('dates') or len(d['dates'])<60: continue
    c=np.full(N,np.nan); v=np.full(N,np.nan)
    for dt,cl,vo in zip(d['dates'],d['closes'],d['volumes']):
        i=di.get(dt)
        if i is not None and cl: c[i]=cl; v[i]=vo
    C.append(c);V.append(v);codes.append(code)
C=np.array(C);V=np.array(V)
print('stocks',len(codes),'days',N)
# daily returns
R=C[:,1:]/C[:,:-1]-1
def ma(arr,n):
    out=np.full_like(arr,np.nan)
    cs=np.nancumsum(np.where(np.isnan(arr),0,arr),axis=1)
    cnt=np.cumsum(~np.isnan(arr),axis=1)
    for j in range(n-1,arr.shape[1]):
        s=cs[:,j]-(cs[:,j-n] if j>=n else 0); k=cnt[:,j]-(cnt[:,j-n] if j>=n else 0)
        out[:,j]=np.where(k==n,s/n,np.nan)
    return out
MA200=ma(C,200); MA50=ma(C,50); MA20=ma(C,20)
# trend-template-ish: close>MA150, >MA200, MA50>MA150>MA200, MA200 rising vs 1 month ago (22d), close>=1.25*52w low, within 25% of 52w high
MA150=ma(C,150)
rows=[]
ew=[]  # equal-weight index
idx=100.0
for j in range(1,N):
    r=R[:,j-1]; valid=~np.isnan(r)&~np.isnan(V[:,j])&(V[:,j]>0)
    # active = traded today (volume>0) and has prev close
    adv=int(np.sum(valid&(r>0))); dec=int(np.sum(valid&(r<0))); unch=int(np.sum(valid&(r==0)))
    ewr=float(np.nanmean(r[valid]))*100 if valid.sum() else np.nan
    idx*=1+ewr/100; ew.append(idx)
    c=C[:,j]; ok=~np.isnan(c)&valid
    a200=np.sum(ok&(c>MA200[:,j]))/max(1,np.sum(ok&~np.isnan(MA200[:,j])))*100
    a50=np.sum(ok&(c>MA50[:,j]))/max(1,np.sum(ok&~np.isnan(MA50[:,j])))*100
    a20=np.sum(ok&(c>MA20[:,j]))/max(1,np.sum(ok&~np.isnan(MA20[:,j])))*100
    lo=max(0,j-249); hi52=np.nanmax(C[:,lo:j+1],axis=1); lo52=np.nanmin(C[:,lo:j+1],axis=1)
    nlow=int(np.sum(ok&(c<=lo52)&(j>=249))); nhigh=int(np.sum(ok&(c>=hi52)&(j>=249)))
    # stage2 template (needs MA200 rising: compare to 22 days ago)
    if j>=222:
        tt=ok&(c>MA150[:,j])&(c>MA200[:,j])&(MA150[:,j]>MA200[:,j])&(MA200[:,j]>MA200[:,j-22])&(MA50[:,j]>MA150[:,j])&(c>MA50[:,j])&(c>=1.25*lo52)&(c>=0.75*hi52)
        ntt=int(np.sum(tt))
    else: ntt=-1
    vol=float(np.nansum(V[:,j]))
    rows.append(dict(date=dates[j],adv=adv,dec=dec,unch=unch,ew_ret=round(ewr,2),ew_idx=round(idx,2),a200=round(a200,1),a50=round(a50,1),a20=round(a20,1),nlow=nlow,nhigh=nhigh,ntt=ntt,vol=vol,n=int(valid.sum())))
json.dump(rows,open(sys.argv[1],'w'),indent=0)
print('done')
