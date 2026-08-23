# -*- coding: utf-8 -*-
"""혼잡도(그날 돌파 수) 효과가 국면 착시인지 확인 + 날 블록 부트스트랩."""
import random, math, sys
from collections import defaultdict
from engine import ROWS, BYDAY, DAYS
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
UPD=[d for d in DAYS if BYDAY[d][0]["up"]]; DND=[d for d in DAYS if not BYDAY[d][0]["up"]]
print("■ 국면 안에서의 혼잡도 효과")
for lab,ds in [("상승국면",UPD),("조정국면",DND)]:
    for lo,hi,l2 in [(1,4,'1~4건'),(5,9,'5~9건'),(10,99,'10건+')]:
        g=[r for d in ds if lo<=len(BYDAY[d])<=hi for r in BYDAY[d]]
        if not g: continue
        w=[r["win"] for r in g if r["win"] is not None]
        nd=sum(1 for d in ds if lo<=len(BYDAY[d])<=hi)
        print(f"  {lab} {l2:<6} {nd:>3}일 {len(g):>3}건 기대 {sum(r['ret'] for r in g)/len(g):>+6.2f}% 승률 {100*sum(w)/len(w):>5.1f}%")
print("\n■ 혼잡도 10건+ vs 나머지 — 날 블록 부트스트랩(2000회, 날 단위 재표집)")
A=[d for d in DAYS if len(BYDAY[d])>=10]; B=[d for d in DAYS if len(BYDAY[d])<10]
def m(ds, sample=None):
    src = sample if sample else ds
    g=[r for d in src for r in BYDAY[d]]
    return sum(r["ret"] for r in g)/len(g)
obs=m(A)-m(B); rng=random.Random(4); out=[]
for _ in range(2000):
    sa=[A[rng.randrange(len(A))] for _ in A]; sb=[B[rng.randrange(len(B))] for _ in B]
    out.append(m(None,sa)-m(None,sb))
out.sort()
print(f"  관측 차이 {obs:+.2f}%p  95%CI [{out[50]:+.2f},{out[1949]:+.2f}]%p  차이<=0 비율 {sum(1 for x in out if x<=0)/2000:.3f}")
print(f"  (10건+ 날은 9일뿐 — 날 단위 표본 9개, 사실상 근거 부족)")
print("\n■ 10건+ 9일 각각")
for d in A:
    g=BYDAY[d]; w=[r["win"] for r in g if r["win"] is not None]
    print(f"  {d} {len(g):>2}건 {'상승' if g[0]['up'] else '조정'} 승 {sum(w)}/{len(w)} 기대 {sum(r['ret'] for r in g)/len(g):+.1f}%")
