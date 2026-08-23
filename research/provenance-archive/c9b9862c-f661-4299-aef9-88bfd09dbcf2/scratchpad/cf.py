import json, os, math
ROOT=r"C:/Users/hanul/playground/my-stock"
d=json.load(open(os.path.join(ROOT,'public/data/scorecard.json'),encoding='utf-8'))
trades=d['trades']

def series(code):
    p=os.path.join(ROOT,'.cache/ohlcv/series',code+'.json')
    if not os.path.exists(p): return None
    return json.load(open(p,encoding='utf-8'))

# data cutoff
s=series('005930') or series('007340')
print('last date sample:', s['dates'][-1], 'n=',len(s['dates']))

def counterfactual(tr, tie='loss', start_offset=1):
    s=series(tr['code'])
    if s is None: return None
    dates=s['dates']; hi=s['highs']; lo=s['lows']; cl=s['closes']
    od=tr['open_date'].replace('-','')
    # find index of open_date
    idx=None
    for i,dt in enumerate(dates):
        if dt.replace('-','')==od: idx=i; break
    if idx is None: return None
    buy=tr['avg_buy']
    tgt=buy*1.20; stp=buy*0.90
    for i in range(idx+start_offset, len(dates)):
        h=hi[i]; l=lo[i]
        hit_t = h>=tgt; hit_s = l<=stp
        if hit_t and hit_s:
            return (20.0 if tie=='win' else -10.0, dates[i], 'ambig')
        if hit_t: return (20.0, dates[i], 'win')
        if hit_s: return (-10.0, dates[i], 'loss')
    return ((cl[-1]/buy-1)*100, dates[-1], 'open')

rows=[]
for tr in trades:
    cf=counterfactual(tr)
    rows.append((tr,cf))
missing=[t['code'] for t,c in rows if c is None]
print('missing series:',missing)
json.dump([{**t,'cf_pct':(c[0] if c else None),'cf_date':(c[1] if c else None),'cf_state':(c[2] if c else None)} for t,c in rows], open(os.path.join(os.path.dirname(__file__),'cf.json'),'w',encoding='utf-8'), ensure_ascii=False)
