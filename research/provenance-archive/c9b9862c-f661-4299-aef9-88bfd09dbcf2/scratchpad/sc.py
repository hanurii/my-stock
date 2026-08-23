import json, math
from collections import OrderedDict

def r2(x): 
    # JS Math.round(x*100)/100 : half-up on positive, half-up toward +inf on negatives
    return math.floor(x*100+0.5)/100

def mean(xs): return sum(xs)/len(xs)
def jr(x): return math.floor(x+0.5)

def days_between(a,b):
    import datetime
    da=datetime.date.fromisoformat(a[:10]); db=datetime.date.fromisoformat(b[:10])
    return (db-da).days

def build_trade(code,name,buys,sells,open_date,close_date,default_stop):
    buyVal=sum(b['price']*b['qty'] for b in buys); buyQty=sum(b['qty'] for b in buys)
    sellVal=sum(s['price']*s['qty'] for s in sells); sellQty=sum(s['qty'] for s in sells)
    avgBuy=buyVal/buyQty; avgSell=sellVal/sellQty
    grossPct=(avgSell/avgBuy-1)*100
    buyFees=sum(b.get('fees',0) or 0 for b in buys)
    sellCosts=sum((s.get('fees',0) or 0)+(s.get('tax',0) or 0) for s in sells)
    netCost=buyVal+buyFees; netProceeds=sellVal-sellCosts
    netPct=(netProceeds/netCost-1)*100; netPctR=r2(netPct)
    outcome='win' if netPctR>0 else 'loss'
    firstStop=buys[0].get('stop')
    planned = (firstStop/avgBuy-1)*100 if firstStop is not None else (-abs(default_stop) if default_stop is not None else None)
    sv = None
    if planned is not None:
        sv = (outcome=='loss' and netPctR < planned-1e-9)
    return dict(code=code,name=name,open_date=open_date,close_date=close_date,
        avg_buy=r2(avgBuy),avg_sell=r2(avgSell),gross_pct=r2(grossPct),net_pct=netPctR,
        gross_won=jr(sellVal-buyVal),net_won=jr(netProceeds-netCost),
        hold_days=days_between(open_date,close_date),outcome=outcome,month=close_date[:7],
        buy_qty=buyQty,sell_qty=sellQty,stop=firstStop,stop_violation=sv,setup=buys[0].get('setup'))

def match(fills, default_stop, mode='current'):
    errors=[];trades=[];openpos=[]
    byCode=OrderedDict()
    for i,f in enumerate(fills):
        byCode.setdefault(f['code'],[]).append((f,i))
    for code,lst in byCode.items():
        s=sorted(lst,key=lambda p:(p[0]['date'][:10] if False else p[0]['date'], p[1]))
        if mode=='buyfirst':
            s=sorted(lst,key=lambda p:(p[0]['date'], 0 if p[0]['side']=='buy' else 1, p[1]))
        elif mode=='minimal':
            # per day, keep original order but if a sell would go negative, pull the needed buys of that day forward
            s=sorted(lst,key=lambda p:(p[0]['date'],p[1]))
            out=[];qty=0;i=0
            days=OrderedDict()
            for p in s: days.setdefault(p[0]['date'],[]).append(p)
            for d,items in days.items():
                q=qty; pend=list(items); ordered=[]
                # greedy: repeatedly take first item that doesn't break; prefer original order
                while pend:
                    pick=None
                    for j,p in enumerate(pend):
                        if p[0]['side']=='buy' or q-p[0]['qty']>=0:
                            pick=j;break
                    if pick is None: pick=0
                    p=pend.pop(pick); ordered.append(p)
                    q += p[0]['qty'] if p[0]['side']=='buy' else -p[0]['qty']
                out.extend(ordered); qty=q
            s=out
        qty=0;buys=[];sells=[];firstBuyDate='';bad=False;ct=[]
        for f,_ in s:
            if f['side']=='buy':
                if qty==0: buys=[];sells=[];firstBuyDate=f['date'][:10]
                buys.append(f);qty+=f['qty']
            else:
                sells.append(f);qty-=f['qty']
                if qty<0:
                    errors.append(f"{code}: 매도 수량이 보유수량 초과 ({f['date']})");bad=True;break
                if qty==0:
                    ct.append(build_trade(code,f['name'],buys,sells,firstBuyDate,f['date'][:10],default_stop))
                    buys=[];sells=[]
        if bad: continue
        trades.extend(ct)
        if qty>0:
            bv=sum(b['price']*b['qty'] for b in buys);bq=sum(b['qty'] for b in buys)
            openpos.append(dict(code=code,name=buys[-1]['name'],qty=qty,avg_buy=r2(bv/bq),open_date=firstBuyDate))
    return trades,openpos,errors

def overall(trades,basis):
    pct=lambda t: t['net_pct'] if basis=='net' else t['gross_pct']
    n=len(trades)
    wins=[t for t in trades if pct(t)>0]; losses=[t for t in trades if pct(t)<=0]
    wr=len(wins)/n; lr=len(losses)/n
    aw=mean([pct(t) for t in wins]) if wins else None
    al=mean([-pct(t) for t in losses]) if losses else None
    payoff=aw/al if aw is not None and al else None
    exp=wr*(aw or 0)-lr*(al or 0)
    def tomax(arr,mag):
        if not arr: return None
        best=arr[0]
        for b in arr[1:]:
            if mag(b)>mag(best): best=b
        return dict(pct=r2(mag(best)),code=best['code'],name=best['name'],date=best['close_date'])
    return dict(win_rate=r2(wr*100),avg_win=r2(aw) if aw is not None else None,
        avg_loss=r2(al) if al is not None else None,payoff_ratio=r2(payoff) if payoff else None,
        expectancy=r2(exp),max_win=tomax(wins,pct),max_loss=tomax(losses,lambda t:-pct(t)),
        win_days=jr(mean([t['hold_days'] for t in wins])) if wins else None,
        loss_days=jr(mean([t['hold_days'] for t in losses])) if losses else None,
        trade_count=n,win_count=len(wins),loss_count=len(losses),
        total_won=sum(t['net_won'] if basis=='net' else t['gross_won'] for t in trades))

def monthly(trades,basis):
    pct=lambda t: t['net_pct'] if basis=='net' else t['gross_pct']
    months=sorted(set(t['month'] for t in trades))
    rows=[]
    for m in months:
        mt=[t for t in trades if t['month']==m]
        w=[t for t in mt if pct(t)>0]; l=[t for t in mt if pct(t)<=0]
        rows.append(dict(month=m,avg_win=r2(mean([pct(t) for t in w])) if w else None,
            avg_loss=r2(mean([-pct(t) for t in l])) if l else None,
            win_rate=r2(len(w)/len(mt)*100),trades=len(mt),
            max_win=r2(max([pct(t) for t in w])) if w else None,
            max_loss=r2(max([-pct(t) for t in l])) if l else None,
            win_days=jr(mean([t['hold_days'] for t in w])) if w else None,
            loss_days=jr(mean([t['hold_days'] for t in l])) if l else None))
    return rows
