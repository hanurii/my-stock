# -*- coding: utf-8 -*-
import json,statistics,io,sys
a=json.load(open('scripts/_min3_20260624.json',encoding='utf-8'))
b=json.load(open('scripts/_min3_20260624_b2.json',encoding='utf-8'))
alld={**a,**b}
out=io.StringIO()
def p(*x): print(*x,file=out)

# ── 손익비 손익분기 승률 (산수) ──
p("【1】 손절-익절 구조의 손익분기 승률 (단순 산수)")
p(f"   +6% 익절 / -2.5% 손절 → 본전 승률 = 2.5/(6+2.5) = {2.5/8.5*100:.0f}%")
p(f"   +10% 익절/ -2.5% 손절 → 본전 승률 = 2.5/(10+2.5)= {2.5/12.5*100:.0f}%")
p("   → 승률만 보면 20~29%만 넘어도 본전. 그럼 쉬워 보이는데, 함정은 '손절이 먼저 닿느냐'.")
p("")

# ── 9~10시 구간(첫 20개 3분봉) 기준 ──
W=20  # 9:00~10:00
p("【2】 -2.5% 손절의 '노이즈 휘둘림' — 9~10시 진입 가정, 종가까지 보유")
whip=0; up_close=0; up_but_stopped=0; stop_total=0
for nm,d in alld.items():
    bars=d['bars']; e=bars[0]['o']  # 9시 시가 진입 근사
    sl=e*0.975
    full=bars
    stopped = any(x['l']<=sl for x in full[1:])
    closed_up = full[-1]['c']>e
    if stopped: stop_total+=1
    if closed_up: up_close+=1
    if closed_up and stopped: up_but_stopped+=1
p(f"   38종목 중 장중 -2.5% 한번이라도 닿음: {stop_total}/38")
p(f"   그날 '상승 마감'한 종목: {up_close}/38")
p(f"   그중 -2.5%에 먼저 털렸을 종목(이긴 말 놓침): {up_but_stopped}/{up_close}")
p("")

# ── 눌림 매수의 역선택: 장대양봉 종목은 눌림을 안 주고 도망간다 ──
p("【3】 '장대양봉이면 눌림 기다려 매수' 규칙의 역선택 문제 (9~10시)")
big=[]; gave_pullback=0; ran_away=0; pb_outcome=[]; run_outcome=[]
for nm,d in alld.items():
    bars=d['bars']; c0=bars[0]
    body=(c0['c']/c0['o']-1)*100
    if body>=3.0:  # 첫봉 장대양봉(+3%↑)
        big.append(nm)
        first_close=c0['c']
        win=bars[1:W]
        # 눌림 = 첫봉 종가 아래로 되돌림(살 기회) 발생?
        pulled = any(x['l']<=first_close for x in win)
        day_ret=(bars[-1]['c']/first_close-1)*100
        if pulled: gave_pullback+=1; pb_outcome.append(day_ret)
        else: ran_away+=1; run_outcome.append(day_ret)
p(f"   첫 3분봉이 장대양봉(+3%↑)인 종목: {len(big)}개")
p(f"   - 9~10시에 눌림 줘서 살 기회 생김: {gave_pullback}개  (이후 첫봉종가대비 평균 {statistics.mean(pb_outcome):+.1f}%)" if pb_outcome else f"   - 눌림 준 종목: 0")
p(f"   - 눌림 없이 도망감(못 삼): {ran_away}개  (놓친 상승 평균 {statistics.mean(run_outcome):+.1f}%)" if run_outcome else f"   - 도망간 종목: 0")
p("   → 살 수 있었던 건 '눌린=약한' 쪽, 정작 잘 간 건 '도망간=못 산' 쪽이면 = 역선택")
sys.stdout.buffer.write(out.getvalue().encode('utf-8'))
