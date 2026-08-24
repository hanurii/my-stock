# -*- coding: utf-8 -*-
import json,glob,statistics,io,sys,datetime as dt
from collections import defaultdict
out=io.StringIO()
def p(*x): print(*x,file=out)
files=glob.glob('.cache/ohlcv/series/*.json')
def sma(a,n):
    out=[None]*len(a);s=0
    for i,v in enumerate(a):
        s+=v
        if i>=n:s-=a[i-n]
        if i>=n-1:out[i]=s/n
    return out
def isow(ds):
    y,m,d=map(int,ds.split('-')); iy,iw,_=dt.date(y,m,d).isocalendar(); return iy*100+iw

# per signal-day: collect next-day open->close of all A&B&C(&D) hits
byday=defaultdict(list)
for fp in files:
    d=json.load(open(fp))
    o=d['opens'];h=d['highs'];l=d['lows'];c=d['closes'];dates=d['dates']
    n=len(c)
    if n<60: continue
    ma5=sma(c,5);ma10=sma(c,10);ma20=sma(c,20)
    wk={}; 
    for i,ds in enumerate(dates): wk[isow(ds)]=c[i]
    weeks=sorted(wk); wc=[wk[w] for w in weeks]; wma=sma(wc,10); wp={w:i for i,w in enumerate(weeks)}
    for i in range(25,n-1):
        if None in (ma5[i],ma10[i],ma20[i],ma5[i-1],ma10[i-1],ma20[i-1]): continue
        if not(c[i-1]<=ma5[i-1] and c[i-1]<=ma10[i-1] and c[i-1]<=ma20[i-1]): continue
        if not(c[i]>ma5[i] and c[i]>ma10[i] and c[i]>ma20[i]): continue
        w=isow(dates[i]); 
        if wp.get(w,0)<10 or wma[wp[w]] is None or not(c[i]>wma[wp[w]]): continue  # weekly D
        if o[i+1]<=0: continue
        byday[dates[i]].append((c[i+1]/o[i+1]-1)*100)  # next-day open->close

# daily cross-sectional mean (only days with >=3 hits)
day_means=[(ds,statistics.mean(v),len(v)) for ds,v in byday.items() if len(v)>=3]
day_means.sort(key=lambda x:x[0])
means=[m for _,m,_ in day_means]
p(f"【20개월간 '신호 발생일'의 다음날 장중(시초→종가) 평균수익률 분포】 (주봉필터 포함, 신호 3건+ 인 날 {len(means)}일)")
means_s=sorted(means)
p(f"  전체 평균 {statistics.mean(means):+.2f}%  중앙값 {statistics.median(means):+.2f}%")
p(f"  분위: p10 {means_s[len(means_s)//10]:+.1f}  p25 {means_s[len(means_s)//4]:+.1f}  p50 {means_s[len(means_s)//2]:+.1f}  p75 {means_s[3*len(means_s)//4]:+.1f}  p90 {means_s[9*len(means_s)//10]:+.1f}")
pos=sum(1 for m in means if m>0); big=sum(1 for m in means if m>=3); big5=sum(1 for m in means if m>=5)
p(f"  '+'인 날: {100*pos/len(means):.0f}%   '+3%↑'인 날: {big} ({100*big/len(means):.0f}%)   '+5%↑'인 날: {big5} ({100*big5/len(means):.0f}%)")
p(f"  → 6/24의 장중 +5.37%는 상위 {100*sum(1 for m in means if m>=5.37)/len(means):.1f}% 안에 드는 날")
p("")
p("  [최근 신호일 상위/하위 샘플]")
top=sorted(day_means,key=lambda x:-x[1])[:5]; bot=sorted(day_means,key=lambda x:x[1])[:5]
for ds,m,nn in top: p(f"    호황 {ds}: 평균 {m:+.1f}% ({nn}건)")
for ds,m,nn in bot: p(f"    부진 {ds}: 평균 {m:+.1f}% ({nn}건)")
sys.stdout.buffer.write(out.getvalue().encode('utf-8'))
