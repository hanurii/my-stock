import json, sys, time, random
from pathlib import Path
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix as om

PD = Path('.cache/pdata')
files = sorted(PD.glob('price_*.json'))
files = [f for f in files if f.name[6:14] >= '20241201']

cache_codes = sorted(p.stem for p in Path('.cache/ohlcv/series').glob('*.json'))
random.seed(7)
CODES = set(random.sample(cache_codes, 400))

acc = {c: {'dates':[],'closes':[],'opens':[],'highs':[],'lows':[],'volumes':[],'_flt':[]} for c in CODES}
t0=time.time()
for f in files:
    day = f.name[6:14]; iso = f'{day[:4]}-{day[4:6]}-{day[6:]}'
    d = json.loads(f.read_text(encoding='utf-8'))
    for c in CODES:
        r = d.get(c)
        if not r: continue
        a = acc[c]
        a['dates'].append(iso); a['closes'].append(float(r['clpr']))
        a['opens'].append(float(r['mkp'])); a['highs'].append(float(r['hipr']))
        a['lows'].append(float(r['lopr'])); a['volumes'].append(float(r['trqu']))
        a['_flt'].append(r.get('fltRt'))
print('read sec', round(time.time()-t0,1), 'files', len(files))

rows=[]
for c in sorted(CODES):
    s = acc[c]
    if len(s['dates'])<10: continue
    om._apply_adjustment(s)
    cache = om.get_series(c)
    if not cache: continue
    cmap = dict(zip(cache['dates'], cache['closes'])); rmap = dict(zip(s['dates'], s['closes']))
    common = sorted(set(cmap)&set(rmap))
    if len(common)<50: continue
    errs = [(abs(rmap[d]-cmap[d])/cmap[d], d) for d in common if cmap[d]]
    mx, mxd = max(errs)
    rows.append((mx, c, mxd, len(common), cmap[mxd], rmap[mxd]))
rows.sort(reverse=True)
print('compared codes:', len(rows))
import statistics
print('max-err distribution: >1%%: %d, >0.1%%: %d, >1e-5: %d, exact(0): %d' % (
  sum(1 for r in rows if r[0]>0.01), sum(1 for r in rows if r[0]>0.001),
  sum(1 for r in rows if r[0]>1e-5), sum(1 for r in rows if r[0]==0)))
print('\nWORST 12:')
for mx,c,d,n,cv,rv in rows[:12]:
    print(f'  {c} maxerr={mx:.4%} on {d}  overlap={n} cache={cv} recon={rv}')
