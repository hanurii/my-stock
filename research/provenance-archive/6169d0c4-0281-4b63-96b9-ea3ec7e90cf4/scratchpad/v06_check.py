# -*- coding: utf-8 -*-
"""06·15 독립 검증 1부 — 변형2·변형10 재현, 버린 승자 27건 분포."""
import json, collections, statistics as st, sys
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\research\handoff\scripts")
import slot_sim
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
net = slot_sim.net
paths=[]
for y in (2021,2022,2023,2024,2025,2026):
    d=json.load(open(BT+r"\out\paths_%d.json"%y,encoding='utf-8'))
    for p in d['paths']:
        paths.append({'code':p['code'],'name':p.get('name'),'pat':p['pattern'],'sd':p['scan_date'],
                      'ed':p['entry_date'],'E':p['entry_price'],'o':p['o'],'h':p['h'],'l':p['l'],
                      'c':p['c'],'dt':p['dates']})
    del d
print("경로 %d" % len(paths))

def base_resolve(p):
    """현행 +20/-10 · M1 · 닿은 날 종가. 반환 (idx, label, gain, reason)"""
    E=p['E']; T=E*1.20; S=E*0.90; h,l,c=p['h'],p['l'],p['c']
    for i in range(len(c)):
        ht,hs=h[i]>=T,l[i]<=S
        if ht and hs: return (i,'loss',(c[i]/E-1)*100,'both')
        if ht: return (i,'win',(c[i]/E-1)*100,'target')
        if hs: return (i,'loss',(c[i]/E-1)*100,'stop')
    g=(c[-1]/E-1)*100
    return (len(c)-1,'win' if g>0 else 'loss',g,'last')

def v2_resolve(p, day=5, thr=-5.0):
    """변형2 — day일차(매수일 0일차) 종가가 thr% 이하면 다음날 시가 청산."""
    E=p['E']; T=E*1.20; S=E*0.90; o,h,l,c=p['o'],p['h'],p['l'],p['c']
    n=len(c)
    for i in range(n):
        ht,hs=h[i]>=T,l[i]<=S
        if ht and hs: return (i,'loss',(c[i]/E-1)*100,'both')
        if ht: return (i,'win',(c[i]/E-1)*100,'target')
        if hs: return (i,'loss',(c[i]/E-1)*100,'stop')
        if i==day and (c[i]/E-1)*100 <= thr:
            if i+1 < n:
                g=(o[i+1]/E-1)*100
                return (i+1,'win' if g>0 else 'loss',g,'signal')
            g=(c[i]/E-1)*100
            return (i,'win' if g>0 else 'loss',g,'signal')
    g=(c[-1]/E-1)*100
    return (n-1,'win' if g>0 else 'loss',g,'last')

def v10_resolve(p):
    """추적손절 -20% (보유 중 최고 종가 대비), 집행은 익일 시가."""
    E=p['E']; T=E*1.20; S=E*0.90; o,h,l,c=p['o'],p['h'],p['l'],p['c']; n=len(c); pk=None
    for i in range(n):
        ht,hs=h[i]>=T,l[i]<=S
        if ht and hs: return (i,'loss',(c[i]/E-1)*100,'both')
        if ht: return (i,'win',(c[i]/E-1)*100,'target')
        if hs: return (i,'loss',(c[i]/E-1)*100,'stop')
        pk=c[i] if pk is None else max(pk,c[i])
        if c[i] <= pk*0.80:
            if i+1 < n:
                g=(o[i+1]/E-1)*100
                return (i+1,'win' if g>0 else 'loss',g,'signal')
            g=(c[i]/E-1)*100; return (i,'win' if g>0 else 'loss',g,'signal')
    g=(c[-1]/E-1)*100
    return (n-1,'win' if g>0 else 'loss',g,'last')

def mk(fn):
    out=[]
    for p in paths:
        i,lb,g,rea=fn(p)
        out.append({'code':p['code'],'pattern':p['pat'],'scan_date':p['sd'],'entry_date':p['ed'],
                    'resolve_date':p['dt'][i],'gain':g,'result':lb,'reason':rea,'days':i})
    return out
B=mk(base_resolve); V2=mk(v2_resolve); V10=mk(v10_resolve)
print("\n[06 재현] 거래당 순수익")
for nm,tr in (('현행',B),('변형2',V2),('변형10',V10)):
    print("  %-6s %+.3f%%  승률 %.1f%%  (결과파일 현행 -0.079/35.0 · 변형2 +0.081/34.3 · 변형10 -0.066/35.0)"
          % (nm, st.mean(net(t['gain']) for t in tr), 100*sum(t['result']=='win' for t in tr)/len(tr)))
print("\n[06 재현] 변형2 청산 사유:", dict(collections.Counter(t['reason'] for t in V2)))
sig=[i for i,t in enumerate(V2) if t['reason']=='signal']
print("  발동 %d건 (결과파일 376) · 그 건들의 현행 결과: %s"
      % (len(sig), dict(collections.Counter(B[i]['reason'] for i in sig))))
lost=[i for i in sig if B[i]['reason']=='target']
print("  버린 승자 %d건 (결과파일 27)" % len(lost))
print("  버린 승자 연도별:", dict(sorted(collections.Counter(B[i]['scan_date'][:4] for i in lost).items())))
print("  버린 승자 종목 중복:", [c for c,n in collections.Counter(B[i]['code'] for i in lost).items() if n>1] or "없음")
print("  발동 연도별:", dict(sorted(collections.Counter(B[i]['scan_date'][:4] for i in sig).items())),
      " (결과파일 108/40/63/56/77/32)")
print("  발동 손익 변화 합 %+.1f%%p · 중앙 %+.2f%%p"
      % (sum(net(V2[i]['gain'])-net(B[i]['gain']) for i in sig),
         st.median([net(V2[i]['gain'])-net(B[i]['gain']) for i in sig])))
print("\n[06 재현] 변형10 동점 — 현행과 결과가 다른 거래 %d건 (결과파일 35)"
      % sum(1 for i in range(len(B)) if abs(V10[i]['gain']-B[i]['gain'])>1e-9 or V10[i]['resolve_date']!=B[i]['resolve_date']))
N=400
eb=[slot_sim.sim(B,seed=i)['equity_pct'] for i in range(N)]
e2=[slot_sim.sim(V2,seed=i)['equity_pct'] for i in range(N)]
e10=[slot_sim.sim(V10,seed=i)['equity_pct'] for i in range(N)]
print("\n[06 재현] 슬롯5 중앙(200회): 현행 %+.1f%% (파일 -33.1) · 변형2 %+.1f%% (파일 -15.3) · 변형10 %+.1f%% (파일 -35.1)"
      % (st.median(eb[:200]), st.median(e2[:200]), st.median(e10[:200])))
d2=[e2[i]-eb[i] for i in range(N)]; d10=[e10[i]-eb[i] for i in range(N)]
print("  변형2 우세율 %.1f%% (파일 77.5) · 동점 %.1f%%" % (100*sum(1 for x in d2 if x>0)/N, 100*sum(1 for x in d2 if x==0)/N))
print("  변형10 우세율 %.1f%% (파일 37.2) · p(차이<0) %.3f (파일 0.495) · 동점 %.1f%% (파일 13.3)"
      % (100*sum(1 for x in d10 if x>0)/N, sum(1 for x in d10 if x<0)/N, 100*sum(1 for x in d10 if x==0)/N))
print("  체결 중앙: 현행 %.0f · 변형2 %.0f (파일 424 / 434)"
      % (st.median(slot_sim.sim(B,seed=i)['n_filled'] for i in range(50)),
         st.median(slot_sim.sim(V2,seed=i)['n_filled'] for i in range(50))))
