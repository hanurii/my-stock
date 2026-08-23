import json,os,collections,math,sys,random
import numpy as np
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
    g=byd[r['date']]; o=[x['is_stop'] for x in g if x is not r]
    r['day_rate']=sum(o)/len(o) if o else 0.5
def zz(a):
    a=np.asarray(a,float); s=a.std(ddof=1) or 1.0
    return (a-a.mean())/s
y=np.array([r['is_stop'] for r in H],float)
vol=zz([r['vol20'] for r in H]); day=zz([r['day_rate'] for r in H])
feat={k:zz([r['pct_'+k] for r in H]) for k in '12345678'}
feat['min']=zz([r['gm_score'] for r in H])
codes=[r['code'] for r in H]
def newton(X,y,iters=25):
    X=np.column_stack([np.ones(len(y)),X]); w=np.zeros(X.shape[1])
    for _ in range(iters):
        s=np.clip(X@w,-30,30); p=1/(1+np.exp(-s)); W=np.clip(p*(1-p),1e-6,None)
        g=X.T@(y-p)-1e-3*w
        Hm=(X.T*W)@X+1e-3*np.eye(X.shape[1])
        try: w=w+np.linalg.solve(Hm,g)
        except np.linalg.LinAlgError: break
    return w
byc=collections.defaultdict(list)
for i,c in enumerate(codes): byc[c].append(i)
ks=list(byc)
rnd=np.random.default_rng(7)
print('=== 5) 변동성 + 그날 시장 통제 후, 조건별 pct 계수 (로지스틱, 표준화) ===')
print('   +계수 = 여유가 클수록 손절↑ (직관과 반대) / -계수 = 빡빡할수록 손절↑ (직관대로)')
print('   n=%d, 종목=%d'%(len(H),len(ks)))
print(f"{'조건':<14}{'계수':>9}{'종목클러스터 95%CI':>24}")
for k in list('12345678')+['min']:
    X=np.column_stack([vol,day,feat[k]])
    w=newton(X,y)[3]
    vals=[]
    for _ in range(600):
        pick=rnd.integers(0,len(ks),len(ks))
        idx=np.concatenate([byc[ks[i]] for i in pick])
        try: vals.append(newton(X[idx],y[idx])[3])
        except Exception: pass
    vals=np.sort(np.array(vals))
    nm=LAB.get(k,'종합min')
    print(f"{nm:<14}{w:>+9.3f}   [{vals[int(.025*len(vals))]:+.3f}, {vals[int(.975*len(vals))]:+.3f}]")
X=np.column_stack([vol,day,feat['7']]); w=newton(X,y)
print('   참고 계수: 변동성 %+.3f · 그날시장 %+.3f'%(w[1],w[2]))
