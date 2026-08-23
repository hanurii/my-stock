import json,os,numpy as np,sys,collections,random
sys.path.insert(0,'scripts')
from canslim_lib import ohlcv_matrix
SP = r'C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad'
C=json.load(open(os.path.join(SP,'clean.json'),encoding='utf-8'))
cache={}
def s_(c):
    if c not in cache: cache[c]=ohlcv_matrix.get_series(c)
    return cache[c]
for r in C:
    s=s_(r['code']); i=list(s['dates']).index(r['date'])
    r['raw10']=(s['closes'][i+10]/r['rec_price']-1)*100
    r['mfe10']=(max(s['highs'][i+1:i+11])/r['rec_price']-1)*100
vs=sorted(r['vol'] for r in C); q=[np.percentile(vs,p) for p in (25,50,75)]
def qi(v): return 0 if v<=q[0] else 1 if v<=q[1] else 2 if v<=q[2] else 3
print('변동성 컷',[round(x,2) for x in q])
print('\n[E] 변동성 4분위: 손절률 vs 순수보유수익 vs 목표도달률')
for i in range(4):
    g=[r for r in C if qi(r['vol'])==i]
    st=sum(1 for r in g if r['w10'][0]=='stop')/len(g)*100
    tg=sum(1 for r in g if r['w10'][0]=='target')/len(g)*100
    print(f'  Q{i+1} n={len(g):3d} 손절={st:5.1f}% 목표도달={tg:5.1f}% 규칙수익={np.mean([r["w10"][1] for r in g]):+6.2f}% '
          f'순수10일평균={np.mean([r["raw10"] for r in g]):+6.2f}% 중앙값={np.median([r["raw10"] for r in g]):+6.2f}% MFE={np.mean([r["mfe10"] for r in g]):+6.2f}%')

print('\n[F] 날짜 내부에서만 비교 (그날 시장 완전 통제)')
byd=collections.defaultdict(list)
for r in C: byd[r['date']].append(r)
def within_date(key, thr_fn):
    num=0;den=0
    for d,g in byd.items():
        if len(g)<6: continue
        med=np.median([key(r) for r in g])
        a=[r for r in g if key(r)>med]; b=[r for r in g if key(r)<=med]
        if len(a)<2 or len(b)<2: continue
        w=len(g)
        num+=w*(thr_fn(a)-thr_fn(b)); den+=w
    return num/den if den else float('nan')
sr=lambda g: sum(1 for r in g if r['w10'][0]=='stop')/len(g)*100
rr=lambda g: np.mean([r['raw10'] for r in g])
print(f'  변동성 상위-하위: 손절률차={within_date(lambda r:r["vol"],sr):+.1f}%p  순수수익차={within_date(lambda r:r["vol"],rr):+.2f}%p')
print(f'  종합점수 상위-하위: 손절률차={within_date(lambda r:r["score"],sr):+.1f}%p  순수수익차={within_date(lambda r:r["score"],rr):+.2f}%p')

print('\n[G] 기간 반분 안정성 (변동성 상위절반-하위절반 손절률차)')
for lab,f in [('7/01~7/22',lambda d: d<'2026-07-23'),('7/23~8/06',lambda d: d>='2026-07-23')]:
    g=[r for r in C if f(r['date'])]
    med=np.median([r['vol'] for r in g])
    a=[r for r in g if r['vol']>med]; b=[r for r in g if r['vol']<=med]
    print(f'  {lab}: n={len(g):3d} 손절률차={sr(a)-sr(b):+.1f}%p  순수수익차={rr(a)-rr(b):+.2f}%p')

print('\n[H] tightest 코호트 (오염제거 후)')
allsr=sr(C)
for k in '12345678':
    g=[r for r in C if r['tightest']==k]
    if not g: continue
    print(f'  {k}: n={len(g):3d} 종목={len(set(r["code"] for r in g)):2d} 손절={sr(g):5.1f}% (전체{allsr:.1f}%, 차{sr(g)-allsr:+.1f}%p) 목표={sum(1 for r in g if r["w10"][0]=="target")/len(g)*100:4.1f}% 중앙변동성={np.median([r["vol"] for r in g]):.2f}')

print('\n[I] 52주고가 거리 계단 (오염제거)')
for lo,hi,lab in [(-5,0,'-5~0%'),(-10,-5,'-10~-5%'),(-15,-10,'-15~-10%'),(-20,-15,'-20~-15%'),(-25,-20,'-25~-20%'),(-99,-25,'<-25%')]:
    g=[r for r in C if lo< (r['pct']['7']/100*20-25) <=hi]
    if g: print(f'  {lab:10s} n={len(g):3d} 손절={sr(g):5.1f}% 중앙변동성={np.median([r["vol"] for r in g]):.2f}')
a=[r for r in C if (r['pct']['7']/100*20-25)>-10]; b=[r for r in C if (r['pct']['7']/100*20-25)<=-10]
print(f'  묶음: -10%이내 n={len(a)} 손절={sr(a):.1f}% (중앙변동성 {np.median([r["vol"] for r in a]):.2f}) vs 더먼쪽 n={len(b)} 손절={sr(b):.1f}% (중앙변동성 {np.median([r["vol"] for r in b]):.2f})')
