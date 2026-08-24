# -*- coding: utf-8 -*-
import json,glob,os,datetime as dt
def sma(a,n):
    return sum(a[-n:])/n if len(a)>=n else None
codes=json.load(open('scripts/_codes_0623sig.json',encoding='utf-8'))
target=set(codes.values())
hits_fresh=set(); hits_above=set()
for fp in glob.glob('.cache/ohlcv/series/*.json'):
    code=os.path.basename(fp)[:-5]
    d=json.load(open(fp)); c=d['closes']; dates=d['dates']
    if len(c)<60 or dates[-1]!='2026-06-23': continue
    m5=sma(c,5);m10=sma(c,10);m20=sma(c,20)
    if None in (m5,m10,m20): continue
    above = c[-1]>m5 and c[-1]>m10 and c[-1]>m20
    fresh = above and (c[-2]<=sma(c[:-1],5) and c[-2]<=sma(c[:-1],10) and c[-2]<=sma(c[:-1],20))
    if above: hits_above.add(code)
    if fresh: hits_fresh.add(code)
print('사장님 6/23 리스트:', len(target),'종목 (ETF 등 제외분 빼면 더 적음)')
print('내 재현[갓 돌파 fresh]: 전체', len(hits_fresh),'종목, 사장님 46개 중', len(target&hits_fresh),'개 잡음')
print('내 재현[이평선 위 above]: 전체', len(hits_above),'종목, 사장님 46개 중', len(target&hits_above),'개 잡음')
