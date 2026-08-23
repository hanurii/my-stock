import json, subprocess, collections, sys
ROOT='C:/Users/hanul/playground/my-stock'
fills=json.load(open(ROOT+'/public/data/scorecard-fills.json',encoding='utf-8'))['fills']

def expected_as_of(d):
    pos=collections.defaultdict(lambda:{'qty':0,'cost':0.0,'name':'','lots':[]})
    for f in sorted(fills,key=lambda x:(x['date'], 0 if x['side']=='buy' else 1)):
        if f['date']>d: break
        p=pos[f['code']]; p['name']=f.get('name','')
        if f['side']=='buy':
            p['qty']+=f['qty']; p['cost']+=f['qty']*f['price']
            p['lots'].append((f['date'],f['price'],f['qty'],f.get('setup')))
        else:
            avg=p['cost']/p['qty'] if p['qty'] else 0
            p['cost']-=avg*f['qty']; p['qty']-=f['qty']
            if p['qty']<=0:
                p['qty']=0;p['cost']=0;p['lots']=[]
    return {c:p for c,p in pos.items() if p['qty']>0}

log=subprocess.run(['git','-C',ROOT,'log','--format=%H %ad','--date=short','--','public/data/sepa-holdings.json'],capture_output=True,text=True).stdout.strip().split('\n')
rows=[l.split(' ',1) for l in log]
rows.reverse()
seen=None
for sha,date in rows:
    try:
        content=subprocess.run(['git','-C',ROOT,'show',f'{sha}:public/data/sepa-holdings.json'],capture_output=True,text=True,encoding='utf-8').stdout
        v=json.loads(content)
    except Exception as e:
        print(sha,date,'parse fail',e); continue
    hs=v.get('holdings',[])
    if not hs: continue
    asof=max(h['buy_datetime'][:10] for h in hs)
    # snapshot date: use commit date
    key=(date,tuple(sorted((h['code'],h['quantity'],h['buy_price'],h['buy_datetime'][:10]) for h in hs)))
    if key==seen: continue
    seen=key
    exp=expected_as_of(date)
    got={h['code']:h for h in hs}
    prob=[]
    for c,p in exp.items():
        if c not in got:
            prob.append(f"누락 {c} {p['name']} qty{p['qty']}")
    for c,h in got.items():
        if c not in exp:
            prob.append(f"잔존(이미청산/미매수) {c} {h.get('name')} qty{h['quantity']}")
        else:
            p=exp[c]; eavg=round(p['cost']/p['qty'])
            if h['quantity']!=p['qty']:
                prob.append(f"수량불일치 {c} {h.get('name')} 목록{h['quantity']} vs 장부{p['qty']}")
            if abs(h['buy_price']-eavg)>2:
                prob.append(f"단가불일치 {c} {h.get('name')} 목록{h['buy_price']} vs 혼합단가{eavg} (lots={p['lots']})")
    if prob:
        print(f"--- {date} {sha[:8]} 보유{len(hs)}종 vs 장부{len(exp)}종")
        for x in prob: print("    ",x)
