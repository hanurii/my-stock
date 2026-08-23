import json, subprocess, collections
ROOT='C:/Users/hanul/playground/my-stock'
fills=json.load(open(ROOT+'/public/data/scorecard-fills.json',encoding='utf-8'))['fills']
def expected_as_of(d, sellfirst=set()):
    pos=collections.defaultdict(lambda:{'qty':0,'cost':0.0,'name':'','lots':[]})
    def key(x):
        pri = 1 if x['side']=='buy' else 0
        if (x['date'],x['code']) in sellfirst: pri = 0 if x['side']=='sell' else 1
        else: pri = 0 if x['side']=='buy' else 1
        return (x['date'],pri)
    for f in sorted(fills,key=key):
        if f['date']>d: break
        p=pos[f['code']]; p['name']=f.get('name','')
        if f['side']=='buy':
            p['qty']+=f['qty']; p['cost']+=f['qty']*f['price']; p['lots'].append((f['date'],f['price'],f['qty']))
        else:
            avg=p['cost']/p['qty'] if p['qty'] else 0
            p['cost']-=avg*f['qty']; p['qty']-=f['qty']
            if p['qty']<=0: p['qty']=0;p['cost']=0.0;p['lots']=[]
    return {c:p for c,p in pos.items() if p['qty']>0}
# same-day sell-then-buy cases (재진입/전량매도후 재매수)
sellfirst={('2026-07-08','222040')}
log=subprocess.run(['git','-C',ROOT,'log','--format=%H %ad','--date=short','--','public/data/sepa-holdings.json'],capture_output=True,text=True).stdout.strip().split('\n')
rows=[l.split(' ',1) for l in log][::-1]
prev=None
for sha,date in rows:
    out=subprocess.run(['git','-C',ROOT,'show',f'{sha}:public/data/sepa-holdings.json'],capture_output=True,text=True,encoding='utf-8').stdout
    try: v=json.loads(out)
    except Exception: continue
    hs=v.get('holdings',[])
    if not hs: continue
    got=collections.defaultdict(lambda:{'qty':0,'cost':0.0,'name':''})
    for h in hs:
        g=got[h['code']]; g['qty']+=h['quantity']; g['cost']+=h['quantity']*h['buy_price']; g['name']=h.get('name')
    exp=expected_as_of(date, sellfirst)
    prob=[]
    for c,p in exp.items():
        if c not in got: prob.append(f"목록누락  {c} {p['name']} {p['qty']:,}주")
    for c,g in got.items():
        if c not in exp: prob.append(f"잔존     {c} {g['name']} {g['qty']:,}주 (장부상 이미 청산)")
        else:
            p=exp[c]; ea=round(p['cost']/p['qty']); ga=round(g['cost']/g['qty'])
            if g['qty']!=p['qty']: prob.append(f"수량불일치 {c} {g['name']} 목록{g['qty']:,} vs 장부{p['qty']:,}")
            elif abs(ga-ea)>2: prob.append(f"단가불일치 {c} {g['name']} 목록{ga:,} vs 혼합{ea:,}")
    sig=(date,tuple(sorted(prob)))
    if prob and sig!=prev:
        print(f"--- {date} {sha[:8]} (목록 {len(got)}종 / 장부 {len(exp)}종)")
        for x in prob: print("   ",x)
    prev=sig
print("=== 오늘(2026-08-21) 최종본 대조 ===")
cur=json.load(open(ROOT+'/public/data/sepa-holdings.json',encoding='utf-8'))['holdings']
exp=expected_as_of('2026-08-21',sellfirst)
ok=True
for h in cur:
    p=exp.get(h['code'])
    if not p: print("  잔존?",h['code']); ok=False; continue
    if h['quantity']!=p['qty'] or abs(h['buy_price']-round(p['cost']/p['qty']))>2:
        print("  불일치",h['code'],h['quantity'],p['qty']); ok=False
for c in exp:
    if c not in {h['code'] for h in cur}: print("  누락",c); ok=False
print("  → 완전일치" if ok else "  → 불일치 있음")
