import json,os,sys,collections
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix
S=os.environ['SCRATCH']
rows=json.load(open(os.path.join(S,'taskC','joinedC.json'),encoding='utf-8'))
cache={}
def ser(code):
    if code not in cache:
        try: cache[code]=ohlcv_matrix.get_series(code)
        except Exception as e: cache[code]=None
    return cache[code]
s=ser(rows[0]['code'])
print(type(s), list(s.keys())[:8] if isinstance(s,dict) else None)
if isinstance(s,dict):
    print(s['dates'][-3:], s['closes'][-3:])
