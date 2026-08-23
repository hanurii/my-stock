# -*- coding: utf-8 -*-
"""과제 C-2: 더 세밀한 국면 잣대 탐색 (4분위 + 날블록 순열검정)"""
import sys, json, math, random
sys.path.insert(0, r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad")
from daytable import build

rows = build()
res = [r for r in rows if r['nres']>0]
SPLIT = '2026-03-25'   # 진입일 전후반 분할

METRICS = [
 ('dist_ma20','지수 20일선 이격(%)'),
 ('slope_ma20_5','20일선 5일 기울기(%)'),
 ('slope_ma20_10','20일선 10일 기울기(%)'),
 ('ret1','지수 전일 수익률(%)'),
 ('ret5','지수 5일 수익률(%)'),
 ('ret10','지수 10일 수익률(%)'),
 ('ret20','지수 20일 수익률(%)'),
 ('days_since_flip','국면 전환 후 경과일'),
 ('pct_above200','200일선 위 종목 비율(%)'),
 ('pct_nh52','52주 신고가 종목 비율(%)'),
 ('d_above200_5','200일선위 비율 5일 변화(%p)'),
 ('d_nh52_5','신고가 비율 5일 변화(%p)'),
 ('ad','그날 상승종목 비율(%)'),
 ('ad_liq','상승비율(거래대금5억+)(%)'),
 ('ad5','상승비율 5일 누적(%)'),
 ('ad10','상승비율 10일 누적(%)'),
 ('n_candidates','그날 후보 수'),
 ('n_entered','그날 진입 수'),
]

def quartiles(sub, key, q=4):
    vals = sorted(r[key] for r in sub if r.get(key) is not None)
    n=len(vals)
    cuts = [vals[int(round(n*i/q))-1 if int(round(n*i/q))>0 else 0] for i in range(1,q)]
    def bucket(v):
        for i,c in enumerate(cuts):
            if v<=c: return i
        return q-1
    out=[]
    for i in range(q):
        g=[r for r in sub if r.get(key) is not None and bucket(r[key])==i]
        w=sum(r['w'] for r in g); l=sum(r['l'] for r in g)
        rets=[e['gain_at_resolve_pct'] for r in g for e in r['events'] if e.get('gain_at_resolve_pct') is not None]
        out.append(dict(i=i, days=len(g), w=w, l=l, n=w+l,
                        wr=100*w/(w+l) if w+l else None,
                        ev=sum(rets)/len(rets) if rets else None, nret=len(rets),
                        lo=min((r[key] for r in g), default=None), hi=max((r[key] for r in g), default=None)))
    return out, cuts

def stat_corr(sub, key):
    """거래 단위: 그날 지표의 순위 vs 승패(1/0) 상관"""
    pairs=[(r[key], r['w'], r['l']) for r in sub if r.get(key) is not None]
    # 날 순위
    order=sorted(range(len(pairs)), key=lambda i:pairs[i][0])
    rank=[0]*len(pairs)
    for rr,i in enumerate(order): rank[i]=rr
    xs=[];ys=[]
    for i,(v,w,l) in enumerate(pairs):
        for _ in range(w): xs.append(rank[i]); ys.append(1.0)
        for _ in range(l): xs.append(rank[i]); ys.append(0.0)
    n=len(xs)
    if n<10: return 0.0
    mx=sum(xs)/n; my=sum(ys)/n
    num=sum((a-mx)*(b-my) for a,b in zip(xs,ys))
    dx=math.sqrt(sum((a-mx)**2 for a in xs)); dy=math.sqrt(sum((b-my)**2 for b in ys))
    return num/(dx*dy) if dx and dy else 0.0

def perm_p(sub, key, reps=5000, seed=7):
    """날 블록 순열: 각 날의 (승,패) 묶음은 그대로 두고 지표 값만 날들 사이에서 섞는다."""
    rnd=random.Random(seed)
    vals=[r[key] for r in sub if r.get(key) is not None]
    days=[r for r in sub if r.get(key) is not None]
    obs=stat_corr(days,key)
    cnt=0
    base=[(r['w'],r['l']) for r in days]
    for _ in range(reps):
        sh=vals[:]; rnd.shuffle(sh)
        fake=[{key:sh[i],'w':base[i][0],'l':base[i][1]} for i in range(len(days))]
        s=stat_corr(fake,key)
        if abs(s)>=abs(obs): cnt+=1
    return obs, (cnt+1)/(reps+1)

def run(sub, label, reps=5000):
    print(f"\n===== {label} (날 {len(sub)}, 결착 {sum(r['nres'] for r in sub)}건, 승률 {100*sum(r['w'] for r in sub)/sum(r['nres'] for r in sub):.1f}%) =====")
    out=[]
    for key,name in METRICS:
        if sum(1 for r in sub if r.get(key) is not None) < 20: continue
        qs,cuts = quartiles(sub,key)
        obs,pv = perm_p(sub,key,reps=reps)
        wrs=[q['wr'] for q in qs]
        mono = all(wrs[i] is not None and wrs[i+1] is not None and wrs[i]<=wrs[i+1] for i in range(3)) or \
               all(wrs[i] is not None and wrs[i+1] is not None and wrs[i]>=wrs[i+1] for i in range(3))
        out.append((pv,key,name,qs,obs,mono,cuts))
    out.sort()
    for pv,key,name,qs,obs,mono,cuts in out:
        s=" · ".join(f"Q{q['i']+1}[{q['lo']:.1f}~{q['hi']:.1f}] {q['wr']:.0f}%({q['n']})/{q['ev']:+.1f}%" if q['wr'] is not None else f"Q{q['i']+1} -" for q in qs)
        print(f"{name:28s} p={pv:.4f} r={obs:+.3f} {'단조' if mono else '    '} | {s}")
    return out

full = run(res, "전체 146일")
up   = run([r for r in res if r['up']], "상승국면만")

json.dump({'metrics':[m[0] for m in METRICS]}, open(r"C:\Users\hanul\AppData\Local\Temp\claude\C--Users-hanul-playground-my-stock\c9b9862c-f661-4299-aef9-88bfd09dbcf2\scratchpad\_t2.json",'w'))
