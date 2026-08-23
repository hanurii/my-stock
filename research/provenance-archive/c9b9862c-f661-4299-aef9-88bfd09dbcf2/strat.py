import json, os, statistics as st, collections
import numpy as np
from scipy import stats
SCR=r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
REPO=r'C:\Users\hanul\playground\my-stock'
store=json.load(open(os.path.join(SCR,'percond.json'),encoding='utf-8'))
led=json.load(open(os.path.join(REPO,'public','data','sepa-buy-rec-ledger.json'),encoding='utf-8'))['entries']
rows=[]
for e in led:
    m=store.get(e['date'],{}).get(e['code'])
    if not m: continue
    res=e.get('resolved') or {}
    if res.get('outcome') not in ('stop','target'): continue
    rows.append({'date':e['date'],'code':e['code'],'name':e['name'],'gm':m['score'],'rs':m['rs'],
                 'ret252':m['ret252'] or 0,'m6':m['margin']['6']+30,'outcome':res['outcome'],
                 'cur':res['cur_ret_pct'],'mg':res['max_gain_pct'],'days':res['days'],'status':e.get('status')})
# sanity
tg=[r for r in rows if r['outcome']=='target']; sp=[r for r in rows if r['outcome']=='stop']
print('target: mg min %.1f, cur중 %.1f | stop: cur max %.1f, mg중 %.1f'%(min(r['mg'] for r in tg),st.median([r['cur'] for r in tg]),max(r['cur'] for r in sp),st.median([r['mg'] for r in sp])))
print('status 분포', collections.Counter(r['status'] for r in rows))

print('\n[날짜 층화] 같은 날 추천끼리만 비교 (시장국면 제거)')
def strat_test(key):
    # Mantel-Haenszel: median split within date
    a=b=c=d=0; diffs=[]
    for dt in sorted(set(r['date'] for r in rows)):
        g=[r for r in rows if r['date']==dt]
        if len(g)<4: continue
        vals=[r[key] for r in g]; mm=np.median(vals)
        lo=[r for r in g if r[key]<mm]; hi=[r for r in g if r[key]>=mm]
        if not lo or not hi: continue
        a+=sum(1 for r in hi if r['outcome']=='stop'); b+=sum(1 for r in hi if r['outcome']=='target')
        c+=sum(1 for r in lo if r['outcome']=='stop'); d+=sum(1 for r in lo if r['outcome']=='target')
        diffs.append(sum(1 for r in hi if r['outcome']=='stop')/len(hi)-sum(1 for r in lo if r['outcome']=='stop')/len(lo))
    p=stats.fisher_exact([[a,b],[c,d]])[1]
    print('  %-10s 상위절반 손절 %d/%d=%.1f%% vs 하위절반 %d/%d=%.1f%%  (풀링 Fisher p=%.4f, 날짜수 %d, 날짜별차이 평균 %+.1f%%p, 부호검정 p=%.3f)'%(
        key,a,a+b,100*a/(a+b),c,c+d,100*c/(c+d),p,len(diffs),100*np.mean(diffs),
        stats.binomtest(sum(1 for x in diffs if x>0),sum(1 for x in diffs if x!=0)).pvalue if sum(1 for x in diffs if x!=0)>0 else 1))
for k in ['gm','rs','ret252','m6']: strat_test(k)

print('\n[종목 클러스터 순열] ret252 / rs / m6 상관의 유의성 재검정')
codes=sorted(set(r['code'] for r in rows)); byc={c:[r for r in rows if r['code']==c] for c in codes}
stopf=[1 if r['outcome']=='stop' else 0 for r in rows]
rng=np.random.default_rng(11)
for key in ['gm','rs','ret252','m6']:
    obs=stats.spearmanr([r[key] for r in rows],stopf).statistic
    cnt=0;N=3000
    for _ in range(N):
        perm=rng.permutation(len(codes)); new=[]
        for i,cd in enumerate(codes):
            src=byc[codes[perm[i]]]
            for j,r in enumerate(byc[cd]): new.append(1 if src[j%len(src)]['outcome']=='stop' else 0)
        # rebuild aligned key list in same order
        keys=[r[key] for cd in codes for r in byc[cd]]
        if abs(stats.spearmanr(keys,new).statistic)>=abs(obs): cnt+=1
    print('  %-8s rho=%+.3f 종목블록순열 p=%.4f'%(key,obs,cnt/N))

print('\n[극단 확장 구간] 52주저가 대비 상승폭 임계')
for cut in [100,120,150,163,200,250,300]:
    hi=[r for r in rows if r['m6']>=cut]; lo=[r for r in rows if r['m6']<cut]
    if len(hi)<15: continue
    a=sum(1 for r in hi if r['outcome']=='stop'); b=sum(1 for r in lo if r['outcome']=='stop')
    p=stats.fisher_exact([[a,len(hi)-a],[b,len(lo)-b]])[1]
    print('  >=%4d%%: n=%3d 손절 %.1f%% | <: n=%3d 손절 %.1f%% 차이 %+.1f%%p Fisher p=%.4f 고유종목 %d'%(
        cut,len(hi),100*a/len(hi),len(lo),100*b/len(lo),100*(a/len(hi)-b/len(lo)),p,len(set(r['code'] for r in hi))))
