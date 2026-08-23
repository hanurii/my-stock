# -*- coding: utf-8 -*-
from engine import *
from statistics import mean
from collections import defaultdict
import random
base=run_rule()
user=run_rule(tp=7.83, stop=-6.64)
d,p=paired_perm(user,base,iters=5000)
print(f"사용자행동근사(+7.83/-6.64) vs 현행(+20/-10): 차이 {d}%p/거래  종목블록순열 p={p} (5000회)")
a1=[x for x in user if x['entry_date']<SPLIT]; b1=[x for x in base if x['entry_date']<SPLIT]
a2=[x for x in user if x['entry_date']>=SPLIT]; b2=[x for x in base if x['entry_date']>=SPLIT]
print("  전반(~2026-03-24, n=%d):"%len(a1), paired_perm(a1,b1,iters=4000))
print("  후반(2026-03-25~, n=%d):"%len(a2), paired_perm(a2,b2,iters=4000))
# 종목 클러스터 부트스트랩 CI
blocks=defaultdict(list)
for a,b in zip(user,base): blocks[a["code"]].append(a["ret"]-b["ret"])
keys=list(blocks); rnd=random.Random(21); boots=[]
for _ in range(4000):
    samp=[blocks[keys[rnd.randrange(len(keys))]] for _ in keys]
    flat=[v for s in samp for v in s]
    boots.append(mean(flat))
boots.sort()
print(f"  종목 클러스터 부트스트랩 95%CI: [{boots[int(.025*4000)]:.2f}, {boots[int(.975*4000)]:.2f}] %p")
# 패턴별
for pat in ("VCP","3C","PP"):
    ua=[x for x,pp in zip(user,PATHS) if pp["pattern"]==pat]; ba=[x for x,pp in zip(base,PATHS) if pp["pattern"]==pat]
    if len(ua)<30: print(f"  {pat}: n={len(ua)} 표본부족"); continue
    print(f"  {pat} n={len(ua)}: 현행 {stats(ba)['avg']:.2f}% → 조기청산 {stats(ua)['avg']:.2f}%  차이 {paired_perm(ua,ba,iters=2000)}")
print()
# +8 익절 단독
u8=run_rule(tp=8.0)
print("조기익절 +8%(손절 -10 유지) vs 현행:", paired_perm(u8,base,iters=5000))
blocks=defaultdict(list)
for a,b in zip(u8,base): blocks[a["code"]].append(a["ret"]-b["ret"])
keys=list(blocks); rnd=random.Random(31); boots=[]
for _ in range(4000):
    samp=[blocks[keys[rnd.randrange(len(keys))]] for _ in keys]
    boots.append(mean([v for s in samp for v in s]))
boots.sort(); print(f"  95%CI [{boots[100]:.2f}, {boots[3900]:.2f}] %p")
