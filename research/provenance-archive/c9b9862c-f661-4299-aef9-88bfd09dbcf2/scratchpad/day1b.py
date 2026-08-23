import json, random, statistics
from collections import defaultdict
ROOT='C:/Users/hanul/playground/my-stock/'
SP='C:/Users/hanul/AppData/Local/Temp/claude/C--Users-hanul-playground-my-stock/c9b9862c-f661-4299-aef9-88bfd09dbcf2/scratchpad/'
bt=json.load(open(ROOT+'public/data/backtest-volatility-pilot.json',encoding='utf-8'))
d1=json.load(open(SP+'day1.json',encoding='utf-8'))
key={(x['code'],x['date']):x for x in d1}
ev=[x for x in bt['events'] if x['result'] in ('win','loss')]
for x in ev:
    k=key[(x['code'],x['entry_date'])]
    x['d1']=k['d1']
byday=defaultdict(list)
for x in ev: byday[x['entry_date']].append(x)

# ---- 같은 날 안에서 첫날 종가 상/하 비교 (부호검정) ----
days=[d for d,g in byday.items() if len(g)>=4]
hi_w=hi_n=lo_w=lo_n=0; up=dn=tie=0
for d in days:
    g=sorted(byday[d],key=lambda x:-x['d1'])
    h=len(g)//2
    a=g[:h]; b=g[-h:]
    aw=sum(1 for x in a if x['result']=='win')/len(a)
    bw=sum(1 for x in b if x['result']=='win')/len(b)
    hi_w+=sum(1 for x in a if x['result']=='win'); hi_n+=len(a)
    lo_w+=sum(1 for x in b if x['result']=='win'); lo_n+=len(b)
    if aw>bw: up+=1
    elif aw<bw: dn+=1
    else: tie+=1
print(f"같은 날 안 비교 ({len(days)}일, 4건+):")
print(f"  첫날종가 상위절반 {hi_w}/{hi_n} = {100*hi_w/hi_n:.1f}%   하위절반 {lo_w}/{lo_n} = {100*lo_w/lo_n:.1f}%")
print(f"  날짜 부호검정 상위승 {up}일 / 하위승 {dn}일 / 무승부 {tie}일")
import math
def signtest(a,b):
    n=a+b
    if n==0: return 1.0
    s=sum(math.comb(n,k) for k in range(min(a,b)+1))*2/2**n
    return min(1.0,s)
print(f"  부호검정 p={signtest(up,dn):.5f}")
# 같은 날 결과 순열 (일 내 셔플) 2000회
rnd=random.Random(3)
obs=hi_w/hi_n-lo_w/lo_n
cnt=0;B=4000
for _ in range(B):
    a_w=a_n=b_w=b_n=0
    for d in days:
        g=byday[d]
        res=[x['result'] for x in g]; rnd.shuffle(res)
        gg=sorted(range(len(g)),key=lambda i:-g[i]['d1'])
        h=len(g)//2
        for i in gg[:h]:
            a_n+=1; a_w+= res[i]=='win'
        for i in gg[-h:]:
            b_n+=1; b_w+= res[i]=='win'
    if a_w/a_n-b_w/b_n >= obs: cnt+=1
print(f"  일내 결과셔플 순열 p={cnt/B:.5f} (관측 격차 {100*obs:.1f}%p)")
# 종목 블록 부트스트랩
codes=sorted(set(x['code'] for x in ev))
bycode=defaultdict(list)
for x in ev: bycode[x['code']].append(x)
rnd=random.Random(5); diffs=[]
for _ in range(2000):
    samp=[c for c in (rnd.choice(codes) for _ in codes)]
    pool=defaultdict(list)
    for i,c in enumerate(samp):
        for x in bycode[c]: pool[(x['entry_date'],i)].append(x)
    aw=an=bw=bn=0
    for k,g in pool.items(): pass
    # 종목 부트스트랩 후 날짜별 재그룹
    dd=defaultdict(list)
    for i,c in enumerate(samp):
        for x in bycode[c]: dd[x['entry_date']].append(x)
    for d,g in dd.items():
        if len(g)<4: continue
        g=sorted(g,key=lambda x:-x['d1']); h=len(g)//2
        aw+=sum(1 for x in g[:h] if x['result']=='win'); an+=h
        bw+=sum(1 for x in g[-h:] if x['result']=='win'); bn+=h
    if an and bn: diffs.append(aw/an-bw/bn)
diffs.sort()
print(f"  종목 블록 부트스트랩 격차 95%구간 {100*diffs[int(.025*len(diffs))]:.1f}%p ~ {100*diffs[int(.975*len(diffs))]:.1f}%p, 0 이하 비율 {sum(1 for v in diffs if v<=0)/len(diffs):.4f}")

# ---- 전후반 ----
for lab,sel in (('전반(~2026-03-25)',lambda d:d<='2026-03-25'),('후반(2026-03-26~)',lambda d:d>'2026-03-25')):
    aw=an=bw=bn=0
    for d in days:
        if not sel(d): continue
        g=sorted(byday[d],key=lambda x:-x['d1']); h=len(g)//2
        aw+=sum(1 for x in g[:h] if x['result']=='win'); an+=h
        bw+=sum(1 for x in g[-h:] if x['result']=='win'); bn+=h
    print(f"  {lab}: 상위 {100*aw/an:.1f}% ({an}건) vs 하위 {100*bw/bn:.1f}% ({bn}건)")

# ---- 첫날 종가 컷 시뮬 ----
print("\n=== 첫날 종가에서 손절(매수가 아래면 정리) 시뮬 ===")
allr=[x['gain_at_resolve_pct'] for x in ev]
print(f"  그대로 보유: {len(ev)}건 평균 {statistics.mean(allr):+.2f}% 승률 {100*sum(1 for x in ev if x['result']=='win')/len(ev):.1f}%")
for cut in (0,-1,-2,-3):
    r=[]
    kept=0
    for x in ev:
        if x['d1']<cut: r.append(x['d1'])
        else: r.append(x['gain_at_resolve_pct']); kept+=1
    print(f"  첫날 종가 {cut:+d}% 미만이면 당일 정리: 평균 {statistics.mean(r):+.2f}%  (계속 보유 {kept}건 / 정리 {len(ev)-kept}건)")
# 전멸일에 적용하면?
rows=json.load(open(SP+'daytab.json',encoding='utf-8'))
zd=set(r['date'] for r in rows if r['n']>=4 and r['w']==0)
z=[x for x in ev if x['entry_date'] in zd]
print(f"  전멸일 84건: 그대로 보유 평균 {statistics.mean([x['gain_at_resolve_pct'] for x in z]):+.2f}%  → 첫날컷 적용 평균 {statistics.mean([x['d1'] if x['d1']<0 else x['gain_at_resolve_pct'] for x in z]):+.2f}%")
