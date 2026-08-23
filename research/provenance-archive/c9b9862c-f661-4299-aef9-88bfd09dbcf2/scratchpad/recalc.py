import json, sys, math
sys.stdout.reconfigure(encoding='utf-8')
raw=json.load(open(r'C:\Users\hanul\playground\my-stock\public\data\scorecard-fills.json',encoding='utf-8'))
fills=raw['fills']
DEF=raw.get('stop_loss_pct_default',-4)
print('fills',len(fills),'stop_default',DEF,'rr',raw.get('rr_target'))
def jround(x):
    # JS Math.round: half away from +inf (toward +inf on .5)
    return math.floor(x+0.5)
def round2(x): return jround(x*100)/100

def build(code,name,buys,sells,od,cd,defstop):
    buyVal=sum(b['price']*b['qty'] for b in buys); buyQty=sum(b['qty'] for b in buys)
    sellVal=sum(s['price']*s['qty'] for s in sells); sellQty=sum(s['qty'] for s in sells)
    avgBuy=buyVal/buyQty; avgSell=sellVal/sellQty
    grossPct=(avgSell/avgBuy-1)*100
    buyFees=sum(b.get('fees') or 0 for b in buys)
    sellCosts=sum((s.get('fees') or 0)+(s.get('tax') or 0) for s in sells)
    netCost=buyVal+buyFees; netProceeds=sellVal-sellCosts
    netPct=round2((netProceeds/netCost-1)*100)
    outcome='win' if netPct>0 else 'loss'
    return dict(code=code,name=name,open_date=od,close_date=cd,net_pct=netPct,gross_pct=round2(grossPct),
                net_won=jround(netProceeds-netCost),gross_won=jround(sellVal-buyVal),
                hold_days=None,outcome=outcome,month=cd[:7],buy_qty=buyQty,sell_qty=sellQty)

def match(fills,defstop):
    errors=[];trades=[];open_=[];dropped={}
    bycode={}
    for i,f in enumerate(fills): bycode.setdefault(f['code'],[]).append((f,i))
    for code,lst in bycode.items():
        s=sorted(lst,key=lambda t:(t[0]['date'],t[1]))
        qty=0;buys=[];sells=[];fb='';bad=False;ct=[]
        for f,_ in s:
            if f['side']=='buy':
                if qty==0: buys=[];sells=[];fb=f['date'][:10]
                buys.append(f);qty+=f['qty']
            else:
                sells.append(f);qty-=f['qty']
                if qty<0:
                    errors.append(f"{code}: over-sell ({f['date']}) qty_short={-qty}")
                    bad=True;break
                if qty==0:
                    ct.append(build(code,f['name'],buys,sells,fb,f['date'][:10],defstop))
                    buys=[];sells=[]
        if bad:
            dropped[code]=dict(trades=ct,resid_qty=qty,name=s[0][0]['name'])
            continue
        trades+=ct
        if qty>0:
            bv=sum(b['price']*b['qty'] for b in buys);bq=sum(b['qty'] for b in buys)
            open_.append(dict(code=code,name=buys[-1]['name'],qty=qty,avg_buy=round2(bv/bq),open_date=fb))
    return trades,open_,errors,dropped

trades,open_,errors,dropped=match(fills,DEF)
print('trades',len(trades),'open',len(open_),'errors',len(errors))
print('total_won net', sum(t['net_won'] for t in trades))
wins=[t for t in trades if t['net_pct']>0]
print('win_rate', round2(len(wins)/len(trades)*100))
print('--- dropped codes ---')
tot=0;cnt=0
for c,v in dropped.items():
    s=sum(t['net_won'] for t in v['trades'])
    tot+=s;cnt+=len(v['trades'])
    print(c,v['name'],'completed_trades',len(v['trades']),'net_won',s,'resid_qty',v['resid_qty'],
          [(t['close_date'],t['net_pct'],t['net_won']) for t in v['trades']])
print('DROPPED total trades',cnt,'net_won',tot)
