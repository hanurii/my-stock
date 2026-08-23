# -*- coding: utf-8 -*-
import json, io, collections, statistics as st, bisect
EV=json.load(io.open('ev.json',encoding='utf-8'))
B='C:/Users/hanul/AppData/Local/Temp/bt5y/'
R=json.load(io.open(B+'regime_long.json',encoding='utf-8'))
rdates=R['dates']; ridx={d:i for i,d in enumerate(rdates)}
NQ=json.load(io.open(B+'nasdaq.json',encoding='utf-8'))
nqd=sorted(NQ['up'])
def nq_lag(kd,k=1):
    i=bisect.bisect_left(nqd,kd)
    return NQ['up'][nqd[i-k]] if i-k>=0 else None
def m(g): return st.mean([x['net'] for x in g]) if g else float('nan')
def wr(g): return sum(1 for x in g if x['result']=='win')/len(g)*100 if g else float('nan')
UPS={'등가중20MA(현행)':dict(zip(rdates,R['up_ew20'])),
     '코스피20MA':dict(zip(rdates,R['up_ks20']))}
# 시총가중 20MA 직접 계산
cw=R['cw']; up_cw=[None]*len(cw)
for i in range(len(cw)):
    if i>=19: up_cw[i]= cw[i] > sum(cw[i-19:i+1])/20
UPS['시총가중20MA']=dict(zip(rdates,up_cw))
print("=== 국면 정의를 바꿔도 '조정+나스닥상승' 칸이 살아있나 ===")
print(f"{'국면정의':<18}{'조정+NQ↑ n':>12}{'거래당':>9}{'조정+NQ↓ n':>12}{'거래당':>9}{'차이':>9}")
for name,UP in UPS.items():
    a=[e for e in EV if UP.get(e['scan_date']) is False and nq_lag(e['entry_date']) is True]
    b=[e for e in EV if UP.get(e['scan_date']) is False and nq_lag(e['entry_date']) is False]
    print(f"{name:<16}{len(a):>12}{m(a):>+8.2f}%{len(b):>12}{m(b):>+8.2f}%{m(a)-m(b):>+8.2f}%p")
print()
print("=== 나스닥 시차를 바꾸면 (진짜 신호면 lag1만 살아야) ===")
UP=UPS['등가중20MA(현행)']
for k in (1,2,3,5):
    a=[e for e in EV if UP.get(e['scan_date']) is False and nq_lag(e['entry_date'],k) is True]
    b=[e for e in EV if UP.get(e['scan_date']) is False and nq_lag(e['entry_date'],k) is False]
    print(f"  나스닥 {k}일 전 방향: 상승 n={len(a):>4} {m(a):>+6.2f}% / 하락 n={len(b):>4} {m(b):>+6.2f}% → 차이 {m(a)-m(b):+.2f}%p")
print()
print("=== 상승국면에서도 같은 방향인가 (신호라면 일관돼야) ===")
for k in (1,2,3):
    a=[e for e in EV if UP.get(e['scan_date']) is True and nq_lag(e['entry_date'],k) is True]
    b=[e for e in EV if UP.get(e['scan_date']) is True and nq_lag(e['entry_date'],k) is False]
    print(f"  lag{k}: 상승 n={len(a):>4} {m(a):>+6.2f}% / 하락 n={len(b):>4} {m(b):>+6.2f}% → 차이 {m(a)-m(b):+.2f}%p")
