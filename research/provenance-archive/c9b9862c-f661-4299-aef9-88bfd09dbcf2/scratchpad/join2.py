import json, sys, os
sys.path.insert(0, r'C:\Users\hanul\playground\my-stock\scripts')
os.chdir(r'C:\Users\hanul\playground\my-stock')
from canslim_lib.trend_template import compute_gate_margin

SP = r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
A = json.load(open(SP + r'\asof.json', encoding='utf-8'))
byasof = A['byasof']
dates = sorted(byasof)

def gm(asof, code):
    rec = byasof[asof]['recs'].get(code)
    if rec is None: return None
    return compute_gate_margin(rec, rec.get('current_price'), rec.get('rs'), rs_min=80)

def pick(code, buydate, strict):
    # strict: asof < buydate ; else asof <= buydate
    cands = [d for d in dates if (d < buydate if strict else d <= buydate)]
    for d in reversed(cands):
        m = gm(d, code)
        if m is not None:
            return d, m
    return None, None

sc = json.load(open('public/data/scorecard.json', encoding='utf-8'))
rows = []
for t in sc['trades']:
    dp, mp = pick(t['code'], t['open_date'], True)
    ds, ms = pick(t['code'], t['open_date'], False)
    rows.append(dict(code=t['code'], name=t['name'], open_date=t['open_date'], close_date=t.get('close_date'),
                     net=t['net_pct'], outcome=t['outcome'], hold=t.get('hold_days'), setup=t.get('setup'),
                     asof_prev=dp, sp=(mp or {}).get('score'), tight_prev=(mp or {}).get('tightest'),
                     per_prev=(mp or {}).get('per_condition'),
                     asof_same=ds, ss=(ms or {}).get('score'), tight_same=(ms or {}).get('tightest')))
json.dump(rows, open(SP + r'\myTrades.json','w',encoding='utf-8'), ensure_ascii=False)
miss = [r for r in rows if r['sp'] is None]
print('trades', len(rows), 'miss_prev', len(miss), 'miss_same', sum(1 for r in rows if r['ss'] is None))
from collections import Counter
import datetime
def lag(r):
    a=datetime.date.fromisoformat(r['asof_prev']); b=datetime.date.fromisoformat(r['open_date']); return (b-a).days
print('lag dist', Counter(lag(r) for r in rows if r['asof_prev']))
print('win', sum(1 for r in rows if r['outcome']=='win'), 'loss', sum(1 for r in rows if r['outcome']!='win'))
