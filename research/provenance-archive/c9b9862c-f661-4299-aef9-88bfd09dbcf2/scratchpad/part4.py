import json, statistics
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/'
ROOT='C:/Users/hanul/playground/my-stock/'
bt=json.load(open(ROOT+'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=bt['events']
reg=json.load(open(ROOT+'public/data/market-regime.json',encoding='utf-8'))['series']
regi={r['date']:i for i,r in enumerate(reg)}
rows=json.load(open(SP+'daytab.json',encoding='utf-8'))
big=sorted([r for r in rows if r['n']>=4],key=lambda r:r['date'])
zero=[r for r in big if r['w']==0]
byday={}
for x in ev: byday.setdefault(x['entry_date'],[]).append(x)
print('=== 전멸일 14일 상세 ===')
for r in zero:
    i=regi[r['date']]
    def fwd(k):
        return 100*(reg[min(i+k,len(reg)-1)]['index']/reg[i]['index']-1)
    print(f"\n■ {r['date']}  진입 {r['n']}건 전패 | 국면 {'상승' if r['r_up'] else '조정'} "
          f"20일선대비 {r['r_dist_ma20']:+.1f}% | 50일선위비율 {r['b_a50']:.0f}% (5일변화 {r['b_a50_chg5']:+.1f}%p) "
          f"| 상승연속 {r['r_up_streak']}일 | 지수 이후5일 {fwd(5):+.1f}% 10일 {fwd(10):+.1f}%")
    for x in sorted(byday[r['date']],key=lambda x:-x['turnover_eok']):
        if x['result'] not in ('win','loss'): continue
        print(f"    {x['name']:<12}{x['pattern']:<5} RS{x['rs']:>3} 거래대금{x['turnover_eok']:>7.0f}억 "
              f"ATR{x['atr_pct']:>5.1f}% 갭{x['gap_up_pct']:>+5.1f}% | 최고 {x['max_gain_pct']:>+5.1f}% "
              f"보유 {x['days_held']:>2}일 → {x['gain_at_resolve_pct']:+.1f}%")

print('\n=== 전멸일 vs 정상일 거래 특성 비교 ===')
zd=set(r['date'] for r in zero); nd=set(r['date'] for r in big)-zd
def stats(dates,label):
    t=[x for d in dates for x in byday[d] if x['result'] in ('win','loss')]
    mg=[x['max_gain_pct'] for x in t]
    dh=[x['days_held'] for x in t]
    fast=sum(1 for x in t if x['days_held']<=3)
    never=sum(1 for x in t if x['max_gain_pct']<3)
    print(f"{label}: {len(t)}건 | 최고상승 중앙값 {statistics.median(mg):+.1f}% 평균 {statistics.mean(mg):+.1f}% "
          f"| 3%도 못오른 비율 {100*never/len(t):.0f}% | 3일내 결착 {100*fast/len(t):.0f}% "
          f"| RS중앙값 {statistics.median([x['rs'] for x in t]):.0f} | ATR중앙값 {statistics.median([x['atr_pct'] for x in t]):.1f}%"
          f" | 거래대금중앙값 {statistics.median([x['turnover_eok'] for x in t]):.0f}억")
stats(zd,'전멸일  ')
stats(nd,'그밖의날')
# pattern mix
import collections
for lab,dates in (('전멸일',zd),('그밖',nd)):
    c=collections.Counter(x['pattern'] for d in dates for x in byday[d] if x['result'] in ('win','loss'))
    tot=sum(c.values())
    print(lab,{k:f'{100*v/tot:.0f}%' for k,v in c.most_common()})
# 같은 종목 반복?
c=collections.Counter(x['name'] for d in zd for x in byday[d] if x['result'] in ('win','loss'))
print('전멸일 중복 등장 종목:',[ (k,v) for k,v in c.most_common() if v>1])
