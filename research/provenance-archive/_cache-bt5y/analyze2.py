# -*- coding: utf-8 -*-
import json, glob, os, random, collections, statistics as st
B=os.environ['LOCALAPPDATA']+'/Temp/bt5y/'
EV=[]
for f in sorted(glob.glob(B+'bt_*.json')):
    EV += [e for e in json.load(open(f,encoding='utf-8'))['events'] if e['result'] in ('win','loss')]
seen=set(); U=[]
for e in sorted(EV,key=lambda x:(x['entry_date'],x['code'])):
    k=(e['scan_date'],e['code'],e['pattern'])
    if k not in seen: seen.add(k); U.append(e)
EV=U
REG=json.load(open(B+'regime_long.json',encoding='utf-8'))
UP={d:u for d,u in zip(REG['dates'],REG['up_ew20'])}
KOS={d:v for d,v in zip(REG['dates'],REG['kospi'])}
FEE=lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100

def sim(events, slots=5, seed=0, filt=None):
    pool=[e for e in events if (filt is None or filt(e))]
    byday=collections.defaultdict(list)
    for e in pool: byday[e['entry_date']].append(e)
    rnd=random.Random(seed); eq=1.0; held=[]; n=0; w=0; peak=1.0; mdd=0.0
    alld=sorted(set(list(byday)+[e['resolve_date'] for e in pool]))
    for d in alld:
        for rd,e,wg in [h for h in held if h[0]<=d]:
            eq += wg*FEE(e['gain_at_resolve_pct'])/100; n+=1; w+= e['result']=='win'
        held=[h for h in held if h[0]>d]
        free=slots-len(held)
        if free>0 and d in byday:
            c=byday[d][:]; rnd.shuffle(c)
            for e in c[:free]: held.append((e['resolve_date'],e,eq/slots))
        peak=max(peak,eq); mdd=min(mdd,eq/peak-1)
    return (eq-1)*100, n, (w/n*100 if n else 0), mdd*100

def band(fn,N=200):
    r=[fn(i) for i in range(N)]
    f=sorted(x[0] for x in r)
    return f[N//2], f[N//20], f[N-N//20], sorted(x[1] for x in r)[N//2], sorted(x[2] for x in r)[N//2], sorted(x[3] for x in r)[N//2]

d0,d1=EV[0]['entry_date'],EV[-1]['resolve_date']
ks=(KOS[max(d for d in REG['dates'] if d<=d1)]/KOS[min(d for d in REG['dates'] if d>=d0)]-1)*100
ew=dict(zip(REG['dates'],REG['ew']))
ewr=(ew[max(d for d in REG['dates'] if d<=d1)]/ew[min(d for d in REG['dates'] if d>=d0)]-1)*100

print("="*88)
print(f"③ 5년 8개월 자산곡선 (슬롯5·자본 1/5·수수료세금 반영·200회 중앙)  {d0} ~ {d1}")
print("="*88)
print(f"{'전략':<26}{'최종':>10}{'5~95%':>19}{'매수':>7}{'승률':>8}{'최대낙폭':>10}")
print('-'*88)
rows=[('① 전부 매수', None), ('② 상승국면에만(주정의)', lambda e: UP.get(e['scan_date']) is True)]
res={}
for lab,f in rows:
    m,lo,hi,n,wr,md = band(lambda s: sim(EV,seed=s,filt=f))
    res[lab]=m
    print(f"{lab:<25}{m:>+9.1f}%{f'{lo:+.0f}~{hi:+.0f}%':>19}{n:>7}{wr:>7.1f}%{md:>9.1f}%")
# 판정4: 같은 건수 무작위 솎아내기
target=band(lambda s: sim(EV,seed=s,filt=lambda e: UP.get(e['scan_date']) is True))[3]
def thin(seed):
    rnd=random.Random(seed+9999)
    keep=set(rnd.sample(range(len(EV)), int(len(EV)*0.648)))
    return sim([e for i,e in enumerate(EV) if i in keep], seed=seed)
m,lo,hi,n,wr,md=band(thin)
print(f"{'③ 무작위 솎아내기(대조)':<25}{m:>+9.1f}%{f'{lo:+.0f}~{hi:+.0f}%':>19}{n:>7}{wr:>7.1f}%{md:>9.1f}%")
r_up=sorted(sim(EV,seed=i,filt=lambda e: UP.get(e['scan_date']) is True)[0] for i in range(200))
r_th=sorted(thin(i)[0] for i in range(200))
beat=sum(1 for a,b in zip(r_up,r_th) if a>b)
print(f"\n[판정4] 무작위 솎아내기 대비: 국면필터가 이긴 경우 {beat}/200 ({beat/2:.0f}%)  "
      f"{'✅ 통과' if beat>=190 else '❌ 실패'}")
print(f"[판정5] 슬롯5 자산곡선 우위: 국면 {res['② 상승국면에만(주정의)']:+.1f}% vs 전부 {res['① 전부 매수']:+.1f}%  "
      f"{'✅' if res['② 상승국면에만(주정의)']>res['① 전부 매수'] else '❌'}")
print(f"\n벤치마크  코스피 {ks:+.1f}%   등가중(평균 종목) {ewr:+.1f}%")

print()
print("="*88)
print("④ 패턴별 (표본을 5배로 늘리면)")
print("="*88)
for p in ('VCP','3C','PP'):
    g=[e for e in EV if e['pattern']==p]
    if not g: continue
    w=sum(1 for e in g if e['result']=='win')
    net=[FEE(e['gain_at_resolve_pct']) for e in g]
    se=st.stdev(net)/len(net)**0.5
    print(f"  {p:<5} {len(g):>5}건  승률 {w/len(g)*100:>5.1f}%  거래당 순 {st.mean(net):>+6.2f}%  (±{se*1.96:.2f} 95%구간)")

print()
print("="*88)
print("⑤ 손절이 값어치를 하는가 — 연도별")
print("="*88)
print(f"{'연도':<8}{'규칙대로(순)':>13}{'손절 없었다면*':>16}")
print('-'*88)
for y in ('2021','2022','2023','2024','2025','2026'):
    g=[e for e in EV if e['scan_date'][:4]==y]
    if not g: continue
    real=st.mean([FEE(e['gain_at_resolve_pct']) for e in g])
    # 손절 없이 목표만: 패한 거래의 최대손실(max_dd)을 그대로 떠안았다고 가정(보수적 근사)
    nostop=st.mean([FEE(e['gain_at_resolve_pct'] if e['result']=='win' else e['max_dd_pct']) for e in g])
    print(f"{y:<8}{real:>+12.2f}%{nostop:>+15.2f}%")
print("  * 근사: 패한 거래는 관측된 최대 낙폭까지 떠안았다고 가정")
