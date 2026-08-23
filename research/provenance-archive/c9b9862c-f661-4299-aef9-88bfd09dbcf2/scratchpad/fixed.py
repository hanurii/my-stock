import json, os, sys
import numpy as np
sys.path.insert(0,'scripts')
os.chdir('C:/Users/hanul/playground/my-stock')
from canslim_lib import ohlcv_matrix
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad'
J=json.load(open(SP+'/joined.json',encoding='utf-8'))
cache={}
def ser(code):
    if code not in cache:
        try: cache[code]=ohlcv_matrix.get_series(code)
        except Exception as e: cache[code]=None
    return cache[code]
s=ser(J[0]['code']); print(type(s), list(s.keys()) if isinstance(s,dict) else s._fields if hasattr(s,'_fields') else dir(s)[:20])
print(s['dates'][-3:] if isinstance(s,dict) else '')
