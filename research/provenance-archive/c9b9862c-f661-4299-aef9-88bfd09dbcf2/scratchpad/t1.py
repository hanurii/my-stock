import json,pickle,sys,statistics as st
sys.stdout.reconfigure(encoding='utf-8')
ROOT='C:/Users/hanul/playground/my-stock'
SC='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad'
P=pickle.load(open(SC+'/px.pkl','rb'))
dates=P['dates']; data=P['data']; DI={d:i for i,d in enumerate(dates)}
ev=json.load(open(ROOT+'/public/data/backtest-volatility-pilot.json',encoding='utf-8'))['events']
wins=[e for e in ev if e['result']=='win']
N=len(dates)

def q(xs,p):
    xs=sorted(xs); k=(len(xs)-1)*p; f=int(k); c=min(f+1,len(xs)-1)
    return xs[f]+(xs[c]-xs[f])*(k-f)

rows=[]
for e in wins:
    d=data.get(e['code']); ei=DI.get(e['entry_date']); ri=DI.get(e['resolve_date'])
    if d is None or ei is None or ri is None: rows.append(None); continue
    cl=d['cl'][ei]; a=d['adj'][ei]
    if not cl or not a: rows.append(None); continue
    base=a*e['entry_price']/cl
    exit_adj=base*(1+e['gain_at_resolve_pct']/100.0)
    r={'e':e,'ri':ri,'exit':exit_adj,'d':d}
    rows.append(r)
rows=[r for r in rows if r]
print('wins tracked', len(rows), '/', len(wins))
print('trading days available after last date:', dates[-1])

for H in (20,40,60):
    ends=[];mfes=[];maes=[]
    for r in rows:
        hi_end=r['ri']+H
        if hi_end>=N: continue
        d=r['d']; ex=r['exit']
        seg=[i for i in range(r['ri']+1,hi_end+1)]
        adjs=[d['adj'][i] for i in seg if d['adj'][i]]
        his=[d['adjhi'][i] for i in seg if d['adjhi'][i]]
        los=[d['adjlo'][i] for i in seg if d['adjlo'][i]]
        if not adjs or not his: continue
        ends.append(adjs[-1]/ex*100-100)
        mfes.append(max(his)/ex*100-100)
        maes.append(min(los)/ex*100-100)
    print('--- H=%d거래일 (n=%d, 완주 가능한 승자만)'%(H,len(ends)))
    print('   익절가 대비 H일후 종가 수익률: 중앙 %+.2f%%  평균 %+.2f%%  Q1 %+.2f  Q3 %+.2f  P90 %+.2f  플러스비율 %.1f%%'%(
        st.median(ends),st.mean(ends),q(ends,.25),q(ends,.75),q(ends,.90),100*sum(1 for x in ends if x>0)/len(ends)))
    print('   익절가 대비 MFE(최대상승): 중앙 %+.2f%%  평균 %+.2f%%  Q3 %+.2f  P90 %+.2f  P95 %+.2f  최대 %+.2f'%(
        st.median(mfes),st.mean(mfes),q(mfes,.75),q(mfes,.90),q(mfes,.95),max(mfes)))
    print('   익절가 대비 MAE(최대하락): 중앙 %+.2f%%  Q1 %+.2f  P10 %+.2f'%(st.median(maes),q(maes,.25),q(maes,.10)))
    print('   MFE>+10%% 비율 %.1f%%, >+20%% %.1f%%, >+50%% %.1f%%'%(
        100*sum(1 for x in mfes if x>10)/len(mfes),100*sum(1 for x in mfes if x>20)/len(mfes),100*sum(1 for x in mfes if x>50)/len(mfes)))
