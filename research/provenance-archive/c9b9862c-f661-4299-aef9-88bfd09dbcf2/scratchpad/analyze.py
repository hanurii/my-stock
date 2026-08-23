import json, os, collections, statistics as st
import numpy as np
from scipy import stats
SCR = r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
rows = json.load(open(os.path.join(SCR,'joined.json'),encoding='utf-8'))

def med(xs): return round(st.median(xs),2) if xs else None

def report(rs, title):
    print('='*70); print(title, ' 전체 n=',len(rs))
    res=[r for r in rs if r['outcome'] in ('stop','target')]
    print('결착 n=',len(res),' stop=',sum(1 for r in res if r['outcome']=='stop'),
          ' target=',sum(1 for r in res if r['outcome']=='target'),
          ' open=',sum(1 for r in rs if r['outcome']=='open'))
    sc=[r['gm_score'] for r in res]
    if sc:
        print('score 분포: min %.1f p25 %.1f med %.1f p75 %.1f max %.1f mean %.1f'%(
            min(sc),np.percentile(sc,25),np.percentile(sc,50),np.percentile(sc,75),max(sc),np.mean(sc)))
    print('%-10s %5s %8s %8s %10s %10s'%('구간','n','손절률','목표률','현재수익中','maxgain中'))
    binstat=[]
    for lo in range(0,100,10):
        hi=lo+10
        b=[r for r in res if (r['gm_score']>=lo and (r['gm_score']<hi if hi<100 else r['gm_score']<=100))]
        if not b:
            print('%-10s %5d %8s'%(f'{lo}-{hi}',0,'-')); binstat.append((lo,0,None,None)); continue
        sr=sum(1 for r in b if r['outcome']=='stop')/len(b)
        tr=sum(1 for r in b if r['outcome']=='target')/len(b)
        print('%-10s %5d %7.1f%% %7.1f%% %9.2f%% %9.2f%%'%(f'{lo}-{hi}',len(b),sr*100,tr*100,
              med([r['cur_ret'] for r in b]), med([r['max_gain'] for r in b])))
        binstat.append((lo,len(b),sr,tr))
    # spearman on binned stop-rate and on raw
    stopflag=[1 if r['outcome']=='stop' else 0 for r in res]
    sc2=[r['gm_score'] for r in res]
    sp=stats.spearmanr(sc2,stopflag); pr=stats.pointbiserialr(stopflag,sc2)
    print('\n[상관] score vs 손절(1/0): Spearman rho=%.4f p=%.4f | point-biserial r=%.4f p=%.4f'%(sp.statistic,sp.pvalue,pr.statistic,pr.pvalue))
    tgt=[1 if r['outcome']=='target' else 0 for r in res]
    sp2=stats.spearmanr(sc2,tgt); print('[상관] score vs 목표도달: rho=%.4f p=%.4f'%(sp2.statistic,sp2.pvalue))
    curall=[r['cur_ret'] for r in res]
    sp3=stats.spearmanr(sc2,curall); print('[상관] score vs 현재수익률: rho=%.4f p=%.4f'%(sp3.statistic,sp3.pvalue))
    sp4=stats.spearmanr(sc2,[r['max_gain'] for r in res]); print('[상관] score vs max_gain: rho=%.4f p=%.4f'%(sp4.statistic,sp4.pvalue))
    # 구간 손절률 단조성 (n>=1 구간만)
    bb=[(lo,n,sr) for lo,n,sr,tr in binstat if n>0]
    if len(bb)>2:
        r5=stats.spearmanr([b[0] for b in bb],[b[2] for b in bb])
        print('[단조성] 구간중심 vs 구간손절률 Spearman rho=%.3f p=%.4f (구간수 %d)'%(r5.statistic,r5.pvalue,len(bb)))
    # cutpoint scan
    print('\n[경계 후보 스캔] cut 미만 vs 이상')
    print('%-6s %6s %8s %6s %8s %9s %9s'%('cut','n<','손절<','n>=','손절>=','차이%p','Fisher p'))
    best=[]
    for cut in range(5,100,5):
        lo=[r for r in res if r['gm_score']<cut]; hi=[r for r in res if r['gm_score']>=cut]
        if len(lo)<10 or len(hi)<10: continue
        a=sum(1 for r in lo if r['outcome']=='stop'); b=sum(1 for r in hi if r['outcome']=='stop')
        p=stats.fisher_exact([[a,len(lo)-a],[b,len(hi)-b]])[1]
        d=(a/len(lo)-b/len(hi))*100
        print('%-6d %6d %7.1f%% %6d %7.1f%% %+8.1f %9.4f'%(cut,len(lo),a/len(lo)*100,len(hi),b/len(hi)*100,d,p))
        best.append((p,cut,d,len(lo),len(hi)))
    if best:
        best.sort(); print('최적(p최소) cut=%d 차이=%+.1f%%p p=%.4f (n<%d, n>=%d)'%(best[0][1],best[0][2],best[0][0],best[0][3],best[0][4]))
    return res

allres = report(rows,'[A] 전체 항목(중복 포함)')
# first appearance per code
seen=set(); firsts=[]
for r in sorted(rows,key=lambda r:(r['date'],r['code'])):
    if r['code'] in seen: continue
    seen.add(r['code']); firsts.append(r)
fres = report(firsts,'[B] 종목별 첫 등장만')
