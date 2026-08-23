import io
exec(io.open('rules.py',encoding='utf-8').read())

def within_rank(feat, minn=2):
    """returns list of (event, normalized rank 0..1 where 1=highest feat)"""
    out=[]
    for d in DAYS:
        g=BY[d]
        if len(g)<minn: continue
        vals=sorted(g,key=lambda e:(feat(e),e['code']))
        n=len(g)
        for i,e in enumerate(vals):
            out.append((e, i/(n-1) if n>1 else 0.5, d))
    return out

feats={'거래대금':lambda e:e['turnover_eok'],
       'ATR':lambda e:e['atr_pct'],
       'RS':lambda e:e['rs'],
       '갭업':lambda e:e['gap_up_pct'],
       '주가':lambda e:e['entry_price']}

for nm,f in feats.items():
    R=within_rank(f)
    res=[(e,r) for e,r in [(x[0],x[1]) for x in R] if e['result'] in ('win','loss')]
    wr=[r for e,r in res if e['result']=='win']; lr=[r for e,r in res if e['result']=='loss']
    obs=sum(wr)/len(wr)-sum(lr)/len(lr)
    # permutation: shuffle result within day
    byd=defaultdict(list)
    for e,r,d in R:
        if e['result'] in ('win','loss'): byd[d].append((e['result'],r))
    rnd=random.Random(7); cnt=0; NP=3000
    for _ in range(NP):
        W=[];L=[]
        for d,lst in byd.items():
            labs=[x[0] for x in lst]; rnd.shuffle(labs)
            for lab,(_,r) in zip(labs,lst):
                (W if lab=='win' else L).append(r)
        if not W or not L: continue
        s=sum(W)/len(W)-sum(L)/len(L)
        if abs(s)>=abs(obs)-1e-12: cnt+=1
    print(f'{nm:6s} 승자평균순위-패자평균순위 = {obs:+.4f}  (0.5=무작위 기준, n승{len(wr)} n패{len(lr)})  perm p={(cnt+1)/(NP+1):.4f}')

print()
# quintiles of within-day turnover rank
R=within_rank(lambda e:e['turnover_eok'], minn=3)
bins=[[] for _ in range(5)]
for e,r,d in R:
    b=min(4,int(r*5)); bins[b].append(e)
print('같은날 거래대금 상대순위 5분위 (하위→상위, 3건이상인 날만)')
for i,b in enumerate(bins):
    w=sum(1 for e in b if e['result']=='win'); rr=sum(1 for e in b if e['result'] in ('win','loss'))
    m=sum(ret(e) for e in b)/len(b)
    print(f'  {i+1}분위 n={len(b):3d} 승률(결착기준)={w/rr*100:5.1f}%  평균수익={m:+5.2f}%')
