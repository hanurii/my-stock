# -*- coding: utf-8 -*-
import json, collections, pickle, os, itertools, math
SP=os.path.dirname(os.path.abspath(__file__)); ROOT=r"C:/Users/hanul/playground/my-stock"
D=pickle.load(open(SP+"/regime_metrics.pkl","rb"))
dates,pos,M,up,idx=D["dates"],D["pos"],D["M"],D["up"],D["idx"]
d=json.load(open(ROOT+"/public/data/backtest-volatility-pilot.json",encoding="utf-8"))
events=[x for x in d["events"] if x["result"] in ("win","loss")]
day_n=collections.defaultdict(int); day_w=collections.defaultdict(int)
for e in events:
    day_n[e["entry_date"]]+=1; day_w[e["entry_date"]]+= 1 if e["result"]=="win" else 0
alldays=sorted(day_n); updays=[dt for dt in alldays if up[pos[dt]-1]]
S=M["⑬상승일비율10"]; val={dt:S[pos[dt]-1] for dt in updays}

# 1) monotonicity over 4 quartiles
srt=sorted(updays,key=lambda dt:val[dt]); k=len(srt)//4
print("[상승국면 88일 4분위 단조성]")
for q in range(4):
    seg=srt[q*k:(q+1)*k] if q<3 else srt[3*k:]
    n=sum(day_n[x] for x in seg); w=sum(day_w[x] for x in seg)
    print(f"  Q{q+1} (값 {min(val[x] for x in seg):.0f}~{max(val[x] for x in seg):.0f}%): {len(seg)}일 {n}거래 승률 {100*w/n:.1f}%")

# 2) cluster-level exact test (each calendar cluster = one observation)
def clusters(days, gap=5):
    ii=sorted(days,key=lambda x:pos[x]); out=[[ii[0]]]
    for x in ii[1:]:
        if pos[x]-pos[out[-1][-1]]>gap: out.append([x])
        else: out[-1].append(x)
    return out
bot=srt[:k]; top=srt[-k:]
ct=clusters(top); cb=clusters(bot)
def cwr(c):
    n=sum(day_n[x] for x in c); w=sum(day_w[x] for x in c); return 100*w/n, n
print("\n[덩어리별 승률 — 유효 표본은 날이 아니라 덩어리]")
A=[]; B=[]
for c in ct:
    r,n=cwr(c); A.append(r); print(f"  상위 {c[0]}~{c[-1]}: {r:.1f}% ({n}거래)")
for c in cb:
    r,n=cwr(c); B.append(r); print(f"  하위 {c[0]}~{c[-1]}: {r:.1f}% ({n}거래)")
# exact Mann-Whitney (permutation over cluster labels)
allv=A+B; nA=len(A)
obs=sum(1 for a in A for b in B if a<b)+0.5*sum(1 for a in A for b in B if a==b)
cnt=0; tot=0
for comb in itertools.combinations(range(len(allv)), nA):
    aa=[allv[i] for i in comb]; bb=[allv[i] for i in range(len(allv)) if i not in comb]
    u=sum(1 for a in aa for b in bb if a<b)+0.5*sum(1 for a in aa for b in bb if a==b)
    tot+=1
    if u>=obs: cnt+=1
print(f"  덩어리 수준 정확검정: 상위 {nA}덩어리 vs 하위 {len(B)}덩어리, p={cnt/tot:.4f} (가능한 최소 p={1/math.comb(len(allv),nA):.4f})")

# 3) is it market timing? forward index return by metric quartile
print("\n[지표가 '시장 앞날'을 맞히는가 — 상승국면 전체 달력일 기준]")
lo=0
while S[lo] is None: lo+=1
rows=[(S[i], (idx[i+10]/idx[i]-1)*100) for i in range(lo, len(idx)-10) if up[i]]
rows.sort()
q=len(rows)//4
for qi in range(4):
    seg=rows[qi*q:(qi+1)*q] if qi<3 else rows[3*q:]
    print(f"  Q{qi+1} 값{seg[0][0]:.0f}~{seg[-1][0]:.0f}%: 이후 10일 지수 {sum(x[1] for x in seg)/len(seg):+.2f}% (n={len(seg)}일)")
