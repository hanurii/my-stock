import json,os,sys,collections
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix
S=os.environ['SCRATCH']
rows=json.load(open(os.path.join(S,'taskC','joinedC.json'),encoding='utf-8'))
cache={}
def ser(code):
    if code not in cache:
        try: cache[code]=ohlcv_matrix.get_series(code)
        except Exception: cache[code]=None
    return cache[code]

def horizon(r,N,stop=-10.0,tgt=20.0):
    s=ser(r['code'])
    if not s: return None
    d=s['dates']
    try: i=d.index(r['date'])
    except ValueError: return None
    p=r['rec_price']
    if not p: return None
    hi,lo,cl=s['highs'],s['lows'],s['closes']
    end=i+N
    if end>=len(d): return None   # 미완성 창 → 제외
    out=None
    for j in range(i+1,end+1):
        if lo[j] is None: continue
        if lo[j]<=p*(1+stop/100): out='stop'; break
        if hi[j]>=p*(1+tgt/100): out='target'; break
    ret=(cl[end]/p-1)*100
    mfe=max((hi[j] for j in range(i+1,end+1) if hi[j] is not None), default=None)
    mfe=(mfe/p-1)*100 if mfe else None
    return dict(out=out or 'none', ret=ret, mfe=mfe)

for N in (10,20):
    ok=0
    for r in rows:
        h=horizon(r,N)
        r['h%d'%N]=h
        if h: ok+=1
    print('N=%d 창 완성 표본 %d/%d'%(N,ok,len(rows)))
json.dump(rows,open(os.path.join(S,'taskC','joinedC2.json'),'w',encoding='utf-8'),ensure_ascii=False)
# quick sanity: agreement with ledger outcome
agree=collections.Counter()
for r in rows:
    h=r.get('h10')
    if h and r['outcome']: agree[(r['outcome'],h['out'])]+=1
print(sorted(agree.items(), key=lambda x:-x[1]))
