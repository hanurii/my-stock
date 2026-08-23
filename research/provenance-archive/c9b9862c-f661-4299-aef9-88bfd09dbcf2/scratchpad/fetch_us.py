# -*- coding: utf-8 -*-
import FinanceDataReader as fdr, json, os
out={}
for sym in ('IXIC','US500','DJI'):
    try:
        df=fdr.DataReader(sym,'2020-09-01','2026-08-22')
        out[sym]={str(d.date()): float(c) for d,c in zip(df.index, df['Close']) if c==c}
        print(sym, len(out[sym]), list(out[sym].items())[0], list(out[sym].items())[-1])
    except Exception as ex:
        print(sym,'ERR',ex)
json.dump(out, open('us_idx.json','w'), indent=0)
