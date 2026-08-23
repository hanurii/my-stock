import json, sys, math, statistics, random
from pathlib import Path
from collections import Counter, defaultdict
sys.path.insert(0, r"C:\Users\hanul\playground\my-stock\scripts")
MAIN = Path(r"C:\Users\hanul\playground\my-stock")
from canslim_lib import ohlcv_matrix
ohlcv_matrix.SERIES_DIR = MAIN/".cache"/"ohlcv"/"series"
d=json.load(open(MAIN/'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
ev=d['events']
vals=sorted(e['atr_pct'] for e in ev); n=len(vals)
def qq(p):
    k=(n-1)*p; f=int(k); c=min(f+1,n-1); return vals[f]+(vals[c]-vals[f])*(k-f)
q1c,q2c,q3c=qq(.25),qq(.5),qq(.75)
def band(v): return "Q1" if v<=q1c else "Q2" if v<=q2c else "Q3" if v<=q3c else "Q4"
for e in ev: e['Q']=band(e['atr_pct']); e['isQ1']= e['Q']=='Q1'
def wr(rows):
    w=sum(1 for r in rows if r['result']=='win'); l=sum(1 for r in rows if r['result']=='loss')
    return w,l,(round(w/(w+l)*100,1) if w+l else None)

# (a) 유의성: Q1 vs 나머지 (2x2 카이제곱 + 피셔 근사)
A=[e for e in ev if e['isQ1']]; B=[e for e in ev if not e['isQ1']]
aw,al,awr=wr(A); bw,bl,bwr=wr(B)
print(f"[a] Q1 {aw}승{al}패 {awr}%  vs 나머지 {bw}승{bl}패 {bwr}%")
tot=aw+al+bw+bl; rw=aw+bw
chi=sum((o-e_)**2/e_ for o,e_ in [
    (aw,(aw+al)*rw/tot),(al,(aw+al)*(tot-rw)/tot),(bw,(bw+bl)*rw/tot),(bl,(bw+bl)*(tot-rw)/tot)])
def chi2_p(x):  # 1 df
    return math.erfc(math.sqrt(x/2))
print(f"    카이제곱 {chi:.2f}  p={chi2_p(chi):.5f}")

# 순열검정(종목 클러스터 고려: 종목 단위로 라벨 셔플)
codes=sorted({e['code'] for e in ev})
by_code=defaultdict(list)
for e in ev: by_code[e['code']].append(e)
obs=awr-bwr
random.seed(7); cnt=0; N=20000
code_isq1={c: statistics.mean([x['isQ1'] for x in by_code[c]])>0.5 for c in codes}
for _ in range(N):
    lab=list(code_isq1.values()); random.shuffle(lab)
    m=dict(zip(code_isq1.keys(),lab))
    a=[e for e in ev if m[e['code']]]; b=[e for e in ev if not m[e['code']]]
    _,_,x=wr(a); _,_,y=wr(b)
    if x is not None and y is not None and (x-y)>=obs: cnt+=1
print(f"    종목단위 순열검정(관측차 {obs:.1f}%p): p={cnt/N:.4f}")

# (b) 종목당 1거래(최초)만
first={}
for e in sorted(ev,key=lambda x:x['entry_date']):
    first.setdefault(e['code'],e)
F=list(first.values())
print(f"\n[b] 종목당 최초 1거래만 (n={len(F)})")
for k in ("Q1","Q2","Q3","Q4"):
    w,l,r=wr([e for e in F if e['Q']==k]); print(f"    {k}: {w}승{l}패 {r}%")

# 승리 집중도
print("\n[b2] Q1 승리 종목 집중도")
c=Counter(e['code'] for e in A if e['result']=='win')
print("    Q1 승 74건이 나온 종목 수:",len(c),"  최다:",c.most_common(5))

# (c) 시간 분할
print("\n[c] 전후반/월별")
mid='2026-03-25'
for lab,f in [("전반",lambda e:e['entry_date']<=mid),("후반",lambda e:e['entry_date']>mid)]:
    print(f"  {lab}: ",end="")
    for k in ("Q1","Q2","Q3","Q4"):
        w,l,r=wr([e for e in ev if e['Q']==k and f(e)]); print(f"{k}={r}%(n={w+l}) ",end="")
    print()
print("  월별 Q1 vs 나머지:")
for m in sorted({e['month'] for e in ev}):
    w1,l1,r1=wr([e for e in ev if e['Q']=='Q1' and e['month']==m])
    w2,l2,r2=wr([e for e in ev if e['Q']!='Q1' and e['month']==m])
    print(f"    {m}  Q1 {str(r1):>5}%(n={w1+l1:>3})   나머지 {str(r2):>5}%(n={w2+l2:>3})")

# (d) 중복보유 공정성
print("\n[d] 보유기간·재진입")
for k in ("Q1","Q2","Q3","Q4"):
    rows=[e for e in ev if e['Q']==k and e['days_held'] is not None]
    dh=[e['days_held'] for e in rows]
    codes_k={e['code'] for e in rows}
    print(f"    {k}: 보유일 중앙값 {statistics.median(dh):>4.0f}  평균 {statistics.mean(dh):>5.1f}  "
          f"거래/종목 {len(rows)/len(codes_k):.2f}")

# (e) 규모 통제 재시도: 거래대금 3분위 × (Q1 vs 나머지)
tv=sorted(e['turnover_eok'] for e in ev); t1,t2=tv[len(tv)//3],tv[2*len(tv)//3]
print(f"\n[e] 거래대금 3분위({t1:.0f}/{t2:.0f}억) 안에서 Q1 vs 나머지")
for lab,lo,hi in [("소형",-1,t1),("중형",t1,t2),("대형",t2,1e18)]:
    sub=[e for e in ev if lo<e['turnover_eok']<=hi]
    w1,l1,r1=wr([e for e in sub if e['isQ1']]); w2,l2,r2=wr([e for e in sub if not e['isQ1']])
    print(f"    {lab}: Q1 {str(r1):>5}%(n={w1+l1:>3})  나머지 {str(r2):>5}%(n={w2+l2:>3})")

# (f) 우선주 누출 / 이상치
pref=[e for e in ev if '우' in e['name']]
print("\n[f] 이름에 '우' 포함(우선주 의심):",Counter(e['name'] for e in pref))
print("    최대 max_gain 상위5:",[(e['name'],e['max_gain_pct']) for e in sorted(ev,key=lambda x:-(x['max_gain_pct'] or 0))[:5]])
print("    최소 max_dd 하위5:",[(e['name'],e['max_dd_pct']) for e in sorted(ev,key=lambda x:(x['max_dd_pct'] or 0))[:5]])

# (g) 패턴 구성 차이
print("\n[g] 사분위별 패턴 구성")
for k in ("Q1","Q2","Q3","Q4"):
    print(f"    {k}:",Counter(e['pattern'] for e in ev if e['Q']==k))
print("    패턴별 승률:")
for p in ("VCP","3C","PP"):
    w,l,r=wr([e for e in ev if e['pattern']==p]); print(f"      {p}: {r}% (n={w+l})")
