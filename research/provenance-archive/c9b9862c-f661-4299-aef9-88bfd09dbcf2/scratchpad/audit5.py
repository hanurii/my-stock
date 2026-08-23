import json, sys, math, statistics, random
from pathlib import Path
from collections import Counter, defaultdict
MAIN = Path(r"C:\Users\hanul\playground\my-stock")
d=json.load(open(MAIN/'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=d['events']
vals=sorted(e['atr_pct'] for e in ev); n=len(vals)
def qq(p):
    k=(n-1)*p; f=int(k); c=min(f+1,n-1); return vals[f]+(vals[c]-vals[f])*(k-f)
q1c=qq(.25)
for e in ev: e['isQ1']= e['atr_pct']<=q1c
R=[e for e in ev if e['result'] in ('win','loss')]
def wr(rows):
    w=sum(1 for r in rows if r['result']=='win'); t=len(rows)
    return w,t,(round(w/t*100,1) if t else None)

print("=== [A] 진입 월 분포: Q1 은 언제 나타나는가 ===")
print(f"  {'월':<9}{'Q1거래':>7}{'나머지':>7}{'Q1비중':>8}{'그달 전체승률':>13}")
for m in sorted({e['month'] for e in R}):
    a=[e for e in R if e['month']==m and e['isQ1']]; b=[e for e in R if e['month']==m and not e['isQ1']]
    _,_,mr=wr(a+b)
    print(f"  {m:<9}{len(a):>7}{len(b):>7}{len(a)/(len(a)+len(b))*100:>7.0f}%{str(mr):>12}%")

print("\n=== [B] 월내 비교 (시장 타이밍 제거) ===")
diffs=[]; W=[]
mh_num=mh_den=0
for m in sorted({e['month'] for e in R}):
    a=[e for e in R if e['month']==m and e['isQ1']]; b=[e for e in R if e['month']==m and not e['isQ1']]
    if len(a)<3 or len(b)<3: 
        print(f"  {m}: 표본부족(Q1 {len(a)}, 나머지 {len(b)}) — 제외"); continue
    aw,at,ar=wr(a); bw,bt,br=wr(b)
    diffs.append(ar-br); W.append(at+bt)
    # Mantel-Haenszel
    N=at+bt
    mh_num += aw*(bt-bw)/N
    mh_den += (at-aw)*bw/N
    print(f"  {m}: Q1 {ar:>5}%(n={at:>3})  나머지 {br:>5}%(n={bt:>3})   차 {ar-br:+.1f}%p")
print(f"\n  단순평균 월별차 : {statistics.mean(diffs):+.1f}%p   (중앙값 {statistics.median(diffs):+.1f}%p)")
print(f"  표본가중 평균차 : {sum(x*w for x,w in zip(diffs,W))/sum(W):+.1f}%p")
print(f"  Mantel-Haenszel 승산비 : {mh_num/mh_den:.2f}  (1.0=효과없음)")

print("\n=== [C] 같은 날 진입한 것끼리만 비교 (가장 엄격) ===")
byday=defaultdict(list)
for e in R: byday[e['entry_date']].append(e)
pa=pb=na=nb=0; days=0; dd=[]
for day,rows in byday.items():
    a=[e for e in rows if e['isQ1']]; b=[e for e in rows if not e['isQ1']]
    if not a or not b: continue
    days+=1
    aw,at,_=wr(a); bw,bt,_=wr(b)
    pa+=aw; na+=at; pb+=bw; nb+=bt
    dd.append((aw/at-bw/bt)*100)
print(f"  Q1·나머지가 함께 진입한 날 {days}일")
print(f"  그 안에서 Q1 {pa}/{na} = {pa/na*100:.1f}%   나머지 {pb}/{nb} = {pb/nb*100:.1f}%   차 {pa/na*100-pb/nb*100:+.1f}%p")
print(f"  날짜별 차이 평균 {statistics.mean(dd):+.1f}%p  중앙값 {statistics.median(dd):+.1f}%p")
# 부호검정
pos=sum(1 for x in dd if x>0); neg=sum(1 for x in dd if x<0)
print(f"  날짜별 부호: Q1우세 {pos}일 / 열세 {neg}일 / 동률 {len(dd)-pos-neg}일")
def binom_p(k,nn):
    return sum(math.comb(nn,i) for i in range(k,nn+1))/2**nn
print(f"  부호검정 p={binom_p(max(pos,neg),pos+neg):.4f}")

# 같은 날 조건부 순열검정
random.seed(11); obs=pa/na-pb/nb; cnt=0; N=20000
pool=[(day,[e['result']=='win' for e in rows],[e['isQ1'] for e in rows]) for day,rows in byday.items()
      if any(e['isQ1'] for e in rows) and any(not e['isQ1'] for e in rows)]
for _ in range(N):
    ca=cb=ta=tb=0
    for day,res,lab in pool:
        l=lab[:]; random.shuffle(l)
        for r,x in zip(res,l):
            if x: ca+=r; ta+=1
            else: cb+=r; tb+=1
    if ta and tb and (ca/ta-cb/tb)>=obs: cnt+=1
print(f"  같은날 조건부 순열검정 p={cnt/N:.4f}")

print("\n=== [D] 국면 통제: 그달 전체승률을 공변량으로 ===")
for lo,hi,lab in [(0,30,"나쁜달(<30%)"),(30,45,"보통(30~45%)"),(45,101,"좋은달(45%+)")]:
    ms=[m for m in {e['month'] for e in R} if (wr([e for e in R if e['month']==m])[2] or 0)>=lo
        and (wr([e for e in R if e['month']==m])[2] or 0)<hi]
    sub=[e for e in R if e['month'] in ms]
    aw,at,ar=wr([e for e in sub if e['isQ1']]); bw,bt,br=wr([e for e in sub if not e['isQ1']])
    print(f"  {lab:<14} 월={sorted(ms)}")
    print(f"      Q1 {str(ar):>5}%(n={at:>3})   나머지 {str(br):>5}%(n={bt:>3})")
