import json, math, random
from collections import defaultdict
D=json.load(open('C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json',encoding='utf-8'))
R=json.load(open('C:/Users/hanul/playground/my-stock/public/data/market-regime.json',encoding='utf-8'))
reg={x['date']:x['up'] for x in R['series']}
ev=[x for x in D['events'] if x['result'] in ('win','loss')]
byday=defaultdict(list)
for x in ev: byday[x['entry_date']].append(x)
days=sorted(byday)
lab={d: reg[byday[d][0]['scan_date']] for d in days}
nup=sum(1 for d in days if lab[d])
print('days',len(days),'up-days',nup,'down-days',len(days)-nup)
def gap(labels):
    wu=nu=wd=nd=0
    for d in days:
        w=sum(1 for x in byday[d] if x['result']=='win'); n=len(byday[d])
        if labels[d]: wu+=w; nu+=n
        else: wd+=w; nd+=n
    return (wu/nu-wd/nd)*100 if nu and nd else 0.0
obs=gap(lab); print('observed gap (pp) %.2f'%obs)
random.seed(7)
# A) day-block permutation: shuffle regime labels across days (keeps within-day clustering)
cnt=0; T=20000
ls=[lab[d] for d in days]
for _ in range(T):
    random.shuffle(ls)
    if gap(dict(zip(days,ls)))>=obs: cnt+=1
print('A day-label permutation p = %.4f (%d/%d)'%((cnt+1)/(T+1),cnt,T))
# B) episode-block permutation: contiguous runs of same label = blocks, shuffle block labels
blocks=[]; cur=[days[0]]
for a,b in zip(days,days[1:]):
    if lab[b]==lab[a]: cur.append(b)
    else: blocks.append((lab[a],cur)); cur=[b]
blocks.append((lab[days[-1]],cur))
print('regime blocks:',len(blocks),'up-blocks',sum(1 for l,_ in blocks if l))
bl=[l for l,_ in blocks]
cnt=0
for _ in range(T):
    random.shuffle(bl)
    lb={}
    for (l,(_,dd)) in zip(bl,blocks):
        for d in dd: lb[d]=l
    if gap(lb)>=obs: cnt+=1
print('B episode-block permutation p = %.4f'%((cnt+1)/(T+1)))
# C) stock-block permutation of outcomes (keeps regime labels, shuffles results by stock block)
bycode=defaultdict(list)
for x in ev: bycode[x['code']].append(x)
codes=list(bycode)
print('codes',len(codes))
def gap_from(assign):
    wu=nu=wd=nd=0
    for x,r in assign:
        if lab[x['entry_date']]: nu+=1; wu+= (r=='win')
        else: nd+=1; wd+= (r=='win')
    return (wu/nu-wd/nd)*100
allres=[x['result'] for x in ev]
cnt=0
for _ in range(T//4):
    pool=allres[:]; random.shuffle(pool)
    # assign shuffled results block-wise by code (block = stock's trades keep contiguous chunk)
    i=0; assign=[]
    for c in codes:
        for x in bycode[c]:
            assign.append((x,pool[i])); i+=1
    if gap_from(assign)>=obs: cnt+=1
print('C stock-block shuffle p = %.4f'%((cnt+1)/(T//4+1)))
# halves
for name,sel in (('전반(<2026-03-25)',[x for x in ev if x['entry_date']<'2026-03-25']),('후반(>=2026-03-25)',[x for x in ev if x['entry_date']>='2026-03-25'])):
    u=[x for x in sel if reg[x['scan_date']]]; d=[x for x in sel if not reg[x['scan_date']]]
    fu=100*sum(1 for x in u if x['result']=='win')/len(u) if u else float('nan')
    fd=100*sum(1 for x in d if x['result']=='win')/len(d) if d else float('nan')
    print('%s  up %d건 %.1f%%  down %d건 %.1f%%  gap %.1fpp'%(name,len(u),fu,len(d),fd,fu-fd))
