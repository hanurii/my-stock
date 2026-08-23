# -*- coding: utf-8 -*-
import sys, json, math, random
sys.path.insert(0, r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
from daytable import build
from pathlib import Path
from collections import defaultdict

SP=Path(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
br=json.loads((SP/"breadth_series.json").read_text(encoding='utf-8'))
print("=== 52주 신고가 계산 모집단(tot52) 시간 추이 — 인위적 표류 확인 ===")
for i,d in enumerate(br['dates']):
    if d in ('2025-11-26','2026-01-15','2026-03-25','2026-06-01','2026-08-20'):
        print(f"  {d}: 모집단 {br['tot52'][i]}, 신고가 {br['nh52'][i]} ({100*br['nh52'][i]/br['tot52'][i]:.2f}%), 200MA모집단 {br['tot200'][i]}")

rows=build(); res=[r for r in rows if r['nres']>0]
lab=[];prev=None;k=0
for r in rows:
    if prev is None or r['days_since_flip']<prev: k+=1
    lab.append(k); prev=r['days_since_flip']
for r,l in zip(rows,lab): r['ep']=l
up=[r for r in res if r['up']]

def cutv(key,q,sel=None):
    vs=sorted(r[key] for r in rows if r.get(key) is not None and (sel is None or sel(r)))
    return vs[int(len(vs)*q)]

for q,label in ((0.75,'상위25%'),(0.80,'상위20%')):
    C=cutv('pct_nh52',q,lambda r:r['up'])
    mask=[d['pct_nh52']<C for d in up]
    def diff(days,m):
        wa=sum(d['w'] for d,x in zip(days,m) if x); la=sum(d['l'] for d,x in zip(days,m) if x)
        wb=sum(d['w'] for d,x in zip(days,m) if not x); lb=sum(d['l'] for d,x in zip(days,m) if not x)
        if wa+la==0 or wb+lb==0: return 0.0
        return 100*wa/(wa+la)-100*wb/(wb+lb)
    obs=diff(up,mask)
    rnd=random.Random(3); reps=5000; c=0
    for _ in range(reps):
        m=mask[:]; rnd.shuffle(m)
        if abs(diff(up,m))>=abs(obs): c+=1
    pday=(c+1)/(reps+1)
    n=len(up); c=0
    for k in range(1,n):
        m=mask[k:]+mask[:k]
        if abs(diff(up,m))>=abs(obs): c+=1
    pcirc=(c+1)/n
    print(f"\n[신고가비율 {label} 제외] 차이 {obs:+.1f}%p · 날블록 p={pday:.4f} · 순환이동 p={pcirc:.4f} (컷 {C:.2f}%)")
    # 에피소드별
    print("  에피소드별: (과열날 승률 vs 그 에피소드 나머지)")
    for e in sorted(set(r['ep'] for r in up)):
        g=[r for r in up if r['ep']==e]
        hot=[r for r in g if r['pct_nh52']>=C]; cool=[r for r in g if r['pct_nh52']<C]
        wh=sum(r['w'] for r in hot); lh=sum(r['l'] for r in hot)
        wc=sum(r['w'] for r in cool); lc=sum(r['l'] for r in cool)
        if wh+lh==0 and wc+lc==0: continue
        sh=f"{100*wh/(wh+lh):.0f}%({wh+lh})" if wh+lh else "-"
        sc=f"{100*wc/(wc+lc):.0f}%({wc+lc})" if wc+lc else "-"
        print(f"    #{e} {g[0]['scan_date']}~{g[-1]['scan_date']}  과열날 {sh:>10s}  평소날 {sc:>10s}")
    # 종목블록 부트스트랩
    bycode=defaultdict(list)
    for d in up:
        for ev in d['events']:
            if ev['result'] in ('win','loss'): bycode[ev['code']].append((ev['result']=='win', d['pct_nh52']<C))
    codes=list(bycode); rnd=random.Random(9); vals=[]
    for _ in range(3000):
        wa=la=wb=lb=0
        for _ in codes:
            cc=codes[rnd.randrange(len(codes))]
            for win,keep in bycode[cc]:
                if keep:
                    wa+= 1 if win else 0; la+= 0 if win else 1
                else:
                    wb+= 1 if win else 0; lb+= 0 if win else 1
        if wa+la and wb+lb: vals.append(100*wa/(wa+la)-100*wb/(wb+lb))
    vals.sort()
    print(f"  종목블록 부트스트랩 95% [{vals[int(.025*len(vals))]:+.1f}, {vals[int(.975*len(vals))]:+.1f}]%p, 부호유지 {100*sum(1 for v in vals if v>0)/len(vals):.1f}%")
    # 전후반
    for half,sel in (('전반',lambda r:r['entry_date']<'2026-03-25'),('후반',lambda r:r['entry_date']>='2026-03-25')):
        g=[r for r in up if sel(r)]
        hot=[r for r in g if r['pct_nh52']>=C]; cool=[r for r in g if r['pct_nh52']<C]
        wh=sum(r['w'] for r in hot); lh=sum(r['l'] for r in hot); wc=sum(r['w'] for r in cool); lc=sum(r['l'] for r in cool)
        print(f"  {half}: 과열 {100*wh/(wh+lh) if wh+lh else 0:.1f}%({wh+lh}) vs 평소 {100*wc/(wc+lc) if wc+lc else 0:.1f}%({wc+lc})")
