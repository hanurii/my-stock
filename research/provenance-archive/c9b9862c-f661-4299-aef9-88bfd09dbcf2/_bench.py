import sys, time, json
from pathlib import Path
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix as om
from canslim_lib.pivot_backtest import truncate_series
from canslim_lib.vcp import evaluate_vcp
from canslim_lib.cheat import evaluate_cheat
from canslim_lib.power_play import evaluate_power_play
from canslim_lib.trend_template import evaluate_trend_template

codes=[p.stem for p in Path('.cache/ohlcv/series').glob('*.json')]
t0=time.time(); series={}
for c in codes:
    s=om.get_series(c)
    if s: series[c]=s
print(f'load all {len(series)} series: {time.time()-t0:.1f}s')

ASOF='2026-06-01'
t0=time.time(); tr={c:truncate_series(s,ASOF) for c,s in series.items()}
t_tr=time.time()-t0; print(f'truncate all: {t_tr:.2f}s')

# detector cost on full universe (worst case: run on everything)
t0=time.time(); n=0
for c,s in list(tr.items()):
    if len(s['closes'])<60: continue
    evaluate_vcp(s); evaluate_cheat(s); evaluate_power_play(s); n+=1
t_det=time.time()-t0
print(f'3 detectors x {n} codes: {t_det:.2f}s  ({t_det/max(n,1)*1000:.3f} ms/code)')
