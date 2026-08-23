import json, sys, math
sys.stdout.reconfigure(encoding='utf-8')
raw=json.load(open(r'C:\Users\hanul\playground\my-stock\public\data\scorecard-fills.json',encoding='utf-8'))
fills=raw['fills']
def jround(x): return math.floor(x+0.5)
def round2(x): return jround(x*100)/100
def build(code,name,buys,sells,od,cd):
    buyVal=sum(b['price']*b['qty'] for b in buys); buyQty=sum(b['qty'] for b in buys)
    sellVal=sum(s['price']*s['qty'] for s in sells); sellQty=sum(s['qty'] for s in sells)
    avgBuy=buyVal/buyQty; avgSell=sellVal/sellQty
    buyFees=sum(b.get('fees') or 0 for b in buys)
    sellCosts=sum((s.get('fees') or 0)+(s.get('tax') or 0) for s in sells)
    netCost=buyVal+buyFees; netProceeds=sellVal-sellCosts
    netPct=round2((netProceeds/netCost-1)*100)
    return dict(code=code,name=name,open_date=od,close_date=cd,net_pct=netPct,
                net_won=jround(netProceeds-netCost),month=cd[:7],buy_qty=buyQty,sell_qty=sellQty)
def match(fills,buyfirst):
    errors=[];trades=[];open_=[]
    bycode={}
    for i,f in enumerate(fills): bycode.setdefault(f['code'],[]).append((f,i))
    for code,lst in bycode.items():
        if buyfirst:
            s=sorted(lst,key=lambda t:(t[0]['date'],0 if t[0]['side']=='buy' else 1,t[1]))
        else:
            s=sorted(lst,key=lambda t:(t[0]['date'],t[1]))
        qty=0;buys=[];sells=[];fb='';bad=False;ct=[]
        for f,_ in s:
            if f['side']=='buy':
                if qty==0: buys=[];sells=[];fb=f['date'][:10]
                buys.append(f);qty+=f['qty']
            else:
                sells.append(f);qty-=f['qty']
                if qty<0:
                    errors.append(code);bad=True;break
                if qty==0:
                    ct.append(build(code,f['name'],buys,sells,fb,f['date'][:10]));buys=[];sells=[]
        if bad: continue
        trades+=ct
        if qty>0:
            bv=sum(b['price']*b['qty'] for b in buys);bq=sum(b['qty'] for b in buys)
            open_.append(dict(code=code,name=buys[-1]['name'],qty=qty))
    return trades,open_,errors
for bf in (False,True):
    t,o,e=match(fills,bf)
    wins=[x for x in t if x['net_pct']>0]
    tot=sum(x['net_won'] for x in t)
    print('buyfirst',bf,'| trades',len(t),'open',len(o),'errors',len(e),'total_won',tot,
          'win_rate',round2(len(wins)/len(t)*100) if t else None)
    if bf:
        print('  remaining error codes:',sorted(set(e)))
        base_codes={x['code'] for x in match(fills,False)[0]}
        newt=[x for x in t if x['code'] not in base_codes]
        print('  newly counted trades:',len(newt),'sum',sum(x['net_won'] for x in newt))
        for x in sorted(t,key=lambda z:z['close_date']):
            pass
# diff of trade sets
base,_,_=match(fills,False)
fixed,_,_=match(fills,True)
key=lambda x:(x['code'],x['open_date'],x['close_date'])
bs={key(x) for x in base}
added=[x for x in fixed if key(x) not in bs]
removed=[x for x in base if key(x) not in {key(y) for y in fixed}]
print('\nADDED',len(added),'sum',sum(x['net_won'] for x in added))
for x in added: print('  +',x['code'],x['name'],x['open_date'],'->',x['close_date'],x['net_pct'],x['net_won'])
print('REMOVED',len(removed),'sum',sum(x['net_won'] for x in removed))
for x in removed: print('  -',x['code'],x['name'],x['open_date'],'->',x['close_date'],x['net_pct'],x['net_won'])
