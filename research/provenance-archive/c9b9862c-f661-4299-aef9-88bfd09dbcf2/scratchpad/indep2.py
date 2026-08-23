import json,os,sys,numpy as np
from collections import defaultdict,Counter
from scipy import stats as st
sys.path.insert(0,'scripts'); os.chdir('C:/Users/hanul/playground/my-stock')
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad'
from canslim_lib import ohlcv_matrix
R=json.load(open(SP+'/H10v.json',encoding='utf-8'))
seen=set();first=[]
for x in sorted(R,key=lambda z:z['date']):
    if x['code'] in seen: continue
    seen.add(x['code']); first.append(x)
hi=[x for x in first if x['ext']>=150]; lo=[x for x in first if x['ext']<150]
cache={}
def ser(c):
    if c not in cache: cache[c]=ohlcv_matrix.get_series(c)
    return cache[c]
def common_dates(codes,a,b):
    s=ser(codes[0]); ds=[d for d in s['dates'] if a<=d<=b]
    for c in codes[1:]:
        st_=set(ser(c)['dates']); ds=[d for d in ds if d in st_]
    return ds
def retmat(codes,ds):
    M=[]
    for c in codes:
        s=ser(c); idx={d:i for i,d in enumerate(s['dates'])}
        cl=np.array([s['closes'][idx[d]] for d in ds],float)
        M.append(np.diff(np.log(cl)))
    return np.array(M)
ds=common_dates([x['code'] for x in first],'2026-07-01','2026-08-07')
print('common trading days',len(ds), ds[0],ds[-1])
Mh=retmat([x['code'] for x in hi],ds); Ml=retmat([x['code'] for x in lo],ds)
iu=np.triu_indices(len(hi),1); iul=np.triu_indices(len(lo),1)
Ch=np.corrcoef(Mh); Cl=np.corrcoef(Ml)
rh=Ch[iu].mean(); rl=Cl[iul].mean()
def neff(n,r): return n/(1+(n-1)*max(r,0))
print('mean pairwise daily-return corr: extended(24) %.3f -> n_eff %.1f | non-ext(52) %.3f -> n_eff %.1f'%(rh,neff(24,rh),rl,neff(52,rl)))

print('\n=== what happened on 2026-07-02? ===')
for lab,g in [('ext>=150 (24)',hi),('ext<150 (52)',lo)]:
    rr=[]
    for x in g:
        s=ser(x['code']); idx={d:i for i,d in enumerate(s['dates'])}
        if '2026-07-02' in idx and '2026-07-01' in idx:
            rr.append((s['closes'][idx['2026-07-02']]/s['closes'][idx['2026-07-01']]-1)*100)
    print(f'  {lab}: 07-02 median {np.median(rr):+.2f}%  mean {np.mean(rr):+.2f}%  n={len(rr)}  pct<-5%: {np.mean(np.array(rr)<-5)*100:.0f}%')

print('\n=== drop the 2026-07-01 cohort: does the extension result survive? ===')
for lab,sub in [('ALL first-appearance',first),
                ('excluding rec_date=2026-07-01',[x for x in first if x['date']!='2026-07-01']),
                ('excluding rec week 07-01..07-04',[x for x in first if not ('2026-07-01'<=x['date']<='2026-07-04')])]:
    h=[x for x in sub if x['ext']>=150]; l=[x for x in sub if x['ext']<150]
    if not h or not l: print(f'  {lab}: n_hi={len(h)} n_lo={len(l)} -- degenerate'); continue
    kh=sum(x['touch'] for x in h); kl=sum(x['touch'] for x in l)
    p=st.fisher_exact([[kh,len(h)-kh],[kl,len(l)-kl]])[1]
    print(f'  {lab}: ext>=150 {kh}/{len(h)}={kh/len(h)*100:.0f}%  ext<150 {kl}/{len(l)}={kl/len(l)*100:.0f}%  fisher p={p:.4g}')
    print(f'      med 10d ret: {np.median([x["ret"] for x in h]):+.2f}% vs {np.median([x["ret"] for x in l]):+.2f}%  | volstd {np.median([x["zret"] for x in h]):+.3f}s vs {np.median([x["zret"] for x in l]):+.3f}s')

print('\n=== per-recommendation-day breakdown of the extension edge (all obs, H=10) ===')
byd=defaultdict(lambda:[[],[]])
for x in R:
    byd[x['date']][0 if x['ext']>=150 else 1].append(x['touch'])
rows=[]
for d in sorted(byd):
    h,l=byd[d]
    if h and l: rows.append((d,len(h),np.mean(h)*100,len(l),np.mean(l)*100))
print(f'  days with both groups: {len(rows)}')
for d,nh,th,nl,tl in rows: print(f'   {d}: ext>=150 n={nh:2d} touch={th:5.1f}% | ext<150 n={nl:2d} touch={tl:5.1f}%  diff={th-tl:+6.1f}%p')
