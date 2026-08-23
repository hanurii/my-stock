import json,os,collections,math,sys,random
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix
S=os.environ['SCRATCH']
rows=json.load(open(os.path.join(S,'taskC','joinedC2.json'),encoding='utf-8'))
LAB={"1":"①150·200일선","2":"②150>200","3":"③200일선상승","4":"④50일선정렬","5":"⑤50일선","6":"⑥52주저가","7":"⑦52주고가","8":"⑧RS"}
cache={}
def ser(c):
    if c not in cache:
        try: cache[c]=ohlcv_matrix.get_series(c)
        except Exception: cache[c]=None
    return cache[c]
H=[]
for r in rows:
    h=r.get('h10')
    if not h: continue
    s=ser(r['code']); vol=None
    if s:
        try:
            i=s['dates'].index(r['date']); cl=s['closes'][max(0,i-20):i+1]
            rr=[(cl[j]/cl[j-1]-1)*100 for j in range(1,len(cl)) if cl[j-1]]
            if len(rr)>=10:
                m=sum(rr)/len(rr); vol=math.sqrt(sum((x-m)**2 for x in rr)/(len(rr)-1))
        except ValueError: pass
    if vol is None: continue
    q=dict(r); q['vol20']=vol; q['is_stop']=1 if h['out']=='stop' else 0
    H.append(q)
byd=collections.defaultdict(list)
for r in H: byd[r['date']].append(r)
for r in H:
    g=byd[r['date']]
    o=[x['is_stop'] for x in g if x is not r]
    r['day_rate']=sum(o)/len(o) if o else 0.5
def z(vals):
    m=sum(vals)/len(vals); sd=math.sqrt(sum((x-m)**2 for x in vals)/max(1,len(vals)-1)) or 1
    return m,sd
def logit(X,y,iters=300,lr=0.3):
    p=len(X[0]); w=[0.0]*p; b=0.0
    n=len(y)
    for _ in range(iters):
        gw=[0.0]*p; gb=0.0
        for xi,yi in zip(X,y):
            s=b+sum(w[j]*xi[j] for j in range(p))
            pr=1/(1+math.exp(-max(-30,min(30,s))))
            e=pr-yi
            for j in range(p): gw[j]+=e*xi[j]
            gb+=e
        for j in range(p): w[j]-=lr*gw[j]/n
        b-=lr*gb/n
    return w,b
def fit(rs,key):
    mv,sv=z([r['vol20'] for r in rs]); md,sd=z([r['day_rate'] for r in rs]); mp,sp=z([r[key] for r in rs])
    X=[[(r['vol20']-mv)/sv,(r['day_rate']-md)/sd,(r[key]-mp)/sp] for r in rs]
    y=[r['is_stop'] for r in rs]
    w,b=logit(X,y)
    return w
print('=== 5) 변동성·그날 시장 통제 후 조건별 계수 (로지스틱, 표준화; +면 여유클수록 손절↑) ===')
print('n=%d 종목=%d'%(len(H),len({r['code'] for r in H})))
byc=collections.defaultdict(list)
for r in H: byc[r['code']].append(r)
ks=list(byc)
print(f"{'조건':<14}{'계수':>8}{'클러스터95%CI':>20}{'p(부호반대)':>12}")
for k in list('12345678'):
    key='pct_'+k
    w=fit(H,key)[2]
    rnd=random.Random(101); vals=[]
    for _ in range(400):
        samp=[x for kk in (rnd.choice(ks) for _ in ks) for x in byc[kk]]
        try: vals.append(fit(samp,key)[2])
        except Exception: pass
    vals.sort()
    pneg=sum(1 for v in vals if v*w<0)/len(vals)
    print(f"{LAB[k]:<14}{w:>+8.3f}   [{vals[int(.025*len(vals))]:+.3f},{vals[int(.975*len(vals))]:+.3f}]{pneg:>12.3f}")
w=fit(H,'gm_score')[2]
rnd=random.Random(101); vals=[]
for _ in range(400):
    samp=[x for kk in (rnd.choice(ks) for _ in ks) for x in byc[kk]]
    try: vals.append(fit(samp,'gm_score')[2])
    except Exception: pass
vals.sort()
print(f"{'종합min':<14}{w:>+8.3f}   [{vals[int(.025*len(vals))]:+.3f},{vals[int(.975*len(vals))]:+.3f}]")
# 변동성/시장 계수 참고
w2=fit(H,'pct_7')
print('  참고: 변동성 계수 %+.3f · 그날시장 계수 %+.3f'%(w2[0],w2[1]))
