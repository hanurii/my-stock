# -*- coding: utf-8 -*-
import json, collections, pickle, random, os, math
random.seed(11)
SP=os.path.dirname(os.path.abspath(__file__)); ROOT=r"C:/Users/hanul/playground/my-stock"
D=pickle.load(open(SP+"/regime_metrics.pkl","rb"))
dates,pos,M,up=D["dates"],D["pos"],D["M"],D["up"]
d=json.load(open(ROOT+"/public/data/backtest-volatility-pilot.json",encoding="utf-8"))
events=[x for x in d["events"] if x["result"] in ("win","loss")]
day_n=collections.defaultdict(int); day_w=collections.defaultdict(int)
for e in events:
    day_n[e["entry_date"]]+=1; day_w[e["entry_date"]]+= 1 if e["result"]=="win" else 0
alldays=sorted(day_n); updays=[dt for dt in alldays if up[pos[dt]-1]]
S=M["⑬상승일비율10"]; val={dt:S[pos[dt]-1] for dt in updays}
srt=sorted(updays,key=lambda dt:val[dt]); k=len(srt)//4
bot=srt[:k]; top=srt[-k:]

def clusters(days, gap=5):
    ii=sorted(days,key=lambda x:pos[x]); out=[[ii[0]]]
    for x in ii[1:]:
        if pos[x]-pos[out[-1][-1]]>gap: out.append([x])
        else: out[-1].append(x)
    return out
ct=clusters(top); cb=clusters(bot)
print("상위 덩어리:", [(c[0],c[-1],len(c)) for c in ct])
print("하위 덩어리:", [(c[0],c[-1],len(c)) for c in cb])
def wr(days):
    n=sum(day_n[x] for x in days); w=sum(day_w[x] for x in days)
    return (100*w/n if n else float('nan'), n)
full=wr(top)[0]-wr(bot)[0]
print(f"전체 차이 {full:+.1f}%p (상위 {wr(top)[0]:.1f}%/{wr(top)[1]}거래, 하위 {wr(bot)[0]:.1f}%/{wr(bot)[1]}거래)")
print("\n[덩어리 하나씩 빼기]")
for c in ct+cb:
    t=[x for x in top if x not in c]; b=[x for x in bot if x not in c]
    a=wr(t); z=wr(b)
    print(f"  빼기 {c[0]}~{c[-1]}({len(c)}일): 상위 {a[0]:.1f}%({a[1]})  하위 {z[0]:.1f}%({z[1]})  차 {a[0]-z[0]:+.1f}%p")

# moving-block permutation preserving BOTH series' autocorrelation:
# cut the uptrend-day sequence into blocks of 10 trading days, shuffle blocks of metric values
seq=sorted(updays,key=lambda x:pos[x])
vals=[val[x] for x in seq]
def stat(vs):
    pr=sorted(zip(vs,seq)); kk=len(pr)//4
    b=pr[:kk]; t=pr[-kk:]
    nb=sum(day_n[dt] for _,dt in b); wb=sum(day_w[dt] for _,dt in b)
    nt=sum(day_n[dt] for _,dt in t); wt=sum(day_w[dt] for _,dt in t)
    return 100*wt/nt-100*wb/nb
obs=stat(vals)
for BL in (5,10,20):
    blocks=[vals[i:i+BL] for i in range(0,len(vals),BL)]
    B=4000; c=0
    for _ in range(B):
        bb=blocks[:]; random.shuffle(bb)
        v=[x for b in bb for x in b][:len(vals)]
        if stat(v)<=obs: c+=1
    print(f"블록길이 {BL}일 블록순열: p={(c+1)/(B+1):.4f}")
