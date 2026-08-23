# -*- coding: utf-8 -*-
from base import *
EV,raw=load_events()
print(f"원시 win/loss 이벤트 {raw}건 → 중복제거 후 {len(EV)}건")
W=[e for e in EV if e['result']=='win']; L=[e for e in EV if e['result']=='loss']
print(f"승 {len(W)}건 평균 {st.mean([e['gain_at_resolve_pct'] for e in W]):+.2f}% / 패 {len(L)}건 평균 {st.mean([e['gain_at_resolve_pct'] for e in L]):+.2f}%")
print(f"승률 {len(W)/len(EV)*100:.2f}%   거래당 총수익 {st.mean([e['gain_at_resolve_pct'] for e in EV]):+.3f}%   거래당 순수익 {mnet(EV):+.3f}%")
pr=st.mean([e['gain_at_resolve_pct'] for e in W])/abs(st.mean([e['gain_at_resolve_pct'] for e in L]))
print(f"손익비 {pr:.2f}  본전승률 {1/(1+pr)*100:.1f}%")
print(f"기간 {EV[0]['entry_date']} ~ {max(e['resolve_date'] for e in EV)}")
r=sorted(sim(EV,seed=s)[0] for s in range(200))
print(f"슬롯5 자산곡선(200시드 중앙) {r[100]:+.1f}%  5~95% {r[10]:+.0f}~{r[190]:+.0f}%")
d0=EV[0]['entry_date']; d1=max(e['resolve_date'] for e in EV)
ks=(KOS[max(d for d in REG['dates'] if d<=d1)]/KOS[min(d for d in REG['dates'] if d>=d0)]-1)*100
print(f"같은 기간 코스피 {ks:+.1f}%")
# 나스닥 asof 정합성
import collections as C
miss=sum(1 for e in EV if feat('IXIC',e['entry_date']) is None)
print(f"나스닥 피처 결측 {miss}건")
