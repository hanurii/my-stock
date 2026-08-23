import io
exec(io.open('rules.py',encoding='utf-8').read())
def rankstat(events_by_day):
    W=[];L=[]
    for d,g in events_by_day.items():
        if len(g)<2: continue
        v=sorted(g,key=lambda e:(e['turnover_eok'],e['code'])); n=len(g)
        for i,e in enumerate(v):
            if e['result']=='win': W.append(i/(n-1))
            elif e['result']=='loss': L.append(i/(n-1))
    return (sum(W)/len(W)-sum(L)/len(L), len(W),len(L)) if W and L else (None,0,0)
def permp(byd,obs,NP=3000,seed=4):
    rnd=random.Random(seed); c=0
    prep=[]
    for d,g in byd.items():
        if len(g)<2: continue
        v=sorted(g,key=lambda e:(e['turnover_eok'],e['code'])); n=len(g)
        prep.append([(e['result'],i/(n-1)) for i,e in enumerate(v) if e['result'] in ('win','loss')])
    for _ in range(NP):
        W=[];L=[]
        for lst in prep:
            labs=[x[0] for x in lst]; rnd.shuffle(labs)
            for lab,(_,r) in zip(labs,lst): (W if lab=='win' else L).append(r)
        if W and L and abs(sum(W)/len(W)-sum(L)/len(L))>=abs(obs)-1e-12: c+=1
    return (c+1)/(NP+1)

print('[C1] 저유동(<20억) 54건 제외해도 남는가')
for lab,thr in (('전체',0),('20억이상만',20),('50억이상만',50),('100억이상만',100)):
    byd=defaultdict(list)
    for e in EV:
        if e['turnover_eok']>=thr: byd[e['entry_date']].append(e)
    s,nw,nl=rankstat(byd)
    if s is None: continue
    p=permp(byd,s)
    print(f'  {lab:10s} 순위차 {s:+.4f} (승{nw}/패{nl}) p={p:.4f}')

print('\n[C2] 하루 후보 4건 이상인 날만 (순서가 실제로 중요한 날)')
byd={d:BY[d] for d in DAYS if len(BY[d])>=4}
s,nw,nl=rankstat(byd); print(f'  순위차 {s:+.4f} (승{nw}/패{nl}) p={permp(byd,s):.4f}')

print('\n[C3] 종목당 1거래만 (첫 거래) — 반복 접기')
seen=set(); byd=defaultdict(list)
for e in sorted(EV,key=lambda x:x['entry_date']):
    if e['code'] in seen: continue
    seen.add(e['code']); byd[e['entry_date']].append(e)
s,nw,nl=rankstat(byd); print(f'  n={sum(len(v) for v in byd.values())} 순위차 {s:+.4f} (승{nw}/패{nl}) p={permp(byd,s):.4f}')

print('\n[C4] 겹침: 거래대금큰순 top6 선택과 다른 규칙 top6 선택의 일치율 (7건이상 날)')
d7=[d for d in DAYS if len(BY[d])>=7]
base={d:set(e['code'] for e in rank(BY[d],'거래대금큰순')[:6]) for d in d7}
for r in RULES:
    if r=='거래대금큰순': continue
    ov=sum(len(base[d]&set(e['code'] for e in rank(BY[d],r)[:6])) for d in d7)/(6*len(d7))*100
    print(f'  {r:22s} {ov:5.1f}%')

print('\n[C5] 갭업 있음/없음 승률')
for lab,f in (('갭업 0%',lambda e:e['gap_up_pct']<=0.001),('갭 0~1%',lambda e:0.001<e['gap_up_pct']<=1),('갭 1~3%',lambda e:1<e['gap_up_pct']<=3),('갭 3%+',lambda e:e['gap_up_pct']>3)):
    g=[e for e in EV if f(e)]
    w=sum(1 for e in g if e['result']=='win'); r=sum(1 for e in g if e['result'] in ('win','loss'))
    print(f'  {lab:8s} n={len(g):3d} 승률{w/r*100:5.1f}% 기대{sum(ret(e) for e in g)/len(g):+5.2f}%')
