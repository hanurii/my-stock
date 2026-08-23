# -*- coding: utf-8 -*-
"""market(KOSPI/KOSDAQ) 선택 규칙 같은날(within-date) 검정."""
import json, random, statistics
from collections import defaultdict, Counter

random.seed(20260822)
PATH = r"C:/Users/hanul/playground/my-stock/public/data/backtest-volatility-pilot.json"
d = json.load(open(PATH, encoding='utf-8'))
ev = d['events']
print("total events:", len(ev))
print("result counts:", Counter(e['result'] for e in ev))

res = [e for e in ev if e['result'] in ('win', 'loss')]
print("resolved (win/loss):", len(res))
print("resolved market counts:", Counter(e['market'] for e in res))
print("overall winrate:", round(100*sum(e['result']=='win' for e in res)/len(res), 2))
for m in ('KOSPI','KOSDAQ'):
    sub=[e for e in res if e['market']==m]
    print(f"  POOLED(무효,참고만) {m}: n={len(sub)} win%={100*sum(x['result']=='win' for x in sub)/len(sub):.2f}")

# ---- 1) entry_date 별 그룹 ----
byday = defaultdict(list)
for e in res:
    byday[e['entry_date']].append(e)

all_days = sorted(byday)
d3 = [k for k in all_days if len(byday[k]) >= 3]
d3both = [k for k in d3 if any(e['market']=='KOSPI' for e in byday[k]) and any(e['market']=='KOSDAQ' for e in byday[k])]
print(f"\ndates total={len(all_days)}  with>=3 cands={len(d3)}  with>=3 AND both markets={len(d3both)}")
print("trades covered on those days:", sum(len(byday[k]) for k in d3both))

W = lambda e: 1.0 if e['result']=='win' else 0.0

def exp_pick2(pref, cands):
    """pref 시장을 우선해 2개 고를 때의 기대 승수(0~2). 동순위는 무작위 → 기대값 해석."""
    A = [e for e in cands if e['market']==pref]
    B = [e for e in cands if e['market']!=pref]
    if len(A) >= 2:
        return 2*sum(map(W,A))/len(A)
    if len(A) == 1:
        return W(A[0]) + (sum(map(W,B))/len(B) if B else 0.0)
    return 2*sum(map(W,B))/len(B)

rows=[]
for k in d3both:
    c = byday[k]
    p_all = sum(map(W,c))/len(c)          # 무작위 2개 기대 승률
    e_kospi  = exp_pick2('KOSPI',  c)/2   # KOSPI 우선 규칙 기대 승률
    e_kosdaq = exp_pick2('KOSDAQ', c)/2
    nk = sum(1 for e in c if e['market']=='KOSPI')
    rows.append(dict(date=k, n=len(c), nk=nk, nd=len(c)-nk, p_all=p_all,
                     kospi=e_kospi, kosdaq=e_kosdaq))

n_days = len(rows)
def avg(f): return sum(f(r) for r in rows)/n_days
# 날짜 동일가중(하루 2매매씩 = 실제 사용자 상황)
rate_rand   = avg(lambda r: r['p_all'])
rate_kospi  = avg(lambda r: r['kospi'])
rate_kosdaq = avg(lambda r: r['kosdaq'])
print(f"\n=== 날짜 동일가중 기대승률 (n_days={n_days}, 매매 {2*n_days}건) ===")
print(f"  KOSPI 우선 2개 : {100*rate_kospi:.2f}%")
print(f"  무작위   2개   : {100*rate_rand:.2f}%")
print(f"  KOSDAQ 우선 2개: {100*rate_kosdaq:.2f}%")

# ---- 3a) 부호검정 ----
def signtest(key):
    pos = sum(1 for r in rows if r[key] > r['p_all'] + 1e-12)
    neg = sum(1 for r in rows if r[key] < r['p_all'] - 1e-12)
    tie = n_days - pos - neg
    n = pos + neg
    # 양측 이항검정 p
    from math import comb
    if n == 0: return pos, neg, tie, 1.0
    k = min(pos, neg)
    p = 2*sum(comb(n,i) for i in range(0, k+1))/2**n
    return pos, neg, tie, min(1.0, p)

for key,label in (('kospi','KOSPI우선'), ('kosdaq','KOSDAQ우선')):
    pos,neg,tie,p = signtest(key)
    print(f"부호검정 {label} vs 무작위: 이긴날 {pos} / 진날 {neg} / 무승부 {tie}  p={p:.4f}")

# ---- 3b) 무작위 2개 뽑기 2000회 부트스트랩(랜덤화 검정) ----
B = 2000
def draw2(pref, c):
    A=[e for e in c if e['market']==pref]; Bm=[e for e in c if e['market']!=pref]
    if len(A)>=2: pick=random.sample(A,2)
    elif len(A)==1: pick=[A[0], random.choice(Bm)]
    else: pick=random.sample(Bm,2)
    return sum(map(W,pick))

rand_dist=[]; kospi_dist=[]; kosdaq_dist=[]
for _ in range(B):
    tot_r=tot_k=tot_d=0
    for r in rows:
        c=byday[r['date']]
        tot_r += sum(map(W, random.sample(c,2)))
        tot_k += draw2('KOSPI', c)
        tot_d += draw2('KOSDAQ', c)
    rand_dist.append(tot_r/(2*n_days))
    kospi_dist.append(tot_k/(2*n_days))
    kosdaq_dist.append(tot_d/(2*n_days))

rand_dist.sort()
def pval(obs):
    ge = sum(1 for x in rand_dist if x >= obs - 1e-12)/B
    le = sum(1 for x in rand_dist if x <= obs + 1e-12)/B
    return min(1.0, 2*min(ge,le))
print(f"\n무작위 2개 분포(B={B}): 평균 {100*statistics.mean(rand_dist):.2f}%  sd {100*statistics.pstdev(rand_dist):.2f}%p"
      f"  2.5~97.5% [{100*rand_dist[int(.025*B)]:.2f}, {100*rand_dist[int(.975*B)]:.2f}]")
print(f"  KOSPI 우선 관측 {100*rate_kospi:.2f}% → 양측 p={pval(rate_kospi):.4f}  (시뮬평균 {100*statistics.mean(kospi_dist):.2f}%)")
print(f"  KOSDAQ우선 관측 {100*rate_kosdaq:.2f}% → 양측 p={pval(rate_kosdaq):.4f}  (시뮬평균 {100*statistics.mean(kosdaq_dist):.2f}%)")

# ---- 보조: 같은날 KOSPI vs KOSDAQ 승률 직접 짝비교 ----
diffs=[]
for k in d3both:
    c=byday[k]
    K=[e for e in c if e['market']=='KOSPI']; D=[e for e in c if e['market']=='KOSDAQ']
    diffs.append(sum(map(W,K))/len(K) - sum(map(W,D))/len(D))
pos=sum(1 for x in diffs if x>1e-12); neg=sum(1 for x in diffs if x<-1e-12); tie=len(diffs)-pos-neg
from math import comb
n=pos+neg; kk=min(pos,neg)
psign = min(1.0, 2*sum(comb(n,i) for i in range(0,kk+1))/2**n) if n else 1.0
print(f"\n같은날 KOSPI승률 - KOSDAQ승률: 평균 {100*statistics.mean(diffs):+.2f}%p  "
      f"KOSPI우세 {pos}일 / KOSDAQ우세 {neg}일 / 동률 {tie}일  부호검정 p={psign:.4f}")

# 같은날 한정 시장별 pooled
Kn=[e for k in d3both for e in byday[k] if e['market']=='KOSPI']
Dn=[e for k in d3both for e in byday[k] if e['market']=='KOSDAQ']
print(f"  (같은날 한정 pooled) KOSPI n={len(Kn)} win%={100*sum(map(W,Kn))/len(Kn):.2f} | "
      f"KOSDAQ n={len(Dn)} win%={100*sum(map(W,Dn))/len(Dn):.2f}")

# 하루 후보 구성 분포
print("\n하루 후보수 분포(대상일):", Counter(r['n'] for r in rows))
print("KOSPI 후보수 분포:", Counter(r['nk'] for r in rows))
print("KOSPI 2개 이상인 날:", sum(1 for r in rows if r['nk']>=2), "/", n_days)
