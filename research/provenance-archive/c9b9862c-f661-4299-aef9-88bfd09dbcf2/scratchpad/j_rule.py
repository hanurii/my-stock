exec(open('j_core.py',encoding='utf-8').read().split("# 9-month window")[0])
import bisect as bi, statistics as st, collections, random
reg=L('regime_long.json'); rd=reg['dates']; rmap=dict(zip(rd,reg['up_ew20']))
def regime(d):
    i=bi.bisect_right(rd,d)-1; return bool(rmap[rd[i]])
for e in ev: e['rg']=regime(e['scan_date'])
def wr(x): return 100*sum(1 for e in x if e['result']=='win')/len(x) if x else float('nan')
def show(x,tag):
    print('%-34s n=%4d  wr=%5.2f%%  net/trade=%+.3f%%  sum=%+.0f%%'%(tag,len(x),wr(x),st.mean(e['net'] for e in x),sum(e['net'] for e in x)))
show(ev,'ALL (no filter)')
show([e for e in ev if e['rg']],'regime UP only')
show([e for e in ev if e['rg'] and e['nq']],'regime UP + NASDAQ UP  <= the rule')
show([e for e in ev if e['rg'] and not e['nq']],'regime UP + NASDAQ DOWN')

# permutation: shuffle nasdaq label calendar (circular), measure within-regime-UP contrast
days=sorted({e['entry_date'] for e in ev}); byday=collections.defaultdict(list)
for e in ev: byday[e['entry_date']].append(e)
seq=[byday[d][0]['nq'] for d in days]
def contrast(labels):
    u=[];dn=[]
    for d,f in zip(days,labels):
        for e in byday[d]:
            if not e['rg']: continue
            (u if f else dn).append(e)
    return wr(u)-wr(dn), st.mean(e['net'] for e in u)-st.mean(e['net'] for e in dn)
obs=contrast(seq); print('\nwithin regime-UP: winrate diff=%+.2f%%p  net diff=%+.3f%%p'%obs)
c=0;n=0;dist=[]
for s in range(1,len(seq)):
    r=contrast(seq[s:]+seq[:s]); n+=1; dist.append(r[0])
    if r[0]>=obs[0]: c+=1
print('circular-shift permutation one-sided p=%.4f (n=%d)  perm 5/50/95 = %+.2f/%+.2f/%+.2f'%(c/n,n,st.quantiles(dist,n=20)[0],st.median(dist),st.quantiles(dist,n=20)[18]))

# also: how many trades survive the rule, and how many trading days
d_rule={e['entry_date'] for e in ev if e['rg'] and e['nq']}
print('\nrule keeps %d/%d trades (%.0f%%) on %d/%d trading days'%(sum(1 for e in ev if e['rg'] and e['nq']),len(ev),100*sum(1 for e in ev if e['rg'] and e['nq'])/len(ev),len(d_rule),len(days)))
