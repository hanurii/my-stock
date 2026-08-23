import json,os,sys,numpy as np
sys.path.insert(0,'scripts'); os.chdir('C:/Users/hanul/playground/my-stock')
from canslim_lib import ohlcv_matrix
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad'
R=json.load(open(SP+'/H10.json',encoding='utf-8'))
bad=sorted([x for x in R if x['rec'] and abs(x['rec']/x['entry']-1)>0.01], key=lambda x:-abs(x['rec']/x['entry']-1))
print('outliers',len(bad))
for x in bad[:20]:
    print(f"{x['date']} {x['code']} {x['name']:<12} rec={x['rec']:>12,.0f} close={x['entry']:>12,.0f} diff={(x['rec']/x['entry']-1)*100:+8.1f}%  ext={x['ext']:.0f}% score={x['score']}")
print()
# also check candidate-file current_price vs ohlcv close
J=json.load(open(SP+'/joined.json',encoding='utf-8'))
dd=[]
for r in J:
    s=ohlcv_matrix.get_series(r['code'])
    if not s: continue
    try: i=s['dates'].index(r['date'])
    except ValueError: continue
    dd.append((abs(r['px_a']/s['closes'][i]-1)*100, r))
dd.sort(key=lambda t:-t[0])
print('cand current_price vs ohlcv close: median %.4f%%  >1%% count %d / %d'%(np.median([d for d,_ in dd]), sum(1 for d,_ in dd if d>1), len(dd)))
for d,r in dd[:8]:
    print(f"  {r['date']} {r['code']} {r['name']:<12} cand={r['px_a']:>12,.0f} ohlcv_close diff={d:+.1f}%")
