# -*- coding: utf-8 -*-
"""거래당 +0.12% 인데 자산곡선 -20.7% — 변동성 손실(variance drag) 확인."""
import json, glob, os, random, collections, statistics as st, math
B=os.environ['LOCALAPPDATA']+'/Temp/bt5y/'
EV=[]
for f in sorted(glob.glob(B+'bt_*.json')):
    EV += [e for e in json.load(open(f,encoding='utf-8'))['events'] if e['result'] in ('win','loss')]
seen=set(); U=[]
for e in sorted(EV,key=lambda x:(x['entry_date'],x['code'])):
    k=(e['scan_date'],e['code'],e['pattern'])
    if k not in seen: seen.add(k); U.append(e)
EV=U
FEE=lambda g: ((1+g/100)*(1-0.0034)/(1+0.0014)-1)*100

net=[FEE(e['gain_at_resolve_pct']) for e in EV]
w=[x for x in net if x>0]; l=[x for x in net if x<=0]
print(f"전체 {len(EV):,}건")
print(f"  승 {len(w):,}건 평균 {st.mean(w):+.2f}%   패 {len(l):,}건 평균 {st.mean(l):+.2f}%")
print(f"  거래당 산술평균 {st.mean(net):+.3f}%   표준편차 {st.stdev(net):.2f}%")
print(f"  손익비 {abs(st.mean(w)/st.mean(l)):.2f}  손익분기 승률 {abs(st.mean(l))/(st.mean(w)+abs(st.mean(l)))*100:.1f}%  실제 {len(w)/len(EV)*100:.1f}%")

print("\n[변동성 손실] 자본의 1/5씩 넣을 때")
r=[x/5/100 for x in net]
ar=st.mean(r); gr=st.mean([math.log(1+x) for x in r])
print(f"  산술 수익 {ar*100:+.4f}%/거래  기하 수익 {(math.exp(gr)-1)*100:+.4f}%/거래  차이(손실) {(ar-(math.exp(gr)-1))*100:.4f}%p")
print(f"  → 431거래 복리: 산술이면 {((1+ar)**431-1)*100:+.1f}%, 기하면 {(math.exp(gr*431)-1)*100:+.1f}%")

print("\n[슬롯5가 실제로 고른 431건은 전체와 다른가]")
def taken(seed, slots=5):
    byday=collections.defaultdict(list)
    for e in EV: byday[e['entry_date']].append(e)
    rnd=random.Random(seed); held=[]; out=[]
    for d in sorted(set(list(byday)+[e['resolve_date'] for e in EV])):
        held=[h for h in held if h[0]>d]
        free=slots-len(held)
        if free>0 and d in byday:
            c=byday[d][:]; rnd.shuffle(c)
            for e in c[:free]: held.append((e['resolve_date'],e)); out.append(e)
    return out
T=taken(0)
tn=[FEE(e['gain_at_resolve_pct']) for e in T]
print(f"  선택 {len(T)}건  승률 {sum(1 for x in tn if x>0)/len(tn)*100:.1f}%  거래당 {st.mean(tn):+.3f}%")
print(f"  (전체 {len(EV)}건 승률 {len(w)/len(EV)*100:.1f}% 거래당 {st.mean(net):+.3f}%)")
print(f"  → 슬롯 제약은 선별을 바꾸지 않는다(승자가 오래 자리를 잡아 매수 기회를 줄일 뿐)")

print("\n[결론 확인] 자산곡선이 마이너스인 이유")
print(f"  거래당 +{st.mean(net):.3f}% 는 산술평균이다. 실제 돈은 곱하기로 불어나므로")
print(f"  변동성이 크면 같은 평균이라도 원금이 준다. 여기선 표준편차 {st.stdev(net):.1f}% 대비")
print(f"  평균이 {st.mean(net):.2f}% 라 변동성 손실이 평균을 잡아먹는다.")
print(f"  손익분기를 넘으려면 승률이 {abs(st.mean(l))/(st.mean(w)+abs(st.mean(l)))*100:.1f}% 이상이어야 하는데 실제는 {len(w)/len(EV)*100:.1f}%.")
