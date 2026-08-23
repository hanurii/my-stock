import json, os, glob, statistics, random
PD=r"C:/Users/hanul/playground/my-stock/.cache/pdata"
bt=json.load(open(r"C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json",encoding='utf-8'))
ev=bt['events']
pit=json.load(open(r'C:/Users/hanul/AppData/Local/Temp/pit_index.json',encoding='utf-8'))
upmap={d:u for d,u in zip(pit['dates'],pit['up'])}
files=sorted(glob.glob(os.path.join(PD,"price_*.json")))
dall=[os.path.basename(f)[6:14] for f in files]
sel=[(d,f) for d,f in zip(dall,files) if "20251126"<=d<="20260821"]
DATES=[d for d,_ in sel]; days=[json.load(open(f,encoding='utf-8')) for _,f in sel]
idx={d:i for i,d in enumerate(DATES)}
def path(code,ed):
    i=idx.get(ed.replace('-',''))
    if i is None: return [],None
    out=[];c=1.0;ts=[]
    for t in range(i+1,len(DATES)):
        v=days[t].get(code)
        if not v or v.get('fltRt') is None: continue
        c*=(1+v['fltRt']/100.0); out.append((c-1)*100); ts.append(t)
    return out,ts,i
def sim_xt(p,ts,i0,stop=-10.0,tp=None,trail=None,arm=20.0):
    peak=0.0;armed=False
    for g,t in zip(p,ts):
        peak=max(peak,g)
        if tp is not None and g>=tp: return tp,t
        if trail is not None:
            if g>=arm: armed=True
            if armed and g<=peak-trail: return peak-trail,t
        if g<=stop: return stop,t
    return (p[-1],ts[-1]) if p else (0.0,i0)

recs=[]
for e in ev:
    p,ts,i0=path(e['code'],e['entry_date'])
    if not p: continue
    cur=sim_xt(p,ts,i0,stop=-10,tp=20)
    tr =sim_xt(p,ts,i0,stop=-10,trail=15,arm=20)
    recs.append(dict(e=e,i0=i0,cur=cur,tr=tr,up=upmap.get(e['entry_date'])))
print("simulatable events:", len(recs))

BUY_F=0.0014; SELL_F=0.0014+0.0020
def run(rule, up_only=False, slots=5, seed=0):
    rnd=random.Random(seed)
    pool=sorted(recs,key=lambda r:(r['i0'], rnd.random()))
    if up_only: pool=[r for r in pool if r['up'] is True]
    cash=1.0; free=[0]*slots   # slot free-from day index
    equity=1.0
    for r in pool:
        cand=[s for s in range(slots) if free[s]<=r['i0']]
        if not cand: continue
        s=cand[0]
        ret,texit=r[rule]
        size=equity/slots
        gross=size*(1+ret/100.0)
        net=gross*(1-SELL_F) - size*BUY_F
        equity += (net-size)
        free[s]=texit
    return equity-1
print()
print("="*96)
print("[5] 슬롯5 자산곡선 (무작위 순서 200회 중앙, 매수0.14%/매도0.34% 반영)")
print("="*96)
print(f"{'':<30}{'전부매수':>14}{'상승국면에만':>16}")
for rule,lab in (('cur','현행 +20/-10'),('tr','+20 도달후 15% 트레일')):
    a=statistics.median([run(rule,False,seed=s) for s in range(200)])*100
    b=statistics.median([run(rule,True ,seed=s) for s in range(200)])*100
    print(f"{lab:<30}{a:>+13.1f}%{b:>+15.1f}%")
print("\n(참고 기준선) 코스피 +63.7% / 코스닥 -12.3% / 시점 등가중 -1.6% / 시점 시총가중 +63.5%")
