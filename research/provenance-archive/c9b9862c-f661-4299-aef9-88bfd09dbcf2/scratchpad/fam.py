import sys,statistics;sys.path.insert(0,'.')
from regimes import make_all
from sim import load_events
from cal import sim
ev=load_events(); R=make_all()
sdates=sorted(set(e['scan_date'] for e in ev))
seqs={}
for r in R:
    fm={}
    for e in ev: fm[e['scan_date']]=r(e)
    s=[fm[d] for d in sdates]
    if all(x is not True for x in s) or all(x is not False for x in s): continue
    seqs[r.name]=s
print('정의 개수',len(seqs))
def run(s):
    fm=dict(zip(sdates,s))
    S={i for i,e in enumerate(ev) if fm.get(e['scan_date']) is True}
    if len(S)<10: return -999
    return sim(ev,S,n_iter=40)[0]
actual={n:run(s) for n,s in seqs.items()}
amax=max(actual.values()); abest=max(actual,key=actual.get)
print('실제 최고 정의: %s  %+.2f%%'%(abest,amax))
nullmax=[]
for k in range(1,len(sdates)):
    vals=[run(s[k:]+s[:k]) for s in seqs.values()]
    nullmax.append(max(vals))
nullmax_s=sorted(nullmax)
worse=sum(1 for x in nullmax if x>=amax)
print('회전 널 %d개의 "35정의 중 최고값" 분포:'%len(nullmax))
print('  중앙 %+.2f%%  5%% %+.2f%%  50%% %+.2f%%  95%% %+.2f%%  최대 %+.2f%%'%(
  statistics.median(nullmax),nullmax_s[int(.05*len(nullmax))],nullmax_s[int(.5*len(nullmax))],
  nullmax_s[int(.95*len(nullmax))],nullmax_s[-1]))
print('  실제 최고(%+.2f%%) 이상인 널 = %d/%d  → 다중검정 보정 p = %.3f'%(amax,worse,len(nullmax),worse/len(nullmax)))
