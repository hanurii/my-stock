# -*- coding: utf-8 -*-
import json, io, sys
data=json.load(open('scripts/_min3_20260624.json',encoding='utf-8'))
out=io.StringIO()
def p(*a): print(*a, file=out)

# verify fast movers: raw 3-min bars early session
for nm in ['화천기공','남화산업','알테오젠','한국콜마','모헨즈']:
    b=data[nm]['bars'][:8]
    p(f"\n=== {nm} ({data[nm]['code']}) 초반 3분봉 ===")
    for x in b:
        tag='양' if x['c']>x['o'] else ('음' if x['c']<x['o'] else '-')
        p(f"  {x['t']}  O{x['o']:>8.0f} H{x['h']:>8.0f} L{x['l']:>8.0f} C{x['c']:>8.0f}  거래량{x['v']:>10.0f} [{tag}]")

# day moves table
p("\n=== 오늘 종목별 09:00 시가대비 장중고가/종가 ===")
rows=[]
for nm,d in data.items():
    bars=d['bars']; o=bars[0]['o']; hi=max(x['h'] for x in bars); lo=min(x['l'] for x in bars); cl=bars[-1]['c']
    rows.append((nm,(hi/o-1)*100,(lo/o-1)*100,(cl/o-1)*100))
for nm,hh,ll,cc in sorted(rows,key=lambda x:-x[1]):
    p(f"  {nm:<13} 고가{hh:+7.2f}%  저가{ll:+7.2f}%  종가{cc:+7.2f}%")

sys.stdout.buffer.write(out.getvalue().encode('utf-8'))
