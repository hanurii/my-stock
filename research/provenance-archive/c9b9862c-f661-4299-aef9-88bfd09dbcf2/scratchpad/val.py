# -*- coding: utf-8 -*-
import json,math,sys
sys.path.insert(0,r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad')
exec(open(r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad\fix.py',encoding='utf-8').read().split("cur,_,_")[0])
cur,_,_=match(lambda t:(t[0]['date'],t[1]),'cur')
disk=json.load(open(r'C:\Users\hanul\playground\my-stock\public\data\scorecard.json',encoding='utf-8'))['trades']
mine={(t['code'],t['open_date'],t['close_date']):t for t in cur}
bad=0
for t in disk:
    k=(t['code'],t['open_date'],t['close_date']); m=mine.get(k)
    if m is None: print('MISSING',k); bad+=1; continue
    for f in ['net_pct','gross_pct','net_won']:
        if abs(m[f]-t[f])>0.005: print('DIFF',k,f,m[f],t[f]); bad+=1
print('replication mismatches:',bad,'of',len(disk))
