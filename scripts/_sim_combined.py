# -*- coding: utf-8 -*-
import json,statistics,io,sys
a=json.load(open('scripts/_min3_20260624.json',encoding='utf-8'))      # top 20
b=json.load(open('scripts/_min3_20260624_b2.json',encoding='utf-8'))   # next 18
top20=set(a); 
alld={**a,**b}
codes=json.load(open('scripts/_tmp_codes.json',encoding='utf-8'))
codes2=json.load(open('scripts/_tmp_codes2.json',encoding='utf-8'))
out=io.StringIO()
def p(*x): print(*x,file=out)
STOP=-2.5; COST=0.5
def sim(bars):
    if len(bars)<3: return None
    c0=bars[0]; bull0=c0['c']>c0['o']
    ei=None;tgt=None
    if bull0:
        if bars[1]['c']>bars[1]['o'] and bars[1]['v']>=c0['v']: ei=1;tgt=10.0
        else: return ('skip',None)
    else:
        for j in range(1,11):
            if j<len(bars) and bars[j]['c']>bars[j]['o'] and bars[j]['c']>c0['o']: ei=j;tgt=6.0;break
        if ei is None: return ('skip',None)
    e=bars[ei]['c']; tp=e*(1+tgt/100); sl=e*(1+istop if False else (1+STOP/100))
    for k in range(ei+1,len(bars)):
        if bars[k]['l']<=sl and bars[k]['h']>=tp: return ('trade',STOP-COST)
        if bars[k]['l']<=sl: return ('trade',STOP-COST)
        if bars[k]['h']>=tp: return ('trade',tgt-COST)
    return ('trade',(bars[-1]['c']/e-1)*100-COST)

def run(names):
    rets=[];sk=0
    for nm in names:
        r=sim(alld[nm]['bars'])
        if r is None: continue
        if r[0]=='skip': sk+=1
        else: rets.append(r[1])
    return rets,sk
def fmt(rets,sk,label):
    if not rets: 
        p(f"{label}: 매매 0건 / 스킵 {sk}");return
    w=sum(1 for x in rets if x>0)
    p(f"{label}: 매매 {len(rets)}건/스킵 {sk}  평균 {statistics.mean(rets):+.2f}%  승률 {100*w/len(rets):.0f}%  합계 {sum(rets):+.1f}%p")

bottom18=list(b.keys())
r1,s1=run(list(a.keys())); r2,s2=run(bottom18); r3,s3=run(list(alld.keys()))
p("="*70)
p("【선택 편향 시연】 같은 매매규칙, 대상 종목만 바꿈")
p("-"*70)
fmt(r1,s1,"① 상위20 (사장님이 처음 주신, 수익률 톱)")
fmt(r2,s2,"② 다음18 (랭크 낮은 종목들)          ")
fmt(r3,s3,"③ 38개 전부                         ")
p("="*70)

# daily moves 6/23->6/24 for the 18
def load_close623(code):
    s=json.load(open(f'.cache/ohlcv/series/{code}.json')); return s['closes'][-1]
p("\n[다음18 종목 6/24 등락률 (6/23종가→6/24종가)]")
mv=[]
for nm in bottom18:
    code=codes2[nm]; c623=load_close623(code); c624=alld[nm]['bars'][-1]['c']
    mv.append((nm,(c624/c623-1)*100))
for nm,m in sorted(mv,key=lambda x:-x[1]):
    p(f"  {nm:<14}{m:+7.1f}%")
p(f"\n  다음18 평균 등락 {statistics.mean([m for _,m in mv]):+.1f}%  (상위20은 전부 +3.7~30%였음)")
sys.stdout.buffer.write(out.getvalue().encode('utf-8'))
