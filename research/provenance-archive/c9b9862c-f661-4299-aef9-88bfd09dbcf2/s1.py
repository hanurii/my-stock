import json, sys
from collections import Counter, defaultdict
SP="C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/"
ev=json.load(open(SP+'feat.json',encoding='utf-8'))
print('days_held dist for resolved:', Counter(e['days_held'] for e in ev if e['result'] in('win','loss')))
res=[e for e in ev if e['result'] in ('win','loss')]
print('resolved',len(res))
above=[e for e in res if e['d1_ret']>=0]
below=[e for e in res if e['d1_ret']<0]
def wr(xs): 
    w=sum(1 for x in xs if x['result']=='win'); return f"{w}/{len(xs)} = {w/len(xs)*100:.1f}%"
print('d1 close >= entry:', wr(above))
print('d1 close <  entry:', wr(below))
# 상세 컷
import statistics
for cut in [2,1,0,-1,-2,-3,-5]:
    g=[e for e in res if e['d1_ret']>=cut]; b=[e for e in res if e['d1_ret']<cut]
    print(f'cut {cut:>3}: above {wr(g)}   below {wr(b)}')
# d1_ret 분포
print('d1_ret quantiles', [round(x,2) for x in statistics.quantiles([e['d1_ret'] for e in res], n=10)])
print('mean d1_ret', round(statistics.mean([e['d1_ret'] for e in res]),3))
