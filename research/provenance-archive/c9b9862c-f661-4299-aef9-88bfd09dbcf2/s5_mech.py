# -*- coding: utf-8 -*-
import json, glob, os, bisect, collections, statistics as st
B=os.environ['LOCALAPPDATA']+'/Temp/bt5y/'
NQ=json.load(open(B+'nasdaq.json',encoding='utf-8')); nqd=sorted(NQ['up'])
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
def before(k,s=0):
    i=bisect.bisect_left(nqd,k)+s
    return nqd[i-1] if 0<i<=len(nqd) else None
for e in EV:
    e['net']=FEE(e['gain_at_resolve_pct']); e['nq']=NQ['up'][before(e['entry_date'])]
    e['reg']=UP.get(e['scan_date'])
def m(g): return st.mean([x['net'] for x in g]) if g else float('nan')
def wr(g): return sum(1 for x in g if x['result']=='win')/len(g)*100 if g else float('nan')

print("="*92); print("⑤ 연도별 — 나스닥 상승 vs 하락 (반전이 전 구간에서 일관되는가)"); print("="*92)
print(f"{'연도':<7}{'상승n':>7}{'승률':>7}{'거래당':>9}   {'하락n':>7}{'승률':>7}{'거래당':>9}{'차이':>10}")
print('-'*92)
sg=[]
for y in ('2021','2022','2023','2024','2025','2026'):
    a=[e for e in EV if e['entry_date'][:4]==y and e['nq']]; b=[e for e in EV if e['entry_date'][:4]==y and not e['nq']]
    if not a or not b: continue
    sg.append(m(a)-m(b))
    print(f"{y:<7}{len(a):>7}{wr(a):>6.1f}%{m(a):>+8.2f}%   {len(b):>7}{wr(b):>6.1f}%{m(b):>+8.2f}%{m(a)-m(b):>+9.2f}%p")
print(f"\n  음(-) 부호 연도: {sum(1 for s in sg if s<0)}/{len(sg)}   → 일관성 {'약함' if sum(1 for s in sg if s<0)<5 else '강함'}")

print("\n"+"="*92); print("⑥ 국면을 통제하면 반전이 남는가 (같은 국면 안에서 비교)"); print("="*92)
for rl,rv in (('상승국면',True),('조정국면',False)):
    a=[e for e in EV if e['reg'] is rv and e['nq']]; b=[e for e in EV if e['reg'] is rv and not e['nq']]
    print(f"  {rl}: 나스닥상승 {len(a):>5}건 {m(a):+.2f}%  vs  나스닥하락 {len(b):>5}건 {m(b):+.2f}%   차이 {m(a)-m(b):+.2f}%p")
# 국면 구성 차이
for lab,g in (('나스닥상승일',[e for e in EV if e['nq']]),('나스닥하락일',[e for e in EV if not e['nq']])):
    up=sum(1 for e in g if e['reg'] is True)
    print(f"  {lab}: 상승국면 비중 {up/len(g)*100:.1f}%")

print("\n"+"="*92); print("⑦ 메커니즘 — 나스닥 상승 다음날 한국은 갭업(진입가가 비싸짐)"); print("="*92)
for lab,g in (('나스닥 상승 후',[e for e in EV if e['nq']]),('나스닥 하락 후',[e for e in EV if not e['nq']])):
    gu=[e['gap_up_pct'] for e in g if e.get('gap_up_pct') is not None]
    print(f"  {lab}: 평균 갭 {st.mean(gu):+.2f}%  중앙 {st.median(gu):+.2f}%  갭>3% 비중 {sum(1 for x in gu if x>3)/len(gu)*100:.1f}%  n={len(gu)}")
# 갭 구간 통제
print("\n  [갭 구간별로 쪼개 통제]")
print(f"  {'갭 구간':<14}{'상승n':>7}{'거래당':>9}   {'하락n':>7}{'거래당':>9}{'차이':>10}")
for lo,hi,nm in ((-99,0,'갭 <=0%'),(0,2,'0~2%'),(2,5,'2~5%'),(5,99,'>5%')):
    a=[e for e in EV if e['nq'] and lo<e.get('gap_up_pct',0)<=hi]
    b=[e for e in EV if not e['nq'] and lo<e.get('gap_up_pct',0)<=hi]
    if len(a)<20 or len(b)<20: continue
    print(f"  {nm:<14}{len(a):>7}{m(a):>+8.2f}%   {len(b):>7}{m(b):>+8.2f}%{m(a)-m(b):>+9.2f}%p")
