# -*- coding: utf-8 -*-
import json, glob, os, random, collections, statistics as st, bisect, math
B=os.environ['LOCALAPPDATA']+'/Temp/bt5y/'
HERE=os.path.dirname(os.path.abspath(__file__))
FEE=lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100

def load_events():
    EV=[]
    for f in sorted(glob.glob(B+'bt_*.json')):
        EV+=[e for e in json.load(open(f,encoding='utf-8'))['events'] if e['result'] in ('win','loss')]
    raw=len(EV)
    seen=set(); U=[]
    for e in sorted(EV,key=lambda x:(x['entry_date'],x['code'],x['pattern'])):
        k=(e['scan_date'],e['code'],e['pattern'])
        if k not in seen: seen.add(k); U.append(e)
    return U, raw

REG=json.load(open(B+'regime_long.json',encoding='utf-8'))
UP={d:u for d,u in zip(REG['dates'],REG['up_ew20'])}
UPKS={d:u for d,u in zip(REG['dates'],REG['up_ks20'])}
KOS={d:v for d,v in zip(REG['dates'],REG['kospi'])}
EWI={d:v for d,v in zip(REG['dates'],REG['ew'])}

US=json.load(open(HERE+'/us_idx.json'))
def idx_series(sym):
    d=US[sym]; dates=sorted(d)
    close=[d[x] for x in dates]
    ret=[None]+[ (close[i]/close[i-1]-1)*100 for i in range(1,len(close))]
    ma20=[None]*len(close)
    for i in range(19,len(close)): ma20[i]=sum(close[i-19:i+1])/20
    up=[None]+[close[i]>close[i-1] for i in range(1,len(close))]
    # consecutive up streak ending at i
    streak=[0]*len(close)
    for i in range(1,len(close)):
        streak[i]= streak[i-1]+1 if up[i] else 0
    return dict(dates=dates, close=close, ret=ret, ma20=ma20, up=up, streak=streak)

SER={s:idx_series(s) for s in ('IXIC','US500','DJI')}

def asof(sym, korean_date):
    """한국 거래일 아침에 이미 확정된 가장 최근 미국 세션(미국날짜 < 한국날짜)의 인덱스."""
    s=SER[sym]; i=bisect.bisect_left(s['dates'], korean_date)
    return (s, i-1) if i>0 else (s, None)

def feat(sym, korean_date):
    s,i=asof(sym,korean_date)
    if i is None or i<20: return None
    return dict(ret=s['ret'][i], up=s['up'][i], above20=s['close'][i]>s['ma20'][i],
                streak=s['streak'][i], date=s['dates'][i])

def net_list(g): return [FEE(x['gain_at_resolve_pct']) for x in g]
def mnet(g): return st.mean(net_list(g)) if g else float('nan')
def wrate(g): return sum(1 for x in g if x['result']=='win')/len(g)*100 if g else float('nan')

def sim(events, slots=5, seed=0):
    byday=collections.defaultdict(list)
    for e in events: byday[e['entry_date']].append(e)
    rnd=random.Random(seed); eq=1.0; held=[]; n=0; w=0; peak=1.0; mdd=0.0
    alld=sorted(set(list(byday)+[e['resolve_date'] for e in events]))
    for d in alld:
        for rd,e,wg in [h for h in held if h[0]<=d]:
            eq += wg*FEE(e['gain_at_resolve_pct'])/100; n+=1; w+= e['result']=='win'
        held=[h for h in held if h[0]>d]
        free=slots-len(held)
        if free>0 and d in byday:
            c=byday[d][:]; rnd.shuffle(c)
            for e in c[:free]: held.append((e['resolve_date'],e,eq/slots))
        peak=max(peak,eq); mdd=min(mdd,eq/peak-1)
    return (eq-1)*100, n, (w/n*100 if n else 0), mdd*100
