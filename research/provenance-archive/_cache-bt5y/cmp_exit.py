# -*- coding: utf-8 -*-
"""청산 규칙 비교 — 슬롯5 자산곡선으로 판정(거래당 수익률로 판정 금지: 사전등록)."""
import json, glob, os, random, collections, statistics as st, math, sys
B=os.environ['LOCALAPPDATA']+'/Temp/bt5y/'
FEE=lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100

def load(pat, folder=''):
    """6개 연도 파일이 다 있을 때만 반환 — 일부만 있으면 구간이 달라 비교가 무효다."""
    files=sorted(glob.glob(B+folder+pat))
    if len(files)<6:
        return None, len(files)
    ev=[]
    for f in files:
        ev += [e for e in json.load(open(f,encoding='utf-8'))['events'] if e['result'] in ('win','loss')]
    seen=set(); U=[]
    for e in sorted(ev,key=lambda x:(x['entry_date'],x['code'])):
        k=(e['scan_date'],e['code'],e['pattern'])
        if k not in seen: seen.add(k); U.append(e)
    return U, 6

def sim(events, slots=5, seed=0):
    byday=collections.defaultdict(list)
    for e in events: byday[e['entry_date']].append(e)
    rnd=random.Random(seed); eq=1.0; held=[]; n=0; w=0; peak=1.0; mdd=0.0
    for d in sorted(set(list(byday)+[e['resolve_date'] for e in events])):
        for rd,e,wg in [h for h in held if h[0]<=d]:
            eq += wg*FEE(e['gain_at_resolve_pct'])/100; n+=1; w+= e['result']=='win'
        held=[h for h in held if h[0]>d]
        free=slots-len(held)
        if free>0 and d in byday:
            c=byday[d][:]; rnd.shuffle(c)
            for e in c[:free]: held.append((e['resolve_date'],e,eq/slots))
        peak=max(peak,eq); mdd=min(mdd,eq/peak-1)
    return (eq-1)*100, n, (w/n*100 if n else 0), mdd*100

def band(ev,N=200):
    r=[sim(ev,seed=i) for i in range(N)]
    f=sorted(x[0] for x in r)
    return f[N//2], f[N//20], f[N-N//20], sorted(x[1] for x in r)[N//2], sorted(x[2] for x in r)[N//2], sorted(x[3] for x in r)[N//2]

VAR=[('+20/-10 (현행)','bt_*.json',''),
     ('+30/-10','t30s10_*.json','exit/'),
     ('+40/-10','t40s10_*.json','exit/'),
     ('+50/-10','t50s10_*.json','exit/'),
     ('+20/-7','t20s7_*.json','exit/'),
     ('+30/-7','t30s7_*.json','exit/'),
     ('+25/-12','t25s12_*.json','exit/'),
     ('+15/-10','t15s10_*.json','exit/')]
print("="*94)
print("청산 규칙 비교 — 5년 8개월, 슬롯5 자산곡선 (200회 중앙)")
print("="*94)
print(f"{'규칙':<16}{'후보':>7}{'승률':>7}{'손익분기':>9}{'여유':>7}{'거래당순':>9}{'자산곡선':>10}{'5~95%':>17}{'낙폭':>8}")
print('-'*94)
for lab,pat,fol in VAR:
    ev,nf=load(pat,fol)
    if ev is None:
        print(f"{lab:<16}  … 미완성 ({nf}/6 연도) — 구간이 달라 비교 제외")
        continue
    net=[FEE(e['gain_at_resolve_pct']) for e in ev]
    w=[x for x in net if x>0]; l=[x for x in net if x<=0]
    be=abs(st.mean(l))/(st.mean(w)+abs(st.mean(l)))*100
    wr=len(w)/len(ev)*100
    m,lo,hi,n,swr,md=band(ev)
    print(f"{lab:<16}{len(ev):>7}{wr:>6.1f}%{be:>8.1f}%{wr-be:>+6.1f}%p{st.mean(net):>+8.2f}%{m:>+9.1f}%{f'{lo:+.0f}~{hi:+.0f}%':>17}{md:>7.1f}%")
print()
print("벤치마크  코스피 +109.0%   평균 종목 +3.0%")
