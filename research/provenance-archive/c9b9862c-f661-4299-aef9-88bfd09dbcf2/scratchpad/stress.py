# -*- coding: utf-8 -*-
import json, collections, pickle, random, os, statistics, math
random.seed(7)
SP=os.path.dirname(os.path.abspath(__file__)); ROOT=r"C:/Users/hanul/playground/my-stock"
D=pickle.load(open(SP+"/regime_metrics.pkl","rb"))
dates,pos,M,up=D["dates"],D["pos"],D["M"],D["up"]; N=len(dates)
d=json.load(open(ROOT+"/public/data/backtest-volatility-pilot.json",encoding="utf-8"))
events=[x for x in d["events"] if x["result"] in ("win","loss")]
day_n=collections.defaultdict(int); day_w=collections.defaultdict(int)
byday=collections.defaultdict(list)
for e in events:
    day_n[e["entry_date"]]+=1; day_w[e["entry_date"]]+= 1 if e["result"]=="win" else 0
    byday[e["entry_date"]].append(e)
alldays=sorted(day_n); updays=[dt for dt in alldays if up[pos[dt]-1]]

name="⑬상승일비율10"
S=M[name]; lo=0
while S[lo] is None: lo+=1
val={dt:S[pos[dt]-1] for dt in updays}
srt=sorted(updays,key=lambda dt:val[dt]); k=len(srt)//4
bot=set(srt[:k]); top=set(srt[-k:])
print(f"[{name} / 상승국면 {len(updays)}일]  하위{len(bot)}일  상위{len(top)}일")
for lab,SS in (("하위(횡보·눌림)",bot),("상위(연일상승)",top)):
    n=sum(day_n[x] for x in SS); w=sum(day_w[x] for x in SS)
    print(f"  {lab}: {len(SS)}일 {n}거래 승률 {100*w/n:.1f}%  값범위 {min(val[x] for x in SS):.0f}~{max(val[x] for x in SS):.0f}%")

def episodes(days):
    ii=sorted(pos[x] for x in days); blocks=1
    for a,b in zip(ii,ii[1:]):
        if b-a>3: blocks+=1
    return blocks
print(f"  달력 덩어리 수: 하위 {episodes(bot)}개, 상위 {episodes(top)}개  (간격 3거래일 초과면 새 덩어리)")
print("  상위분위 날짜:", " ".join(sorted(top)))
print("  하위분위 날짜:", " ".join(sorted(bot)))

# autocorrelation length of the metric -> effective independent shifts
ser=[v for v in S[lo:]]
mu=sum(ser)/len(ser)
def ac(k):
    a=[(ser[i]-mu) for i in range(len(ser)-k)]; b=[(ser[i+k]-mu) for i in range(len(ser)-k)]
    num=sum(x*y for x,y in zip(a,b)); den=math.sqrt(sum(x*x for x in a)*sum(y*y for y in b))
    return num/den if den else 0
first0=next((k for k in range(1,60) if ac(k)<=0),None)
print(f"  지표 자기상관: lag5={ac(5):.2f} lag10={ac(10):.2f} lag20={ac(20):.2f} 최초 0교차 lag={first0}")
print(f"  순환이동 유효 독립 표본 ≈ {len(ser)}/{first0 if first0 else 20} ≈ {len(ser)//(first0 if first0 else 20)}개")

# split-half (entry 2026-03-25)
CUT="2026-03-25"
for lab,f in (("전반(~03-24)",lambda dt: dt<CUT),("후반(03-25~)",lambda dt: dt>=CUT)):
    t=[x for x in top if f(x)]; b=[x for x in bot if f(x)]
    nt=sum(day_n[x] for x in t); wt=sum(day_w[x] for x in t)
    nb=sum(day_n[x] for x in b); wb=sum(day_w[x] for x in b)
    st=f"{100*wt/nt:.1f}%({nt})" if nt else "n/a"
    sb=f"{100*wb/nb:.1f}%({nb})" if nb else "n/a"
    print(f"  {lab}: 상위 {st}  하위 {sb}  차 {(100*wt/nt-100*wb/nb):+.1f}%p" if nt and nb else f"  {lab}: 상위 {st} 하위 {sb}")

# correlation with index 10d return (same underlying bet?)
v2={dt:M["②지수10일수익"][pos[dt]-1] for dt in updays}
xs=[val[dt] for dt in updays]; ys=[v2[dt] for dt in updays]
mx=sum(xs)/len(xs); my=sum(ys)/len(ys)
num=sum((a-mx)*(b-my) for a,b in zip(xs,ys))
den=math.sqrt(sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))
print(f"  ⑬ vs ②지수10일수익 상관: r={num/den:.2f}  (같은 베팅의 다른 얼굴인지)")

# stock-block permutation: shuffle whole-stock outcome blocks across trades
codes=collections.defaultdict(list)
for e in events: codes[e["code"]].append(e)
def stat_from_assign(assign):
    n_t=w_t=n_b=w_b=0
    for e,win in assign:
        dt=e["entry_date"]
        if dt in top: n_t+=1; w_t+=win
        elif dt in bot: n_b+=1; w_b+=win
    if not n_t or not n_b: return 0
    return 100*w_t/n_t-100*w_b/n_b
obs=stat_from_assign([(e, 1 if e["result"]=="win" else 0) for e in events])
B=3000; c=0
blocks=[[1 if e["result"]=="win" else 0 for e in v] for v in codes.values()]
flat=[e for v in codes.values() for e in v]
for _ in range(B):
    bl=blocks[:]; random.shuffle(bl)
    outs=[x for b in bl for x in b]
    if stat_from_assign(list(zip(flat,outs)))<=obs: c+=1   # one-sided (obs negative)
print(f"  종목블록 순열(3000회, 관측차 {obs:+.1f}%p): p={(c+1)/(B+1):.4f}")
