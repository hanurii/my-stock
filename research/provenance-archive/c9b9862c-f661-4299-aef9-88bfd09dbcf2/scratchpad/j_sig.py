exec(open('j_core.py',encoding='utf-8').read().split("# 9-month window")[0])
import random, collections
days=sorted({e['entry_date'] for e in ev})
print('\n[trading days with trades] %d  avg trades/day=%.2f'%(len(days),len(ev)/len(days)))
byday=collections.defaultdict(list)
for e in ev: byday[e['entry_date']].append(e)

# calendar of KR trading days (from regime) to do circular shift of nasdaq label series
reg=L('regime_long.json')
lab={}
for d in days: lab[d]=byday[d][0]['nq']
seq=[lab[d] for d in days]

def diff_wr(labels):
    u=[];dn=[]
    for d,fl in zip(days,labels):
        for e in byday[d]: (u if fl else dn).append(e)
    if not u or not dn: return None
    return (100*sum(1 for e in u if e['result']=='win')/len(u) - 100*sum(1 for e in dn if e['result']=='win')/len(dn),
            sum(e['net'] for e in u)/len(u) - sum(e['net'] for e in dn)/len(dn))
obs=diff_wr(seq); print('observed diff wr=%+.2f%%p  net=%+.3f%%p'%obs)

# day-level t-test on per-day mean net
dm_u=[st.mean(e['net'] for e in byday[d]) for d in days if lab[d]]
dm_d=[st.mean(e['net'] for e in byday[d]) for d in days if not lab[d]]
import math
def welch(a,b):
    ma,mb=st.mean(a),st.mean(b); va,vb=st.variance(a),st.variance(b)
    se=math.sqrt(va/len(a)+vb/len(b)); return (ma-mb), (ma-mb)/se
d_,t_=welch(dm_u,dm_d)
print('day-level mean net: up %d days %+.3f%%  down %d days %+.3f%%  diff=%+.2f%%p  t=%.2f'%(len(dm_u),st.mean(dm_u),len(dm_d),st.mean(dm_d),d_,t_))

# circular shift permutation over full nasdaq label calendar
N=len(seq); cnt=0; tot=0; dist=[]
for s in range(1,N):
    r=diff_wr(seq[s:]+seq[:s])
    if r is None: continue
    tot+=1; dist.append(r[0])
    if r[0]<=obs[0]: cnt+=1
print('circular-shift permutation (winrate diff): one-sided p=%.4f  (n_shifts=%d)  perm 5%%/50%%/95%% = %+.2f / %+.2f / %+.2f'%(
    cnt/tot,tot,st.quantiles(dist,n=20)[0],st.median(dist),st.quantiles(dist,n=20)[18]))
