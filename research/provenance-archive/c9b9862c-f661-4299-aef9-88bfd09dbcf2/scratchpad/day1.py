import json, sys, statistics
sys.path.insert(0,'C:/Users/hanul/playground/my-stock/scripts')
from canslim_lib import ohlcv_matrix as om
from canslim_lib.pivot_backtest import truncate_series
ROOT='C:/Users/hanul/playground/my-stock/'
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/'
bt=json.load(open(ROOT+'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=[x for x in bt['events'] if x['result'] in ('win','loss')]
cache={}
out=[]
miss=0
for x in ev:
    c=x['code']
    if c not in cache:
        try: cache[c]=om.get_series(c)
        except Exception: cache[c]=None
    s=cache[c]
    if not s: miss+=1; continue
    t=truncate_series(s,x['entry_date'])
    if not t['dates'] or t['dates'][-1]!=x['entry_date']: miss+=1; continue
    cl=t['closes'][-1]; hi=t['highs'][-1]; lo=t['lows'][-1]; op=t['opens'][-1]
    if not cl: miss+=1; continue
    d1=100*(cl/x['entry_price']-1)
    out.append(dict(code=c,name=x['name'],date=x['entry_date'],res=x['result'],d1=d1,
                    d1_hi=100*(hi/x['entry_price']-1)))
print('day1 계산 성공',len(out),'실패',miss)
json.dump(out,open(SP+'day1.json','w',encoding='utf-8'),ensure_ascii=False)
def wr(g):
    return (len(g), 100*sum(1 for x in g if x['res']=='win')/len(g)) if g else (0,0)
print('\n=== 진입 첫날 종가가 매수가 대비 어땠나 → 최종 승률 ===')
bands=[('-99~-4%',-99,-4),('-4~-2%',-4,-2),('-2~0%',-2,0),('0~+2%',0,2),('+2~+5%',2,5),('+5%~',5,999)]
for lab,a,b in bands:
    g=[x for x in out if a<=x['d1']<b]
    n,w=wr(g); print(f'  {lab:<10}{n:>4}건 승률 {w:>5.1f}%')
red=[x for x in out if x['d1']<0]; grn=[x for x in out if x['d1']>=0]
print(f'  ► 첫날 종가 매수가 아래 {len(red)}건 승률 {wr(red)[1]:.1f}%  /  위 {len(grn)}건 승률 {wr(grn)[1]:.1f}%')
# 전멸일에서 첫날 빨간불 비율
rows=json.load(open(SP+'daytab.json',encoding='utf-8'))
big=sorted([r for r in rows if r['n']>=4],key=lambda r:r['date'])
zd=set(r['date'] for r in big if r['w']==0); nd=set(r['date'] for r in big)-zd
for lab,ds in (('전멸일',zd),('그밖의날',nd)):
    g=[x for x in out if x['date'] in ds]
    r=sum(1 for x in g if x['d1']<0)
    print(f'  {lab}: {len(g)}건 중 첫날 종가 매수가 아래 {r}건 ({100*r/len(g):.0f}%)')
# 그날 첫날 빨간불 비율로 그날 전체를 판단할 수 있나
print('\n=== 그날 산 종목 중 첫날 종가가 매수가 아래인 비율 → 그날 승률 ===')
for r in big:
    pass
dd=[]
for r in big:
    g=[x for x in out if x['date']==r['date']]
    if len(g)<4: continue
    frac=sum(1 for x in g if x['d1']<0)/len(g)
    dd.append((r['date'],frac,r['w'],r['n']))
for lo,hi,lab in ((0,0.4,'40%미만'),(0.4,0.7,'40~70%'),(0.7,1.01,'70%이상')):
    g=[d for d in dd if lo<=d[1]<hi]
    if not g: continue
    n=sum(d[3] for d in g); w=sum(d[2] for d in g)
    print(f'  {lab:<8}{len(g):>3}일 승률 {100*w/n:>5.1f}% 전멸 {sum(1 for d in g if d[2]==0)}일')
