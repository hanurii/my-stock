import sys,os,json,statistics
sys.path.insert(0,'.')
from regimes import make_all
from sim import load_events, net_mult
from cal import sim

ev=load_events(); R=make_all()
allidx=set(range(len(ev)))
base,_=sim(ev,allidx)
print('필터없음(전부매수) 슬롯5 = %+.2f%%   후보 614건'%base)
print()
rows=[]
for r in R:
    S={i for i,e in enumerate(ev) if r(e) is True}
    N={i for i,e in enumerate(ev) if r(e) is False}
    m,taken=sim(ev,S)
    mn,_=sim(ev,N) if N else (float('nan'),0)
    g_in=statistics.mean([ev[i]['gain_at_resolve_pct'] for i in S]) if S else float('nan')
    g_out=statistics.mean([ev[i]['gain_at_resolve_pct'] for i in N]) if N else float('nan')
    win_in=sum(1 for i in S if ev[i]['result']=='win')/max(1,sum(1 for i in S if ev[i]['result'] in('win','loss')))*100
    win_out=sum(1 for i in N if ev[i]['result']=='win')/max(1,sum(1 for i in N if ev[i]['result'] in('win','loss')))*100
    rows.append((r.name,len(S),taken,m,mn,g_in,g_out,win_in,win_out))
rows.sort(key=lambda x:-x[3])
print('%-38s %5s %6s %9s %9s %8s %8s %6s %6s'%('국면정의','후보','체결','슬롯5(국면ON)','슬롯5(국면OFF)','건당ON','건당OFF','승률ON','승률OFF'))
for n,ns,tk,m,mn,gi,go,wi,wo in rows:
    print('%-38s %5d %6.0f %+12.2f%% %+12.2f%% %+7.2f%% %+7.2f%% %5.1f%% %5.1f%%'%(n,ns,tk,m,mn,gi,go,wi,wo))
json.dump([list(x) for x in rows],open('rows1.json','w'),ensure_ascii=False)
