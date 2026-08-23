import json, collections, statistics
from math import comb
BASE=r"C:/Users/hanul/playground/my-stock/public/data/"
d=json.load(open(BASE+"backtest-volatility-pilot.json",encoding="utf-8"))
ev=d["events"]; reg=json.load(open(BASE+"market-regime.json",encoding="utf-8"))["series"]
upmap={r["date"]:bool(r["up"]) for r in reg}
P=[dict(day=x["entry_date"],scan=x["scan_date"],win=1 if x["result"]=="win" else 0,to=x["turnover_eok"]) for x in ev]
byday=collections.defaultdict(list)
for x in P: byday[x["day"]].append(x)
days=sorted(byday); lab={dy:upmap[byday[dy][0]["scan"]] for dy in days}
def rw(n,w,K):
    k=min(K,n)
    if w==0: return 1.0
    if n-w<k: return 0.0
    return comb(n-w,k)/comb(n,k)
print("### 순서 규칙의 물리적 한계 (오라클: 미래를 알고 승자부터 담는 경우)")
zero=[dy for dy in days if sum(y['win'] for y in byday[dy])==0]
print(" 그날 후보 중 이긴 종목이 아예 0개인 날: %d/%d = %.1f%%  <- 어떤 순서 규칙도 이 아래로 못 내려감"%(len(zero),len(days),100*len(zero)/len(days)))
for K in (1,3,6):
    r=statistics.mean([rw(len(byday[dy]),sum(y['win'] for y in byday[dy]),K) for dy in days])
    print("  K=%d: 무작위 %.1f%% → 오라클 %.1f%% (최대 개선 여지 %.1f%%p)"%(K,100*r,100*len(zero)/len(days),100*(r-len(zero)/len(days))))
print()
up=[x for x in days if lab[x]]; dn=[x for x in days if not lab[x]]
for nm,sel in (("상승국면일",up),("조정국면일",dn)):
    z=sum(1 for dy in sel if sum(y['win'] for y in byday[dy])==0)
    print(" %s: 승자 0인 날 %d/%d = %.1f%%"%(nm,z,len(sel),100*z/len(sel)))
print()
print("### 국면 구간(연속 덩어리) 수 = 사실상의 표본 크기")
seq=[lab[dy] for dy in days]
runs=1+sum(1 for i in range(1,len(seq)) if seq[i]!=seq[i-1])
lens=[];cur=1
for i in range(1,len(seq)):
    if seq[i]==seq[i-1]: cur+=1
    else: lens.append(cur);cur=1
lens.append(cur)
print(" 146 진입일이 %d개 구간으로 뭉침 (구간 길이: %s)"%(runs,lens))
