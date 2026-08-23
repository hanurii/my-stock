import json,os,collections,math,sys,random
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix
S=os.environ['SCRATCH']
rows=json.load(open(os.path.join(S,'taskC','joinedC2.json'),encoding='utf-8'))
LAB={"1":"①150·200","2":"②150>200","3":"③200상승","4":"④50정렬","5":"⑤50일선","6":"⑥52주저가","7":"⑦52주고가","8":"⑧RS"}
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
    s=ser(r['code'])
    vol=None
    if s:
        try:
            i=s['dates'].index(r['date']); cl=s['closes'][max(0,i-20):i+1]
            rr=[(cl[j]/cl[j-1]-1)*100 for j in range(1,len(cl)) if cl[j-1]]
            if len(rr)>=10:
                m=sum(rr)/len(rr); vol=math.sqrt(sum((x-m)**2 for x in rr)/(len(rr)-1))
        except ValueError: pass
    q=dict(r); q['vol20']=vol
    q['is_stop']=1 if h['out']=='stop' else 0
    q['rule_ret']=-10.0 if h['out']=='stop' else (20.0 if h['out']=='target' else h['ret'])
    H.append(q)
V=[r for r in H if r['vol20'] is not None]
V.sort(key=lambda r:r['vol20'])
half=len(V)//2
bands=[('저변동(하위50%%, 일변동<%.1f%%)'%V[half]['vol20'],V[:half]),('고변동(상위50%%)',V[half:])]
def rank_split(rs,key):
    o=sorted(rs,key=lambda r:(r[key],r['code'],r['date']))
    n=len(o); return o[:n//2], o[n-n//2:]
print('=== 강건성 D(수정): 변동성 반분 안에서 조건별 효과 (여유 상위 - 하위 손절률차) ===')
print('   전체 손절률: 저변동 %.1f%% / 고변동 %.1f%%'%(100*sum(r['is_stop'] for r in bands[0][1])/len(bands[0][1]),100*sum(r['is_stop'] for r in bands[1][1])/len(bands[1][1])))
print(f"{'조건':<12}{'저변동차':>10}{'고변동차':>10}{'통제 후 평균':>12}{'통제 전(날짜내)':>14}")
byd=collections.defaultdict(list)
for r in H: byd[r['date']].append(r)
def within(rs,key):
    hi=[];lo=[]
    d2=collections.defaultdict(list)
    for r in rs: d2[r['date']].append(r)
    for d,g in d2.items():
        if len(g)<4: continue
        a,b=rank_split(g,key)
        hi+=b; lo+=a
    if not hi or not lo: return None
    return 100*sum(x['is_stop'] for x in hi)/len(hi)-100*sum(x['is_stop'] for x in lo)/len(lo)
for k in '12345678':
    ds=[]
    for nm,sel in bands:
        a,b=rank_split(sel,'pct_'+k)
        ds.append(100*sum(r['is_stop'] for r in b)/len(b)-100*sum(r['is_stop'] for r in a)/len(a))
    w=within(H,'pct_'+k)
    print(f"{LAB[k]:<12}{ds[0]:>+10.1f}{ds[1]:>+10.1f}{sum(ds)/2:>+12.1f}{(w if w is not None else float('nan')):>+14.1f}")
ds=[]
for nm,sel in bands:
    a,b=rank_split(sel,'gm_score')
    ds.append(100*sum(r['is_stop'] for r in b)/len(b)-100*sum(r['is_stop'] for r in a)/len(a))
print(f"{'종합min':<12}{ds[0]:>+10.1f}{ds[1]:>+10.1f}{sum(ds)/2:>+12.1f}{within(H,'gm_score'):>+14.1f}")
# 변동성 자체 판별력
print()
o=sorted(V,key=lambda r:r['vol20']); n=len(o)
for i,lab in enumerate(['최저1/4','2/4','3/4','최고1/4']):
    g=o[i*n//4:(i+1)*n//4]
    print(f"  변동성 {lab}: 일변동 {g[0]['vol20']:.1f}~{g[-1]['vol20']:.1f}%  n={len(g)} 손절률 {100*sum(r['is_stop'] for r in g)/len(g):>5.1f}%  규칙수익 {sum(r['rule_ret'] for r in g)/len(g):>6.2f}%")
