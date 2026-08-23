import sys,random,statistics as st
sys.path.insert(0,'C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad')
from engine import data,dates,DI,EV,UP,SELL_FEE,BUY_FEE,mtm,base_of,N
import engine as E

def run(e,trail_pct,trig=1.20):
    r=base_of(e)
    if r is None: return None
    d,ei,base=r
    tgt=base*trig; stp=base*0.90
    hit=False;runmax=None;trail=None
    for i in range(ei,N):
        hi=d['adjhi'][i]; lo=d['adjlo'][i]; op=d['adjop'][i]
        if hi is None or lo is None: continue
        if hit:
            if lo<=trail: return {'e':e,'ei':ei,'xi':i,'ret':min(trail,op or trail)/base-1,'closed':True,'d':d,'base':base}
            if hi>runmax: runmax=hi; trail=runmax*(1-trail_pct)
        else:
            if lo<=stp: return {'e':e,'ei':ei,'xi':i,'ret':min(stp,op or stp)/base-1,'closed':True,'d':d,'base':base}
            if hi>=tgt: hit=True; runmax=hi; trail=runmax*(1-trail_pct)
    return {'e':e,'ei':ei,'xi':N-1,'ret':None,'closed':False,'d':d,'base':base}

def sim(trades,regime=None,trials=400,slots=5):
    byday={}
    for t in trades:
        if regime=='up' and not UP.get(t['e']['scan_date'],False): continue
        byday.setdefault(t['ei'],[]).append(t)
    fin=[];ntr=[]
    for tr in range(trials):
        rng=random.Random(tr); cash=1.0; op=[]; cnt=0
        for i in range(N):
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
        fin.append(cash+sum(p['val0']*mtm(p['t']['d'],N-1,p['t']['base'])*(1-SELL_FEE) for p in op)); ntr.append(cnt)
    fs=sorted(fin)
    return (fs[len(fs)//2]-1)*100, st.mean(ntr)

print('추적손절 폭 민감도 (트리거 +20%)')
for tp in (0.06,0.08,0.10,0.12,0.15,0.20,0.25):
    ts=[x for x in (run(e,tp) for e in EV) if x]
    rets=[t['ret'] if t['closed'] else mtm(t['d'],N-1,t['base'])-1 for t in ts]
    a,na=sim(ts,None); b,nb=sim(ts,'up')
    print('  trail -%2.0f%%  거래당 %+5.2f%%  슬롯5 전부 %+6.1f%%(n%.0f)  상승국면 %+6.1f%%(n%.0f)'%(tp*100,100*st.mean(rets),a,na,b,nb))
print('트리거 민감도 (추적폭 -10%)')
for tg in (1.10,1.15,1.20,1.30,1.50):
    ts=[x for x in (run(e,0.10,tg) for e in EV) if x]
    rets=[t['ret'] if t['closed'] else mtm(t['d'],N-1,t['base'])-1 for t in ts]
    a,na=sim(ts,None); b,nb=sim(ts,'up')
    print('  트리거 +%2.0f%%  거래당 %+5.2f%%  슬롯5 전부 %+6.1f%%(n%.0f)  상승국면 %+6.1f%%(n%.0f)'%((tg-1)*100,100*st.mean(rets),a,na,b,nb))
