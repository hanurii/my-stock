# -*- coding: utf-8 -*-
import json, glob, os, io, bisect, collections, statistics as st
B='C:/Users/hanul/AppData/Local/Temp/bt5y/'
FEE=lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
EV=[]
for f in sorted(glob.glob(B+'bt_*.json')):
    d=json.load(io.open(f,encoding='utf-8'))
    EV+=[e for e in d['events'] if e['result'] in ('win','loss')]
print('raw win/loss:',len(EV))
seen=set(); U=[]
for e in sorted(EV,key=lambda x:(x['entry_date'],x['code'],x['pattern'])):
    k=(e['scan_date'],e['code'],e['pattern'])
    if k in seen: continue
    seen.add(k); U.append(e)
EV=U
print('dedup:',len(EV))
R=json.load(io.open(B+'regime_long.json',encoding='utf-8'))
UP=dict(zip(R['dates'],R['up_ew20']))
EW=dict(zip(R['dates'],R['ew']))
KS=dict(zip(R['dates'],R['kospi']))
rdates=R['dates']
ridx={d:i for i,d in enumerate(rdates)}
NQ=json.load(io.open(B+'nasdaq.json',encoding='utf-8'))
nqd=sorted(NQ['up'])
def nq_before(kd):
    i=bisect.bisect_left(nqd,kd)
    return NQ['up'][nqd[i-1]] if i>0 else None
def nq_date_before(kd):
    i=bisect.bisect_left(nqd,kd)
    return nqd[i-1] if i>0 else None
for e in EV:
    e['_nq']=nq_before(e['entry_date'])
    e['_nqd']=nq_date_before(e['entry_date'])
    e['_reg']=UP.get(e['scan_date'])
    e['net']=FEE(e['gain_at_resolve_pct'])
EV=[e for e in EV if e['_reg'] is not None and e['_nq'] is not None]
print('usable(reg&nq known):',len(EV))
def m(g): return st.mean([x['net'] for x in g]) if g else float('nan')
def wr(g): return sum(1 for x in g if x['result']=='win')/len(g)*100 if g else float('nan')
print()
print('== 전체 ==')
print(f"n={len(EV)} 승률 {wr(EV):.1f}% 거래당 {m(EV):+.2f}% (원수익 {st.mean([e['gain_at_resolve_pct'] for e in EV]):+.2f}%)")
W=[e for e in EV if e['result']=='win']; L=[e for e in EV if e['result']=='loss']
print(f"승 {len(W)} {st.mean([e['gain_at_resolve_pct'] for e in W]):+.2f}% / 패 {len(L)} {st.mean([e['gain_at_resolve_pct'] for e in L]):+.2f}%")
print()
print('== 4칸 ==')
cells={}
for lab,r,n in [('상승+NQ상승',True,True),('상승+NQ하락',True,False),('조정+NQ상승',False,True),('조정+NQ하락',False,False)]:
    g=[e for e in EV if e['_reg'] is r and e['_nq'] is n]
    cells[lab]=g
    print(f"{lab:<14}{len(g):>6}건 승률{wr(g):>6.1f}% 거래당{m(g):>+7.2f}%  중앙{st.median([x['net'] for x in g]):>+7.2f}%")
print()
print('== 조정칸 연도별 ==')
print(f"{'연도':<6}{'조정+NQ상승 n':>14}{'승률':>7}{'거래당':>9}   {'조정+NQ하락 n':>14}{'승률':>7}{'거래당':>9}{'차이':>10}")
for y in ['2021','2022','2023','2024','2025','2026']:
    a=[e for e in cells['조정+NQ상승'] if e['entry_date'][:4]==y]
    b=[e for e in cells['조정+NQ하락'] if e['entry_date'][:4]==y]
    d=(m(a)-m(b)) if a and b else float('nan')
    print(f"{y:<6}{len(a):>14}{wr(a):>6.1f}%{m(a):>+8.2f}%   {len(b):>14}{wr(b):>6.1f}%{m(b):>+8.2f}%{d:>+9.2f}%p")
a=cells['조정+NQ상승']; b=cells['조정+NQ하락']
print(f"{'전체':<6}{len(a):>14}{wr(a):>6.1f}%{m(a):>+8.2f}%   {len(b):>14}{wr(b):>6.1f}%{m(b):>+8.2f}%{m(a)-m(b):>+9.2f}%p")
json.dump([{k:v for k,v in e.items()} for e in EV], io.open('C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/ev.json','w',encoding='utf-8'))
