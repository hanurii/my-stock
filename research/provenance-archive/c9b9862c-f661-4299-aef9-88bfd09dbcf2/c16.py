import json,os,collections,math,sys
import numpy as np
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix
S=os.environ['SCRATCH']
rows=json.load(open(os.path.join(S,'taskC','joinedC2.json'),encoding='utf-8'))
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
    q['rule_ret']=-10.0 if h['out']=='stop' else (20.0 if h['out']=='target' else h['ret'])
    p={k:r['pct_'+k] for k in '12345678'}; v=sorted(p.values())
    q['S_min']=v[0]; q['S_low2']=(v[0]+v[1])/2; q['S_7']=p['7']; q['S_7ext']=p['7']-(p['6']+p['8'])/2
    q['near10']=1 if (r['mrg_7']-25.0)>=-10 else 0
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
near=np.array([r['near10'] for r in H],float)
def newton(X,y,it=25):
    X=np.column_stack([np.ones(len(y)),X]); w=np.zeros(X.shape[1])
    for _ in range(it):
        s=np.clip(X@w,-30,30); p=1/(1+np.exp(-s)); W=np.clip(p*(1-p),1e-6,None)
        g=X.T@(y-p)-1e-3*w; Hm=(X.T*W)@X+1e-3*np.eye(X.shape[1])
        try: w=w+np.linalg.solve(Hm,g)
        except np.linalg.LinAlgError: break
    return w
codes=[r['code'] for r in H]; byc=collections.defaultdict(list)
for i,c in enumerate(codes): byc[c].append(i)
ks=list(byc); rng=np.random.default_rng(5)
X=np.column_stack([vol,day,near])
w=newton(X,y); vals=[]
for _ in range(800):
    pick=rng.integers(0,len(ks),len(ks)); idx=np.concatenate([byc[ks[i]] for i in pick])
    try: vals.append(newton(X[idx],y[idx])[3])
    except Exception: pass
vals=np.sort(np.array(vals))
print('=== ⑦ "52주고가 -10% 이내" 더미, 변동성·그날시장 통제 ===')
print('  계수 %+.3f (오즈비 %.2f) 95%%CI[%+.3f,%+.3f] p(계수>=0)=%.3f'%(w[3],math.exp(w[3]),vals[19],vals[-20],(vals>=0).mean()))
print('  단순 손절률: -10%% 이내 %.1f%%(n=%d) vs 더 먼 %.1f%%(n=%d)'%(
  100*np.mean(y[near==1]),(near==1).sum(),100*np.mean(y[near==0]),(near==0).sum()))
print()
print('=== 4b) 이중층화(날짜 × 변동성4분위) 안에서 점수 상위절반-하위절반 ===')
V=sorted(H,key=lambda r:r['vol20']); n=len(V)
for i,r in enumerate(V): r['vq']=min(3,i*4//n)
def strat(key):
    hi=[];lo=[]
    g2=collections.defaultdict(list)
    for r in H: g2[(r['date'],r['vq'])].append(r)
    for kk,g in g2.items():
        if len(g)<4: continue
        o=sorted(g,key=lambda r:(r[key],r['code'])); m=len(o)//2
        lo+=o[:m]; hi+=o[len(o)-m:]
    if not hi: return None
    return (len(hi),100*sum(r['is_stop'] for r in hi)/len(hi)-100*sum(r['is_stop'] for r in lo)/len(lo),
            sum(r['rule_ret'] for r in hi)/len(hi)-sum(r['rule_ret'] for r in lo)/len(lo))
for nm,key in [('현행 min(8조건)','S_min'),('하위2개평균','S_low2'),('⑦ 단독','S_7'),('⑦-(⑥⑧평균)','S_7ext')]:
    s=strat(key)
    if s: print(f"  {nm:<14} 대상 {s[0]*2:>3}건  손절률차 {s[1]:+6.1f}%p  규칙수익차 {s[2]:+6.2f}%p")
print()
print('=== 참고: 변동성만으로 층화(날짜내) ===')
def strat_day(key):
    hi=[];lo=[]
    for d,g in byd.items():
        if len(g)<4: continue
        o=sorted(g,key=lambda r:(r[key],r['code'])); m=len(o)//2
        lo+=o[:m]; hi+=o[len(o)-m:]
    return (100*sum(r['is_stop'] for r in hi)/len(hi)-100*sum(r['is_stop'] for r in lo)/len(lo),
            sum(r['rule_ret'] for r in hi)/len(hi)-sum(r['rule_ret'] for r in lo)/len(lo))
a=strat_day('vol20'); print('  변동성 상위절반-하위절반: 손절률차 %+.1f%%p 규칙수익차 %+.2f%%p'%a)
