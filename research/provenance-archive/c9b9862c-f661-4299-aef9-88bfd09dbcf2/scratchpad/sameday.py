import sys, json, math, random
sys.path.insert(0,'.')
from lib import *
from collections import defaultdict, Counter

d, ev = load()
R = resolved(ev)
print("resolved n =", len(R))
w=[e['gain_at_resolve_pct'] for e in R if e['result']=='win']
l=[e['gain_at_resolve_pct'] for e in R if e['result']=='loss']
import statistics as s
print("win mean %.2f med %.2f min %.2f max %.2f" % (s.mean(w),s.median(w),min(w),max(w)))
print("loss mean %.2f med %.2f min %.2f max %.2f" % (s.mean(l),s.median(l),min(l),max(l)))

def binom_p_two(k, n, p=0.5):
    if n==0: return 1.0
    def pmf(i): return math.comb(n,i)*p**i*(1-p)**(n-i)
    obs = pmf(k)
    tot = sum(pmf(i) for i in range(n+1) if pmf(i) <= obs*(1+1e-9))
    return min(1.0, tot)

def sameday(events, pred, label=""):
    """pred(e)->True(A)/False(B)/None(제외). 같은 스캔일에 A,B 둘 다 있는 날만."""
    byday = defaultdict(lambda: ([],[]))
    for e in events:
        v = pred(e)
        if v is None: continue
        byday[e['scan_date']][0 if v else 1].append(e)
    days=[]
    for dte,(A,B) in byday.items():
        if not A or not B: continue
        wa = 100*sum(1 for x in A if x['result']=='win')/len(A)
        wb = 100*sum(1 for x in B if x['result']=='win')/len(B)
        ra = sum(x['gain_at_resolve_pct'] for x in A)/len(A)
        rb = sum(x['gain_at_resolve_pct'] for x in B)/len(B)
        days.append((dte, wa-wb, ra-rb, len(A), len(B)))
    if not days:
        return dict(label=label, n_days=0)
    pos = sum(1 for x in days if x[1] > 0); neg = sum(1 for x in days if x[1] < 0); tie = sum(1 for x in days if x[1]==0)
    p = binom_p_two(pos, pos+neg)
    med = s.median(x[1] for x in days)
    medr = s.median(x[2] for x in days)
    nA=sum(x[3] for x in days); nB=sum(x[4] for x in days)
    # 전체 (같은날 제한 없는) 승률
    A=[e for e in events if pred(e) is True]; B=[e for e in events if pred(e) is False]
    wrA=wr(A); wrB=wr(B)
    return dict(label=label, n_days=len(days), pos=pos, neg=neg, tie=tie, p=p,
                med_wr_diff=med, med_ret_diff=medr, nA=nA, nB=nB,
                overall_A=wrA, overall_B=wrB)

def show(r):
    if r.get('n_days',0)==0:
        print(f"{r['label']:38s} | 비교가능일 0"); return
    print(f"{r['label']:38s} | 일수 {r['n_days']:3d} (A우세 {r['pos']:3d} / B우세 {r['neg']:3d} / 동률 {r['tie']:3d}) "
          f"p={r['p']:.3f} | 일중앙승률차 {r['med_wr_diff']:+.1f}%p 수익차 {r['med_ret_diff']:+.2f}%p | "
          f"A {r['overall_A'][0]:.1f}%(n{r['overall_A'][1]}) B {r['overall_B'][0]:.1f}%(n{r['overall_B'][1]})")

tests = []
# 패턴
tests.append(sameday(R, lambda e: e['pattern']=='VCP', "패턴 VCP vs 나머지"))
tests.append(sameday(R, lambda e: e['pattern']=='3C', "패턴 3C vs 나머지"))
# 시장
tests.append(sameday(R, lambda e: e['market']=='KOSPI', "시장 KOSPI vs KOSDAQ"))
# RS 여러 컷
for cut in (85, 88, 90, 92, 95):
    tests.append(sameday(R, lambda e,c=cut: e['rs']>=c, f"RS >= {cut}"))
# 거래대금
for cut in (10, 20, 30, 50, 100, 200):
    tests.append(sameday(R, lambda e,c=cut: e['turnover_eok']>=c, "거래대금 >= %d억" % cut))
# 가격대
buckets = sorted(set(e['price_bucket'] for e in R))
print("price buckets:", buckets)
for b in buckets:
    tests.append(sameday(R, lambda e,b=b: e['price_bucket']==b, f"가격대 {b} vs 나머지"))
# 진입 초과폭 (entry/pivot-1)
for cut in (0.5, 1.0, 2.0, 3.0):
    tests.append(sameday(R, lambda e,c=cut: e['overrun_pct']>=c, f"피벗초과진입 >= {cut}%"))
tests.append(sameday(R, lambda e: e['overrun_pct']<=0.01, "피벗 정확체결(초과 0%)"))
# 갭업
for cut in (0.0, 1.0, 2.0, 3.0):
    tests.append(sameday(R, lambda e,c=cut: e['gap_up_pct']>=c, f"갭업 >= {cut}%"))
# ATR (기각 확인용)
for cut in (5.0, 6.0, 7.0, 8.0):
    tests.append(sameday(R, lambda e,c=cut: e['atr_pct']<c, f"ATR < {cut}% (저변동)"))

for t in tests: show(t)
