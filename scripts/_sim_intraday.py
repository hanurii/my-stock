# -*- coding: utf-8 -*-
import json
data=json.load(open('scripts/_min3_20260624.json',encoding='utf-8'))

# ── 사장님 매매방식 해석 (3분봉 기준) ───────────────────────────
# [경로1] 첫 3분봉이 양봉:
#   - 1·2번째 3분봉이 연속 양봉 + 거래량 증가(폭발) → 2번째봉 종가에 매수, 목표 +10%
# [경로2] 첫 3분봉이 음봉:
#   - 이후 30분(=3분봉 10개) 내에 시가(첫봉 시가)를 회복하는 양봉 출현 → 그 봉 종가에 매수, 목표 +6%
#   - 30분내 회복 못하면 매수 포기(스킵)
# 공통: 손절 -2.5%, 당일 보유, 미달 시 마감(15:21) 종가 청산
# 동일봉서 목표·손절 동시터치 시 보수적으로 손절 우선.
STOP=-2.5
def simulate(bars):
    if len(bars)<3: return None
    c0=bars[0]
    bull0 = c0['c']>c0['o']
    entry_i=None; target=None; reason=''
    if bull0:
        # 경로1: 1,2번 연속 양봉 + 거래량 증가
        c1=bars[1]
        bull1 = c1['c']>c1['o']
        volup = c1['v']>=c0['v']
        if bull1 and volup:
            entry_i=1; target=10.0; reason='경로1 연속양봉+거래량↑(목표10%)'
        else:
            return {'action':'skip','why':'첫봉 양봉이나 2연속양봉+거래량 미충족'}
    else:
        # 경로2: 30분(봉10개) 내 시가회복 양봉
        for j in range(1,11):
            if j>=len(bars): break
            cj=bars[j]
            if cj['c']>cj['o'] and cj['c']>c0['o']:
                entry_i=j; target=6.0; reason=f'경로2 {j*3}분뒤 시가회복 양봉(목표6%)'
                break
        if entry_i is None:
            return {'action':'skip','why':'음봉 후 30분내 시가회복 실패 → 포기'}
    e=bars[entry_i]['c']
    tp=e*(1+target/100); sl=e*(1+STOP/100)
    for k in range(entry_i+1,len(bars)):
        b=bars[k]
        hit_sl=b['l']<=sl; hit_tp=b['h']>=tp
        if hit_sl and hit_tp: return {'action':'trade','entry':e,'exit':sl,'ret':STOP,'reason':reason,'exitT':b['t'],'why':'동시터치→손절'}
        if hit_sl: return {'action':'trade','entry':e,'exit':sl,'ret':STOP,'reason':reason,'exitT':b['t'],'why':'손절'}
        if hit_tp: return {'action':'trade','entry':e,'exit':tp,'ret':target,'reason':reason,'exitT':b['t'],'why':'익절'}
    last=bars[-1]['c']
    return {'action':'trade','entry':e,'exit':last,'ret':(last/e-1)*100,'reason':reason,'exitT':bars[-1]['t'],'why':'마감청산'}

print(f"{'종목':<13}{'결과':<6}{'진입가':>8}{'청산':>8}{'손익%':>8}  설명")
print('-'*80)
rets=[]; traded=0; skipped=0
day_moves=[]
for nm,d in data.items():
    bars=d['bars']
    o=bars[0]['o']; hi=max(b['h'] for b in bars); lo=min(b['l'] for b in bars); cl=bars[-1]['c']
    day_moves.append((nm, (hi/o-1)*100, (cl/o-1)*100))
    r=simulate(bars)
    if r['action']=='skip':
        skipped+=1
        print(f"{nm:<13}{'스킵':<6}{'':>8}{'':>8}{'':>8}  {r['why']}")
    else:
        traded+=1; rets.append(r['ret'])
        print(f"{nm:<13}{'매매':<6}{r['entry']:>8.0f}{r['exit']:>8.0f}{r['ret']:>+8.2f}  {r['reason']} | {r['why']}@{r['exitT']}")

print('-'*80)
import statistics
COST=0.5
if rets:
    net=[x-COST for x in rets]
    wins=sum(1 for x in net if x>0)
    print(f"매매 {traded}건 / 스킵 {skipped}건")
    print(f"평균손익(비용0.5%차감): {statistics.mean(net):+.2f}%  승률 {100*wins/len(net):.0f}%  합계 {sum(net):+.1f}%p")
    print(f"  내역(net): {', '.join(f'{x:+.1f}' for x in sorted(net,reverse=True))}")
print()
print("[참고] 오늘 각 종목 09:00시가 대비 — 장중고가 / 종가:")
for nm,hh,cc in sorted(day_moves,key=lambda x:-x[1]):
    print(f"  {nm:<13} 고가 {hh:+6.2f}%   종가 {cc:+6.2f}%")
