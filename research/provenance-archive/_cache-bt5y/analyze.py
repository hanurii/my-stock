# -*- coding: utf-8 -*-
"""5년 8개월 검증 — 사전등록 기준대로."""
import json, glob, os, random, collections, statistics as st, math
B=os.environ['LOCALAPPDATA']+'/Temp/bt5y/'
EV=[]
for f in sorted(glob.glob(B+'bt_*.json')):
    j=json.load(open(f,encoding='utf-8'))
    EV += [e for e in j['events'] if e['result'] in ('win','loss')]
EV.sort(key=lambda e:(e['entry_date'], e['code']))
# 슬라이스 경계 중복 제거
seen=set(); U=[]
for e in EV:
    k=(e['scan_date'],e['code'],e['pattern'])
    if k in seen: continue
    seen.add(k); U.append(e)
EV=U
REG=json.load(open(B+'regime_long.json',encoding='utf-8'))
UP={d:u for d,u in zip(REG['dates'],REG['up_ew20'])}
UPK={d:u for d,u in zip(REG['dates'],REG['up_ks20'])}
KOS={d:v for d,v in zip(REG['dates'],REG['kospi'])}

FEE=lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100
def yr(e): return e['scan_date'][:4]
BUCKET={'2021':'2021','2022':'2022','2023':'2023','2024':'2024','2025':'2025~26','2026':'2025~26'}

print(f"총 확정 거래 {len(EV):,}건  ({EV[0]['scan_date']} ~ {EV[-1]['scan_date']})")
print()
print("="*84)
print("① 연도별 성적 — 하락장에서 살아남는가")
print("="*84)
print(f"{'연도':<8}{'거래':>7}{'승률':>8}{'거래당(총)':>11}{'거래당(순)':>11}{'등가중':>9}{'코스피':>9}")
print('-'*84)
for y in ('2021','2022','2023','2024','2025','2026'):
    g=[e for e in EV if yr(e)==y]
    if not g: continue
    w=sum(1 for e in g if e['result']=='win')
    gross=st.mean([e['gain_at_resolve_pct'] for e in g])
    netv=st.mean([FEE(e['gain_at_resolve_pct']) for e in g])
    ds=[d for d in REG['dates'] if d.startswith(y)]
    ewr=(dict(zip(REG['dates'],REG['ew']))[ds[-1]]/dict(zip(REG['dates'],REG['ew']))[ds[0]]-1)*100
    ksr=(KOS[ds[-1]]/KOS[ds[0]]-1)*100 if KOS.get(ds[0]) and KOS.get(ds[-1]) else float('nan')
    print(f"{y:<8}{len(g):>7}{w/len(g)*100:>7.1f}%{gross:>+10.2f}%{netv:>+10.2f}%{ewr:>+8.1f}%{ksr:>+8.1f}%")
allw=sum(1 for e in EV if e['result']=='win')
print('-'*84)
print(f"{'전체':<8}{len(EV):>7}{allw/len(EV)*100:>7.1f}%"
      f"{st.mean([e['gain_at_resolve_pct'] for e in EV]):>+10.2f}%"
      f"{st.mean([FEE(e['gain_at_resolve_pct']) for e in EV]):>+10.2f}%")

print()
print("="*84)
print("② 국면별 — 사용자 가설: 조정장엔 못 쓴다")
print("="*84)
print(f"{'구간':<10}{'상승 거래':>10}{'승률':>7}{'거래당':>9}   {'조정 거래':>10}{'승률':>7}{'거래당':>9}{'차이':>9}")
print('-'*84)
signs=[]
for b in ('2021','2022','2023','2024','2025~26'):
    g=[e for e in EV if BUCKET.get(yr(e))==b]
    up=[e for e in g if UP.get(e['scan_date'])]
    dn=[e for e in g if UP.get(e['scan_date'])==False]
    if not up or not dn: continue
    fu=st.mean([FEE(e['gain_at_resolve_pct']) for e in up])
    fd=st.mean([FEE(e['gain_at_resolve_pct']) for e in dn])
    wu=sum(1 for e in up if e['result']=='win')/len(up)*100
    wd=sum(1 for e in dn if e['result']=='win')/len(dn)*100
    signs.append(fu-fd)
    print(f"{b:<10}{len(up):>10}{wu:>6.1f}%{fu:>+8.2f}%   {len(dn):>10}{wd:>6.1f}%{fd:>+8.2f}%{fu-fd:>+8.2f}%p")
up=[e for e in EV if UP.get(e['scan_date'])]; dn=[e for e in EV if UP.get(e['scan_date'])==False]
FU=st.mean([FEE(e['gain_at_resolve_pct']) for e in up]); FD=st.mean([FEE(e['gain_at_resolve_pct']) for e in dn])
print('-'*84)
print(f"{'전체':<10}{len(up):>10}{sum(1 for e in up if e['result']=='win')/len(up)*100:>6.1f}%{FU:>+8.2f}%   "
      f"{len(dn):>10}{sum(1 for e in dn if e['result']=='win')/len(dn)*100:>6.1f}%{FD:>+8.2f}%{FU-FD:>+8.2f}%p")
print(f"\n[판정1] 다섯 구간 부호 일치: {'✅ 통과' if all(s>0 for s in signs) else '❌ 실패'}  ({['%+.2f'%s for s in signs]})")

# 대조군: 코스피 20MA
upk=[e for e in EV if UPK.get(e['scan_date'])]; dnk=[e for e in EV if UPK.get(e['scan_date'])==False]
FUK=st.mean([FEE(e['gain_at_resolve_pct']) for e in upk]); FDK=st.mean([FEE(e['gain_at_resolve_pct']) for e in dnk])
print(f"[판정3] 코스피20MA 대조군: 상승 {len(upk)}건 {FUK:+.2f}% vs 조정 {len(dnk)}건 {FDK:+.2f}%  차이 {FUK-FDK:+.2f}%p"
      f"  {'✅ 부호 일치' if (FUK-FDK)>0 else '❌ 부호 반대'}")

# 원형이동 순열
days=sorted({e['scan_date'] for e in EV})
byday=collections.defaultdict(list)
for e in EV: byday[e['scan_date']].append(FEE(e['gain_at_resolve_pct']))
lab=[UP.get(d) for d in days]
obs=FU-FD
cnt=0; tot=0
for sh in range(1,len(days)):
    L=lab[sh:]+lab[:sh]
    a=[v for d,l in zip(days,L) if l for v in byday[d]]
    b=[v for d,l in zip(days,L) if l is False for v in byday[d]]
    if len(a)<50 or len(b)<50: continue
    tot+=1
    if (st.mean(a)-st.mean(b))>=obs: cnt+=1
p=(cnt+1)/(tot+1)
print(f"[판정2] 원형이동 순열검정: 관측 {obs:+.2f}%p, {cnt}/{tot} 초과 → p={p:.4f}  {'✅ 통과' if p<0.05 else '❌ 실패'}")
json.dump({'n':len(EV)}, open(B+'_n.json','w'))
