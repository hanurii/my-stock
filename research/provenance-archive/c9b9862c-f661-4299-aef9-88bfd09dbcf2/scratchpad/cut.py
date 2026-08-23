import sys,random,statistics as st
sys.path.insert(0,'C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad')
import engine as E
from engine import data,dates,DI,EV,UP,SELL_FEE,BUY_FEE,mtm,base_of

def run_rule(e,rule,END):
    r=base_of(e)
    if r is None: return None
    d,ei,base=r
    if ei>=END: return None
    tgt=base*1.20; stp=base*0.90
    hit=False; runmax=None; trail=None
    for i in range(ei,END):
        hi=d['adjhi'][i]; lo=d['adjlo'][i]; op=d['adjop'][i]
        if hi is None or lo is None: continue
        if rule=='target_stop':
            if lo<=stp: return (i,min(stp,op or stp)/base-1,True,d,ei,base)
            if hi>=tgt: return (i,max(tgt,op or tgt)/base-1,True,d,ei,base)
        elif rule=='stop_only':
            if lo<=stp: return (i,min(stp,op or stp)/base-1,True,d,ei,base)
        else:
            if hit:
                if lo<=trail: return (i,min(trail,op or trail)/base-1,True,d,ei,base)
                if hi>runmax: runmax=hi; trail=runmax*0.90
            else:
                if lo<=stp: return (i,min(stp,op or stp)/base-1,True,d,ei,base)
                if hi>=tgt: hit=True; runmax=hi; trail=runmax*0.90
    return (END-1,None,False,d,ei,base)

def build(rule,END):
    out=[]
    for e in EV:
        r=run_rule(e,rule,END)
        if r is None: continue
        xi,ret,cl,d,ei,base=r
        out.append({'e':e,'ei':ei,'xi':xi,'ret':ret,'closed':cl,'d':d,'base':base})
    return out

def sim(trades,END,regime=None,trials=400,slots=5):
    byday={}
    for t in trades:
        if regime=='up' and not UP.get(t['e']['scan_date'],False): continue
        byday.setdefault(t['ei'],[]).append(t)
    fin=[];ntr=[]
    for tr in range(trials):
        rng=random.Random(tr)
        cash=1.0; op=[]; cnt=0
        for i in range(END):
            still=[]
            for p in op:
                t=p['t']
                if t['closed'] and t['xi']==i: cash+=p['val0']*(1+t['ret'])*(1-SELL_FEE)
                else: still.append(p)
            op=still
            c=byday.get(i)
            if c:
                c=list(c); rng.shuffle(c)
                for t in c:
                    if len(op)>=slots: break
                    eq=cash+sum(p['val0']*mtm(p['t']['d'],i,p['t']['base']) for p in op)
                    size=min(eq/slots,cash)
                    if size<=1e-9: break
                    cash-=size; op.append({'t':t,'val0':size*(1-BUY_FEE)}); cnt+=1
        fin.append(cash+sum(p['val0']*mtm(p['t']['d'],END-1,p['t']['base'])*(1-SELL_FEE) for p in op))
        ntr.append(cnt)
    return fin,ntr

for cut in ('2026-04-30','2026-05-29','2026-06-30','2026-07-31','2026-08-20'):
    END=DI[cut]+1
    line=[]
    for rule in ('target_stop','trail_after_target','stop_only'):
        ts=build(rule,END)
        for reg in (None,'up'):
            f,n=sim(ts,END,regime=reg)
            fs=sorted(f)
            line.append('%s/%s %+.1f%%(n%.0f)'%(rule[:5],'all' if reg is None else 'up',(fs[len(fs)//2]-1)*100,st.mean(n)))
    print(cut,' | '.join(line))
