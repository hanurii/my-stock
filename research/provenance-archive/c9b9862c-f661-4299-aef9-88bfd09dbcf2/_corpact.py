import json, sys, time
from pathlib import Path
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix as om

PD=Path('.cache/pdata')
files=[f for f in sorted(PD.glob('price_*.json')) if '20250602'<=f.name[6:14]<='20260820']
print('files', len(files))
raw={}  # code -> {iso: clpr}
for f in files:
    day=f.name[6:14]; iso=f'{day[:4]}-{day[4:6]}-{day[6:]}'
    d=json.loads(f.read_text(encoding='utf-8'))
    for c,r in d.items():
        cp=r.get('clpr')
        if cp: raw.setdefault(c,{})[iso]=float(cp)
print('codes in pdata window', len(raw))

flagged=[]
for p in Path('.cache/ohlcv/series').glob('*.json'):
    c=p.stem
    if c not in raw: continue
    s=om.get_series(c)
    if not s: continue
    rm=raw[c]
    ratios=[]
    for d,adj in zip(s['dates'], s['closes']):
        r=rm.get(d)
        if r: ratios.append((d, adj/r))
    if len(ratios)<50: continue
    vals=[v for _,v in ratios]
    mn,mx=min(vals),max(vals)
    if mx/mn > 1.02:   # >2% drift = corporate action inside window
        flagged.append((mx/mn, c, ratios[0][0], round(ratios[0][1],4), ratios[-1][0], round(ratios[-1][1],4)))
flagged.sort(reverse=True)
print(f'\nstocks with adjustment drift >2% inside 2025-06~2026-08: {len(flagged)}')
for f_ in flagged[:15]:
    print('  factor=%.3f  %s  %s adj/raw=%.4f -> %s adj/raw=%.4f'%f_)
