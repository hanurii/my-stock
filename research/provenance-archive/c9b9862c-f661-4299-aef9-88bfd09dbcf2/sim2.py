import json,io,bisect,random,statistics as st
from collections import defaultdict
exec(open('C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/sim.py').read().split("if __name__")[0])

def simulate2(events, seed, nslots=5, sizing='V5'):
    rnd=random.Random(seed)
    byday=defaultdict(list)
    for e in events: byday[e['entry_date']].append(e)
    alldates=sorted(set([e['entry_date'] for e in events]+[e['resolve_date'] for e in events]))
    cash=1.0; slots=[]; taken=[]
    for d in alldates:
        rem=[]
        for (rd,cost,mult) in slots:
            if rd<=d: cash+=cost*mult
            else: rem.append((rd,cost,mult))
        slots=rem
        cands=byday.get(d,[])
        if cands:
            cands=list(cands); rnd.shuffle(cands)
            for e in cands:
                if len(slots)>=nslots: break
                if sizing=='V5':
                    V=cash+sum(c for (_,c,_) in slots); amt=min(V/nslots,cash)
                elif sizing=='freecash':
                    amt=cash/(nslots-len(slots))
                elif sizing=='fixed':
                    amt=min(0.2,cash)
                if amt<=1e-9: break
                cash-=amt; slots.append((e['resolve_date'],amt,net_mult(e['gain_at_resolve_pct']))); taken.append(e)
    for (rd,cost,mult) in slots: cash+=cost*mult
    return cash-1.0,len(taken)

conf=[e for e in ev if e['result'] in ('win','loss')]
for sizing in ['V5','freecash','fixed']:
    for label,sub in [('ALL',ev),('ALLconf',conf),('UPscan',[e for e in ev if e['up_scan']]),('UPscan_conf',[e for e in conf if e['up_scan']])]:
        r=[];n=[]
        for s in range(300):
            a,b=simulate2(sub,s,sizing=sizing); r.append(a); n.append(b)
        print(f'{sizing:9s} {label:12s} med={st.median(r)*100:+7.2f}%  trades={st.median(n):.0f}')
