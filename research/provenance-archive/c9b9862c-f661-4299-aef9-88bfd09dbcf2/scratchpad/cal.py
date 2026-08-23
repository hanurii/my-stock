import json,random,statistics,collections,sys
sys.path.insert(0,'.')
from sim import load_events, pit_regime, net_mult

def sim(events, allowed, slots=5, n_iter=300, seed=0, sizing='equity', feemode='std'):
    evs=[e for i,e in enumerate(events) if i in allowed]
    by_entry=collections.defaultdict(list)
    for e in evs: by_entry[e['entry_date']].append(e)
    all_dates=sorted(set([e['entry_date'] for e in evs]+[e['resolve_date'] for e in evs]))
    rnd=random.Random(seed); finals=[]; ntaken=[]
    for it in range(n_iter):
        cash=1.0; open_pos=[]; taken=0
        for dt in all_dates:
            still=[]
            for rd,amt,g in open_pos:
                if rd<=dt:
                    if feemode=='std': m=net_mult(g)
                    elif feemode=='none': m=1+g/100
                    elif feemode=='flat': m=(1+g/100)-0.0048
                    cash+=amt*m
                else: still.append((rd,amt,g))
            open_pos=still
            cands=list(by_entry.get(dt,[]))
            if cands:
                rnd.shuffle(cands)
                for e in cands:
                    if len(open_pos)>=slots: break
                    if sizing=='equity':
                        eq=cash+sum(a for _,a,_ in open_pos); size=eq/slots
                    else:
                        size=cash/(slots-len(open_pos))
                    if size>cash: size=cash
                    if size<=1e-9: break
                    cash-=size; open_pos.append((e['resolve_date'],size,e['gain_at_resolve_pct'])); taken+=1
        for rd,amt,g in open_pos:
            if feemode=='std': m=net_mult(g)
            elif feemode=='none': m=1+g/100
            elif feemode=='flat': m=(1+g/100)-0.0048
            cash+=amt*m
        finals.append(cash-1.0); ntaken.append(taken)
    finals.sort()
    return statistics.median(finals)*100.0, statistics.median(ntaken)

if __name__=='__main__':
    ev=load_events(); reg=pit_regime()
    conf={i for i,e in enumerate(ev) if e['result'] in ('win','loss')}
    allidx=set(range(len(ev)))
    up_scan={i for i in allidx if reg.get(ev[i]['scan_date']) is True}
    up_conf=up_scan & conf
    for sizing in ('equity','cash'):
        for feemode in ('std','none','flat'):
            for label,S in (('ALL',allidx),('ALLconf',conf),('UP',up_scan),('UPconf',up_conf)):
                r,nt=sim(ev,S,sizing=sizing,feemode=feemode)
                print(f'{sizing:6s} {feemode:5s} {label:8s} n_cand={len(S):3d} taken={nt:5.0f} ret={r:+7.2f}%')
