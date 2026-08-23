import sys, time, json
from pathlib import Path
sys.path.insert(0, r'C:\Users\hanul\playground\my-stock\scripts')
from canslim_lib.pivot_backtest import truncate_series
from canslim_lib.trend_template import evaluate_trend_template
from canslim_lib.vcp import evaluate_vcp
from canslim_lib.cheat import evaluate_cheat
from canslim_lib.power_play import evaluate_power_play
from screen_trend_template import _compute_rs_for_all

SER = Path(r'C:\Users\hanul\playground\my-stock\.cache\ohlcv\series')
t0 = time.perf_counter()
full = {}
for f in sorted(SER.glob('*.json')):
    try:
        full[f.stem] = json.loads(f.read_text(encoding='utf-8'))
    except Exception:
        pass
print('load all series', round(time.perf_counter()-t0, 1), 's', len(full))

D = '2026-06-01'
t = time.perf_counter()
st = {c: truncate_series(s, D) for c, s in full.items()}
st = {c: s for c, s in st.items() if len(s['closes']) >= 200}
t1 = time.perf_counter(); print('truncate', round(t1-t, 2), 's ->', len(st))
rs = _compute_rs_for_all([{'code': c, 'closes': s['closes'], 'ok': True} for c, s in st.items()])
t2 = time.perf_counter(); print('rs', round(t2-t1, 2), 's')
pas = [c for c, s in st.items()
       if evaluate_trend_template(s['closes'], rs=(rs.get(c) or {}).get('rs'), rs_min=80)['pass']]
t3 = time.perf_counter(); print('tt', round(t3-t2, 2), 's passers', len(pas))
for c in pas:
    evaluate_vcp(st[c]); evaluate_cheat(st[c]); evaluate_power_play(st[c])
t4 = time.perf_counter(); print('detectors', round(t4-t3, 2), 's')
print('per-scan-date', round(t4-t, 2), 's -> 300 dates =', round((t4-t)*300/60, 1), 'min')
