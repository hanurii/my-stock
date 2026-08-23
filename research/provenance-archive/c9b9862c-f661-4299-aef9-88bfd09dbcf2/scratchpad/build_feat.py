import json, sys, os
sys.path.insert(0, os.path.join(os.getcwd(), 'scripts'))
from canslim_lib import ohlcv_matrix
from canslim_lib.pivot_backtest import truncate_series

d = json.load(open('public/data/backtest-volatility-pilot.json', encoding='utf-8'))
events = d['events']
out = []
miss = 0
cache = {}
for e in events:
    code = e['code']
    if code not in cache:
        cache[code] = ohlcv_matrix.get_series(code)
    s = cache[code]
    rec = dict(e)
    rec['d1_close'] = None; rec['d1_ret'] = None
    rec['d2_close'] = None; rec['d1_high']=None; rec['d1_low']=None; rec['d1_vol']=None
    if s:
        dates = s['dates']
        if e['entry_date'] in dates:
            i = dates.index(e['entry_date'])
            c = s['closes'][i]
            rec['d1_close'] = c
            rec['d1_high'] = s['highs'][i]; rec['d1_low']=s['lows'][i]; rec['d1_vol']=s['volumes'][i]
            if c and e['entry_price']:
                rec['d1_ret'] = (c/e['entry_price']-1)*100
            rec['d1_ret_pivot'] = (c/e['pivot']-1)*100 if c else None
            if i+1 < len(dates):
                rec['d2_close'] = s['closes'][i+1]
                rec['d2_open'] = s['opens'][i+1] if 'opens' in s else None
        else:
            miss += 1
    else:
        miss += 1
    out.append(rec)
print('miss', miss, 'total', len(out), file=sys.stderr)
json.dump(out, open(sys.argv[1],'w',encoding='utf-8'), ensure_ascii=False)
