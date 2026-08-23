import json, sys
from pathlib import Path
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix as om
from canslim_lib.minervini_filter import MIN_TURNOVER_EOK_DEFAULT as MINT
print('liquidity threshold (eok):', MINT)

PD=Path('.cache/pdata')
files=[f for f in sorted(PD.glob('price_*.json')) if '20250602'<=f.name[6:14]<='20260820']
raw={}
for f in files:
    day=f.name[6:14]; iso=f'{day[:4]}-{day[4:6]}-{day[6:]}'
    d=json.loads(f.read_text(encoding='utf-8'))
    for c,r in d.items():
        cp=r.get('clpr'); tq=r.get('trqu')
        if cp: raw.setdefault(c,{})[iso]=(float(cp), float(tq or 0))

spur_pass=0; spur_fail=0; tot=0; affected=set()
for p in Path('.cache/ohlcv/series').glob('*.json'):
    c=p.stem
    if c not in raw: continue
    s=om.get_series(c)
    if not s: continue
    rm=raw[c]
    ds=s['dates']; cl=s['closes']
    idx={d:i for i,d in enumerate(ds)}
    # rolling 50d avg turnover, adjusted vs raw
    common=[d for d in ds if d in rm]
    if len(common)<60: continue
    adjT=[]; rawT=[]
    for d in common:
        i=idx[d]; rc,vol=rm[d]
        adjT.append(cl[i]*vol/1e8); rawT.append(rc*vol/1e8)
    for k in range(50,len(common)):
        a=sum(adjT[k-50:k])/50; r=sum(rawT[k-50:k])/50
        tot+=1
        if a>=MINT and r<MINT: spur_pass+=1; affected.add(c)
        elif a<MINT and r>=MINT: spur_fail+=1; affected.add(c)
print(f'stock-days evaluated: {tot}')
print(f'spurious PASS (adj>=thr but true<thr): {spur_pass}  ({spur_pass/tot:.2%})')
print(f'spurious FAIL (adj<thr but true>=thr): {spur_fail}  ({spur_fail/tot:.2%})')
print(f'distinct stocks affected: {len(affected)}')
