# -*- coding: utf-8 -*-
import json, statistics, io, sys
COST=0.5; W=20
def classify(b0):
    body=(b0['c']/b0['o']-1)*100
    if body>=6: return '장대양봉'
    if body>0: return '양봉'
    if body>-6: return '음봉'
    return '장대음봉'
def exit_sim(bars,ei,entry,target=6,stop=-5):
    tp=entry*(1+target/100); sl=entry*(1+stop/100)
    for k in range(ei+1,len(bars)):
        x=bars[k]
        if x['l']<=sl and x['h']>=tp: return stop
        if x['l']<=sl: return stop
        if x['h']>=tp: return target
    return (bars[-1]['c']/entry-1)*100
def entry_of(bars,form):
    b0=bars[0]
    if form=='양봉': return 0
    if form=='장대양봉':
        r0=b0['h']-b0['l']
        for j in range(1,min(W,len(bars))):
            x=bars[j]
            if x['v']<=b0['v']*0.5 and (x['h']-x['l'])<r0*0.7: return j
        return None
    if form=='음봉':
        body0=b0['o']-b0['c']
        for j in range(1,min(W,len(bars))):
            x=bars[j]
            if x['c']>x['o'] and (x['c']-x['o'])>body0: return j
        return None
    return None  # 장대음봉

def run(path, skip_eumbong):
    data=json.load(open(path,encoding='utf-8'))
    rets=[]; blind=[]
    for nm,d in data.items():
        bars=d['bars']
        if not bars: continue
        form=classify(bars[0])
        if form=='장대음봉': continue
        b0c=bars[0]['c']; blind.append((bars[-1]['c']/b0c-1)*100-COST)
        if skip_eumbong and form=='음봉': continue
        ei=entry_of(bars,form)
        if ei is None: continue
        rets.append(exit_sim(bars,ei,bars[ei]['c'])-COST)
    return rets, blind

out=io.StringIO()
def p(*a): print(*a,file=out)
for label,path in [('6/24 (강세)','scripts/_min3_user40_0624.json'),('6/23 (급락)','scripts/_min3_20260623.json')]:
    p(f"\n=== {label} — 시나리오 A(+6/-5) ===")
    for skip,name in [(False,'현행(음봉=상쇄양봉 진입)'),(True,'변경(음봉=진입안함)')]:
        rets,blind=run(path,skip)
        if rets:
            w=100*sum(1 for x in rets if x>0)/len(rets)
            p(f"  {name:<22} 진입 {len(rets):2d}건  평균 {statistics.mean(rets):+.2f}%/건  승률 {w:.0f}%  합계 {sum(rets):+.1f}%p")
    bw=100*sum(1 for x in blind if x>0)/len(blind)
    p(f"  {'블라인드(다 사서 종가)':<22} {len(blind):2d}종목  평균 {statistics.mean(blind):+.2f}%/건  승률 {bw:.0f}%")
sys.stdout.buffer.write(out.getvalue().encode('utf-8'))
