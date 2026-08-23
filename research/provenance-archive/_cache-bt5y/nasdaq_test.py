# -*- coding: utf-8 -*-
"""나스닥 전일 종가 × 등가중 국면 — 5년 8개월 검정."""
import json, glob, os, random, collections, statistics as st, bisect
B=os.environ['LOCALAPPDATA']+'/Temp/bt5y/'
FEE=lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
EV=[]
for f in sorted(glob.glob(B+'bt_*.json')):
    EV+=[e for e in json.load(open(f,encoding='utf-8'))['events'] if e['result'] in ('win','loss')]
seen=set(); U=[]
for e in sorted(EV,key=lambda x:(x['entry_date'],x['code'])):
    k=(e['scan_date'],e['code'],e['pattern'])
    if k not in seen: seen.add(k); U.append(e)
EV=U
REG=json.load(open(B+'regime_long.json',encoding='utf-8'))
UP={d:u for d,u in zip(REG['dates'],REG['up_ew20'])}
NQ=json.load(open(B+'nasdaq.json',encoding='utf-8'))
nq_dates=sorted(NQ['up'])

def nq_before(korean_date):
    """한국 date 아침에 볼 수 있는 가장 최근 미국 종가의 방향(= 그 미국 날짜 < 한국 날짜)."""
    i=bisect.bisect_left(nq_dates, korean_date)   # korean_date 미만 중 최대
    return NQ['up'][nq_dates[i-1]] if i>0 else None

for e in EV:
    e['_nq']=nq_before(e['entry_date'])       # 매수 당일 아침 판단
    e['_reg']=UP.get(e['scan_date'])          # 전날 종가 국면

def m(g): return st.mean([FEE(x['gain_at_resolve_pct']) for x in g]) if g else float('nan')
def wr(g): return sum(1 for x in g if x['result']=='win')/len(g)*100 if g else float('nan')

print("="*86)
print("① 나스닥 전일 종가만 (5년 8개월, 3,681건)")
print("="*86)
a=[e for e in EV if e['_nq'] is True]; b=[e for e in EV if e['_nq'] is False]
print(f"  나스닥 상승 {len(a):>5}건  승률 {wr(a):.1f}%  거래당 {m(a):+.2f}%")
print(f"  나스닥 하락 {len(b):>5}건  승률 {wr(b):.1f}%  거래당 {m(b):+.2f}%")
print(f"  차이 {m(a)-m(b):+.2f}%p")

print()
print("="*86)
print("② 나스닥 × 등가중 국면 (사용자가 쓰는 🟢🟡🔴)")
print("="*86)
print(f"{'조합':<26}{'거래':>7}{'승률':>8}{'거래당':>10}")
print('-'*86)
cells=[('🟢 국면상승 + 나스닥상승', True, True),
       ('🟡 국면상승 + 나스닥하락', True, False),
       ('🟡 국면조정 + 나스닥상승', False, True),
       ('🔴 국면조정 + 나스닥하락', False, False)]
for lab,r,n in cells:
    g=[e for e in EV if e['_reg'] is r and e['_nq'] is n]
    print(f"{lab:<24}{len(g):>7}{wr(g):>7.1f}%{m(g):>+9.2f}%")

print()
print("="*86)
print("③ 연도별 — 🟢(둘 다 상승) vs 나머지  ★사전등록 기준: 전 구간 부호 일치")
print("="*86)
print(f"{'연도':<7}{'🟢 거래':>9}{'승률':>8}{'거래당':>10}   {'나머지':>9}{'승률':>8}{'거래당':>10}{'차이':>9}")
print('-'*86)
signs=[]
for y in ('2021','2022','2023','2024','2025','2026'):
    G=[e for e in EV if e['scan_date'][:4]==y and e['_reg'] is True and e['_nq'] is True]
    O=[e for e in EV if e['scan_date'][:4]==y and not (e['_reg'] is True and e['_nq'] is True)]
    if not G or not O: continue
    signs.append(m(G)-m(O))
    print(f"{y:<7}{len(G):>9}{wr(G):>7.1f}%{m(G):>+9.2f}%   {len(O):>9}{wr(O):>7.1f}%{m(O):>+9.2f}%{m(G)-m(O):>+8.2f}%p")
G=[e for e in EV if e['_reg'] is True and e['_nq'] is True]
O=[e for e in EV if not (e['_reg'] is True and e['_nq'] is True)]
print('-'*86)
print(f"{'전체':<7}{len(G):>9}{wr(G):>7.1f}%{m(G):>+9.2f}%   {len(O):>9}{wr(O):>7.1f}%{m(O):>+9.2f}%{m(G)-m(O):>+8.2f}%p")
print(f"\n[판정1] 전 구간 부호 일치: {'✅ 통과' if all(s>0 for s in signs) else '❌ 실패'}  ({['%+.2f'%s for s in signs]})")

# 원형이동 순열 (달력 구조 보존)
days=sorted({e['entry_date'] for e in EV})
byday=collections.defaultdict(list)
for e in EV: byday[e['entry_date']].append(FEE(e['gain_at_resolve_pct']))
lab=[(UP.get(d) is True) and (nq_before(d) is True) for d in days]
obs=m(G)-m(O)
cnt=tot=0
for sh in range(1,len(days)):
    L=lab[sh:]+lab[:sh]
    x=[v for d,l in zip(days,L) if l for v in byday[d]]
    z=[v for d,l in zip(days,L) if not l for v in byday[d]]
    if len(x)<100 or len(z)<100: continue
    tot+=1
    if (st.mean(x)-st.mean(z))>=obs: cnt+=1
print(f"[판정2] 원형이동 순열: 관측 {obs:+.2f}%p, {cnt}/{tot} 초과 → p={(cnt+1)/(tot+1):.4f}  "
      f"{'✅ 통과' if (cnt+1)/(tot+1)<0.05 else '❌ 실패'}")
