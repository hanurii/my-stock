import json,pickle,sys,random,statistics as st
sys.stdout.reconfigure(encoding='utf-8')
ROOT='C:/Users/hanul/playground/my-stock'
SC='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad'
P=pickle.load(open(SC+'/px.pkl','rb'))
dates=P['dates']; data=P['data']; DI={d:i for i,d in enumerate(dates)}
N=len(dates)
EV=json.load(open(ROOT+'/public/data/backtest-volatility-pilot.json',encoding='utf-8'))['events']
PIT=json.load(open('C:/Users/hanul/AppData/Local/Temp/pit_index.json',encoding='utf-8'))
UP={d:bool(u) for d,u in zip(PIT['dates'],PIT['up'])}

BUY_FEE=0.0014; SELL_FEE=0.0014+0.0020

SCALE={}
for code,d in data.items():
    li=None
    for i in range(N-1,-1,-1):
        if d['cl'][i] is not None: li=i; break
    if li is not None and d['adj'][li]:
        SCALE[code]=d['cl'][li]/d['adj'][li]

def base_of(e):
    d=data.get(e['code']); ei=DI.get(e['entry_date']); sc=SCALE.get(e['code'])
    if d is None or ei is None or not sc: return None
    return d,ei,e['entry_price']/sc

def run_rule(e, rule):
    """returns (exit_idx, exit_ret, closed_bool, price_series_fn)"""
    r=base_of(e)
    if r is None: return None
    d,ei,base=r
    tgt=base*1.20; stp=base*0.90
    hit_target=False; runmax=None; trail=None
    for i in range(ei,N):
        hi=d['adjhi'][i]; lo=d['adjlo'][i]; op=d['adjop'][i]
        if hi is None or lo is None: continue
        if rule=='target_stop':
            if lo<=stp and hi>=tgt:   # ambiguous -> conservative stop
                px=min(stp, op if op else stp); return (i, px/base-1, True, d, ei, base)
            if hi>=tgt:
                px=max(tgt, op if op else tgt); return (i, px/base-1, True, d, ei, base)
            if lo<=stp:
                px=min(stp, op if op else stp); return (i, px/base-1, True, d, ei, base)
        elif rule=='stop_only':
            if lo<=stp:
                px=min(stp, op if op else stp); return (i, px/base-1, True, d, ei, base)
        elif rule=='trail_after_target':
            if hit_target:
                if lo<=trail:
                    px=min(trail, op if op else trail); return (i, px/base-1, True, d, ei, base)
                if hi>runmax: runmax=hi; trail=runmax*0.90
            else:
                if lo<=stp and hi>=tgt:
                    px=min(stp, op if op else stp); return (i, px/base-1, True, d, ei, base)
                if lo<=stp:
                    px=min(stp, op if op else stp); return (i, px/base-1, True, d, ei, base)
                if hi>=tgt:
                    hit_target=True; runmax=hi; trail=runmax*0.90
    return (N-1, None, False, d, ei, base)   # still open at data end

def mtm(d, i, base):
    a=d['adj'][i]
    j=i
    while a is None and j>0:
        j-=1; a=d['adj'][j]
    return (a/base) if a else 1.0

def build(rule):
    out=[]
    for e in EV:
        r=run_rule(e,rule)
        if r is None: continue
        xi,ret,closed,d,ei,base=r
        out.append({'e':e,'ei':ei,'xi':xi,'ret':ret,'closed':closed,'d':d,'base':base})
    return out

def slot_sim(trades, slots=5, regime=None, seed=0, trials=300):
    """regime: None=all, 'up'=only enter when pit up on scan_date"""
    byday={}
    for t in trades:
        if regime=='up':
            sd=t['e']['scan_date']
            if not UP.get(sd, False): continue
        byday.setdefault(t['ei'],[]).append(t)
    finals=[]; ntrades=[]
    rng=random.Random(seed)
    for tr in range(trials):
        cash=1.0; open_pos=[]   # dict: t, size(cost basis value at entry, net of fee -> shares value), entry_val
        cnt=0
        for i in range(N):
            # exits first
            still=[]
            for p in open_pos:
                t=p['t']
                if t['closed'] and t['xi']==i:
                    cash += p['val0']*(1+t['ret'])*(1-SELL_FEE)
                else:
                    still.append(p)
            open_pos=still
            # entries
            cands=byday.get(i)
            if cands:
                cands=list(cands); rng.shuffle(cands)
                for t in cands:
                    if len(open_pos)>=slots: break
                    eq=cash+sum(p['val0']*mtm(p['t']['d'],i,p['t']['base']) for p in open_pos)
                    size=min(eq/slots, cash)
                    if size<=1e-9: break
                    cash-=size
                    open_pos.append({'t':t,'val0':size*(1-BUY_FEE)})
                    cnt+=1
        eq=cash+sum(p['val0']*mtm(p['t']['d'],N-1,p['t']['base'])*(1-SELL_FEE) for p in open_pos)
        finals.append(eq); ntrades.append(cnt)
    finals.sort()
    return {'median':(finals[len(finals)//2]-1)*100,
            'p10':(finals[int(len(finals)*0.10)]-1)*100,
            'p90':(finals[int(len(finals)*0.90)]-1)*100,
            'mean':(st.mean(finals)-1)*100,
            'ntrades':st.mean(ntrades)}

def slot_sim2(trades, slots=5, regime=None, seed=0, trials=300, sizing='cashsplit', ambig_as=None):
    byday={}
    for t in trades:
        if regime=='up' and not UP.get(t['e']['scan_date'],False): continue
        byday.setdefault(t['ei'],[]).append(t)
    finals=[];ntr=[]
    rng=random.Random(seed)
    for tr in range(trials):
        cash=1.0; op=[]; cnt=0
        for i in range(N):
            still=[]
            for p in op:
                t=p['t']
                if t['closed'] and t['xi']==i:
                    cash += p['val0']*(1+t['ret'])*(1-SELL_FEE)
                else: still.append(p)
            op=still
            c=byday.get(i)
            if c:
                c=list(c); rng.shuffle(c)
                for t in c:
                    if len(op)>=slots: break
                    free=slots-len(op)
                    if sizing=='cashsplit': size=cash/free
                    elif sizing=='equity5':
                        eq=cash+sum(p['val0']*mtm(p['t']['d'],i,p['t']['base']) for p in op)
                        size=min(eq/slots,cash)
                    elif sizing=='fixed': size=min(0.2,cash)
                    if size<=1e-9: break
                    cash-=size; op.append({'t':t,'val0':size*(1-BUY_FEE)}); cnt+=1
        eq=cash+sum(p['val0']*mtm(p['t']['d'],N-1,p['t']['base'])*(1-SELL_FEE) for p in op)
        finals.append(eq); ntr.append(cnt)
    finals.sort()
    return {'median':(finals[len(finals)//2]-1)*100,'p10':(finals[int(trials*0.1)]-1)*100,
            'p90':(finals[int(trials*0.9)]-1)*100,'mean':(st.mean(finals)-1)*100,'ntrades':st.mean(ntr)}

def slot_sim3(trades, slots=5, regime=None, seed=0, trials=300, sizing='equity5'):
    byday={}
    for t in trades:
        if regime=='up' and not UP.get(t['e']['scan_date'],False): continue
        byday.setdefault(t['ei'],[]).append(t)
    finals=[];ntr=[];unreal=[]
    for tr in range(trials):
        rng=random.Random(seed*100000+tr)   # paired across rules
        cash=1.0; op=[]; cnt=0
        for i in range(N):
            still=[]
            for p in op:
                t=p['t']
                if t['closed'] and t['xi']==i: cash += p['val0']*(1+t['ret'])*(1-SELL_FEE)
                else: still.append(p)
            op=still
            c=byday.get(i)
            if c:
                c=list(c); rng.shuffle(c)
                for t in c:
                    if len(op)>=slots: break
                    free=slots-len(op)
                    if sizing=='cashsplit': size=cash/free
                    elif sizing=='fixed': size=min(0.2,cash)
                    else:
                        eq=cash+sum(p['val0']*mtm(p['t']['d'],i,p['t']['base']) for p in op)
                        size=min(eq/slots,cash)
                    if size<=1e-9: break
                    cash-=size; op.append({'t':t,'val0':size*(1-BUY_FEE)}); cnt+=1
        openval=sum(p['val0']*mtm(p['t']['d'],N-1,p['t']['base'])*(1-SELL_FEE) for p in op)
        finals.append(cash+openval); ntr.append(cnt); unreal.append(openval/(cash+openval))
    return finals, ntr, unreal
