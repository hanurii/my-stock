import sys,statistics,json;sys.path.insert(0,'.')
from regimes import make_all
from sim import load_events
from cal import sim
import collections,random
ev=load_events(); R={r.name:r for r in make_all()}
allidx=set(range(len(ev)))

def band(S,n=300):
    import cal
    # reuse sim internals to get full distribution
    from cal import sim as _s
    # replicate distribution
    evs=[e for i,e in enumerate(ev) if i in S]
    by=collections.defaultdict(list)
    for e in evs: by[e['entry_date']].append(e)
    dates=sorted(set([e['entry_date'] for e in evs]+[e['resolve_date'] for e in evs]))
    rnd=random.Random(0); finals=[]
    from sim import net_mult
    for it in range(n):
        cash=1.0; op=[]
        for dt in dates:
            st=[]
            for rd,a,g in op:
                if rd<=dt: cash+=a*net_mult(g)
                else: st.append((rd,a,g))
            op=st
            c=list(by.get(dt,[])); rnd.shuffle(c)
            for e in c:
                if len(op)>=5: break
                eq=cash+sum(a for _,a,_ in op); size=min(eq/5,cash)
                if size<=1e-9: break
                cash-=size; op.append((e['resolve_date'],size,e['gain_at_resolve_pct']))
        for rd,a,g in op: cash+=a*net_mult(g)
        finals.append((cash-1)*100)
    finals.sort()
    return finals[int(.05*n)],statistics.median(finals),finals[int(.95*n)]

names=['EW20_baseline(등가중20일선)','코스피20일선','코스닥20일선','CW20(시총가중20일선)',
       '나스닥 전일종가상승','나스닥20일선','S&P500 전일종가상승','다우20일선','자기시장 20일선(코스피주=코스피,코스닥주=코스닥)']
lo,md,hi=band(allidx)
print('%-40s %5s  %-30s'%('국면정의','후보','슬롯5 (무작위순서 5%/중앙/95%)'))
print('%-40s %5d  %+6.1f%% / %+6.1f%% / %+6.1f%%'%('필터없음(전부매수)',len(allidx),lo,md,hi))
for n in names:
    S={i for i,e in enumerate(ev) if R[n](e) is True}
    lo,md,hi=band(S)
    print('%-40s %5d  %+6.1f%% / %+6.1f%% / %+6.1f%%'%(n,len(S),lo,md,hi))
print()
# how many defs beat no-filter
base=sim(ev,allidx,n_iter=300)[0]
cnt=0; tot=0
for n,r in R.items():
    S={i for i,e in enumerate(ev) if r(e) is True}
    if len(S)==len(ev) or len(S)<10: continue
    tot+=1
    if sim(ev,S,n_iter=300)[0]>base: cnt+=1
print('34개 정의 중 "필터없음"(%+.2f%%)보다 나은 것: %d개 / %d개'%(base,cnt,tot))
