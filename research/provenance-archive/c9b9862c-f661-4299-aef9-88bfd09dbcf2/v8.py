import json, math, random
from collections import defaultdict
D=json.load(open('C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json',encoding='utf-8'))
R=json.load(open('C:/Users/hanul/playground/my-stock/public/data/market-regime.json',encoding='utf-8'))
reg={x['date']:x['up'] for x in R['series']}
byday=defaultdict(list)
for x in D['events']:
    if x['result'] in ('win','loss'): byday[x['entry_date']].append(1 if x['result']=='win' else 0)
days=sorted(byday)
idx={d:i for i,d in enumerate(days)}
random.seed(3)
T=40000
def sim(chunks, uponly=False, maxgap=None):
    """chunks: list like [6] or [3,3] or [2,2,2] or [1]*6 ; pick from distinct consecutive-ish days"""
    z=0; n=0; wins=[]
    pool=[d for d in days if (not uponly or reg[[x for x in D['events'] if x['entry_date']==d][0]['scan_date']])] if False else days
    for _ in range(T):
        k=len(chunks)
        # choose a starting index and take next k days that have enough entries
        tries=0
        while True:
            tries+=1
            if tries>200: break
            i=random.randrange(len(days))
            sel=[]; j=i; ok=True
            for c in chunks:
                # advance to next day with >= c entries
                while j<len(days) and len(byday[days[j]])<c: j+=1
                if j>=len(days): ok=False; break
                if uponly and not upday[days[j]]: ok=False; break
                sel.append((days[j],c)); j+=1
            if ok and (maxgap is None or idx[sel[-1][0]]-idx[sel[0][0]]<=maxgap):
                break
        if tries>200: continue
        s=[]
        for d,c in sel: s+= random.sample(byday[d],c)
        n+=1; z+= (sum(s)==0); wins.append(sum(s))
    return 100*z/n, sum(wins)/len(wins), n
upday={}
for x in D['events']:
    if x['result'] in ('win','loss'): upday[x['entry_date']]=reg[x['scan_date']]
for chunks,lbl in (([6],'한 날 6개'),([3,3],'이틀 3+3'),([2,2,2],'사흘 2+2+2'),([1]*6,'엿새 1개씩')):
    for uo in (False,True):
        p,mw,n=sim(chunks,uo)
        print('%-12s %-4s 전멸확률 %.1f%%  평균승수 %.2f/6  (n=%d)'%(lbl,'상승' if uo else '전체',p,mw,n))
print()
# lag autocorrelation of day win-rate (days with >=3)
ds=[d for d in days if len(byday[d])>=3]
rate={d:sum(byday[d])/len(byday[d]) for d in ds}
import statistics
def corr(pairs):
    if len(pairs)<8: return float('nan'),len(pairs)
    xs=[a for a,b in pairs]; ys=[b for a,b in pairs]
    mx=sum(xs)/len(xs); my=sum(ys)/len(ys)
    num=sum((a-mx)*(b-my) for a,b in pairs)
    den=math.sqrt(sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))
    return num/den, len(pairs)
for L in (1,2,3,5,10):
    pairs=[]
    for d in ds:
        i=idx[d]
        if i+L<len(days) and days[i+L] in rate: pairs.append((rate[d],rate[days[i+L]]))
    c,n=corr(pairs)
    print('진입일 승률 자기상관 lag%-2d = %+.3f (쌍 %d)'%(L,c,n))
