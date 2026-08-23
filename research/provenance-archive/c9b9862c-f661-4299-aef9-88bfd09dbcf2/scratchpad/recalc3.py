import json, sys, math
sys.stdout.reconfigure(encoding='utf-8')
raw=json.load(open(r'C:\Users\hanul\playground\my-stock\public\data\scorecard-fills.json',encoding='utf-8'))
fills=raw['fills']
def jround(x): return math.floor(x+0.5)
def round2(x): return jround(x*100)/100
def build(code,name,buys,sells,od,cd):
    buyVal=sum(b['price']*b['qty'] for b in buys); buyQty=sum(b['qty'] for b in buys)
    sellVal=sum(s['price']*s['qty'] for s in sells)
    buyFees=sum(b.get('fees') or 0 for b in buys)
    sellCosts=sum((s.get('fees') or 0)+(s.get('tax') or 0) for s in sells)
    netCost=buyVal+buyFees; netProceeds=sellVal-sellCosts
    return dict(code=code,name=name,open_date=od,close_date=cd,
                net_pct=round2((netProceeds/netCost-1)*100),net_won=jround(netProceeds-netCost))
# minimal reorder: within same date, promote buys only when a sell would go negative
def match_min(fills):
    trades=[];errors=[]
    bycode={}
    for i,f in enumerate(fills): bycode.setdefault(f['code'],[]).append((f,i))
    for code,lst in bycode.items():
        s=[f for f,_ in sorted(lst,key=lambda t:(t[0]['date'],t[1]))]
        # group by date
        out=[]
        i=0
        while i<len(s):
            d=s[i]['date']; grp=[]
            while i<len(s) and s[i]['date']==d: grp.append(s[i]); i+=1
            out.append(grp)
        qty=0;buys=[];sells=[];fb='';ct=[]
        for grp in out:
            pend=list(grp)
            seq=[]
            q=qty
            while pend:
                # take first item that keeps q>=0
                took=None
                for j,f in enumerate(pend):
                    if f['side']=='buy': took=j;break
                    if f['qty']<=q: took=j;break
                if took is None:
                    # need a buy -> none left; error
                    took=0
                f=pend.pop(took)
                q += f['qty'] if f['side']=='buy' else -f['qty']
                seq.append(f)
            # reorder: prefer original order but promote buy when needed
            # redo properly: iterate original order, defer sells that would go negative
            seq2=[];deferred=[];q=qty
            for f in grp:
                if f['side']=='buy':
                    seq2.append(f); q+=f['qty']
                    k=0
                    while k<len(deferred):
                        if deferred[k]['qty']<=q:
                            q-=deferred[k]['qty']; seq2.append(deferred.pop(k))
                        else: k+=1
                else:
                    if f['qty']<=q: q-=f['qty']; seq2.append(f)
                    else: deferred.append(f)
            seq2+=deferred
            for f in seq2:
                if f['side']=='buy':
                    if qty==0: buys=[];sells=[];fb=f['date'][:10]
                    buys.append(f);qty+=f['qty']
                else:
                    sells.append(f);qty-=f['qty']
                    if qty<0: errors.append((code,f['date']));qty=0;buys=[];sells=[];break
                    if qty==0:
                        ct.append(build(code,f['name'],buys,sells,fb,f['date'][:10]));buys=[];sells=[]
        trades+=ct
    return trades,errors
t,e=match_min(fills)
print('minimal-reorder trades',len(t),'errors',e,'total_won',sum(x['net_won'] for x in t))
base=json.load(open(r'C:\Users\hanul\playground\my-stock\public\data\scorecard.json',encoding='utf-8'))['trades']
bs={(x['code'],x['open_date'],x['close_date']) for x in base}
added=[x for x in t if (x['code'],x['open_date'],x['close_date']) not in bs]
print('ADDED',len(added),'sum',sum(x['net_won'] for x in added))
for x in added: print('  +',x['code'],x['name'],x['open_date'],'->',x['close_date'],x['net_pct'],x['net_won'])

wins=[x for x in t if x['net_pct']>0]
losses=[x for x in t if x['net_pct']<=0]
mean=lambda a: sum(a)/len(a)
aw=mean([x['net_pct'] for x in wins]); al=mean([-x['net_pct'] for x in losses])
wr=len(wins)/len(t)
print()
print('CORRECTED: trades',len(t),'win',len(wins),'loss',len(losses))
print('win_rate',round2(wr*100),'avg_win',round2(aw),'avg_loss',round2(al))
print('expectancy',round2(wr*aw-(1-wr)*al))
print('total_won',sum(x['net_won'] for x in t))
