# -*- coding: utf-8 -*-
import json,statistics,io,sys
a=json.load(open('scripts/_min3_20260624.json',encoding='utf-8'))
b=json.load(open('scripts/_min3_20260624_b2.json',encoding='utf-8'))
alld={**a,**b}
c1=json.load(open('scripts/_tmp_codes.json',encoding='utf-8'))
c2=json.load(open('scripts/_tmp_codes2.json',encoding='utf-8'))
codes={**c1,**c2}
out=io.StringIO()
def p(*x): print(*x,file=out)

# ---- signal-day daily move (6/23 close -> 6/24 close), unbiased over all 38 ----
daymoves=[]; intraday_oh=[]; intraday_ol=[]; limitup=0; gap_up=[]
for nm,d in alld.items():
    code=codes[nm]
    s=json.load(open(f'.cache/ohlcv/series/{code}.json'))
    c623=s['closes'][-1]
    bars=d['bars']; o9=bars[0]['o']; hi=max(x['h'] for x in bars); lo=min(x['l'] for x in bars); cl=bars[-1]['c']
    dm=(cl/c623-1)*100; daymoves.append(dm)
    intraday_oh.append((hi/o9-1)*100); intraday_ol.append((lo/o9-1)*100)
    gap_up.append((o9/c623-1)*100)
    # 상한가 직행(못삼): 등락률>=+29% 이고 장중저가가 시가 위(=한번도 안빠짐)
    if dm>=29.0 and (lo/o9-1)*100 >= -0.5: limitup+=1

def st(x): return f"평균 {statistics.mean(x):+.2f}%  중앙값 {statistics.median(x):+.2f}%  양봉비율 {100*sum(1 for v in x if v>0)/len(x):.0f}%  (최저 {min(x):+.1f} ~ 최고 {max(x):+.1f})"

p("="*72)
p(f"【검색식이 뽑은 투자가능 38종목 — 6/24 전체 통계 (선택편향 제거)】")
p("-"*72)
p(f"  6/24 등락률(6/23종가→종가): {st(daymoves)}")
p(f"  장중 시가→고가(최대 상승여력): {st(intraday_oh)}")
p(f"  장중 시가→저가(최대 하락):     {st(intraday_ol)}")
p(f"  시가 갭(전일종가→9시시가):     {st(gap_up)}")
p(f"  상한가 직행(사실상 매수불가): {limitup}종목 / 38")
p("="*72)

# ---- intraday method on all 38 ----
STOP=-2.5; COST=0.5
def sim(bars):
    if len(bars)<3: return ('skip',None)
    c0=bars[0]
    if c0['c']>c0['o']:
        if bars[1]['c']>bars[1]['o'] and bars[1]['v']>=c0['v']: ei,tgt=1,10.0
        else: return ('skip',None)
    else:
        ei=None
        for j in range(1,11):
            if j<len(bars) and bars[j]['c']>bars[j]['o'] and bars[j]['c']>c0['o']: ei,tgt=j,6.0;break
        if ei is None: return ('skip',None)
    e=bars[ei]['c']; tp=e*(1+tgt/100); sl=e*(1+STOP/100)
    for k in range(ei+1,len(bars)):
        if bars[k]['l']<=sl: return ('trade',STOP-COST)
        if bars[k]['h']>=tp: return ('trade',tgt-COST)
    return ('trade',(bars[-1]['c']/e-1)*100-COST)
rets=[];sk=0
for nm in alld:
    r=sim(alld[nm]['bars'])
    if r[0]=='skip': sk+=1
    else: rets.append(r[1])
w=sum(1 for x in rets if x>0)
p(f"\n[사장님 3분봉 매매방식을 38종목 전체에 적용 — *단, 같은날 못삼 함정 잔존*]")
p(f"  매매 {len(rets)}건 / 스킵 {sk}건  평균 {statistics.mean(rets):+.2f}%/건  승률 {100*w/len(rets):.0f}%  합계 {sum(rets):+.1f}%p")
sys.stdout.buffer.write(out.getvalue().encode('utf-8'))
