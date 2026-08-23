import json, os, collections, statistics as st
import numpy as np
from scipy import stats
SCR = r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
rows = json.load(open(os.path.join(SCR,'joined.json'),encoding='utf-8'))
res=[r for r in rows if r['outcome'] in ('stop','target')]
print('결착',len(res),'고유종목',len(set(r['code'] for r in res)))

# 1) all_pass vs gate_near score
print('\n[1] all_pass / gate_near 별 score & 결과')
for key in [True,False]:
    b=[r for r in res if r['cand_all_pass']==key]
    if not b: continue
    sc=[r['gm_score'] for r in b]
    print(' all_pass=%s n=%d  score med %.1f (min %.1f max %.1f)  손절률 %.1f%%'%(
        key,len(b),np.median(sc),min(sc),max(sc),100*sum(1 for r in b if r['outcome']=='stop')/len(b)))
for key in [True,False,None]:
    b=[r for r in res if r.get('gate_near')==key]
    if not b: continue
    sc=[r['gm_score'] for r in b]
    print(' gate_near=%s n=%d  score med %.1f  손절률 %.1f%%'%(key,len(b),np.median(sc),
        100*sum(1 for r in b if r['outcome']=='stop')/len(b)))

# 2) 월별 기저율 (시장 국면 통제)
print('\n[2] 추천월별 결착')
for m in ['2026-07','2026-08']:
    b=[r for r in res if r['date'].startswith(m)]
    print('  %s n=%d 손절률 %.1f%% score med %.1f'%(m,len(b),100*sum(1 for r in b if r['outcome']=='stop')/len(b),np.median([r['gm_score'] for r in b])))
# 주별
print('  주별:')
for wk in sorted(set(r['date'][:7]+'-W'+str((int(r['date'][8:10])-1)//7+1) for r in res)):
    b=[r for r in res if r['date'][:7]+'-W'+str((int(r['date'][8:10])-1)//7+1)==wk]
    print('   %s n=%3d 손절%.0f%% score med %.0f'%(wk,len(b),100*sum(1 for r in b if r['outcome']=='stop')/len(b),np.median([r['gm_score'] for r in b])))

# 3) all_pass=True 만
ap=[r for r in res if r['cand_all_pass']]
print('\n[3] all_pass=True 만 (n=%d, 고유 %d)'%(len(ap),len(set(r['code'] for r in ap))))
sc=[r['gm_score'] for r in ap]; sf=[1 if r['outcome']=='stop' else 0 for r in ap]
print('  Spearman score vs 손절 rho=%.4f p=%.4f'%(stats.spearmanr(sc,sf).statistic,stats.spearmanr(sc,sf).pvalue))
for lo in range(0,100,10):
    b=[r for r in ap if lo<=r['gm_score']<(lo+10 if lo<90 else 101)]
    if b: print('   %3d-%3d n=%3d 손절 %.1f%% 목표 %.1f%% cur중 %.1f%% mg중 %.1f%%'%(lo,lo+10,len(b),
        100*sum(1 for r in b if r['outcome']=='stop')/len(b),100*sum(1 for r in b if r['outcome']=='target')/len(b),
        st.median([r['cur_ret'] for r in b]), st.median([r['max_gain'] for r in b])))

# 4) 종목 클러스터 순열검정 (같은 종목 반복 = 독립 아님)
print('\n[4] 종목단위 순열검정 (cut=80, 전체표본)')
def stat_cut(rs,cut):
    lo=[r for r in rs if r['gm_score']<cut]; hi=[r for r in rs if r['gm_score']>=cut]
    if not lo or not hi: return 0
    return sum(1 for r in lo if r['outcome']=='stop')/len(lo) - sum(1 for r in hi if r['outcome']=='stop')/len(hi)
obs=stat_cut(res,80); print('  관측 차이 %+.1f%%p'%(obs*100))
# 종목 단위로 outcome 블록을 섞음
codes=sorted(set(r['code'] for r in res))
byc={c:[r for r in res if r['code']==c] for c in codes}
rng=np.random.default_rng(7); cnt=0; N=5000
for _ in range(N):
    perm=rng.permutation(len(codes))
    newrows=[]
    for i,c in enumerate(codes):
        src=byc[codes[perm[i]]]
        for j,r in enumerate(byc[c]):
            rr=dict(r); rr['outcome']=src[j%len(src)]['outcome']; newrows.append(rr)
    if abs(stat_cut(newrows,80))>=abs(obs): cnt+=1
print('  종목블록 순열 양측 p=%.4f (%d/%d)'%(cnt/N,cnt,N))
print('  ※ cut 19개 스캔 → Bonferroni 보정 p = %.3f (0.036 x 19)'%min(1,0.036*19))

# 5) 조건별 여유 마진이 예측하나 — per_condition 재계산 필요 → tightest 조건 분포만
print('\n[5] 가장 빡빡한 조건별')
c=collections.Counter(r['tightest_label'] for r in res)
for k,v in c.most_common():
    b=[r for r in res if r['tightest_label']==k]
    print('  %-14s n=%3d 손절 %.1f%% score med %.1f'%(k,v,100*sum(1 for x in b if x['outcome']=='stop')/v,np.median([x['gm_score'] for x in b])))

# 6) 해결 속도 편향
print('\n[6] score 3분위별 결착속도/미결착 비율')
allr=[r for r in rows if r['outcome'] in ('stop','target','open')]
q=np.percentile([r['gm_score'] for r in allr],[33.3,66.7]); print('  분위 경계',np.round(q,1))
for i,(lo,hi) in enumerate([(-1,q[0]),(q[0],q[1]),(q[1],101)]):
    b=[r for r in allr if lo<r['gm_score']<=hi]
    rb=[r for r in b if r['outcome']!='open']
    print('  Q%d n=%3d 결착률 %.0f%% 결착일수중앙 %s 손절률(결착중) %.1f%%'%(i+1,len(b),100*len(rb)/len(b),
        st.median([r['days'] for r in rb]) if rb else None,
        100*sum(1 for r in rb if r['outcome']=='stop')/len(rb) if rb else 0))

# 7) 초안 경계 3구간 검정
print('\n[7] 초안 경계(<20 / 20-50 / >=50) 검정')
for label,f in [('전체',res),('첫등장',None)]:
    pass
def three(rs,tag):
    g={'🔴<20':[r for r in rs if r['gm_score']<20],'🟡20-50':[r for r in rs if 20<=r['gm_score']<50],'🟢>=50':[r for r in rs if r['gm_score']>=50]}
    print(' ',tag)
    tab=[]
    for k,b in g.items():
        if not b: continue
        s=sum(1 for r in b if r['outcome']=='stop')
        print('    %-8s n=%3d 손절 %.1f%% 목표 %.1f%% cur중 %+.2f%%'%(k,len(b),100*s/len(b),100*(len(b)-s)/len(b),st.median([r['cur_ret'] for r in b])))
        tab.append([s,len(b)-s])
    if len(tab)==3:
        chi=stats.chi2_contingency(np.array(tab))
        print('    카이제곱 p=%.4f'%chi.pvalue)
three(res,'전체 항목')
seen=set(); firsts=[]
for r in sorted(rows,key=lambda r:(r['date'],r['code'])):
    if r['code'] in seen: continue
    seen.add(r['code']); firsts.append(r)
three([r for r in firsts if r['outcome'] in ('stop','target')],'첫 등장만')
