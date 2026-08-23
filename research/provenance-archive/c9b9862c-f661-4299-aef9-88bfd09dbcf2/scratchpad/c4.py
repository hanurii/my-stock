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
d_first=min(e['entry_date'] for e in EV); d_last=max(e['entry_date'] for e in EV)
cal=[d for d in rdates if d_first<=d<=d_last]; N=len(cal)
reg=[UP.get(rdates[ridx[d]-1]) for d in cal]
nq=[nq_before(d) for d in cal]
byday=collections.defaultdict(list)
for e in EV: byday[e['entry_date']].append(e['net'])
rets=[byday.get(d,[]) for d in cal]
print(f"나스닥 방향 1일 자기상관 확인: 상승비율 {sum(1 for x in nq if x)/N*100:.1f}%")
seq=[1 if x else 0 for x in nq]
lag1=sum(1 for i in range(N-1) if seq[i]==seq[i+1])/(N-1)
print(f"  전일과 방향 일치율 {lag1*100:.1f}% (무작위면 50%)")
print(f"국면 상승 비율 {sum(1 for x in reg if x)/N*100:.1f}%, 전일 일치율 {sum(1 for i in range(N-1) if reg[i]==reg[i+1])/(N-1)*100:.1f}%")
print(f"국면×나스닥 독립성: 국면상승일 중 NQ상승 {sum(1 for i in range(N) if reg[i] and nq[i])/max(1,sum(1 for x in reg if x))*100:.1f}% / 국면조정일 중 NQ상승 {sum(1 for i in range(N) if (reg[i] is False) and nq[i])/max(1,sum(1 for x in reg if x is False))*100:.1f}%")

def within(shift, want_reg):
    a=[0.0,0]; b=[0.0,0]
    for i in range(N):
        r=rets[i]
        if not r or reg[i] is not want_reg: continue
        if nq[(i+shift)%N]: a[0]+=sum(r); a[1]+=len(r)
        else: b[0]+=sum(r); b[1]+=len(r)
    if a[1]<50 or b[1]<50: return None
    return a[0]/a[1]-b[0]/b[1]
o_corr=within(0,False); o_up=within(0,True)
Dc=[];Du=[];Dm=[]
for s in range(1,N):
    if min(s,N-s)<5: continue
    x=within(s,False); y=within(s,True)
    if x is None or y is None: continue
    Dc.append(x); Du.append(y); Dm.append(max(abs(x),abs(y)))
print(f"\n=== ★조건부 순열 (국면 라벨 고정, 나스닥 라벨만 원형이동) ===")
print(f"  조정 국면 내부 (NQ상승-NQ하락): 관측 {o_corr:+.2f}%p")
print(f"     단측 p={(sum(1 for x in Dc if x<=o_corr)+1)/(len(Dc)+1):.4f}  양측 p={(sum(1 for x in Dc if abs(x)>=abs(o_corr))+1)/(len(Dc)+1):.4f}  (귀무 sd {st.pstdev(Dc):.2f})")
print(f"  상승 국면 내부 (NQ상승-NQ하락): 관측 {o_up:+.2f}%p")
print(f"     단측 p={(sum(1 for x in Du if x>=o_up)+1)/(len(Du)+1):.4f}  양측 p={(sum(1 for x in Du if abs(x)>=abs(o_up))+1)/(len(Du)+1):.4f}  (귀무 sd {st.pstdev(Du):.2f})")
p2=(sum(1 for x in Dm if x>=abs(o_corr))+1)/(len(Dm)+1)
print(f"  ★2개 하위대비 중 최대 선택 보정: p={p2:.4f}")

# 4칸 전부를 다시: 셀평균-나머지, 조건부(나스닥만 이동)
def cellstat(shift):
    acc=collections.defaultdict(lambda:[0.0,0]); tot=0.0;n=0
    for i in range(N):
        r=rets[i]
        if not r: continue
        c=(reg[i], nq[(i+shift)%N])
        acc[c][0]+=sum(r); acc[c][1]+=len(r); tot+=sum(r); n+=len(r)
    out={}
    for c,(s,k) in acc.items():
        if k<50 or c[0] is None: continue
        out[c]=s/k-(tot-s)/(n-k)
    return out
oc=cellstat(0); o_t=oc[(False,True)]
Dmax=[]
for s in range(1,N):
    if min(s,N-s)<5: continue
    o=cellstat(s)
    if len(o)<4: continue
    Dmax.append(max(abs(v) for v in o.values()))
print(f"  ★4칸 최대통계량 보정(조건부): 관측 |{o_t:+.2f}| p={(sum(1 for x in Dmax if x>=abs(o_t))+1)/(len(Dmax)+1):.4f}")

# 일 단위(day-level) 검정 — 유효 표본은 거래일
print(f"\n=== 일 단위 검정 (하루=1관측, 그날 평균수익) ===")
dayA=[st.mean(rets[i]) for i in range(N) if rets[i] and reg[i] is False and nq[i]]
dayB=[st.mean(rets[i]) for i in range(N) if rets[i] and reg[i] is False and not nq[i]]
print(f"  조정+NQ상승 {len(dayA)}일 평균 {st.mean(dayA):+.2f}% 중앙 {st.median(dayA):+.2f}% sd {st.pstdev(dayA):.2f}")
print(f"  조정+NQ하락 {len(dayB)}일 평균 {st.mean(dayB):+.2f}% 중앙 {st.median(dayB):+.2f}% sd {st.pstdev(dayB):.2f}")
import math
se=math.sqrt(st.pstdev(dayA)**2/len(dayA)+st.pstdev(dayB)**2/len(dayB))
print(f"  차이 {st.mean(dayA)-st.mean(dayB):+.2f}%p  t≈{(st.mean(dayA)-st.mean(dayB))/se:.2f}")

# 연도 제외 민감도
print(f"\n=== 연도 하나씩 빼기 (조정 내부 대비) ===")
for y in ['2021','2022','2023','2024','2025','2026']:
    a=[];b=[]
    for i in range(N):
        if not rets[i] or reg[i] is not False or cal[i][:4]==y: continue
        (a if nq[i] else b).extend(rets[i])
    print(f"  {y} 제외: 상승 n={len(a):>4} {st.mean(a):+.2f}% / 하락 n={len(b):>4} {st.mean(b):+.2f}% → 차이 {st.mean(a)-st.mean(b):+.2f}%p")
