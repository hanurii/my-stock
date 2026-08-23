# -*- coding: utf-8 -*-
import json, os, bisect, datetime as dt, collections, statistics as st, random
B=os.environ['LOCALAPPDATA']+'/Temp/bt5y/'
S=os.path.dirname(__file__)
NQ=json.load(open(B+'nasdaq.json',encoding='utf-8')); nqd=sorted(NQ['up'])
EV=json.load(open(S+'/EV.json',encoding='utf-8'))
REG=json.load(open(B+'regime_long.json',encoding='utf-8'))
UP={d:u for d,u in zip(REG['dates'],REG['up_ew20'])}
FEE=lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
for e in EV: e['net']=FEE(e['gain_at_resolve_pct'])

def before(k,shift=0):
    """shift=0: k 미만 최대 미국날(정본). shift=+1: k 이상 최소(룩어헤드). shift=-1: 한 칸 더 과거."""
    i=bisect.bisect_left(nqd,k)+shift
    return nqd[i-1] if 0<i<=len(nqd) else None
def exact_prev(k):
    """캘린더상 정확히 하루 전 미국날짜만. 없으면(주말·휴일) None → 제외."""
    p=(dt.date.fromisoformat(k)-dt.timedelta(days=1)).isoformat()
    return p if p in NQ['up'] else None

VAR={
 '정본 : entry_date 미만 최대 미국날'      : lambda e: before(e['entry_date'],0),
 '(a) scan_date 미만 최대 미국날'          : lambda e: before(e['scan_date'],0),
 '(b) entry_date-1 정확매칭(휴일 제외)'    : lambda e: exact_prev(e['entry_date']),
 '(c-1) 한 칸 미래 = 룩어헤드(당일 미국종가)': lambda e: before(e['entry_date'],+1),
 '(c-2) 한 칸 과거로 밀림(전전 미국날)'    : lambda e: before(e['entry_date'],-1),
}
def wr(g): return sum(1 for x in g if x['result']=='win')/len(g)*100 if g else float('nan')
def m(g):  return st.mean([x['net'] for x in g]) if g else float('nan')

# 일단위 클러스터 t (같은 한국 날짜 = 라벨 공유 → 유효 표본은 '일')
def day_test(evs, key):
    byday=collections.defaultdict(list)
    for e in evs:
        u=key(e)
        if u is None: continue
        byday[(e['entry_date'],NQ['up'][u])].append(e['net'])
    A=[st.mean(v) for (d,l),v in byday.items() if l]      # 나스닥 상승일들의 '일평균'
    Bd=[st.mean(v) for (d,l),v in byday.items() if not l]
    if len(A)<2 or len(Bd)<2: return None
    diff=st.mean(A)-st.mean(Bd)
    se=(st.variance(A)/len(A)+st.variance(Bd)/len(Bd))**0.5
    return diff, diff/se, len(A), len(Bd)

print("="*104)
print("④ 정렬 방식별 — 나스닥 전일 상승 vs 하락 (거래당 순수익, 수수료·세금 반영)")
print("="*104)
print(f"{'정렬':<42}{'표본':>7}{'상승n':>7}{'승률':>7}{'거래당':>9}  {'하락n':>7}{'승률':>7}{'거래당':>9}{'차이':>9}{'일t':>7}")
print('-'*104)
for lab,key in VAR.items():
    ev=[e for e in EV if key(e) is not None]
    a=[e for e in ev if NQ['up'][key(e)]]; b=[e for e in ev if not NQ['up'][key(e)]]
    d=day_test(ev,key)
    t=f"{d[1]:+.2f}" if d else "-"
    print(f"{lab:<42}{len(ev):>7}{len(a):>7}{wr(a):>6.1f}%{m(a):>+8.2f}%  {len(b):>7}{wr(b):>6.1f}%{m(b):>+8.2f}%{m(a)-m(b):>+8.2f}%p{t:>7}")

print("\n[일단위(클러스터) 검정 — 같은 날 거래는 라벨을 공유하므로 유효표본=일]")
for lab,key in VAR.items():
    d=day_test(EV,key)
    if d: print(f"  {lab:<42} 일평균차 {d[0]:+.2f}%p  t={d[1]:+.2f}  (상승 {d[2]}일 / 하락 {d[3]}일)")

# 원형이동 순열 (달력 구조 보존) — 정본 정렬로 '반전'의 유의성
days=sorted({e['entry_date'] for e in EV})
byday=collections.defaultdict(list)
for e in EV: byday[e['entry_date']].append(e['net'])
lab0=[NQ['up'][before(d,0)] for d in days]
obs=m([e for e in EV if NQ['up'][before(e['entry_date'],0)]])-m([e for e in EV if not NQ['up'][before(e['entry_date'],0)]])
cnt=tot=0; dist=[]
for sh in range(1,len(days)):
    L=lab0[sh:]+lab0[:sh]
    x=[v for d,l in zip(days,L) if l for v in byday[d]]
    z=[v for d,l in zip(days,L) if not l for v in byday[d]]
    if len(x)<100 or len(z)<100: continue
    dd=st.mean(x)-st.mean(z); dist.append(dd); tot+=1
    if dd<=obs: cnt+=1      # 반전(하락이 더 좋다) 방향의 단측
print(f"\n[원형이동 순열] 관측 {obs:+.2f}%p, 순열 중 이보다 더 음(-)인 경우 {cnt}/{tot} → 단측 p={(cnt+1)/(tot+1):.4f}")
dist.sort()
print(f"  순열분포 5%={dist[len(dist)//20]:+.2f}  중앙={dist[len(dist)//2]:+.2f}  95%={dist[-len(dist)//20]:+.2f}")
