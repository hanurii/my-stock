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
    r=dict(e); r.pop('resolved'); r.update({'gm':m['score'],'pct':m['pct'],'margin':m['margin'],
        'tight':m['tightest'],'label':m['label'],'all_pass':m['all_pass'],'rs':m['rs'],'ret252':m['ret252'],
        'outcome':res['outcome'],'cur':res['cur_ret_pct'],'mg':res['max_gain_pct'],'days':res['days']})
    rows.append(r)
print('결착 n=',len(rows),'고유',len(set(r['code'] for r in rows)))
LAB={'1':'①종가>150/200MA','2':'②150>200MA','3':'③200MA상승','4':'④50>150/200MA','5':'⑤종가>50MA','6':'⑥52주저가+30%','7':'⑦52주고가-25%','8':'⑧RS'}
stop=[1 if r['outcome']=='stop' else 0 for r in rows]
print('\n[조건별 여유(원단위 %p 마진) → 손절/수익 상관]')
print('%-16s %8s %8s %8s %8s %8s'%('조건','rho(손절)','p','rho(cur)','p','중앙마진'))
for k in '12345678':
    v=[r['margin'][k] for r in rows]
    a=stats.spearmanr(v,stop); b=stats.spearmanr(v,[r['cur'] for r in rows])
    print('%-16s %8.3f %8.4f %8.3f %8.4f %8.1f'%(LAB[k],a.statistic,a.pvalue,b.statistic,b.pvalue,np.median(v)))
print('\n[대안 종합점수]')
alts={'min(현행 score)':[r['gm'] for r in rows],
      '평균 pct':[np.mean(list(r['pct'].values())) for r in rows],
      '중앙 pct':[np.median(list(r['pct'].values())) for r in rows],
      '2번째로 빡빡한 pct':[sorted(r['pct'].values())[1] for r in rows],
      '빡빡한 조건 개수(pct<20)':[sum(1 for v in r['pct'].values() if v<20) for r in rows],
      'RS':[r['rs'] for r in rows],
      '252일 상승률':[r['ret252'] or 0 for r in rows]}
for k,v in alts.items():
    a=stats.spearmanr(v,stop); b=stats.spearmanr(v,[r['cur'] for r in rows]); c=stats.spearmanr(v,[r['mg'] for r in rows])
    print(' %-22s rho손절=%+.3f p=%.4f | rho현재수익=%+.3f p=%.4f | rho maxgain=%+.3f p=%.4f'%(k,a.statistic,a.pvalue,b.statistic,b.pvalue,c.statistic,c.pvalue))
print('\n[⑥ 52주저가 대비 상승폭 = 사전 상승폭] 4분위')
v=[r['margin']['6']+30 for r in rows]
qs=np.percentile(v,[25,50,75])
for i,(lo,hi) in enumerate([(-1e9,qs[0]),(qs[0],qs[1]),(qs[1],qs[2]),(qs[2],1e9)]):
    b=[r for r,x in zip(rows,v) if lo<x<=hi]
    print('  Q%d (저가대비 %.0f~%.0f%%) n=%3d 손절 %.1f%% 목표 %.1f%% mg중 %.1f%%'%(i+1,max(lo,min(v)),min(hi,max(v)),len(b),
        100*sum(1 for r in b if r['outcome']=='stop')/len(b),100*sum(1 for r in b if r['outcome']=='target')/len(b),st.median([r['mg'] for r in b])))
print('\n[⑦ 52주고가와의 거리] 4분위 (margin7-25 = 고가대비 %, 0에 가까울수록 신고가 근처)')
v=[r['margin']['7']-25 for r in rows]
qs=np.percentile(v,[25,50,75])
for i,(lo,hi) in enumerate([(-1e9,qs[0]),(qs[0],qs[1]),(qs[1],qs[2]),(qs[2],1e9)]):
    b=[r for r,x in zip(rows,v) if lo<x<=hi]
    print('  Q%d (고가대비 %.1f~%.1f%%) n=%3d 손절 %.1f%% 목표 %.1f%% mg중 %.1f%%'%(i+1,max(lo,min(v)),min(hi,max(v)),len(b),
        100*sum(1 for r in b if r['outcome']=='stop')/len(b),100*sum(1 for r in b if r['outcome']=='target')/len(b),st.median([r['mg'] for r in b])))
