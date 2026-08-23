import json, io, bisect, statistics as st
B='C:/Users/hanul/AppData/Local/Temp/bt5y/'
def L(p): return json.load(io.open(B+p,encoding='utf-8'))

ev=[]; raw=0
for y in range(2021,2027):
    d=L('bt_%d.json'%y)
    for e in d['events']:
        raw+=1
        if e['result'] in ('win','loss'): ev.append(e)
seen=set(); ded=[]
for e in ev:
    k=(e['scan_date'],e['code'],e['pattern'])
    if k in seen: continue
    seen.add(k); ded.append(e)
print('raw events(all results)=%d  win/loss=%d  after dedup=%d  removed=%d'%(raw,len(ev),len(ded),len(ev)-len(ded)))
ev=ded
def net(g): return ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
for e in ev: e['net']=net(e['gain_at_resolve_pct'])

w=[e for e in ev if e['result']=='win']; l=[e for e in ev if e['result']=='loss']
print('n=%d  win=%d loss=%d  winrate=%.2f%%  per-trade net=%+.3f%%'%(len(ev),len(w),len(l),100*len(w)/len(ev),st.mean(e['net'] for e in ev)))
mw=st.mean(e['net'] for e in w); ml=st.mean(e['net'] for e in l)
print('avg win net=%+.2f%%  avg loss net=%+.2f%%  payoff=%.3f  breakeven wr=%.2f%%'%(mw,ml,mw/-ml,100*(-ml)/(mw-ml)))

# nasdaq label: strictly prior US session
nq=L('nasdaq.json'); nqd=sorted(nq['close']); up=nq['up']
def lab(kdate):
    i=bisect.bisect_left(nqd,kdate)-1
    if i<0: return None
    d=nqd[i]
    return (d, up[d])
bad=0; lags={}
for e in ev:
    r=lab(e['entry_date'])
    e['nq_src']=r[0]; e['nq']=bool(r[1])
    if r[0]>=e['entry_date']: bad+=1
print('lookahead violations(us_date>=kr_date)=%d'%bad)

def sub(f): return [e for e in ev if f(e)]
def stats(x,tag):
    if not x: print(tag,'empty'); return
    wr=100*sum(1 for e in x if e['result']=='win')/len(x)
    print('%-28s n=%5d  wr=%5.2f%%  net/trade=%+.3f%%  sum_net=%+.0f%%'%(tag,len(x),wr,st.mean(e['net'] for e in x),sum(e['net'] for e in x)))
print()
stats(ev,'ALL')
stats(sub(lambda e:e['nq']),'NASDAQ UP day')
stats(sub(lambda e:not e['nq']),'NASDAQ DOWN day')

# 9-month window
print()
for start in ['2025-12-01','2025-01-01','2024-01-01','2023-01-01','2022-01-01','2021-01-01']:
    s=sub(lambda e,s=start: e['entry_date']>=s)
    u=[e for e in s if e['nq']]; dn=[e for e in s if not e['nq']]
    wru=100*sum(1 for e in u if e['result']=='win')/len(u); wrd=100*sum(1 for e in dn if e['result']=='win')/len(dn)
    print('from %s n=%5d  up n=%4d wr=%5.2f  down n=%4d wr=%5.2f  diff=%+.2f%%p  netdiff=%+.2f%%p'%(
        start,len(s),len(u),wru,len(dn),wrd,wru-wrd, st.mean(e['net'] for e in u)-st.mean(e['net'] for e in dn)))
