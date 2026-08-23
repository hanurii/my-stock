import json, sys, time
from pathlib import Path
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix as om

PD = Path('.cache/pdata')
files = sorted(PD.glob('price_*.json'))
files = [f for f in files if f.name[6:14] >= '20240102']
print('pdata files to read:', len(files))

CODES = ['005930','000660','204610']
acc = {c: {'dates':[],'closes':[],'opens':[],'highs':[],'lows':[],'volumes':[],'_flt':[]} for c in CODES}
t0=time.time()
for f in files:
    day = f.name[6:14]
    iso = f'{day[:4]}-{day[4:6]}-{day[6:]}'
    d = json.loads(f.read_text(encoding='utf-8'))
    for c in CODES:
        r = d.get(c)
        if not r: continue
        a = acc[c]
        a['dates'].append(iso); a['closes'].append(float(r['clpr']))
        a['opens'].append(float(r['mkp'])); a['highs'].append(float(r['hipr']))
        a['lows'].append(float(r['lopr'])); a['volumes'].append(float(r['trqu']))
        a['_flt'].append(r.get('fltRt'))
print('read sec', round(time.time()-t0,1))

for c in CODES:
    s = acc[c]
    om._apply_adjustment(s)
    cache = om.get_series(c)
    if not cache: print(c,'no cache'); continue
    cmap = dict(zip(cache['dates'], cache['closes']))
    rmap = dict(zip(s['dates'], s['closes']))
    common = sorted(set(cmap) & set(rmap))
    errs = [abs(rmap[d]-cmap[d])/cmap[d] for d in common if cmap[d]]
    print(f'{c}: recon {len(s["dates"])} bars {s["dates"][0]}~{s["dates"][-1]} | overlap {len(common)} | maxerr {max(errs):.7f} meanerr {sum(errs)/len(errs):.7f}')
    # worst offenders
    pairs = sorted(((abs(rmap[d]-cmap[d])/cmap[d], d) for d in common if cmap[d]), reverse=True)[:3]
    print('   worst:', [(d, round(e,6), cmap[d], rmap[d]) for e,d in pairs])
