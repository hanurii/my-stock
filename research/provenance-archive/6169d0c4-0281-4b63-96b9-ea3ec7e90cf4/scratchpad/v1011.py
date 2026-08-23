# -*- coding: utf-8 -*-
import json, glob, collections, statistics as st, sys
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\research\handoff\scripts")
import slot_sim
BT = r"C:\Users\hanul\playground\my-stock\.cache\bt5y"
ev=[]
for f in sorted(glob.glob(BT+r"\bt_*.json")): ev+=json.load(open(f,encoding='utf-8'))['events']
seen,U=set(),[]
for e in sorted(ev,key=lambda x:(x['entry_date'],x['code'])):
    k=(e['scan_date'],e['code'],e['pattern'])
    if k not in seen: seen.add(k); U.append(e)
R=[e for e in U if e['result'] in ('win','loss')]
byday=collections.defaultdict(list)
for e in R: byday[e['entry_date']].append(e)

def rho(days):
    """Fleiss 식 이항 급내상관 — k>=2 인 날만 기여."""
    N=sum(len(v) for v in days); W=sum(1 for v in days for e in v if e['result']=='win')
    p=W/N; num=den=0
    for v in days:
        k=len(v)
        if k<2: continue
        w=sum(1 for e in v if e['result']=='win')
        Pi=(w*(w-1)+(k-w)*(k-w-1))/(k*(k-1))
        num+=k*(k-1)*Pi; den+=k*(k-1)
    Pb=num/den; Pe=p*p+(1-p)*(1-p)
    return (Pb-Pe)/(1-Pe), N, p

r,N,p = rho(list(byday.values()))
print("[11] 전체 ρ = %+.4f  (파일 +0.0957) · 거래 %d · 승률 %.3f" % (r,N,p))
print("     연도별 ρ (파일: 2023 ≈0.003 · 2026 ≈0.176)")
for y in ('2021','2022','2023','2024','2025','2026'):
    dv=[v for d,v in byday.items() if d[:4]==y]
    rr,nn,pp = rho(dv)
    print("       %s ρ = %+.4f (거래 %d · 날 %d)" % (y,rr,nn,len(dv)))

print("\n[11 슬롯5] 하루 최대 체결 — 200 seed")
paths=[]
for y in (2021,2022,2023,2024,2025,2026):
    d=json.load(open(BT+r"\out\paths_%d.json"%y,encoding='utf-8'))
    for pth in d['paths']:
        E=pth['entry_price']; T=E*1.20; S=E*0.90; h,l,c=pth['h'],pth['l'],pth['c']; rr=None
        for i in range(len(c)):
            ht,hs=h[i]>=T,l[i]<=S
            if ht and hs: rr=(i,'loss'); break
            if ht: rr=(i,'win'); break
            if hs: rr=(i,'loss'); break
        if rr is None:
            g=(c[-1]/E-1)*100; rr=(len(c)-1,'win' if g>0 else 'loss')
        i,lb=rr
        paths.append({'code':pth['code'],'pattern':pth['pattern'],'scan_date':pth['scan_date'],
                      'entry_date':pth['entry_date'],'resolve_date':pth['dates'][i],'result':lb})
    del d
bd=collections.defaultdict(list)
for t in paths: bd[t['entry_date']].append(t)
dts=sorted(set(list(bd)+[t['resolve_date'] for t in paths]))
mx=collections.Counter(); overall=0
for s in range(200):
    held=[]; m=0
    for d in dts:
        held=[x for x in held if x[0]>=d]
        free=5-len(held)
        if free>0 and d in bd:
            c=bd[d][:]; c.sort(key=lambda t: slot_sim.order_key(s,t))
            take=c[:free]
            m=max(m,len(take))
            for t in take: held.append((t['resolve_date'],t))
    mx[m]+=1; overall=max(overall,m)
print("     seed별 '하루 최대 체결'의 분포:", dict(sorted(mx.items())))
print("     200 seed 통틀어 하루 최대 체결 = %d건  (파일 4)" % overall)
print("     참고 — 제약 없는 하루 진입 최대 = %d건" % max(len(v) for v in byday.values()))

print("\n[10] 두 비율")
tot_d=tot_t=same_d=same_t=one_d=one_t=0
for d,v in byday.items():
    if len(v)<2: continue
    tot_d+=1; tot_t+=len(v)
    gaps=[round(e['gap_up_pct'],2) for e in v]
    if len(set(gaps))==1: same_d+=1; same_t+=len(v)
    hi=[e for e in v if e['gap_up_pct']>0]; lo=[e for e in v if e['gap_up_pct']<=0]
    if hi and lo and (len(hi)==1 or len(lo)==1): one_d+=1; one_t+=len(v)
    elif not hi or not lo: pass
print("     후보 2건 이상인 날 %d일 (거래 %d)" % (tot_d,tot_t))
print("     세 팔이 같은 결과가 되는 날(전부 동점) %d일 = %.1f%% · 거래 %.1f%%  (파일 59.1 / 40.7)"
      % (same_d,100*same_d/tot_d,100*same_t/tot_t))
print("     한쪽 무리가 1건뿐인 날 %d일 = %.1f%% · 거래 %.1f%%  (파일 69.5 / 55.6)"
      % (one_d,100*one_d/tot_d,100*one_t/tot_t))
