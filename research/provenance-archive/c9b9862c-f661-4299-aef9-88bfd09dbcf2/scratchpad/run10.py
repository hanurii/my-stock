import io
exec(io.open('rules.py',encoding='utf-8').read())
d7=[d for d in DAYS if len(BY[d])>=7]
rnd=random.Random(31); tot=0
for _ in range(2000):
    s=0
    for d in d7:
        g=BY[d]; a=set(x['code'] for x in random.sample(g,6)); b=set(x['code'] for x in random.sample(g,6))
        s+=len(a&b)
    tot+=s/(6*len(d7))
print(f'[D1] 무작위 두 규칙끼리의 기계적 겹침 기대치 = {tot/2000*100:.1f}%  (7건이상 {len(d7)}일)')
print('    → 겹침 70%대는 "그림자"의 증거가 못 됨(무작위끼리도 이만큼 겹침)')

# 월별 부호
print('\n[D2] 월별 같은날 거래대금 순위차')
bym=defaultdict(list)
for d in DAYS: bym[d[:7]].append(d)
pos=0;neg=0
for m in sorted(bym):
    W=[];L=[]
    for d in bym[m]:
        g=BY[d]
        if len(g)<2: continue
        v=sorted(g,key=lambda e:(e['turnover_eok'],e['code'])); n=len(g)
        for i,e in enumerate(v):
            if e['result']=='win': W.append(i/(n-1))
            elif e['result']=='loss': L.append(i/(n-1))
    if W and L:
        s=sum(W)/len(W)-sum(L)/len(L); pos+= s>0; neg+= s<=0
        print(f'   {m} {s:+.3f} (승{len(W)}/패{len(L)})')
print(f'   부호 +{pos} / -{neg}')

# 일 단위 잭나이프
print('\n[D3] 하루씩 빼는 잭나이프(가장 영향 큰 날 제거 후)')
def stat(days):
    W=[];L=[]
    for d in days:
        g=BY[d]
        if len(g)<2: continue
        v=sorted(g,key=lambda e:(e['turnover_eok'],e['code'])); n=len(g)
        for i,e in enumerate(v):
            if e['result']=='win': W.append(i/(n-1))
            elif e['result']=='loss': L.append(i/(n-1))
    return sum(W)/len(W)-sum(L)/len(L)
full=stat(DAYS)
js=sorted(((stat([x for x in DAYS if x!=d]),d) for d in DAYS))
print(f'   전체 {full:+.4f}; 가장 낮아지는 5일 제거시: ', [f'{s:+.4f}' for s,_ in js[:5]])
print(f'   상위 3일 제거해도 {stat([x for x in DAYS if x not in {js[0][1],js[1][1],js[2][1]}]):+.4f}')
