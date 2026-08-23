# -*- coding: utf-8 -*-
import json
d=json.load(open(r'C:\Users\hanul\playground\my-stock\public\data\scorecard-fills.json',encoding='utf-8'))
fills=d['fills']
codes=['009150','086670','219130','069730','222040','037760','192080','127120','019540','483650','005950','093190','204610','009190']
byCode={}
for i,f in enumerate(fills): byCode.setdefault(f['code'],[]).append((f,i))
for c in codes:
    s=sorted(byCode[c],key=lambda t:(t[0]['date'],t[1]))
    print('='*70)
    q=0; errshown=False
    for f,i in s:
        if f['side']=='buy': q+=f['qty']; mark=''
        else:
            q-=f['qty']; mark=' <<< ERROR(qty<0)' if q<0 and not errshown else ''
            if q<0 and not errshown: errshown=True
        print(f"{c} {f['name'][:8]:10s} {f['date']} {f['side']:4s} qty={f['qty']:6d} price={f['price']:>10} run_qty={q}{mark}")
        if q<0: q=0  # just for display continuation
