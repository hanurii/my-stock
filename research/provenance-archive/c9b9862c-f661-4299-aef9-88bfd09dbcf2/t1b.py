import sys,statistics as st
sys.path.insert(0,'C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad')
from engine import *
def q(xs,p):
    xs=sorted(xs); k=(len(xs)-1)*p; f=int(k); c=min(f+1,len(xs)-1)
    return xs[f]+(xs[c]-xs[f])*(k-f)
wins=[e for e in EV if e['result']=='win']
rows=[]
for e in wins:
    r=base_of(e)
    if r is None: continue
    d,ei,base=r
    ri=DI.get(e['resolve_date'])
    if ri is None: continue
    ex=base*(1+e['gain_at_resolve_pct']/100.0)
    rows.append((e,d,ri,ex,base))
print('승리 추적 %d / %d'%(len(rows),len(wins)))
print('데이터 마지막일 %s'%dates[-1])
for H in (20,40,60):
    ends=[];mfes=[];maes=[];ex_abs=[]
    for e,d,ri,ex,base in rows:
        end=ri+H
        if end>=N: continue
        seg=range(ri+1,end+1)
        a=[d['adj'][i] for i in seg if d['adj'][i]]
        hi=[d['adjhi'][i] for i in seg if d['adjhi'][i]]
        lo=[d['adjlo'][i] for i in seg if d['adjlo'][i]]
        if not a or not hi: continue
        ends.append(a[-1]/ex*100-100); mfes.append(max(hi)/ex*100-100); maes.append(min(lo)/ex*100-100)
        ex_abs.append(max(hi)/base*100-100)
    print('=== H=%d거래일  n=%d'%(H,len(ends)))
    print(' [익절가 대비 MFE]  중앙 %+.1f%%  Q3 %+.1f%%  P90 %+.1f%%  평균 %+.1f%%  P95 %+.1f%%'%(st.median(mfes),q(mfes,.75),q(mfes,.90),st.mean(mfes),q(mfes,.95)))
    print(' [익절가 대비 H일후 종가] 중앙 %+.1f%%  평균 %+.1f%%  Q1 %+.1f  Q3 %+.1f  플러스 %.0f%%'%(st.median(ends),st.mean(ends),q(ends,.25),q(ends,.75),100*sum(1 for x in ends if x>0)/len(ends)))
    print(' [익절가 대비 MAE]  중앙 %+.1f%%  Q1 %+.1f%%  P10 %+.1f%%'%(st.median(maes),q(maes,.25),q(maes,.10)))
    print(' MFE>+10%% %.0f%% / >+20%% %.0f%% / >+50%% %.0f%%'%(100*sum(1 for x in mfes if x>10)/len(mfes),100*sum(1 for x in mfes if x>20)/len(mfes),100*sum(1 for x in mfes if x>50)/len(mfes)))
    print(' [진입가 대비 총 MFE(익절후 구간)] 중앙 %+.1f%%  P90 %+.1f%%'%(st.median(ex_abs),q(ex_abs,.90)))
