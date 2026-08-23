# -*- coding: utf-8 -*-
import sys, json, math
from datetime import date
sys.path.insert(0, r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
from daytable import build
rows=build(); res=[r for r in rows if r['nres']>0]

# 카이제곱 p값
def chi2_sf(x,k):
    # Wilson-Hilferty 근사
    z=((x/k)**(1/3) - (1-2/(9*k)))/math.sqrt(2/(9*k))
    return 0.5*math.erfc(z/math.sqrt(2))
up4=[r for r in res if r['up'] and r['nres']>=3]
pp=sum(r['w'] for r in up4)/sum(r['nres'] for r in up4)
chi=sum((r['w']-r['nres']*pp)**2/(r['nres']*pp*(1-pp)) for r in up4)
print(f"상승국면 3건+ 날 과산포 카이제곱 {chi:.1f} / df {len(up4)-1} → p ≈ {chi2_sf(chi,len(up4)-1):.2e}")

def cutv(key,q,sel=None):
    vs=sorted(r[key] for r in rows if r.get(key) is not None and (sel is None or sel(r)))
    return vs[int(len(vs)*q)]
Cup=cutv('pct_nh52',0.80,lambda r:r['up']); Cr10=cutv('ret10',0.75,lambda r:r['up'])

# 과열날 거래의 성격
hot=[e for r in res if r['up'] and r['pct_nh52']>=Cup for e in r['events'] if e['result'] in ('win','loss')]
cool=[e for r in res if r['up'] and r['pct_nh52']<Cup for e in r['events'] if e['result'] in ('win','loss')]
for nm,g in (('과열날',hot),('평소날',cool)):
    print(f"{nm}: n={len(g)} 평균 최대이익 {sum(e['max_gain_pct'] for e in g)/len(g):+.1f}% · 평균 최대낙폭 {sum(e['max_dd_pct'] for e in g)/len(g):+.1f}% · 평균 보유 {sum(e['days_held'] for e in g)/len(g):.1f}일 · 실현 {sum(e['gain_at_resolve_pct'] for e in g)/len(g):+.2f}%")
    q=sum(1 for e in g if e['days_held']<=1)
    print(f"    1일 이내 결착(즉사/즉승) {q}건 ({100*q/len(g):.0f}%)")

# 슬롯 유휴율
SLOT=5; SIZE=10_000_000; FEE=0.34
alldates=sorted(set(r['entry_date'] for r in rows))
def occupancy(passfn):
    op=[]; used=0; tot=0; buys=0
    for r in rows:
        D=r['entry_date']; op=[p for p in op if p[0]>=D]
        if passfn(r):
            free=SLOT-len(op)
            for e in sorted(r['events'], key=lambda e:-(e.get('turnover_eok') or 0)):
                if free<=0: break
                op.append((e['resolve_date'],0)); free-=1; buys+=1
        used+=len(op); tot+=SLOT
    return 100*used/tot, buys
print()
for nm,fn in (('①전부',lambda r:True),('②상승국면',lambda r:r['up']),
              ('⑤상승+신고가과열·지수과열 쉼',lambda r:r['up'] and r['pct_nh52']<Cup and r['ret10']<Cr10)):
    o,b=occupancy(fn)
    print(f"{nm:26s} 자금 가동률 {o:.0f}% · 매수 {b}건 · 매매일 {sum(1 for r in rows if fn(r))}/146일")

# 과열날이 실제로 언제였나 (달력)
print("\n=== '신고가 과열' 로 걸러지는 날 (상승국면 상위20%) ===")
hd=[r for r in rows if r['up'] and r['pct_nh52']>=Cup]
print(f"총 {len(hd)}일: ", ", ".join(r['scan_date'] for r in hd))
