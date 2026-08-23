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
    out=[];c=1.0;ts=[]
    for t in range(i+1,len(DATES)):
        v=days[t].get(code)
        if not v or v.get('fltRt') is None: continue
        c*=(1+v['fltRt']/100.0); out.append((c-1)*100); ts.append(t)
    return out,ts,i
def sim_xt(p,ts,i0,stop=-10.0,trail=None,arm=20.0):
    peak=0.0;armed=False
    for g,t in zip(p,ts):
        peak=max(peak,g)
        if g>=arm: armed=True
        if armed and g<=peak-trail: return peak-trail,t
        if g<=stop: return stop,t
    return (p[-1],ts[-1]) if p else (0.0,i0)
recs=[]
for e in ev:
    p,ts,i0=path(e['code'],e['entry_date'])
    orig_ret=e['gain_at_resolve_pct']
    ri=idx.get(e['resolve_date'].replace('-','')) if e.get('resolve_date') else None
    if ri is None: ri=(ts[-1] if ts else i0)
    tr=sim_xt(p,ts,i0,stop=-10,trail=15,arm=20)
    recs.append(dict(e=e,i0=i0,orig=(orig_ret,ri),tr=tr,up=upmap.get(e['entry_date'])))
BUY_F=0.0014; SELL_F=0.0034
def run(rule,up_only,seed,slots=5):
    rnd=random.Random(seed)
    pool=sorted(recs,key=lambda r:(r['i0'],rnd.random()))
    if up_only: pool=[r for r in pool if r['up'] is True]
    free=[0]*slots; eq=1.0; taken=0
    for r in pool:
        cand=[s for s in range(slots) if free[s]<=r['i0']]
        if not cand: continue
        s=cand[0]; ret,tex=r[rule]; size=eq/slots
        net=size*(1+ret/100.0)*(1-SELL_F)-size*BUY_F
        eq+=net-size; free[s]=tex; taken+=1
    return eq-1,taken
print("="*96)
print("[5b] 슬롯5 — 원본 resolve 데이터로 현행규칙 재현 시도 (200회 중앙)")
print("="*96)
for rule,lab in (('orig','현행 +20/-10 (원본 resolve 그대로)'),('tr','+20 도달후 15% 트레일 (재시뮬)')):
    for uo,ul in ((False,'전부매수'),(True,'상승국면만')):
        vals=[run(rule,uo,s) for s in range(200)]
        med=statistics.median([v for v,_ in vals])*100
        tk=statistics.median([t for _,t in vals])
        print(f"  {lab:<36}{ul:<10}{med:>+8.1f}%   (체결 {tk:.0f}건)")
print("\n제시된 기준선: 전부매수 +1.6%, 상승국면만 +35.4%")
