import json, math, random
from collections import defaultdict
D=json.load(open('C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json',encoding='utf-8'))
R=json.load(open('C:/Users/hanul/playground/my-stock/public/data/market-regime.json',encoding='utf-8'))
reg={x['date']:x['up'] for x in R['series']}
ALL=D['events']
# sensitivity: ambiguous/unresolved treatment
def wipe_days(mapper,minn=4,uponly=False):
    byday=defaultdict(list)
    for x in ALL:
        r=mapper(x)
        if r is None: continue
        if uponly and not reg[x['scan_date']]: continue
        byday[x['entry_date']].append(r)
    ds=[(d,v) for d,v in byday.items() if len(v)>=minn]
    k=len(ds); N=sum(len(v) for _,v in ds); W=sum(sum(v) for _,v in ds); p=W/N
    z=sum(1 for _,v in ds if sum(v)==0)
    exp=sum((1-p)**len(v) for _,v in ds)
    return k,N,p,z,exp
for lbl,mp in (('결착만(ambig 제외)',lambda x: 1 if x['result']=='win' else (0 if x['result']=='loss' else None)),
               ('ambig=승 취급',lambda x: 1 if x['result'] in ('win','ambiguous') else (0 if x['result']=='loss' else None)),
               ('ambig=패 취급',lambda x: 1 if x['result']=='win' else (0 if x['result'] in ('loss','ambiguous') else None))):
    for uo in (False,True):
        k,N,p,z,e=wipe_days(mp,4,uo)
        print('%-16s %-6s days=%2d N=%3d p=%.3f 전멸=%2d (%2.0f%%)  기대 %.1f (%.0f%%)'%(lbl,'상승' if uo else '전체',k,N,p,z,100*z/k,e,100*e/k))
print()
# --- spreading test: 6 from one day vs 3+3 from two consecutive entry days ---
byday=defaultdict(list)
for x in ALL:
    if x['result'] in ('win','loss'): byday[x['entry_date']].append(1 if x['result']=='win' else 0)
days=sorted(byday)
random.seed(11)
def pick(v,k):
    return random.sample(v,k) if len(v)>=k else None
T=20000
# same-day 6
z1=n1=0; z2=n2=0
big=[d for d in days if len(byday[d])>=6]
pairs=[(a,b) for a,b in zip(days,days[1:]) if len(byday[a])>=3 and len(byday[b])>=3]
print('6건+ 가능한 날 %d일 / 연속 두날 3+3 가능한 쌍 %d개'%(len(big),len(pairs)))
for _ in range(T):
    d=random.choice(big); s=pick(byday[d],6)
    n1+=1; z1+= (sum(s)==0)
    a,b=random.choice(pairs); s=pick(byday[a],3)+pick(byday[b],3)
    n2+=1; z2+= (sum(s)==0)
print('한날 6개 전멸확률 %.1f%%  /  이틀 3+3 전멸확률 %.1f%%'%(100*z1/n1,100*z2/n2))
# expectancy
def exp_ret(sel):
    w=sum(1 for x in sel if x['result']=='win'); n=len(sel)
    return 100*(w/n*0.20 + (1-w/n)*(-0.10)), n
res=[x for x in ALL if x['result'] in ('win','loss')]
u=[x for x in res if reg[x['scan_date']]]; dn=[x for x in res if not reg[x['scan_date']]]
print('기대수익/거래(+20/-10): 전체 %.2f%% (n=%d) / 상승 %.2f%% (n=%d) / 조정 %.2f%% (n=%d)'%(exp_ret(res)[0],len(res),exp_ret(u)[0],len(u),exp_ret(dn)[0],len(dn)))
