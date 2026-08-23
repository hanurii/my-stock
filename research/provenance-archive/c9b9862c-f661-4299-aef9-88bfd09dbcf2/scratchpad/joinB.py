# -*- coding: utf-8 -*-
import json,glob,os,sys
sys.path.insert(0,r'C:\Users\hanul\playground\my-stock\scripts')
os.chdir(r'C:\Users\hanul\playground\my-stock')
from canslim_lib.trend_template import compute_gate_margin
SP=r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'

files={}
for f in sorted(glob.glob(os.path.join(SP,'cand','*.json'))):
    d=json.load(open(f,encoding='utf-8'))
    asof=d['asof']
    # keep latest generated per asof
    if asof in files and files[asof][0] >= d['generated_at']:
        continue
    idx={}
    for c in d['candidates']:
        idx[c['code']]=c
    files[asof]=(d['generated_at'], idx)
asofs=sorted(files)
print('asof days:',len(asofs), asofs[0], asofs[-1])

def lookup(code, open_date, mode):
    # mode 'prev': strictly before open_date ; 'same': <= open_date
    cands=[a for a in asofs if (a<open_date if mode=='prev' else a<=open_date)]
    for a in reversed(cands):
        rec=files[a][1].get(code)
        if rec is None: continue
        m=compute_gate_margin(rec, rec.get('current_price'), rec.get('rs'), rs_min=80)
        if m is None: continue
        return a, rec, m
    return None,None,None

sc=json.load(open('public/data/scorecard.json',encoding='utf-8'))
rows=[]
for t in sc['trades']:
    a_p,rec_p,m_p=lookup(t['code'],t['open_date'],'prev')
    a_s,rec_s,m_s=lookup(t['code'],t['open_date'],'same')
    rows.append(dict(code=t['code'],name=t['name'],open_date=t['open_date'],close_date=t['close_date'],
        net=t['net_pct'],outcome=t['outcome'],setup=t.get('setup'),hold=t['hold_days'],
        asof_prev=a_p, score_prev=(m_p or {}).get('score'), tight_prev=(m_p or {}).get('tightest_label'),
        rs_prev=(rec_p or {}).get('rs'), allpass_prev=(rec_p or {}).get('all_pass'),
        asof_same=a_s, score_same=(m_s or {}).get('score'), tight_same=(m_s or {}).get('tightest_label'),
        rs_same=(rec_s or {}).get('rs'), allpass_same=(rec_s or {}).get('all_pass'),
        per_prev=(m_p or {}).get('per_condition')))
json.dump(rows,open(os.path.join(SP,'tradesB.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
miss_p=[r for r in rows if r['score_prev'] is None]
miss_s=[r for r in rows if r['score_same'] is None]
print('total',len(rows),'miss_prev',len(miss_p),'miss_same',len(miss_s))
for r in miss_p: print(' MISSprev',r['open_date'],r['code'],r['name'])
for r in miss_s: print(' MISSsame',r['open_date'],r['code'],r['name'])
# lag distribution
from collections import Counter
import datetime as dt
def lag(a,b):
    return (dt.date.fromisoformat(b)-dt.date.fromisoformat(a)).days
print('lag prev days:',Counter(lag(r['asof_prev'],r['open_date']) for r in rows if r['asof_prev']))
