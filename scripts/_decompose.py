# -*- coding: utf-8 -*-
import json,statistics,io,sys,os
alld=json.load(open('scripts/_min3_0624_for0623sig.json',encoding='utf-8'))
out=io.StringIO()
def p(*x): print(*x,file=out)
COST=0.5
def mean(x): return statistics.mean(x) if x else 0

gap=[]; oc=[]; oh=[]; ol=[]; naive=[]; tp_stop=[]
for nm,d in alld.items():
    bars=d['bars']; code=d['code']
    o9=bars[0]['o']; cl=bars[-1]['c']; hi=max(b['h'] for b in bars); lo=min(b['l'] for b in bars)
    sp=f'.cache/ohlcv/series/{code}.json'
    if os.path.exists(sp):
        c623=json.load(open(sp))['closes'][-1]; gap.append((o9/c623-1)*100)
    oc.append((cl/o9-1)*100); oh.append((hi/o9-1)*100); ol.append((lo/o9-1)*100)
    naive.append((cl/o9-1)*100 - COST)   # 9시 시초가 매수→종가 청산, 손절無
    # 9시 시초가 매수 + 목표6%/손절-2.5%
    e=o9; tp=e*1.06; sl=e*0.975; r=None
    for b in bars[1:]:
        if b['l']<=sl: r=-2.5;break
        if b['h']>=tp: r=6.0;break
    if r is None: r=(cl/e-1)*100
    tp_stop.append(r-COST)

p("【수익 출처 분해 — 검색식 45종목, 6/24】")
p(f"  ① 전일종가→9시시가 갭(못 먹는 부분):     평균 {mean(gap):+.2f}%")
p(f"  ② 9시시가→종가 (장중, 먹을 수 있는 부분): 평균 {mean(oc):+.2f}%  중앙값 {statistics.median(oc):+.2f}%")
p(f"     (장중 시가→고가 평균 +{mean(oh):.1f}% / 시가→저가 평균 {mean(ol):.1f}%)")
p("")
p("【같은 45종목, 매매방식만 다르게 (전부 9시 시초가 일괄 매수 가정)】")
nv=sum(1 for x in naive if x>0); tv=sum(1 for x in tp_stop if x>0)
p(f"  Ⓐ 단순: 시초가 매수→종가 청산, 손절 없음:   평균 {mean(naive):+.2f}%/건  승률 {100*nv/len(naive):.0f}%  합계 {sum(naive):+.1f}%p")
p(f"  Ⓑ 목표6%/손절-2.5% (시초가 일괄):           평균 {mean(tp_stop):+.2f}%/건  승률 {100*tv/len(tp_stop):.0f}%  합계 {sum(tp_stop):+.1f}%p")
p(f"  Ⓒ 사장님 3분봉 분기전략(A+C, -2.5손절):     평균 +1.66%/건  (앞 결과)")
p("")
p("  → Ⓐ(아무 기술 없이 그냥 보유)가 Ⓑ·Ⓒ보다 높으면, '3분봉 기술·손절'이 오히려 수익을 깎는 것.")
sys.stdout.buffer.write(out.getvalue().encode('utf-8'))
