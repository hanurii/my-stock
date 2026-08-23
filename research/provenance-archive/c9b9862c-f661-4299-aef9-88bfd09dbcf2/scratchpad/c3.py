# -*- coding: utf-8 -*-
import json, io, collections, statistics as st, random, bisect
EV=json.load(io.open('ev.json',encoding='utf-8'))
B='C:/Users/hanul/AppData/Local/Temp/bt5y/'
R=json.load(io.open(B+'regime_long.json',encoding='utf-8'))
rdates=R['dates']; ridx={d:i for i,d in enumerate(rdates)}
UP=dict(zip(rdates,R['up_ew20']))
NQ=json.load(io.open(B+'nasdaq.json',encoding='utf-8'))
nqd=sorted(NQ['up'])
def nq_before(kd):
    i=bisect.bisect_left(nqd,kd); return NQ['up'][nqd[i-1]] if i>0 else None
# scan_date == 직전 거래일인지 확인
bad=0
for e in EV:
    i=ridx.get(e['entry_date'])
    if i is None or i==0 or rdates[i-1]!=e['scan_date']: bad+=1
print(f"scan_date != 직전거래일 인 건수: {bad} / {len(EV)}")
# 공변량 균형
A=[e for e in EV if e['_reg'] is False and e['_nq'] is True]
Bc=[e for e in EV if e['_reg'] is False and e['_nq'] is False]
def m(g,k='net'): return st.mean([x[k] for x in g])
print('\n=== 조정 두 칸 공변량 균형 ===')
print(f"{'항목':<16}{'조정+NQ상승':>12}{'조정+NQ하락':>12}")
for k in ['rs','atr_pct','turnover_eok','gap_up_pct','max_gain_pct','max_dd_pct','days_held']:
    print(f"{k:<16}{m(A,k):>12.2f}{m(Bc,k):>12.2f}")
for k in ['pattern','market','price_bucket']:
    ca=collections.Counter(e[k] for e in A); cb=collections.Counter(e[k] for e in Bc)
    keys=sorted(set(ca)|set(cb))
    print(f"  {k}: "+' | '.join(f"{x}:{ca[x]/len(A)*100:.0f}%/{cb[x]/len(Bc)*100:.0f}%" for x in keys))
# 패턴별 조정칸 분해
print('\n=== 조정+NQ상승 패턴별 ===')
for p in sorted({e['pattern'] for e in A}):
    ga=[e for e in A if e['pattern']==p]; gb=[e for e in Bc if e['pattern']==p]
    print(f"  {p:<12} 상승 n={len(ga):>4} {m(ga):>+7.2f}%   하락 n={len(gb):>4} {m(gb):>+7.2f}%")

# ===== 원형이동 순열검정 =====
d_first=min(e['entry_date'] for e in EV); d_last=max(e['entry_date'] for e in EV)
cal=[d for d in rdates if d_first<=d<=d_last]
N=len(cal)
lab=[]
for i,d in enumerate(cal):
    gi=ridx[d]
    reg=UP.get(rdates[gi-1]) if gi>0 else None
    lab.append((reg, nq_before(d)))
byday=collections.defaultdict(list)
for e in EV: byday[e['entry_date']].append(e['net'])
rets=[byday.get(d,[]) for d in cal]
CELLS=[(False,True),(False,False),(True,True),(True,False)]
NAMES={(False,True):'조정+NQ상승',(False,False):'조정+NQ하락',(True,True):'상승+NQ상승',(True,False):'상승+NQ하락'}
def stats_for(shift):
    acc={c:[0.0,0] for c in CELLS}; tot=0.0; n=0
    for i in range(N):
        r=rets[i]
        if not r: continue
        c=lab[(i+shift)%N]
        if c in acc:
            acc[c][0]+=sum(r); acc[c][1]+=len(r)
        tot+=sum(r); n+=len(r)
    out={}
    for c in CELLS:
        s,k=acc[c]
        if k<50: out[c]=None; continue
        rest=(tot-s)/(n-k)
        out[c]=(s/k, s/k-rest, k)
    return out
obs=stats_for(0)
print('\n=== 관측 통계량 (칸 - 나머지) ===')
for c in CELLS:
    mu,dif,k=obs[c]; print(f"  {NAMES[c]:<14} n={k:>5} 거래당 {mu:>+7.2f}%  vs나머지 {dif:>+7.2f}%p")
# 조정 내부 대비
def cond_stat(shift):
    a=[0.0,0]; b=[0.0,0]
    for i in range(N):
        r=rets[i]
        if not r: continue
        c=lab[(i+shift)%N]
        if c==(False,True): a[0]+=sum(r); a[1]+=len(r)
        elif c==(False,False): b[0]+=sum(r); b[1]+=len(r)
    if a[1]<50 or b[1]<50: return None
    return a[0]/a[1]-b[0]/b[1]
obs_cond=cond_stat(0)
print(f"  [조정 내부] 상승-하락 = {obs_cond:+.2f}%p")

shifts=[s for s in range(1,N) if min(s,N-s)>=20]
D_target=[]; D_max=[]; D_cond=[]
for s in shifts:
    o=stats_for(s)
    v=o[(False,True)]
    if v is None: continue
    D_target.append(v[1])
    mx=max((abs(o[c][1]) for c in CELLS if o[c]), default=None)
    D_max.append(mx)
    cc=cond_stat(s)
    if cc is not None: D_cond.append(cc)
o_t=obs[(False,True)][1]
p_t=(sum(1 for x in D_target if x<=o_t)+1)/(len(D_target)+1)          # 단측(더 나쁨)
p_t2=(sum(1 for x in D_target if abs(x)>=abs(o_t))+1)/(len(D_target)+1) # 양측
p_max=(sum(1 for x in D_max if x>=abs(o_t))+1)/(len(D_max)+1)          # 다중검정 보정(최대통계량)
p_c=(sum(1 for x in D_cond if x<=obs_cond)+1)/(len(D_cond)+1)
p_c2=(sum(1 for x in D_cond if abs(x)>=abs(obs_cond))+1)/(len(D_cond)+1)
print(f"\n=== 원형이동 순열검정 (거래일 달력 {N}일, 유효 shift {len(D_target)}개) ===")
print(f"  ① 조정+NQ상승 vs 나머지 : 관측 {o_t:+.2f}%p  단측 p={p_t:.4f}  양측 p={p_t2:.4f}")
print(f"  ② ★다중검정 보정(4칸 최대|통계량|) : p={p_max:.4f}")
print(f"  ③ 조정 내부 (상승-하락) : 관측 {obs_cond:+.2f}%p 단측 p={p_c:.4f} 양측 p={p_c2:.4f}")
print(f"     귀무분포 요약: 평균 {st.mean(D_target):+.2f} 표준편차 {st.pstdev(D_target):.2f} / 5%분위 {sorted(D_target)[int(len(D_target)*0.05)]:+.2f} / 95% {sorted(D_target)[int(len(D_target)*0.95)]:+.2f}")
print(f"     조정내부 귀무: 표준편차 {st.pstdev(D_cond):.2f} 5%분위 {sorted(D_cond)[int(len(D_cond)*0.05)]:+.2f}")
json.dump({'D_target':D_target,'D_cond':D_cond,'D_max':D_max},io.open('perm.json','w'))
