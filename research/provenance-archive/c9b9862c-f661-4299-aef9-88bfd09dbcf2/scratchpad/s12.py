import sys; sys.path.insert(0,'C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad')
from base import load
import numpy as np, pandas as pd
from scipy import stats as st
ev,r=load(); r=r.reset_index(drop=True)
# 모호/미결착을 패로/승으로 몰아도 상위25% 우위가 유지되는지
e=ev.copy(); e['hi']=e['pct_all']>0.75
for how in ['loss','win']:
    e['w2']=e['result'].map({'win':1,'loss':0,'ambiguous':1 if how=='win' else 0,'unresolved':1 if how=='win' else 0})
    print(f'모호·미결착을 {how}으로: 상위25% {100*e[e.hi].w2.mean():.1f}%(n{e.hi.sum()}) vs 나머지 {100*e[~e.hi].w2.mean():.1f}%(n{(~e.hi).sum()})')
# 상위50% 동일
e['hi5']=e['pct_all']>0.5
for how in ['loss','win']:
    e['w2']=e['result'].map({'win':1,'loss':0,'ambiguous':1 if how=='win' else 0,'unresolved':1 if how=='win' else 0})
    print(f'모호·미결착을 {how}으로: 상위50% {100*e[e.hi5].w2.mean():.1f}% vs 나머지 {100*e[~e.hi5].w2.mean():.1f}%')
