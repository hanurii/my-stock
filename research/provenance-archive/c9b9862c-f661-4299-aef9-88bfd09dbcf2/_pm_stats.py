import json, numpy as np
from pathlib import Path
P = Path(r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\aff259ca-1adc-48bc-b0c7-37693e4ef158\scratchpad\passmatrix.npz')
z = np.load(P, allow_pickle=True)
dates = z['dates']; codes = z['codes']
i0 = int(np.searchsorted(dates, '2025-06-02'))
ap = z['all_pass'][i0:]; el = z['eligible'][i0:]; pres = z['present'][i0:]; vol = z['vol'][i0:]
print('window', dates[i0], '~', dates[-1], 'days', ap.shape[0])
sel = ap & el
print('gate stock-days (all_pass & eligible):', int(sel.sum()), '| per day avg', round(sel.sum()/ap.shape[0],1))
print('unique codes ever passing gate:', int((sel.any(0)).sum()))
print('all_pass but NOT eligible stock-days:', int((ap & ~el).sum()))
# halted proxy: 5 consecutive zero-volume ending that day
v = np.nan_to_num(vol, nan=-1.0)
zero = (v == 0)
halt = np.zeros_like(zero)
for k in range(4, zero.shape[0]):
    halt[k] = zero[k-4:k+1].all(0)
print('all_pass & halted(5d zero vol) stock-days:', int((ap & halt).sum()))
# survivorship: codes that disappear before the last date
PD = Path(r'C:\Users\hanul\playground\my-stock\.cache\pdata')
last = json.loads((PD/'price_20260820.json').read_text(encoding='utf-8'))
alive = set(last.keys())
gone_mask = np.array([c not in alive for c in codes])
print('gate-passing codes that are gone by 2026-08-20:', int((sel.any(0) & gone_mask).sum()))
print('their gate stock-days:', int(sel[:, gone_mask].sum()))
