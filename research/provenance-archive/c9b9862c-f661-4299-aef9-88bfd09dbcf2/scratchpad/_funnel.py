import sys, numpy as np
from pathlib import Path
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix as om
from canslim_lib.pivot_backtest import truncate_series
from canslim_lib.vcp import evaluate_vcp
from canslim_lib.cheat import evaluate_cheat
from canslim_lib.power_play import evaluate_power_play

z=np.load(r'C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/aff259ca-1adc-48bc-b0c7-37693e4ef158/scratchpad/passmatrix.npz', allow_pickle=True)
dates=z['dates']; codes=z['codes']; ap=z['all_pass']; rs=z['rs']; el=z['eligible']

lo=int(np.searchsorted(dates,'2026-01-12'))
hi=int(np.searchsorted(dates,'2026-08-07',side='right'))
scan=list(range(lo,hi,7))
print('scan days:', len(scan), dates[scan[0]], '~', dates[scan[-1]])

tot_gate=0; act=0; act_er=0
for i in scan:
    d=str(dates[i])
    gate=codes[(ap[i])&(rs[i]>=80)&(el[i])]
    tot_gate+=len(gate)
    for c in gate:
        s=om.get_series(str(c))
        if not s: continue
        t=truncate_series(s,d)
        if len(t['closes'])<60: continue
        for fn in (evaluate_vcp, evaluate_cheat, evaluate_power_play):
            r=fn(t)
            if r.get('status')=='actionable' and r.get('pivot_price'):
                act+=1
                if r.get('entry_ready'): act_er+=1
n=len(scan)
print(f'gate: {tot_gate} ({tot_gate/n:.1f}/day)')
print(f'actionable: {act} ({act/n:.1f}/day)')
print(f'actionable AND entry_ready: {act_er} ({act_er/n:.1f}/day)')
print(f'inflation factor = {act/max(act_er,1):.2f}x')
