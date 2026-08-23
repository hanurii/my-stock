import sys,statistics;sys.path.insert(0,'.')
from regimes import make_all
from sim import load_events, net_mult
ev=load_events(); R=make_all()
sdates=sorted(set(e['scan_date'] for e in ev))
bydate={}
for e in ev: bydate.setdefault(e['scan_date'],[]).append(e['gain_at_resolve_pct'])
allg=[e['gain_at_resolve_pct'] for e in ev]
print('전체 %d건 건당 평균 %+.2f%%'%(len(allg),statistics.mean(allg)))
print()
print('%-38s %5s %8s %8s %8s %8s'%('국면정의','ON건수','건당ON','건당OFF','차이(pp)','회전p'))
out=[]
for r in R:
    fm={}
    for e in ev: fm[e['scan_date']]=r(e)
    seq=[fm[d] for d in sdates]
    if all(x is not True for x in seq) or all(x is not False for x in seq):
        continue
    def sep(s):
        on=[];off=[]
        for d,f in zip(sdates,s):
            if f is True: on+=bydate[d]
            elif f is False: off+=bydate[d]
        if not on or not off: return None,0,None,None
        return statistics.mean(on)-statistics.mean(off), len(on), statistics.mean(on), statistics.mean(off)
    a,non,mon,moff=sep(seq)
    null=[]
    for k in range(1,len(sdates)):
        rot=seq[k:]+seq[:k]
        v,_,_,_=sep(rot)
        if v is not None: null.append(v)
    p=sum(1 for x in null if x>=a)/len(null)
    out.append((r.name,non,mon,moff,a,p))
out.sort(key=lambda x:-x[4])
for n,non,mon,moff,a,p in out:
    print('%-38s %5d %+7.2f%% %+7.2f%% %+7.2f %6.3f'%(n,non,mon,moff,a,p))
