import json
from collections import Counter
SP="C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/"
ev=json.load(open(SP+'feat.json',encoding='utf-8'))
print(Counter((e['result'], e['days_held']==0) for e in ev))
amb=[e for e in ev if e['result']=='ambiguous']
print('ambiguous days_held', Counter(e['days_held'] for e in amb))
unr=[e for e in ev if e['result']=='unresolved']
print('unresolved', len(unr), [ (u['entry_date'],u['days_held'],u['gain_at_resolve_pct']) for u in unr])
import statistics
print('gap_up mean', round(statistics.mean(e['gap_up_pct'] for e in ev),2), 'median', round(statistics.median(e['gap_up_pct'] for e in ev),2))
print('entry/pivot ratio mean', round(statistics.mean(e['entry_price']/e['pivot'] for e in ev),4))
