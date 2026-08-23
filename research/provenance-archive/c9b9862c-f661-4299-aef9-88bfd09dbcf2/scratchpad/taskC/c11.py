import json,os,collections,math,random,sys
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix
S=os.environ['SCRATCH']
rows=json.load(open(os.path.join(S,'taskC','joinedC2.json'),encoding='utf-8'))
LAB={"1":"①","2":"②","3":"③","4":"④","5":"⑤","6":"⑥","7":"⑦","8":"⑧"}
cache={}
def ser(c):
    if c not in cache:
        try: cache[c]=ohlcv_matrix.get_series(c)
        except Exception: cache[c]=None
    return cache[c]
# 변동성(직전 20일 종가수익률 표준편차)
for r in rows:
    s=ser(r['code']); r['vol20']=None
    if not s: continue
    try: i=s['dates'].index(r['date'])
    except ValueError: continue
    cl=s['closes'][max(0,i-20):i+1]
    rr=[(cl[j]/cl[j-1]-1)*100 for j in range(1,len(cl)) if cl[j-1]]
    if len(rr)>=10:
        m=sum(rr)/len(rr); r['vol20']=math.sqrt(sum((x-m)**2 for x in rr)/(len(rr)-1))
def prep(rs,hk):
    out=[]
    for r in rs:
        h=r.get(hk)
        if not h: continue
        q=dict(r); q['is_stop']=1 if h['out']=='stop' else 0
        q['rule_ret']=-10.0 if h['out']=='stop' else (20.0 if h['out']=='target' else h['ret'])
        out.append(q)
    return out
def within(rs,key):
    byd=collections.defaultdict(list)
    for r in rs: byd[r['date']].append(r)
    hi=[];lo=[]
    for d,g in byd.items():
        if len(g)<4: continue
        v=sorted(x[key] for x in g); med=v[len(v)//2]
        a=[x for x in g if x[key]>med]; b=[x for x in g if x[key]<=med]
        if a and b: hi+=a; lo+=b
    if not hi or not lo: return None
    return (100*sum(x['is_stop'] for x in hi)/len(hi)-100*sum(x['is_stop'] for x in lo)/len(lo), len(hi)+len(lo))
print('=== 강건성 A: 20일 고정창 (날짜내 상위-하위 손절률 차, +면 여유클수록 손절↑) ===')
H20=prep(rows,'h20'); H10=prep(rows,'h10')
print('n10=%d n20=%d'%(len(H10),len(H20)))
for k in '12345678':
    a=within(H10,'pct_'+k); b=within(H20,'pct_'+k)
    print(f"  {LAB[k]}  10일 "+(f"{a[0]:+6.1f}%p(n={a[1]})" if a else "  n/a")+"   20일 "+(f"{b[0]:+6.1f}%p(n={b[1]})" if b else "  n/a"))
for nm,key in [('종합min','gm_score')]:
    a=within(H10,key); b=within(H20,key)
    print(f"  {nm} 10일 {a[0]:+6.1f}%p   20일 {b[0]:+6.1f}%p")
print()
print('=== 강건성 B: 원장 outcome(전량, 미결=비손절 처리) ===')
L=[dict(r,is_stop=1 if r['outcome']=='stop' else 0) for r in rows if r['outcome']]
print('n=%d'%len(L))
for k in '12345678':
    a=within(L,'pct_'+k); print(f"  {LAB[k]}  {a[0]:+6.1f}%p")
a=within(L,'gm_score'); print(f"  종합min {a[0]:+6.1f}%p")
print()
print('=== 강건성 C: 여유도와 변동성(직전20일 일간표준편차) 상관 ===')
V=[r for r in H10 if r['vol20']]
def corr(a,b):
    ma=sum(a)/len(a); mb=sum(b)/len(b)
    num=sum((x-ma)*(y-mb) for x,y in zip(a,b))
    da=math.sqrt(sum((x-ma)**2 for x in a)); db=math.sqrt(sum((y-mb)**2 for y in b))
    return num/(da*db) if da and db else 0
for k in '12345678':
    print(f"  {LAB[k]} corr(pct,vol20)={corr([r['pct_'+k] for r in V],[r['vol20'] for r in V]):+.2f}")
print(f"  종합min corr={corr([r['gm_score'] for r in V],[r['vol20'] for r in V]):+.2f}")
lo=[r for r in V if r['vol20']<3]; hi=[r for r in V if r['vol20']>=3]
print('  변동성<3%%: n=%d 손절률 %.1f%% | >=3%%: n=%d 손절률 %.1f%%'%(len(lo),100*sum(r['is_stop'] for r in lo)/len(lo),len(hi),100*sum(r['is_stop'] for r in hi)/len(hi)))
print()
print('=== 강건성 D: 변동성 구간 내에서 ⑥·⑧·⑦ 효과 (변동성 통제) ===')
for band,sel in [('저변동(<3%)',lo),('고변동(>=3%)',hi)]:
    out=[]
    for k in '678':
        v=sorted(r['pct_'+k] for r in sel); med=v[len(v)//2]
        a=[r for r in sel if r['pct_'+k]>med]; b=[r for r in sel if r['pct_'+k]<=med]
        d=100*sum(r['is_stop'] for r in a)/len(a)-100*sum(r['is_stop'] for r in b)/len(b)
        out.append(f"{LAB[k]} {d:+5.1f}%p")
    print('  '+band+' n=%d  '%len(sel)+'  '.join(out))
