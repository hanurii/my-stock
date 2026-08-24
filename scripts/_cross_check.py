# -*- coding: utf-8 -*-
import json, glob, io, sys
min3=json.load(open('scripts/_min3_20260624.json',encoding='utf-8'))
codes=json.load(open('scripts/_tmp_codes.json',encoding='utf-8'))
out=io.StringIO()
def p(*a): print(*a,file=out)
def sma(a,n):
    if len(a)<n: return None
    return sum(a[-n:])/n

p(f"{'종목':<13}{'6/23종가':>10}{'6/24시가':>10}{'6/24종가':>10}{'6/24등락':>9}  {'6/24 5/10/20 동시돌파?':<22}")
p('-'*92)
cross_cnt=0
for nm,code in codes.items():
    s=json.load(open(f'.cache/ohlcv/series/{code}.json'))
    closes=s['closes']; dates=s['dates']
    c623=closes[-1]   # last in series = 2026-06-23
    bars=min3[nm]['bars']
    o624=bars[0]['o']; c624=bars[-1]['c']
    chg=(c624/c623-1)*100
    # MAs as of 6/23 (before 6/24) and as of 6/24 (append c624)
    ma5_p=sma(closes,5); ma10_p=sma(closes,10); ma20_p=sma(closes,20)
    c2=closes+[c624]
    ma5=sma(c2,5); ma10=sma(c2,10); ma20=sma(c2,20)
    below_prev = c623<=ma5_p and c623<=ma10_p and c623<=ma20_p
    above_now  = c624>ma5 and c624>ma10 and c624>ma20
    crossed = below_prev and above_now
    if crossed: cross_cnt+=1
    p(f"{nm:<13}{c623:>10.0f}{o624:>10.0f}{c624:>10.0f}{chg:>+8.1f}%  {'★ 6/24가 돌파일' if crossed else ('이미 정배열 위' if above_now else '미충족')}")
p('-'*92)
p(f"6/24에 '5/10/20 동시 상향돌파'가 발생한 종목: {cross_cnt}/20")
sys.stdout.buffer.write(out.getvalue().encode('utf-8'))
