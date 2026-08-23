import sys,json;sys.path.insert(0,'.')
from regimes import make_all
from sim import load_events
ev=load_events(); R={r.name:r for r in make_all()}
def S(n): return {i for i,e in enumerate(ev) if R[n](e) is True}
a=S('EW20_baseline(등가중20일선)'); b=S('CW20(시총가중20일선)'); k=S('코스피20일선'); q=S('코스닥20일선'); nx=S('나스닥20일선')
def jac(x,y): return len(x&y)/len(x|y)*100
print('EW20 vs CW20  겹침 %.1f%% (교집합 %d)'%(jac(a,b),len(a&b)))
print('EW20 vs 코스피20 겹침 %.1f%%'%jac(a,k))
print('EW20 vs 코스닥20 겹침 %.1f%%'%jac(a,q))
print('EW20 vs 나스닥20 겹침 %.1f%%'%jac(a,nx))
print('코스피20 vs 코스닥20 겹침 %.1f%%'%jac(k,q))
# date-level agreement
import collections
dates=sorted(set(e['scan_date'] for e in ev))
def flag(n,dt):
    for e in ev:
        if e['scan_date']==dt: return R[n](e)
fa={}; 
for n in ['EW20_baseline(등가중20일선)','CW20(시총가중20일선)','코스피20일선','코스닥20일선']:
    fa[n]={}
    for e in ev: fa[n][e['scan_date']]=R[n](e)
import itertools
names=list(fa)
for x,y in itertools.combinations(names,2):
    ag=sum(1 for d in dates if fa[x][d]==fa[y][d])/len(dates)*100
    print('날짜단위 일치 %-28s vs %-16s %.1f%% (%d일)'%(x,y,ag,len(dates)))
