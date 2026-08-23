# -*- coding: utf-8 -*-
import json, io, collections, statistics as st
EV=json.load(io.open('ev.json',encoding='utf-8'))
B='C:/Users/hanul/AppData/Local/Temp/bt5y/'
R=json.load(io.open(B+'regime_long.json',encoding='utf-8'))
rdates=R['dates']; ridx={d:i for i,d in enumerate(rdates)}
EW=R['ew']; KS=R['kospi']; CW=R['cw']
def m(g): return st.mean([x['net'] for x in g]) if g else float('nan')
def wr(g): return sum(1 for x in g if x['result']=='win')/len(g)*100 if g else float('nan')
A=[e for e in EV if e['_reg'] is False and e['_nq'] is True]   # 조정+NQ상승
Bc=[e for e in EV if e['_reg'] is False and e['_nq'] is False] # 조정+NQ하락
print('=== 거래일 집중도 ===')
for lab,g in [('조정+NQ상승',A),('조정+NQ하락',Bc)]:
    byd=collections.Counter(e['entry_date'] for e in g)
    nd=len(byd)
    top=byd.most_common(8)
    print(f"{lab}: {len(g)}건 / 진입일 {nd}일 / 일평균 {len(g)/nd:.1f}건")
    print('   최다일:', ', '.join(f'{d}({c})' for d,c in top))
    # 상위 10일이 차지하는 비중
    s=sorted(byd.values(),reverse=True)
    print(f"   상위10일 비중 {sum(s[:10])/len(g)*100:.1f}%  상위20일 {sum(s[:20])/len(g)*100:.1f}%")
print()
print('=== 월별 (조정+NQ상승) 손실 상위 ===')
mm=collections.defaultdict(list)
for e in A: mm[e['entry_date'][:7]].append(e)
rows=sorted(mm.items(), key=lambda kv: sum(x['net'] for x in kv[1]))
print('  월      n   거래당    월합(건수x거래당)')
for k,v in rows[:10]:
    print(f"  {k}  {len(v):>3}  {m(v):>+7.2f}%   {sum(x['net'] for x in v):>+8.1f}")
print('  ... 상위(플러스) ...')
for k,v in rows[-5:]:
    print(f"  {k}  {len(v):>3}  {m(v):>+7.2f}%   {sum(x['net'] for x in v):>+8.1f}")
tot=sum(x['net'] for x in A)
worst5=sum(sum(x['net'] for x in v) for k,v in rows[:5])
print(f"\n  전체 합 {tot:+.1f} / 최악 5개월 합 {worst5:+.1f}  → 최악5개월 제거시 거래당 {(tot-worst5)/(len(A)-sum(len(v) for k,v in rows[:5])):+.2f}%")
print()
print('=== 가설: 그날 국내 지수 수익률 ===')
def ret(idx, d, k=1):
    i=ridx.get(d)
    if i is None or i+k>=len(idx) or i-0<0: return None
    return None
def dayret(series,d):
    i=ridx.get(d)
    if i is None or i<1: return None
    return (series[i]/series[i-1]-1)*100
def fwd(series,d,k):
    i=ridx.get(d)
    if i is None or i+k>=len(series): return None
    return (series[i+k]/series[i]-1)*100
print(f"{'칸':<14}{'n':>5}{'진입일 EW당일':>13}{'KOSPI당일':>11}{'전일(scan) EW':>14}{'EW +5일':>9}{'EW +20일':>10}")
for lab,g in [('조정+NQ상승',A),('조정+NQ하락',Bc),
              ('상승+NQ상승',[e for e in EV if e['_reg'] and e['_nq']]),
              ('상승+NQ하락',[e for e in EV if e['_reg'] and not e['_nq']])]:
    days=sorted({e['entry_date'] for e in g})
    d0=[dayret(EW,d) for d in days]; d0=[x for x in d0 if x is not None]
    k0=[dayret(KS,d) for d in days]; k0=[x for x in k0 if x is not None]
    sd=sorted({e['scan_date'] for e in g})
    s0=[dayret(EW,d) for d in sd]; s0=[x for x in s0 if x is not None]
    f5=[fwd(EW,d,5) for d in days]; f5=[x for x in f5 if x is not None]
    f20=[fwd(EW,d,20) for d in days]; f20=[x for x in f20 if x is not None]
    print(f"{lab:<14}{len(days):>5}{st.mean(d0):>+12.2f}%{st.mean(k0):>+10.2f}%{st.mean(s0):>+13.2f}%{st.mean(f5):>+8.2f}%{st.mean(f20):>+9.2f}%")
print()
print('=== 조정 국면 깊이(20MA 대비 등가중 이격) 비교 ===')
import statistics
def ma(series,i,n=20):
    if i<n-1: return None
    return sum(series[i-n+1:i+1])/n
for lab,g in [('조정+NQ상승',A),('조정+NQ하락',Bc)]:
    days=sorted({e['scan_date'] for e in g})
    dev=[]
    for d in days:
        i=ridx.get(d)
        if i is None: continue
        mv=ma(EW,i)
        if mv: dev.append((EW[i]/mv-1)*100)
    print(f"{lab}: 스캔일 {len(dev)}일, 20MA 이격 평균 {st.mean(dev):+.2f}% 중앙 {st.median(dev):+.2f}%")
