import json,math
def round2(x): 
    # JS Math.round(x*100)/100  (half-up toward +inf)
    return math.floor(x*100+0.5)/100
def days(a,b):
    import datetime
    da=datetime.date.fromisoformat(a[:10]); db=datetime.date.fromisoformat(b[:10])
    return (db-da).days

def build_trade(code,name,buys,sells,od,cd,dsp):
    buyVal=sum(b['price']*b['qty'] for b in buys); buyQty=sum(b['qty'] for b in buys)
    sellVal=sum(s['price']*s['qty'] for s in sells); sellQty=sum(s['qty'] for s in sells)
    avgBuy=buyVal/buyQty; avgSell=sellVal/sellQty
    grossPct=(avgSell/avgBuy-1)*100
    buyFees=sum(b.get('fees',0) or 0 for b in buys)
    sellCosts=sum((s.get('fees',0) or 0)+(s.get('tax',0) or 0) for s in sells)
    netCost=buyVal+buyFees; netProceeds=sellVal-sellCosts
    netPct=(netProceeds/netCost-1)*100; netPctR=round2(netPct)
    outcome='win' if netPctR>0 else 'loss'
    return dict(code=code,name=name,open_date=od,close_date=cd,
        avg_buy=round2(avgBuy),avg_sell=round2(avgSell),
        gross_pct=round2(grossPct),net_pct=netPctR,
        gross_won=round(sellVal-buyVal),net_won=round(netProceeds-netCost),
        hold_days=days(od,cd),outcome=outcome,month=cd[:7],
        buy_qty=buyQty,sell_qty=sellQty)

def match(fills,dsp=-10,mode='current'):
    errors=[];trades=[];openp=[]
    by={}
    for i,f in enumerate(fills):
        by.setdefault(f['code'],[]).append((i,f))
    for code,lst in by.items():
        s=sorted(lst,key=lambda x:(x[1]['date'],x[0]))
        qty=0;buys=[];sells=[];fbd='';bad=False;ct=[]
        for i,f in s:
            if f['side']=='buy':
                if qty==0: buys=[];sells=[];fbd=f['date'][:10]
                buys.append(f);qty+=f['qty']
            else:
                sells.append(f);qty-=f['qty']
                if qty<0:
                    errors.append(f"{code}: over-sell ({f['date']})");bad=True;break
                if qty==0:
                    ct.append(build_trade(code,f['name'],buys,sells,fbd,f['date'][:10],dsp))
                    buys=[];sells=[]
        if bad and mode=='current': continue
        trades.extend(ct)
        if qty>0:
            bv=sum(b['price']*b['qty'] for b in buys);bq=sum(b['qty'] for b in buys)
            openp.append(dict(code=code,name=buys[-1]['name'],qty=qty,avg_buy=round2(bv/bq),open_date=fbd))
    return trades,openp,errors
