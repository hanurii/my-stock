# -*- coding: utf-8 -*-
import json, random, math, sys
from pathlib import Path
from collections import defaultdict
from engine import ROWS, BYDAY, DAYS, RULES, pick, pick_random, agg
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TIE_DRAWS = 200      # 동점 파단 평균
RAND_DRAWS = 500     # 무작위 기준선
PERM = 3000          # 같은날 선택 순열
SIGNFLIP = 5000      # 종목 블록 부호뒤집기

def binom_p(k, n):
    """양측 부호검정 p (정확)."""
    if n == 0: return 1.0
    c = lambda a,b: math.comb(a,b)
    tail = sum(c(n,i) for i in range(0, min(k, n-k)+1)) / 2**n
    return min(1.0, 2*tail)

def run(K, days, label):
    dsel = [d for d in days if len(BYDAY[d]) > K]      # 선택이 갈리는 날
    print(f"\n{'='*96}\n■ K={K}  {label}   선택이 갈리는 날 {len(dsel)}일 / 전체 {len(days)}일")
    # 전체 포트폴리오(모든 날, K까지) 무작위 기준선
    rng = random.Random(7)
    base_all=[]; base_sel=[]
    for _ in range(RAND_DRAWS):
        s_all=[]; s_sel=[]
        for d in days:
            p = pick_random(BYDAY[d], K, rng)
            s_all += p
            if d in dsel: s_sel += p
        base_all.append(agg(s_all)); base_sel.append(agg(s_sel))
    r_all = (sum(x[0] for x in base_all)/RAND_DRAWS, sum(x[1] for x in base_all)/RAND_DRAWS)
    r_sel = (sum(x[0] for x in base_sel)/RAND_DRAWS, sum(x[1] for x in base_sel)/RAND_DRAWS)
    print(f"  (a) 무작위 {RAND_DRAWS}회 평균 : 전체 {len(days)}일 기대 {r_all[0]:+.2f}% 승률 {r_all[1]:.1f}% "
          f"| 갈리는날만 기대 {r_sel[0]:+.2f}% 승률 {r_sel[1]:.1f}%")

    # 같은날 선택 순열 귀무분포(갈리는 날만, 기대값 기준)
    rngp = random.Random(99)
    null=[]
    for _ in range(PERM):
        s=[]
        for d in dsel: s += pick_random(BYDAY[d], K, rngp)
        null.append(agg(s)[0])
    null.sort()
    mu_null = sum(null)/len(null)

    out=[]
    for name, keyf, desc in RULES:
        rngr = random.Random(hash(name) & 0xffff)
        ev_l=[]; wr_l=[]; sel_last=None
        day_rule = defaultdict(list)   # 동점평균용 per-day 기대값
        for t in range(TIE_DRAWS):
            s=[]
            for d in dsel:
                p = pick(BYDAY[d], keyf, desc, K, rngr)
                s += p
                day_rule[d].append(sum(x["ret"] for x in p)/len(p))
            a = agg(s); ev_l.append(a[0]); wr_l.append(a[1])
        ev = sum(ev_l)/TIE_DRAWS; wr = sum(wr_l)/TIE_DRAWS
        # 전체 포트폴리오(모든 날)
        ev_all_l=[]; wr_all_l=[]
        for t in range(TIE_DRAWS):
            s=[]
            for d in days: s += pick(BYDAY[d], keyf, desc, K, rngr)
            a=agg(s); ev_all_l.append(a[0]); wr_all_l.append(a[1])
        ev_all=sum(ev_all_l)/TIE_DRAWS; wr_all=sum(wr_all_l)/TIE_DRAWS
        # 부호검정: 그날 규칙 상위K 평균 vs 그날 전체 평균(=무작위 기대)
        wpos=wneg=wtie=0
        for d in dsel:
            rm = sum(day_rule[d])/len(day_rule[d])
            dm = sum(x["ret"] for x in BYDAY[d])/len(BYDAY[d])
            if abs(rm-dm) < 1e-9: wtie+=1
            elif rm>dm: wpos+=1
            else: wneg+=1
        p_sign = binom_p(min(wpos,wneg), wpos+wneg)
        # 순열 p (양측)
        gt = sum(1 for x in null if x >= ev); lt = sum(1 for x in null if x <= ev)
        p_perm = min(1.0, 2*min(gt,lt)/PERM)
        out.append(dict(name=name, ev=ev, wr=wr, ev_all=ev_all, wr_all=wr_all,
                        d=ev-mu_null, pos=wpos, neg=wneg, tie=wtie,
                        p_sign=p_sign, p_perm=p_perm))
    out.sort(key=lambda x:-x["ev"])
    print(f"  {'규칙':<32}{'기대값':>8}{'승률':>7} | {'무작위대비':>9} | {'부호(승-패)':>12}{'p부호':>8}{'p순열':>8} | {'전체포트'}")
    for o in out:
        print(f"  {o['name']:<32}{o['ev']:>+7.2f}%{o['wr']:>6.1f}% | {o['d']:>+8.2f}%p | "
              f"{o['pos']:>5}-{o['neg']:<4}({o['tie']}무) {o['p_sign']:>7.3f}{o['p_perm']:>8.3f} | "
              f"{o['ev_all']:>+6.2f}% {o['wr_all']:.1f}%")
    return out, r_sel, mu_null

if __name__ == "__main__":
    res={}
    for K in (1,2,3,5,6):
        res[K] = run(K, DAYS, "전체기간 2025-11-27~2026-08-21")[0]
    json.dump({str(k):v for k,v in res.items()}, open("resA.json","w",encoding="utf-8"), ensure_ascii=False)
