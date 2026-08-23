import pickle,os
import numpy as np
SP=r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
fw=pickle.load(open(os.path.join(SP,'fw3.pkl'),'rb'))
bad=[r for r in fw if abs(r['rec_price']/r['close_i']-1)*100>1]
print(len(bad))
for r in sorted(bad,key=lambda x:-abs(x['rec_price']/x['close_i']-1))[:20]:
    print('%s %s %-12s rec=%.1f close=%.1f candprice=%.1f diff=%.1f%% t10=%s exp=%.0f score=%.1f'%(
        r['date'],r['code'],r['name'][:10],r['rec_price'],r['close_i'],r['price'],(r['rec_price']/r['close_i']-1)*100,r['t10'],r['exp'] or -1,r['score']))
