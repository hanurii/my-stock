# -*- coding: utf-8 -*-
import json, io, collections, statistics as st, bisect, math
EV=json.load(io.open('ev.json',encoding='utf-8'))
B='C:/Users/hanul/AppData/Local/Temp/bt5y/'
R=json.load(io.open(B+'regime_long.json',encoding='utf-8'))
rdates=R['dates']; ridx={d:i for i,d in enumerate(rdates)}
EW=R['ew']; KS=R['kospi']
NQ=json.load(io.open(B+'nasdaq.json',encoding='utf-8'))
nqd=sorted(NQ['close']); NC=NQ['close']
def prev_nq_ret(kd):
    i=bisect.bisect_left(nqd,kd)
    if i<2: return None
    return (NC[nqd[i-1]]/NC[nqd[i-2]]-1)*100
def dayret(s,d):
    i=ridx.get(d)
    return None if (i is None or i<1) else (s[i]/s[i-1]-1)*100
def fwd(s,d,k):
    i=ridx.get(d)
    return None if (i is None or i+k>=len(s)) else (s[i+k]/s[i]-1)*100
def m(g,k='net'): return st.mean([x[k] for x in g]) if g else float('nan')
def wr(g): return sum(1 for x in g if x['result']=='win')/len(g)*100 if g else float('nan')
for e in EV:
    e['ewd']=dayret(EW,e['entry_date']); e['ksd']=dayret(KS,e['entry_date'])
    e['nqr']=prev_nq_ret(e['entry_date'])
    e['f20']=fwd(EW,e['entry_date'],20); e['f5']=fwd(EW,e['entry_date'],5)
A=[e for e in EV if e['_reg'] is False and e['_nq'] is True]
Bc=[e for e in EV if e['_reg'] is False and e['_nq'] is False]
print("=== 가설검정 ①: '국내가 미국을 못 따라간 날' 이 나쁜가? (조정+NQ상승 781건 내부) ===")
follow=[e for e in A if e['ewd'] is not None and e['ewd']>0]
notf  =[e for e in A if e['ewd'] is not None and e['ewd']<=0]
print(f"  당일 등가중 ↑(따라감) n={len(follow):>4} 승률{wr(follow):>5.1f}% 거래당 {m(follow):+.2f}%")
print(f"  당일 등가중 ↓(못따라감) n={len(notf):>4} 승률{wr(notf):>5.1f}% 거래당 {m(notf):+.2f}%")
print(f"  → 가설이 맞으려면 '못따라감'이 더 나빠야 함. 실제 차이 {m(notf)-m(follow):+.2f}%p")
print(f"  참고) 조정+NQ하락 칸도 같은 분해: 당일↑ n={len([e for e in Bc if e['ewd']>0])} {m([e for e in Bc if e['ewd']>0]):+.2f}% / 당일↓ n={len([e for e in Bc if e['ewd']<=0])} {m([e for e in Bc if e['ewd']<=0]):+.2f}%")
print()
print("=== 가설검정 ②: 나스닥 상승'폭' 이 클수록 나쁜가? (조정 국면 1,297건) ===")
allc=[e for e in EV if e['_reg'] is False and e['nqr'] is not None]
allc.sort(key=lambda x:x['nqr'])
q=len(allc)//5
for i in range(5):
    g=allc[i*q:(i+1)*q] if i<4 else allc[4*q:]
    print(f"  나스닥 전일 {g[0]['nqr']:+5.2f}~{g[-1]['nqr']:+5.2f}%  n={len(g):>4} 승률{wr(g):>5.1f}% 거래당 {m(g):+.2f}%")
print()
print("=== 가설검정 ③: 이 칸은 '조정 중 반등(데드캣)' 인가? — 진입 후 시장 경로 ===")
for lab,g in [('조정+NQ상승',A),('조정+NQ하락',Bc)]:
    days=sorted({e['entry_date'] for e in g})
    f5=[fwd(EW,d,5) for d in days]; f5=[x for x in f5 if x is not None]
    f20=[fwd(EW,d,20) for d in days]; f20=[x for x in f20 if x is not None]
    pos20=sum(1 for x in f20 if x>0)/len(f20)*100
    # 진입일이 직전 5일 반등의 몇번째인가
    bk=[]
    for d in days:
        i=ridx[d]
        bk.append((EW[i]/EW[i-5]-1)*100 if i>=5 else None)
    bk=[x for x in bk if x is not None]
    print(f"  {lab}: 직전5일 등가중 {st.mean(bk):+.2f}% | 이후5일 {st.mean(f5):+.2f}% | 이후20일 {st.mean(f20):+.2f}% (플러스 비율 {pos20:.0f}%)")
print()
print("=== 실전 적용시 효과: '조정+나스닥상승' 날은 매수 금지 ===")
tot=sum(e['net'] for e in EV)
rest=[e for e in EV if not (e['_reg'] is False and e['_nq'] is True)]
print(f"  전체        n={len(EV):>5} 승률 {wr(EV):.1f}% 거래당 {m(EV):+.2f}%  합 {tot:+.0f}")
print(f"  이 칸 제외  n={len(rest):>5} 승률 {wr(rest):.1f}% 거래당 {m(rest):+.2f}%  합 {sum(e['net'] for e in rest):+.0f}")
print(f"  → 거래당 {m(rest)-m(EV):+.2f}%p 개선, 거래 {len(EV)-len(rest)}건(-{(len(EV)-len(rest))/len(EV)*100:.0f}%) 감소")
print()
print("=== 전·후반 분할 (사후 아님을 보는 최소한의 OOS) ===")
for lab,yrs in [('전반 2021-2023',{'2021','2022','2023'}),('후반 2024-2026',{'2024','2025','2026'})]:
    a=[e for e in A if e['entry_date'][:4] in yrs]; b=[e for e in Bc if e['entry_date'][:4] in yrs]
    print(f"  {lab}: 상승 n={len(a):>4} {m(a):+.2f}% / 하락 n={len(b):>4} {m(b):+.2f}% → 차이 {m(a)-m(b):+.2f}%p")
print()
print("=== 갭업·진입가 확인 (더 비싸게 산 것이 원인인가) ===")
for lab,g in [('조정+NQ상승',A),('조정+NQ하락',Bc)]:
    gu=[e for e in g if e['gap_up_pct']>0]
    print(f"  {lab}: 갭업 비율 {len(gu)/len(g)*100:.1f}%, 갭업 평균 {st.mean([e['gap_up_pct'] for e in gu]):.2f}%, 전체평균 {m(g,'gap_up_pct'):.2f}%")
print()
print("=== 승/패 구조 분해 ===")
for lab,g in [('조정+NQ상승',A),('조정+NQ하락',Bc)]:
    w=[e for e in g if e['result']=='win']; l=[e for e in g if e['result']=='loss']
    print(f"  {lab}: 승 {len(w)}건 {m(w):+.2f}% / 패 {len(l)}건 {m(l):+.2f}% / 승률 {wr(g):.1f}% / 본전승률 {abs(m(l))/(m(w)+abs(m(l)))*100:.1f}%")
