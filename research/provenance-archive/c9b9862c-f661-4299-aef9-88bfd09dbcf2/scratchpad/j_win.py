exec(open('j_core.py',encoding='utf-8').read().split("# 9-month window")[0])
import collections, statistics as st
def wr(x): return 100*sum(1 for e in x if e['result']=='win')/len(x) if x else float('nan')
def d9(sub):
    u=[e for e in sub if e['nq']]; dn=[e for e in sub if not e['nq']]
    return len(sub),len(u),len(dn),wr(u)-wr(dn)
# non-overlapping 9-month windows, cut backwards from end
import datetime as dt
def addm(ym,k):
    y,m=divmod((ym[0]*12+ym[1]-1)+k,12); return (y,m+1)
end=(2026,9)  # exclusive
print('[non-overlapping 9-month windows, cut backward from 2026-09]')
res=[]
for i in range(7):
    hi=addm(end,-9*i); lo=addm(end,-9*(i+1))
    slo='%04d-%02d'%lo; shi='%04d-%02d'%hi
    s=[e for e in ev if slo<=e['entry_date'][:7]<shi]
    if len(s)<50: continue
    n,nu,nd,d=d9(s); res.append(d)
    print('  %s ~ %s  n=%4d (up %4d/down %4d)  diff=%+.2f%%p'%(slo,addm(hi,-1) and '%04d-%02d'%addm(hi,-1),n,nu,nd,d))
print('  -> positive %d/%d, median=%+.2f%%p, mean=%+.2f%%p'%(sum(1 for x in res if x>0),len(res),st.median(res),st.mean(res)))

# rolling 9-month windows (monthly step)
print('\n[all overlapping 9-month windows]')
roll=[]
ym=(2021,2)
while True:
    hi=addm(ym,9)
    if '%04d-%02d'%hi>'2026-09': break
    s=[e for e in ev if '%04d-%02d'%ym<=e['entry_date'][:7]<'%04d-%02d'%hi]
    if len(s)>=150:
        n,nu,nd,d=d9(s); roll.append(('%04d-%02d'%ym,d,n))
    ym=addm(ym,1)
vals=[r[1] for r in roll]
print('  windows=%d  median=%+.2f%%p  sd=%.2f  min=%+.2f (%s)  max=%+.2f (%s)'%(
  len(roll),st.median(vals),st.pstdev(vals),min(vals),min(roll,key=lambda r:r[1])[0],max(vals),max(roll,key=lambda r:r[1])[0]))
print('  windows with diff >= +9.7%%p: %d / %d'%(sum(1 for v in vals if v>=9.7),len(vals)))

# month breakdown of the discovery window
print('\n[9-month discovery window 2025-12~2026-08, monthly]')
s=[e for e in ev if e['entry_date']>='2025-12-01']
for m in sorted({e['entry_date'][:7] for e in s}):
    x=[e for e in s if e['entry_date'][:7]==m]
    u=[e for e in x if e['nq']]; dn=[e for e in x if not e['nq']]
    print('  %s n=%3d  up %3d wr=%5.1f  down %3d wr=%5.1f  diff=%+6.1f%%p'%(m,len(x),len(u),wr(u),len(dn),wr(dn),wr(u)-wr(dn)))
for drop in [['2026-04'],['2025-12'],['2025-12','2026-04']]:
    x=[e for e in s if e['entry_date'][:7] not in drop]
    n,nu,nd,d=d9(x); print('  drop %-20s n=%3d  diff=%+.2f%%p'%(','.join(drop),n,d))

# 4-cell regime x nasdaq (regime by scan_date, ew 20MA)
reg=L('regime_long.json')
rmap=dict(zip(reg['dates'],reg['up_ew20']))
import bisect as bi
rd=reg['dates']
def regime(d):
    i=bi.bisect_right(rd,d)-1
    return bool(rmap[rd[i]]) if i>=0 else None
print('\n[4 cells: KR regime(ew20MA, scan_date) x NASDAQ prev-close]')
tot={}
for rg in (True,False):
    for nqf in (True,False):
        x=[e for e in ev if regime(e['scan_date'])==rg and e['nq']==nqf]
        tot[(rg,nqf)]=x
        print('  regime=%-6s nasdaq=%-5s n=%4d  wr=%5.2f%%  net/trade=%+.3f%%'%('UP' if rg else 'CORR','UP' if nqf else 'DOWN',len(x),wr(x),st.mean(e['net'] for e in x)))
worst=tot[(False,True)]
rest=[e for e in ev if not (regime(e['scan_date'])==False and e['nq'])]
print('  worst-cell excluded: n=%d  net/trade=%+.3f%%  (vs all %+.3f%%)'%(len(rest),st.mean(e['net'] for e in rest),st.mean(e['net'] for e in ev)))
# month-paired test inside correction regime
print('\n[correction regime, month-paired comparison]')
pairs=[]
months=sorted({e['entry_date'][:7] for e in ev})
for m in months:
    a=[e for e in ev if e['entry_date'][:7]==m and regime(e['scan_date'])==False and e['nq']]
    b=[e for e in ev if e['entry_date'][:7]==m and regime(e['scan_date'])==False and not e['nq']]
    if len(a)>=3 and len(b)>=3: pairs.append((m,st.mean(e['net'] for e in a)-st.mean(e['net'] for e in b)))
import math
dv=[p[1] for p in pairs]
t=st.mean(dv)/(st.pstdev(dv)/math.sqrt(len(dv)-1))
print('  months compared=%d  up-better months=%d (%.0f%%)  median diff=%+.2f%%p  mean=%+.2f%%p  t=%.2f'%(
   len(pairs),sum(1 for v in dv if v>0),100*sum(1 for v in dv if v>0)/len(pairs),st.median(dv),st.mean(dv),t))
# yearly sign of overall nasdaq diff
print('\n[yearly nasdaq up-down winrate diff, all trades]')
for y in range(2021,2027):
    x=[e for e in ev if e['entry_date'][:4]==str(y)]
    n,nu,nd,d=d9(x); print('  %d n=%4d  diff=%+.2f%%p'%(y,n,d))
