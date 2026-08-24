# -*- coding: utf-8 -*-
import json,statistics,io,sys
a=json.load(open('scripts/_min3_20260624.json',encoding='utf-8'))
b=json.load(open('scripts/_min3_20260624_b2.json',encoding='utf-8'))
alld={**a,**b}
out=io.StringIO()
def p(*x): print(*x,file=out)
W=20      # 9:00~10:00 (매수는 이 안에서만)
STOP=-2.5; COST=0.5

def run_path(bars, entry_i, entry_px, target):
    tp=entry_px*(1+target/100); sl=entry_px*(1+STOP/100)
    maxup=0; maxdn=0
    for k in range(entry_i+1, len(bars)):
        x=bars[k]
        maxup=max(maxup,(x['h']/entry_px-1)*100); maxdn=min(maxdn,(x['l']/entry_px-1)*100)
        if x['l']<=sl and x['h']>=tp: return STOP, '손절(동시)', maxup,maxdn
        if x['l']<=sl: return STOP, '손절', maxup,maxdn
        if x['h']>=tp: return target, '익절', maxup,maxdn
    return (bars[-1]['c']/entry_px-1)*100, '종가청산', maxup,maxdn

# 분류 + 진입 규칙
branches={'A_작은양봉':[], 'B_장대양봉':[], 'C_음봉':[], 'skip':[]}
for nm,d in alld.items():
    bars=d['bars']; c0=bars[0]
    body=(c0['c']/c0['o']-1)*100
    res=None
    if c0['c']>c0['o'] and body<3:            # A: 작은 양봉 → 즉시 추세진입(다음봉 시가)
        ei=1; e=bars[1]['o']; tgt=6.0
        r=run_path(bars,ei,e,tgt); branches['A_작은양봉'].append((nm,e,)+r)
    elif body>=3:                              # B: 장대양봉 → 눌림(첫봉종가 이하) 대기 매수, 추격금지
        first_c=c0['c']; ei=None
        for j in range(1,W):
            if j<len(bars) and bars[j]['l']<=first_c:
                ei=j; e=min(first_c, bars[j]['o']); break
        if ei is None: branches['skip'].append((nm,'장대양봉인데 눌림없음')); continue
        tgt=10.0
        r=run_path(bars,ei,e,tgt); branches['B_장대양봉'].append((nm,e,)+r)
    else:                                       # C: 음봉 시작 → 상쇄양봉+변동성축소+거래량마름 대기
        ei=None
        for j in range(1,W):
            if j>=len(bars): break
            x=bars[j]
            offset = x['c']>x['o'] and x['c']>c0['o']           # 음봉 상쇄 양봉
            volsdry = x['v']<c0['v']                            # 거래량 마름
            rng_small = (x['h']-x['l']) < (c0['h']-c0['l'])     # 변동폭 축소
            if offset and volsdry and rng_small:
                ei=j; e=x['c']; break
        if ei is None: branches['skip'].append((nm,'음봉후 조건 미충족')); continue
        tgt=6.0
        r=run_path(bars,ei,e,tgt); branches['C_음봉'].append((nm,e,)+r)

def summarize(key):
    rows=branches[key]
    if not rows: p(f"  [{key}] 해당 없음"); return
    rets=[r[2]-COST for r in rows]
    wins=sum(1 for x in rets if x>0)
    tp=sum(1 for r in rows if r[3]=='익절'); sl=sum(1 for r in rows if '손절' in r[3]); cc=sum(1 for r in rows if r[3]=='종가청산')
    mu=statistics.mean([r[4] for r in rows]); md=statistics.mean([r[5] for r in rows])
    p(f"  [{key}] {len(rows)}종목  평균 {statistics.mean(rets):+.2f}%/건  승률 {100*wins/len(rets):.0f}%")
    p(f"        익절 {tp} / 손절 {sl} / 종가청산 {cc}   |  진입후 최대상승 평균 +{mu:.1f}%, 최대하락 평균 {md:.1f}%")

p("="*74)
p("【첫 3분봉 유형별 전략 분석 — 6/24 실제 3분봉, 9~10시 매수창】")
p("  A=작은양봉→즉시진입(목표6%) / B=장대양봉→눌림대기(목표10%) / C=음봉→상쇄+거래량마름대기(목표6%)")
p("  손절 -2.5%, 당일 종가청산, 비용 0.5% 차감")
p("-"*74)
for k in ['A_작은양봉','B_장대양봉','C_음봉']:
    summarize(k)
p(f"  [매수 포기(skip)] {len(branches['skip'])}종목: " + ", ".join(f"{nm}({why})" for nm,why in branches['skip']))
p("-"*74)
allrows=branches['A_작은양봉']+branches['B_장대양봉']+branches['C_음봉']
allrets=[r[2]-COST for r in allrows]
p(f"  전체 진입 {len(allrows)}건  평균 {statistics.mean(allrets):+.2f}%/건  승률 {100*sum(1 for x in allrets if x>0)/len(allrets):.0f}%  합계 {sum(allrets):+.1f}%p")
p("="*74)

# 유형별 명세
p("\n[세부 — 종목별]")
for k in ['A_작은양봉','B_장대양봉','C_음봉']:
    p(f"  ◆ {k}")
    for r in branches[k]:
        p(f"     {r[0]:<14} 진입{r[1]:>9.0f}  결과 {r[2]-COST:+6.2f}% [{r[3]}]  (장중 최대 +{r[4]:.1f}/{r[5]:.1f}%)")
sys.stdout.buffer.write(out.getvalue().encode('utf-8'))
