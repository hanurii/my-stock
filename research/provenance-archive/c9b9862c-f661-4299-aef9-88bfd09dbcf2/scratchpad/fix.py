# -*- coding: utf-8 -*-
import json, math
d=json.load(open(r'C:\Users\hanul\playground\my-stock\public\data\scorecard-fills.json',encoding='utf-8'))
fills=d['fills']
def round2(x): return math.floor(x*100+0.5)/100
def build(code,name,buys,sells,od,cd):
    bV=sum(b['price']*b['qty'] for b in buys); bQ=sum(b['qty'] for b in buys)
    sV=sum(s['price']*s['qty'] for s in sells); sQ=sum(s['qty'] for s in sells)
    aB=bV/bQ; aS=sV/sQ
    bF=sum(b.get('fees',0) or 0 for b in buys); sC=sum((s.get('fees',0) or 0)+(s.get('tax',0) or 0) for s in sells)
    nc=bV+bF; np_=sV-sC
    return dict(code=code,name=name,open_date=od,close_date=cd,gross_pct=round2((aS/aB-1)*100),
        net_pct=round2((np_/nc-1)*100),net_won=round(np_-nc),month=cd[:7])
def match(key,label):
    byCode={}
    for i,f in enumerate(fills): byCode.setdefault(f['code'],[]).append((f,i))
    trades=[];errs=[];op=[]
    for code,lst in byCode.items():
        s=sorted(lst,key=key)
        q=0;buys=[];sells=[];fbd='';bad=False;ct=[]
        for f,_ in s:
            if f['side']=='buy':
                if q==0: buys=[];sells=[];fbd=f['date'][:10]
                buys.append(f); q+=f['qty']
            else:
                sells.append(f); q-=f['qty']
                if q<0: errs.append((code,f['date'])); bad=True; break
                if q==0: ct.append(build(code,f['name'],buys,sells,fbd,f['date'][:10])); buys=[];sells=[]
        if bad: continue
        trades.extend(ct)
        if q>0: op.append((code,q,fbd))
    print(f"--- {label}: trades={len(trades)} open={len(op)} errors={len(errs)}")
    return trades,op,errs

cur,_,_   = match(lambda t:(t[0]['date'],t[1]), 'CURRENT (file order within date)')
fx ,opf,ef= match(lambda t:(t[0]['date'], 0 if t[0]['side']=='buy' else 1, t[1]), 'FIXED (buys before sells within date)')
curset={(t['code'],t['open_date'],t['close_date']) for t in cur}
gained=[t for t in fx if (t['code'],t['open_date'],t['close_date']) not in curset]
fxset={(t['code'],t['open_date'],t['close_date']) for t in fx}
dropped=[t for t in cur if (t['code'],t['open_date'],t['close_date']) not in fxset]
print('\nGAINED', len(gained))
from collections import Counter
c=Counter(); tot=0
for t in sorted(gained,key=lambda t:(t['code'],t['close_date'])):
    c[t['code']]+=1; tot+=t['net_won']
    print(f"  {t['code']} {t['name']:9s} {t['open_date']}~{t['close_date']} net%={t['net_pct']:>7} net_won={t['net_won']:>10,} gross%={t['gross_pct']}")
print('  by code',dict(c)); print('  total net_won',f'{tot:,}')
print('  aug closes', sum(1 for t in gained if t['close_date'][:7]=='2026-08'))
print('\nDROPPED (existed before, gone after fix)', len(dropped))
for t in dropped: print(f"  {t['code']} {t['name']} {t['open_date']}~{t['close_date']} net%={t['net_pct']} net_won={t['net_won']:,}")
print('\nremaining errors after fix:',ef)
print('open after fix:',len(opf))

print('\nOPEN after fix:',sorted(o[0] for o in opf))
cur2,opc2,_=match(lambda t:(t[0]['date'],t[1]),'recheck-current')
print('OPEN current   :',sorted(o[0] for o in opc2))
print('same?',sorted(o[0] for o in opf)==sorted(o[0] for o in opc2))
from collections import Counter
print('\nMonthly after fix:',Counter(t['month'] for t in fx))
print('Monthly current  :',Counter(t['month'] for t in cur))
w=[t for t in fx if t['net_pct']>0]
print(f'FIXED overall: n={len(fx)} win={len(w)} rate={len(w)/len(fx)*100:.2f}% total_won={sum(t["net_won"] for t in fx):,}')
w2=[t for t in cur if t['net_pct']>0]
print(f'CURR  overall: n={len(cur)} win={len(w2)} rate={len(w2)/len(cur)*100:.2f}% total_won={sum(t["net_won"] for t in cur):,}')
