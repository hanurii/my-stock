import io
exec(io.open('rules.py',encoding='utf-8').read())
SPLIT='2026-03-25'

def rank_stat(days, feat=lambda e:e['turnover_eok']):
    W=[];L=[]
    for d in days:
        g=BY[d]
        if len(g)<2: continue
        vals=sorted(g,key=lambda e:(feat(e),e['code'])); n=len(g)
        for i,e in enumerate(vals):
            if e['result']=='win': W.append(i/(n-1))
            elif e['result']=='loss': L.append(i/(n-1))
    if not W or not L: return None,0,0
    return sum(W)/len(W)-sum(L)/len(L), len(W), len(L)

h1=[d for d in DAYS if d< SPLIT]; h2=[d for d in DAYS if d>=SPLIT]
print('전반기(진입일<%s) 일수%d / 후반기 %d'%(SPLIT,len(h1),len(h2)))
for nm,dd in (('전반',h1),('후반',h2),('전체',DAYS)):
    s,nw,nl=rank_stat(dd); print(f'  {nm} 거래대금 순위차 {s:+.4f} (승{nw}/패{nl})')

# 국면별
up=[d for d in DAYS if regime_up(BY[d][0]['scan_date'])]
dn=[d for d in DAYS if not regime_up(BY[d][0]['scan_date'])]
for nm,dd in (('상승국면일',up),('조정국면일',dn)):
    s,nw,nl=rank_stat(dd); print(f'  {nm}({len(dd)}일) 거래대금 순위차 {s:+.4f} (승{nw}/패{nl})')

# 종목 클러스터 부트스트랩 (350 종목 리샘플)
bycode=defaultdict(list)
for e in EV: bycode[e['code']].append(e)
codes=list(bycode)
# precompute per-event within-day rank
rankmap={}
for d in DAYS:
    g=BY[d]
    if len(g)<2: continue
    vals=sorted(g,key=lambda e:(e['turnover_eok'],e['code'])); n=len(g)
    for i,e in enumerate(vals): rankmap[id(e)]=i/(n-1)
rnd=random.Random(11); stats=[]
for _ in range(2000):
    W=[];L=[]
    for _ in range(len(codes)):
        c=codes[rnd.randrange(len(codes))]
        for e in bycode[c]:
            if id(e) not in rankmap: continue
            if e['result']=='win': W.append(rankmap[id(e)])
            elif e['result']=='loss': L.append(rankmap[id(e)])
    if W and L: stats.append(sum(W)/len(W)-sum(L)/len(L))
stats.sort()
lo=stats[int(.025*len(stats))]; hi=stats[int(.975*len(stats))]
neg=sum(1 for s in stats if s<=0)/len(stats)
print(f'\n종목 클러스터 부트스트랩(2000회): 95%CI [{lo:+.4f}, {hi:+.4f}]  0이하 비율={neg:.4f}')

# 절대 거래대금 구간
print('\n절대 50일평균 거래대금 구간별')
edges=[(0,20),(20,50),(50,100),(100,300),(300,1e9)]
for a,b in edges:
    g=[e for e in EV if a<=e['turnover_eok']<b]
    if not g: continue
    w=sum(1 for e in g if e['result']=='win'); r=sum(1 for e in g if e['result'] in ('win','loss'))
    print(f'  {a}~{b if b<1e9 else "∞"}억  n={len(g):3d} 승률={w/r*100:5.1f}% 기대수익={sum(ret(e) for e in g)/len(g):+5.2f}%')
